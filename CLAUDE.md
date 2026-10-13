# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate the existing venv (Windows)
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the full test suite
pytest
pytest -v

# Run a single test file / test
pytest tests/todoist/test_tasks.py
pytest tests/todoist/test_tasks.py::test_create_task_success -v

# Run the FastAPI webhook server (app.py)
uvicorn app:app --port 8000
# Swagger UI: http://127.0.0.1:8000/docs

# Run the MCP server directly (normally launched by Claude Desktop over STDIO)
python -m plugvan.todoist

# Create tasks with the standalone CLI (main.py)
python main.py --file tasks_sample.json
python main.py --json '[{"content": "Task", "due_string": "today", "priority": 2}]'

# Google Tasks -> Todoist sync service
python sync_worker.py                    # one-shot
python sync_worker.py --watch --interval 15   # continuous watching (polling)

# Webhook client (sends a JSON file to a running app.py instance)
python send_to_bridge.py --file tasks_sample.json

# Docker (runs sync_worker.py once by default)
docker build -t todoist-bridge .
docker run --env-file .env todoist-bridge
```

There is no configured linter/formatter in this repo (no ruff/black/mypy config) — do not act as if there were one.

Required environment variables (`.env`, see `.env.example`): `TODOIST_API_TOKEN`, `WEBHOOK_SECRET_TOKEN`, optional `ALLOWED_ORIGINS` (CORS, default `*`). They are loaded through the Pydantic `Settings` in `config.py`. The sync worker additionally needs a Google OAuth `credentials.json` (Desktop Client) file in the repo root; `token.json` is created automatically on first authentication. For serverless/ephemeral environments, both can be supplied via the `GOOGLE_CREDENTIALS_JSON` / `GOOGLE_TOKEN_JSON` environment variables.

## Architecture

This project is not a single application but a Python toolkit made of **four independent entry points that all go through the same validation/task-creation core**:

- `plugvan.todoist` (the `plugvan/todoist/` package, `python -m plugvan.todoist`) — the tool surface exposed to Claude Desktop; a FastMCP server running over STDIO. It is self-contained: it talks to Todoist not through `todoist_client.py` but directly through the official `todoist-api-python` SDK, and has its own name-resolution/validation logic.
- `app.py` — FastAPI REST server (webhook target for automations such as n8n/Make). Authentication is done with a constant-time (`secrets.compare_digest`) comparison of the `X-Bridge-Token` header.
- `main.py` — a CLI tool run directly; it also exports the `build_project_map` / `resolve_project_id` functions, which `app.py` imports and reuses for its own project-name resolution.
- `sync_worker.py` — an OAuth 2.0 service that pulls tasks from Google Tasks, transforms each item with `parse_google_task`, sends it to Todoist, and deletes the successfully created tasks from the source Google Task.

### Shared core (used by `main.py`, `app.py`, `sync_worker.py`)

- `models.py` — `TaskPayload` (single task) and `BatchTaskPayload` (`tasks: List[TaskPayload]`, maximum 50) are the Pydantic schemas everything is validated against. `project_name` defaults to `"Odak & Gelişim"`; `priority` ranges from 1 (normal) to 4 (urgent) — note: Todoist's own API and `sync_worker.py`'s tag parser (`p1`=urgent..`p4`=normal) invert this scale, which is why the priority mapping is done explicitly in `parse_google_task`.
- `parser.py` — `parse_tasks_from_json` strips markdown code fences (` ```json ... ``` `) from raw LLM output, then accepts three JSON shapes: a plain list, `{"tasks": [...]}`, or a single task object. Raises `TaskParseError` on failure.
- `todoist_client.py` — a thin `requests` wrapper over the Todoist REST API v1 (used by `main.py`, `app.py`, `sync_worker.py`; NOT used by `plugvan.todoist`, which uses the SDK). It raises typed exceptions that `app.py`'s FastAPI exception handlers map to HTTP responses (`TodoistAuthError` 401, `TodoistValidationError` 400, `TodoistServerError` 5xx, with `TodoistAPIError` as the base class). `create_task` accepts both keyword arguments and a `TaskPayload`/dict as the first positional argument.
- Project-name resolution is deliberately duplicated in three places with the same case-insensitive/Unicode-normalized logic: `main.py::resolve_project_id` (dict lookup), `todoist_client.py::resolve_project_name` (Todoist REST), and `plugvan/todoist/resolvers.py::resolve_project` (SDK; additionally with Inbox alias, single-candidate partial match and ambiguity layers). The difference in behavior is deliberate: MCP tools return an error on an unknown name, while the CLI/webhook/sync worker fall back to the Inbox. When touching the resolution logic, check whether the change needs to be applied to all three.

### `plugvan.todoist` internals

The top-level `plugvan/` package is empty (no multi-app server code yet); the Todoist integration lives under `plugvan/todoist/`:
- `server.py` — the `FastMCP("Todoist")` object; the 22 tools are registered here explicitly with `mcp.add_tool(...)` **in a fixed order** (the order is part of the published surface, do not change it).
- `tools/` — one module per domain (`tasks`, `projects`, `sections`, `labels`, `comments`); tools are plain functions without decorators. The deadline/HTTP error helpers live only in `tasks.py`.
- `client.py` — `get_api_client()`; builds a `TodoistAPI` from `TODOIST_API_TOKEN` on every call. Tools call it through the module attribute (`client.get_api_client()`), so in tests the **single patch target** is `plugvan.todoist.client.get_api_client`.
- `limits.py` — the `MAX_*_LENGTH` constants. `resolvers.py` — `resolve_project` / `resolve_section` / `resolve_label`, four result types (`Found`, `NotFound`, `Ambiguous`, `LookupFailed`), `ambiguous_message`, `_normalize`.
- `__main__.py` — the entry point: `load_dotenv()` and `logging.basicConfig(...)` run only here. The logger name is `"todoist_mcp"` in all modules.

Import side effects: our modules have no import side effects. However, when `server.py` is imported, the SDK's `FastMCP()` constructor adds a log handler (`RichHandler`) to the root logger; this comes from the SDK, not from our code.

Each tool independently:
1. Validates inputs against the `MAX_*_LENGTH` constants in `limits.py`.
2. Resolves human-readable names to IDs with `resolve_project` / `resolve_section` / `resolve_label` (including Turkish-aware normalization via `_normalize`). Each resolution returns one of four results and the tool handles each one separately; nothing is written in the failure cases:
   - `Found(id, name)`: a single match; messages show `name` (the actual name in Todoist), not the user's input. `id=None` only happens when the Inbox alias is used while there is no Inbox in the list.
   - `NotFound(query)`: a `⚠️ … bulunamadı` message, no candidate list.
   - `Ambiguous(query, candidates, has_more)`: via `ambiguous_message`, at most 5 `name (ID)` candidates and a suggestion to use the ID.
   - `LookupFailed(error_type)`: the tool's generic `❌ … Check server logs` message; only `error_type` is written to the log, never the exception text or the HTTP response.

   Matching rules vary by tool:
   - Project, in destructive tools (`delete_project`, `update_project`): ID or exact name only.
   - Project, in `update_section`'s project scope: ID → Inbox alias → exact name.
   - Project, in other tools (`create_task`, `update_task`, `create_project` parent project, `create_section`, `list_sections`): ID → Inbox alias → exact name → partial match only if there is a single candidate.
   - Section, everywhere: ID or exact name only, no partial match. In task tools it is searched only within the resolved project; in `update_task`, if no project is given, within the task's current project.
   - Label: a leading `@` is stripped; ID or exact name only. Two labels that differ only in letter case are ambiguous.
   - `create_task`/`update_task` validate the target first, then write.
3. Calls the Todoist SDK through the `TodoistAPI` built by `client.get_api_client()`.

The decision to give tool names an application prefix (such as `todoist_create_task`) was postponed: it will be done later with the standalone `fastmcp`'s `mount(server, namespace=...)` feature, without changing code. This requires moving from the SDK's FastMCP to the standalone `fastmcp`; therefore do not remove the `fastmcp` dependency from `requirements.txt`.

### `sync_worker.py` tag syntax

`parse_google_task` extracts structured fields from free-text Google Task titles/notes with regexes in this order: priority (`p[1-4]`), due date (`@today`, `@tomorrow at 15:00`, ...), project (`[Project Name]` or `#Project Name`), then an inline time pulled from the notes and combined with Google's `due` date into an ISO `due_datetime` (`Saat: HH:MM` or a bare `HH:MM`). The text left after tag extraction becomes `content`.

### Tests

`tests/` mirrors the module structure and mocks all network/API calls — no real Todoist or Google calls are made.
- `tests/todoist/` — the `plugvan.todoist` tests, mirroring the package one-to-one: `test_tasks.py`, `test_projects.py`, `test_sections.py`, `test_labels.py`, `test_comments.py`, `test_resolvers.py`, `test_server_surface.py`. It has its own `__init__.py` (imported as `tests.todoist`).
- `tests/todoist/helpers.py` — lightweight `MockProject`/`MockLabel`/`MockSection`/`MockComment`/`MockTask` classes that mirror the SDK's object attributes instead of mocking the SDK client wholesale, `_make_http_status_error`, and `write_call_count` (counts all write calls on the mocked SDK; every public method other than `get_`/`filter_`/`search_` counts as a write). Because it does not start with `test_`, pytest does not collect it.
- The others are at the root: `test_api.py`, `test_models.py`, `test_parser.py`, `test_todoist_client.py`, `test_project_resolution.py`.

**Surface snapshot rule:** `tests/fixtures/todoist_mcp_tool_surface.json` is a one-time recording of the MCP tool surface (22 tools: name, description, `inputSchema`, `outputSchema`) taken from the old module before the move; `test_server_surface.py` compares the live server against it by name (order-independent). The fixture is **never regenerated** unless there is a deliberate behavior change; changing a tool's description/parameter breaks the test, and updating the fixture means knowingly accepting that change.

## Language

All commit messages, PR titles and bodies, issue titles and bodies, review comments, CHANGELOG entries and in-repo documentation are written in English, regardless of the language used in chat with the maintainer. The only exception is README.tr.md, the Turkish translation of README.md, which is maintained as a user-facing second language.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues (`kagankurubas/plugvan`) and managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The default five labels are used: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: a single `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
