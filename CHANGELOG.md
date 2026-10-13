# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- The Todoist MCP server moved from the single-file `todoist_mcp.py` into
  the `plugvan.todoist` package (server, client, limits, resolvers, and one
  tools module per domain). No behavior change: same 22 tools, names,
  descriptions and schemas.
- Entry point is now `python -m plugvan.todoist` (the old script is removed,
  no shim).
- Tests patch a single target: `plugvan.todoist.client.get_api_client`
  (renamed from the private helper). MCP tests now live in `tests/todoist/`.
- **Action required:** Claude Desktop configs that run the old
  `todoist_mcp.py` path must be updated to `"args": ["-m", "plugvan.todoist"]`
  with `"PYTHONPATH": "<REPO_PATH>"` in `env`, then restart Claude Desktop.

### Added
- MCP tool surface snapshot test: all 22 tools' name, description,
  input and output schema are compared against a fixture recorded before
  the move. Suite: 181 → 183.
- `update_section` MCP tool: rename a Todoist section by ID or name.
  Optional `project_name_or_id` scopes name resolution so same-named
  sections in different projects can't be confused.
- 9 tests for `update_section` (rename by name/ID, project scoping,
  not-found, empty/too-long input, sanitized error). Suite: 172 → 181.

### Backlog
- `update_section`: expose `order` and `collapsed` (supported by the SDK).
- `project_move`: needs the Sync API's separate command.
