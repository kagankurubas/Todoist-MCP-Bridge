"""Name/ID resolution helpers for Todoist projects, labels and sections."""

import logging
from typing import Optional

from todoist_api_python.api import TodoistAPI

logger = logging.getLogger("todoist_mcp")


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
