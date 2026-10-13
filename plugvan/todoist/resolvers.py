"""Name/ID resolution helpers for Todoist projects, labels and sections.

`resolve_project` / `resolve_section` / `resolve_label` return exactly one of four
outcomes: `Found`, `NotFound`, `Ambiguous` or `LookupFailed`. The older
`_resolve_*` / `_find_project_id` helpers further down are compatibility wrappers
that keep the previous first-wins behavior for existing tools until they migrate.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Union

from todoist_api_python.api import TodoistAPI

logger = logging.getLogger("todoist_mcp")

MAX_AMBIGUOUS_CANDIDATES = 5
INBOX_ALIASES = frozenset({"gelen kutusu", "inbox", "gelenkutusu", "inbox/gelen kutusu"})
INBOX_DISPLAY_NAME = "Gelen Kutusu"


@dataclass(frozen=True)
class Candidate:
    """One possible match in an ambiguous resolution."""

    id: str
    name: str

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"


@dataclass(frozen=True)
class Found:
    """Exactly one match. `id` is None only for an Inbox alias when no Inbox project is
    listed; the caller then omits project_id and Todoist uses the Inbox."""

    id: Optional[str]
    name: str


@dataclass(frozen=True)
class NotFound:
    """No candidate matched the cleaned query."""

    query: str


@dataclass(frozen=True)
class Ambiguous:
    """More than one candidate matched; at most MAX_AMBIGUOUS_CANDIDATES are kept, in list order."""

    query: str
    candidates: tuple[Candidate, ...]
    has_more: bool

    def candidate_lines(self) -> list[str]:
        lines = [str(candidate) for candidate in self.candidates]
        if self.has_more:
            lines.append("…")
        return lines


@dataclass(frozen=True)
class LookupFailed:
    """Listing from the Todoist API raised. Carries the exception type only, never its message."""

    error_type: str


Resolution = Union[Found, NotFound, Ambiguous, LookupFailed]


def _normalize(text: str) -> str:
    """Normalizes string for robust case-insensitive comparison (supporting Turkish and Unicode chars)."""
    return text.strip().lower().replace("ı", "i").replace("İ", "i").replace("i̇", "i")


def _get_all_projects(api: TodoistAPI) -> list:
    """Retrieves all projects from Todoist API across batches."""
    projects = []
    for batch in api.get_projects():
        projects.extend(batch)
    return projects


def _get_all_labels(api: TodoistAPI) -> list:
    """Retrieves all labels from Todoist API across batches."""
    labels = []
    for batch in api.get_labels():
        labels.extend(batch)
    return labels


def _get_all_sections(api: TodoistAPI, project_id: Optional[str] = None) -> list:
    """Retrieves sections from Todoist API across batches."""
    sections = []
    kwargs = {}
    if project_id:
        kwargs["project_id"] = project_id
    for batch in api.get_sections(**kwargs):
        sections.extend(batch)
    return sections


def _pick(query: str, matches: list) -> Optional[Resolution]:
    """Turns the matches of one resolution step into Found / Ambiguous, or None to continue."""
    if not matches:
        return None
    if len(matches) == 1:
        return Found(str(matches[0].id), getattr(matches[0], "name", ""))
    candidates = tuple(
        Candidate(str(item.id), getattr(item, "name", "")) for item in matches[:MAX_AMBIGUOUS_CANDIDATES]
    )
    return Ambiguous(query, candidates, has_more=len(matches) > MAX_AMBIGUOUS_CANDIDATES)


def _lookup_failed(kind: str, e: Exception) -> LookupFailed:
    logger.error(
        "Failed to retrieve %s for resolution (error_type=%s)",
        kind,
        type(e).__name__,
        exc_info=False,
    )
    return LookupFailed(type(e).__name__)


def _match_id_then_exact(items: list, query: str) -> Optional[Resolution]:
    by_id = _pick(query, [item for item in items if str(getattr(item, "id", "")) == query])
    if by_id:
        return by_id
    normalized = _normalize(query)
    return _pick(query, [item for item in items if _normalize(getattr(item, "name", "")) == normalized])


def resolve_project(
    api: TodoistAPI,
    name_or_id: str,
    *,
    allow_partial: bool = False,
    allow_inbox_alias: bool = False,
) -> Resolution:
    """Resolves a project: ID → Inbox alias (if allowed) → exact name → partial (if allowed).

    Each step returns as soon as it has a match; several matches in one step are Ambiguous.
    An Inbox alias always resolves: to the Inbox project, or Found(None, ...) if none is listed.
    """
    query = name_or_id.strip() if isinstance(name_or_id, str) else ""
    if not query:
        return NotFound("")

    try:
        projects = _get_all_projects(api)
    except Exception as e:
        return _lookup_failed("projects", e)

    by_id = _pick(query, [p for p in projects if str(getattr(p, "id", "")) == query])
    if by_id:
        return by_id

    normalized = _normalize(query)
    if allow_inbox_alias and normalized in INBOX_ALIASES:
        inbox = _pick(query, [p for p in projects if getattr(p, "is_inbox_project", False)])
        if inbox:
            return inbox
        alias_named = _pick(query, [p for p in projects if _normalize(getattr(p, "name", "")) in INBOX_ALIASES])
        return alias_named or Found(None, INBOX_DISPLAY_NAME)

    exact = _pick(query, [p for p in projects if _normalize(getattr(p, "name", "")) == normalized])
    if exact:
        return exact

    if allow_partial:
        partial = _pick(query, [p for p in projects if normalized in _normalize(getattr(p, "name", ""))])
        if partial:
            return partial

    return NotFound(query)


def resolve_section(api: TodoistAPI, name_or_id: str, *, project_id: Optional[str] = None) -> Resolution:
    """Resolves a section by ID or exact name only (never partially).

    With project_id, only sections of that project are candidates.
    """
    query = name_or_id.strip() if isinstance(name_or_id, str) else ""
    if not query:
        return NotFound("")

    try:
        sections = _get_all_sections(api, project_id=project_id)
    except Exception as e:
        return _lookup_failed("sections", e)

    if project_id:
        sections = [s for s in sections if str(getattr(s, "project_id", project_id)) == str(project_id)]

    return _match_id_then_exact(sections, query) or NotFound(query)


def resolve_label(api: TodoistAPI, name_or_id: str) -> Resolution:
    """Resolves a label by ID or exact name (leading '@' stripped); no partial matching."""
    query = name_or_id.strip().lstrip("@") if isinstance(name_or_id, str) else ""
    if not query:
        return NotFound("")

    try:
        labels = _get_all_labels(api)
    except Exception as e:
        return _lookup_failed("labels", e)

    return _match_id_then_exact(labels, query) or NotFound(query)


# ---------------------------------------------------------------------
# Compatibility wrappers: previous first-wins behavior, kept unchanged for
# tools that have not migrated to resolve_* yet. Remove once unused (#14).
# ---------------------------------------------------------------------

def _find_project_id(api: TodoistAPI, project_name: str) -> Optional[str]:
    """Resolves matching Todoist project ID by project name."""
    project_id, _ = _resolve_project(api, project_name)
    return project_id


def _resolve_project(api: TodoistAPI, name_or_id: str) -> tuple[Optional[str], Optional[str]]:
    """Resolves project ID and display name from either a project ID or project name.

    Returns:
        tuple[Optional[str], Optional[str]]: (project_id, project_name) or (None, None)
    """
    clean_identifier = name_or_id.strip() if isinstance(name_or_id, str) else ""
    if not clean_identifier:
        return None, None

    try:
        projects = _get_all_projects(api)
    except Exception as e:
        logger.error(
            "Failed to retrieve projects list for project resolution (error_type=%s)",
            type(e).__name__,
            exc_info=False,
        )
        return None, None

    # 1. Direct ID match
    for project in projects:
        if str(getattr(project, "id", "")) == clean_identifier:
            return str(project.id), getattr(project, "name", "Bilinmeyen Proje")

    # 2. Inbox query alias check
    normalized_target = _normalize(clean_identifier)
    inbox_aliases = ["gelen kutusu", "inbox", "gelenkutusu", "inbox/gelen kutusu"]
    if normalized_target in inbox_aliases:
        for project in projects:
            if getattr(project, "is_inbox_project", False):
                return str(project.id), getattr(project, "name", "Gelen Kutusu")
            if _normalize(getattr(project, "name", "")) in inbox_aliases:
                return str(project.id), getattr(project, "name", "Gelen Kutusu")

    # 3. Exact name match
    for project in projects:
        if _normalize(getattr(project, "name", "")) == normalized_target:
            return str(project.id), getattr(project, "name", "")

    # 4. Partial name match
    for project in projects:
        if normalized_target in _normalize(getattr(project, "name", "")):
            return str(project.id), getattr(project, "name", "")

    return None, None


def _resolve_label(api: TodoistAPI, name_or_id: str) -> tuple[Optional[str], Optional[str]]:
    """Resolves label ID and name from either ID or name.

    Returns:
        tuple[Optional[str], Optional[str]]: (label_id, label_name) or (None, None)
    """
    clean_identifier = name_or_id.strip().lstrip("@") if isinstance(name_or_id, str) else ""
    if not clean_identifier:
        return None, None

    try:
        labels = _get_all_labels(api)
    except Exception as e:
        logger.error(
            "Failed to retrieve labels for resolution (error_type=%s)",
            type(e).__name__,
            exc_info=False,
        )
        return None, None

    # 1. Direct ID match
    for label in labels:
        if str(getattr(label, "id", "")) == clean_identifier:
            return str(label.id), getattr(label, "name", "")

    # 2. Exact name match
    normalized = _normalize(clean_identifier)
    for label in labels:
        if _normalize(getattr(label, "name", "")) == normalized:
            return str(label.id), getattr(label, "name", "")

    return None, None


def _resolve_section(api: TodoistAPI, name_or_id: str, project_id: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """Resolves section ID and name from either ID or name.

    Returns:
        tuple[Optional[str], Optional[str]]: (section_id, section_name) or (None, None)
    """
    clean_identifier = name_or_id.strip() if isinstance(name_or_id, str) else ""
    if not clean_identifier:
        return None, None

    try:
        sections = _get_all_sections(api, project_id=project_id)
    except Exception as e:
        logger.error(
            "Failed to retrieve sections for resolution (error_type=%s)",
            type(e).__name__,
            exc_info=False,
        )
        return None, None

    # 1. Direct ID match
    for section in sections:
        if str(getattr(section, "id", "")) == clean_identifier:
            return str(section.id), getattr(section, "name", "")

    # 2. Exact name match
    normalized = _normalize(clean_identifier)
    for section in sections:
        if _normalize(getattr(section, "name", "")) == normalized:
            return str(section.id), getattr(section, "name", "")

    return None, None
