"""Todoist project tools."""

import logging
from typing import Annotated, Optional

from pydantic import Field

from plugvan.todoist import client
from plugvan.todoist.limits import (
    MAX_PROJECT_NAME_LENGTH,
    MAX_TASK_ID_LENGTH,
    MAX_COLOR_LENGTH,
)
from plugvan.todoist.resolvers import (
    _get_all_projects,
    _resolve_project,
)

logger = logging.getLogger("todoist_mcp")


def list_projects() -> str:
    """Lists all user projects in Todoist with their hierarchy (nested/subprojects), names, IDs, and details."""
    try:
        api = client.get_api_client()
        projects = _get_all_projects(api)

        if not projects:
            return "ℹ️ Todoist hesabınızda herhangi bir proje bulunamadı."

        children_map: dict[Optional[str], list] = {}
        all_ids = {str(getattr(p, "id", "")) for p in projects}

        for project in projects:
            parent_id = str(project.parent_id) if getattr(project, "parent_id", None) else None
            if parent_id not in all_ids:
                parent_id = None
            children_map.setdefault(parent_id, []).append(project)

        lines = [f"📁 Mevcut Projeler (Toplam: {len(projects)}):", ""]

        def format_project_tree(parent_id: Optional[str], depth: int = 0, counter: list[int] = None):
            if counter is None:
                counter = [1]
            for project in children_map.get(parent_id, []):
                is_inbox = " [Gelen Kutusu]" if getattr(project, "is_inbox_project", False) else ""
                is_fav = " ⭐" if getattr(project, "is_favorite", False) else ""
                color_info = f", Renk: {project.color}" if getattr(project, "color", None) else ""
                
                if depth == 0:
                    prefix = f"{counter[0]}. "
                    counter[0] += 1
                else:
                    prefix = "   " * depth + "└── "

                lines.append(f"{prefix}[{project.id}] {project.name}{is_inbox}{is_fav}{color_info}")
                if getattr(project, "url", None):
                    url_indent = "   " * (depth + 1)
                    lines.append(f"{url_indent}• URL: {project.url}")

                format_project_tree(str(project.id), depth + 1, counter)

        format_project_tree(None, depth=0)

        return "\n".join(lines).strip()
    except Exception as e:
        logger.error(
            "Failed to list projects from Todoist (error_type=%s)",
            type(e).__name__,
            exc_info=False,
        )
        return "❌ Failed to list projects from Todoist. Check server logs for details."


def get_project(
    project_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_TASK_ID_LENGTH,
            description="The Todoist Project ID to retrieve (required).",
        ),
    ],
) -> str:
    """Retrieves a single Todoist project by its ID, showing all its fields (name, color, parent_id, favorite status, view style).

    Args:
        project_id: The ID of the Todoist project to retrieve (max 100 chars).
    """
    clean_project_id = str(project_id).strip() if project_id is not None else ""
    if not clean_project_id:
        return "❌ Invalid input: Project ID cannot be empty or whitespace."
    if len(clean_project_id) > MAX_TASK_ID_LENGTH:
        return f"❌ Invalid input: Project ID exceeds maximum length of {MAX_TASK_ID_LENGTH} characters."

    try:
        api = client.get_api_client()
        project = api.get_project(project_id=clean_project_id)

        color_display = project.color if getattr(project, "color", None) else "Yok"
        parent_display = project.parent_id if getattr(project, "parent_id", None) else "Yok (üst seviye proje)"
        favorite_display = "Evet" if getattr(project, "is_favorite", False) else "Hayır"
        view_style_display = getattr(project, "view_style", None) or "Belirlenmedi"

        return (
            f"📁 Proje Detayları (ID: {project.id})\n"
            f"• İsim: {project.name}\n"
            f"• Renk: {color_display}\n"
            f"• Üst Proje ID (parent_id): {parent_display}\n"
            f"• Favori mi: {favorite_display}\n"
            f"• Görünüm Stili: {view_style_display}\n"
            f"• URL: {project.url}"
        )
    except Exception as e:
        logger.error(
            "Failed to retrieve project from Todoist (project_id=%s, error_type=%s)",
            clean_project_id,
            type(e).__name__,
            exc_info=False,
        )
        return f"❌ Failed to retrieve project from Todoist (ID: {clean_project_id}). Check server logs for details."


def create_project(
    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_PROJECT_NAME_LENGTH,
            description="The name of the new project (required).",
        ),
    ],
    parent_project_name_or_id: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_PROJECT_NAME_LENGTH,
            description="Parent project name or ID to create this project as a nested subproject (optional).",
        ),
    ] = None,
    color: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_COLOR_LENGTH,
            description="Color name for the project icon (e.g. 'berry_red', 'charcoal', 'teal', optional).",
        ),
    ] = None,
) -> str:
    """Creates a new project or subproject in Todoist.

    Args:
        name: Name of the project (must not be empty, max 120 chars).
        parent_project_name_or_id: Optional parent project name or ID to create as a nested subproject.
        color: Optional color name (e.g. 'berry_red', 'sky_blue', 'mint_green').
    """
    clean_name = name.strip() if isinstance(name, str) else ""
    if not clean_name:
        return "❌ Invalid input: Project name cannot be empty or whitespace."
    if len(clean_name) > MAX_PROJECT_NAME_LENGTH:
        return f"❌ Invalid input: Project name exceeds maximum length of {MAX_PROJECT_NAME_LENGTH} characters."

    clean_parent = parent_project_name_or_id.strip() if isinstance(parent_project_name_or_id, str) else None
    if clean_parent and len(clean_parent) > MAX_PROJECT_NAME_LENGTH:
        return f"❌ Invalid input: Parent project identifier exceeds maximum length of {MAX_PROJECT_NAME_LENGTH} characters."

    clean_color = color.strip().lower() if isinstance(color, str) else None
    if clean_color and len(clean_color) > MAX_COLOR_LENGTH:
        return f"❌ Invalid input: Color name exceeds maximum length of {MAX_COLOR_LENGTH} characters."

    try:
        api = client.get_api_client()
        kwargs = {}
        parent_display = ""

        if clean_parent:
            parent_id, parent_name = _resolve_project(api, clean_parent)
            if not parent_id:
                return f"⚠️ Belirtilen üst proje bulunamadı: '{clean_parent}'."
            kwargs["parent_id"] = parent_id
            parent_display = f"\n• Üst Proje: '{parent_name}' (ID: {parent_id})"

        if clean_color:
            kwargs["color"] = clean_color

        project = api.add_project(name=clean_name, **kwargs)

        color_str = f"\n• Renk: {project.color}" if getattr(project, "color", None) else ""
        url_str = f"\n• URL: {project.url}" if getattr(project, "url", None) else ""

        return (
            f"✅ Proje başarıyla oluşturuldu!\n"
            f"• ID: {project.id}\n"
            f"• İsim: {project.name}"
            f"{parent_display}"
            f"{color_str}"
            f"{url_str}"
        )
    except Exception as e:
        logger.error(
            "Failed to create project in Todoist (name=%s, error_type=%s)",
            clean_name,
            type(e).__name__,
            exc_info=False,
        )
        return f"❌ Failed to create project '{clean_name}' in Todoist. Check server logs for details."


def update_project(
    project_name_or_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_PROJECT_NAME_LENGTH,
            description="The Todoist Project ID or Project Name to update (required).",
        ),
    ],
    name: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_PROJECT_NAME_LENGTH,
            description="New name for the project (optional).",
        ),
    ] = None,
    color: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_COLOR_LENGTH,
            description="New color name for the project icon (e.g. 'berry_red', 'charcoal', 'teal', optional).",
        ),
    ] = None,
) -> str:
    """Updates an existing Todoist project's name or color.

    Note: Todoist's API does not support changing a project's parent through this
    endpoint (there is no move/reparent operation for projects), so this tool only
    updates name and color.

    Args:
        project_name_or_id: The ID or name of the project to update (required).
        name: New name for the project (max 120 chars).
        color: New color name for the project icon (e.g. 'berry_red', 'sky_blue', 'mint_green').
    """
    clean_identifier = str(project_name_or_id).strip() if project_name_or_id is not None else ""
    if not clean_identifier:
        return "❌ Invalid input: Project identifier cannot be empty or whitespace."
    if len(clean_identifier) > MAX_PROJECT_NAME_LENGTH:
        return f"❌ Invalid input: Project identifier exceeds maximum length of {MAX_PROJECT_NAME_LENGTH} characters."

    clean_name = name.strip() if isinstance(name, str) else None
    if clean_name is not None and not clean_name:
        return "❌ Invalid input: New project name cannot be empty or whitespace."
    if clean_name is not None and len(clean_name) > MAX_PROJECT_NAME_LENGTH:
        return f"❌ Invalid input: New project name exceeds maximum length of {MAX_PROJECT_NAME_LENGTH} characters."

    clean_color = color.strip().lower() if isinstance(color, str) else None
    if clean_color and len(clean_color) > MAX_COLOR_LENGTH:
        return f"❌ Invalid input: Color name exceeds maximum length of {MAX_COLOR_LENGTH} characters."

    if clean_name is None and clean_color is None:
        return "⚠️ Güncellenecek hiçbir alan belirtilmedi. Lütfen name veya color parametresi girin."

    try:
        api = client.get_api_client()
        project_id, old_name = _resolve_project(api, clean_identifier)

        if not project_id:
            return f"⚠️ Güncellenecek proje bulunamadı: '{clean_identifier}'."

        kwargs = {}
        updated_fields = []
        if clean_name is not None:
            kwargs["name"] = clean_name
            updated_fields.append(f"İsim: '{clean_name}'")
        if clean_color is not None:
            kwargs["color"] = clean_color
            updated_fields.append(f"Renk: '{clean_color}'")

        api.update_project(project_id=project_id, **kwargs)

        changes_summary = "\n".join([f"• {field}" for field in updated_fields])
        return (
            f"✅ Proje başarıyla güncellendi (ID: {project_id})!\n"
            f"Yapılan değişiklikler:\n"
            f"{changes_summary}"
        )
    except Exception as e:
        logger.error(
            "Failed to update project in Todoist (identifier=%s, error_type=%s)",
            clean_identifier,
            type(e).__name__,
            exc_info=False,
        )
        return f"❌ Failed to update project '{clean_identifier}' in Todoist. Check server logs for details."


def delete_project(
    project_name_or_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_PROJECT_NAME_LENGTH,
            description="The Todoist Project ID or Project Name to delete (required).",
        ),
    ],
) -> str:
    """Deletes a project from Todoist by either its ID or project name.

    Args:
        project_name_or_id: The ID or name of the project to delete.
    """
    clean_identifier = str(project_name_or_id).strip() if project_name_or_id is not None else ""
    if not clean_identifier:
        return "❌ Invalid input: Project identifier cannot be empty or whitespace."
    if len(clean_identifier) > MAX_PROJECT_NAME_LENGTH:
        return f"❌ Invalid input: Project identifier exceeds maximum length of {MAX_PROJECT_NAME_LENGTH} characters."

    try:
        api = client.get_api_client()
        project_id, project_name = _resolve_project(api, clean_identifier)

        if not project_id:
            return f"⚠️ Silinecek proje bulunamadı: '{clean_identifier}'."

        success = api.delete_project(project_id=project_id)
        display_name = f"'{project_name}' (ID: {project_id})" if project_name else f"ID: {project_id}"

        if success:
            return f"🗑️ Proje başarıyla silindi: {display_name}."
        else:
            return f"⚠️ Proje silinemedi: {display_name}."
    except Exception as e:
        logger.error(
            "Failed to delete project in Todoist (identifier=%s, error_type=%s)",
            clean_identifier,
            type(e).__name__,
            exc_info=False,
        )
        return f"❌ Failed to delete project '{clean_identifier}' in Todoist. Check server logs for details."
