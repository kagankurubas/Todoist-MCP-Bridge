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
from plugvan.todoist.messages import MissingMessageError, message
from plugvan.todoist.resolvers import (
    Ambiguous,
    LookupFailed,
    NotFound,
    _get_all_projects,
    ambiguous_message,
    resolve_project,
)

logger = logging.getLogger("todoist_mcp")


def list_projects() -> str:
    """Lists all user projects in Todoist with their hierarchy (nested/subprojects), names, IDs, and details."""
    try:
        api = client.get_api_client()
        projects = _get_all_projects(api)

        if not projects:
            return message("project.list.empty")

        children_map: dict[Optional[str], list] = {}
        all_ids = {str(getattr(p, "id", "")) for p in projects}

        for project in projects:
            parent_id = str(project.parent_id) if getattr(project, "parent_id", None) else None
            if parent_id not in all_ids:
                parent_id = None
            children_map.setdefault(parent_id, []).append(project)

        lines = [message("project.list.header", count=len(projects)), ""]

        def format_project_tree(parent_id: Optional[str], depth: int = 0, counter: list[int] = None):
            if counter is None:
                counter = [1]
            for project in children_map.get(parent_id, []):
                is_inbox = message("inbox.marker") if getattr(project, "is_inbox_project", False) else ""
                is_fav = " ⭐" if getattr(project, "is_favorite", False) else ""
                color_info = message("project.list.color_suffix", color=project.color) if getattr(project, "color", None) else ""
                
                if depth == 0:
                    prefix = f"{counter[0]}. "
                    counter[0] += 1
                else:
                    prefix = "   " * depth + "└── "

                lines.append(f"{prefix}[{project.id}] {project.name}{is_inbox}{is_fav}{color_info}")
                if getattr(project, "url", None):
                    url_indent = "   " * (depth + 1)
                    lines.append(message("project.list.url_line", indent=url_indent, url=project.url))

                format_project_tree(str(project.id), depth + 1, counter)

        format_project_tree(None, depth=0)

        return "\n".join(lines).strip()
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to list projects from Todoist (error_type=%s)",
            type(e).__name__,
            exc_info=False,
        )
        return message("project.list_failed")


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
        return message("invalid.project_id_empty")
    if len(clean_project_id) > MAX_TASK_ID_LENGTH:
        return message("invalid.project_id_too_long", limit=MAX_TASK_ID_LENGTH)

    try:
        api = client.get_api_client()
        project = api.get_project(project_id=clean_project_id)

        color_display = project.color if getattr(project, "color", None) else message("project.detail.none")
        parent_display = project.parent_id if getattr(project, "parent_id", None) else message("project.detail.no_parent")
        favorite_display = message("project.detail.yes") if getattr(project, "is_favorite", False) else message("project.detail.no")
        view_style_display = getattr(project, "view_style", None) or message("project.detail.not_set")

        return message(
            "project.detail",
            id=project.id,
            name=project.name,
            color=color_display,
            parent=parent_display,
            favorite=favorite_display,
            view_style=view_style_display,
            url=project.url,
        )
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve project from Todoist (project_id=%s, error_type=%s)",
            clean_project_id,
            type(e).__name__,
            exc_info=False,
        )
        return message("project.get_failed", id=clean_project_id)


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
        return message("invalid.project_name_empty")
    if len(clean_name) > MAX_PROJECT_NAME_LENGTH:
        return message("invalid.project_name_too_long", limit=MAX_PROJECT_NAME_LENGTH)

    clean_parent = parent_project_name_or_id.strip() if isinstance(parent_project_name_or_id, str) else None
    if clean_parent and len(clean_parent) > MAX_PROJECT_NAME_LENGTH:
        return message("invalid.parent_project_identifier_too_long", limit=MAX_PROJECT_NAME_LENGTH)

    clean_color = color.strip().lower() if isinstance(color, str) else None
    if clean_color and len(clean_color) > MAX_COLOR_LENGTH:
        return message("invalid.color_too_long", limit=MAX_COLOR_LENGTH)

    failure_message = message("project.create_failed", name=clean_name)
    try:
        api = client.get_api_client()
        kwargs = {}
        parent_display = ""

        if clean_parent:
            parent = resolve_project(api, clean_parent, allow_partial=True, allow_inbox_alias=True)
            if isinstance(parent, LookupFailed):
                return failure_message
            if isinstance(parent, Ambiguous):
                return ambiguous_message(parent, "ambiguous.project")
            # Found(None, ...) is an Inbox alias with no listed Inbox: a parent needs a real project ID.
            if isinstance(parent, NotFound) or parent.id is None:
                return message("project.parent_not_found", name=clean_parent)
            parent_id, parent_name = parent.id, parent.name
            kwargs["parent_id"] = parent_id
            parent_display = message("project.created.parent_line", name=parent_name, id=parent_id)

        if clean_color:
            kwargs["color"] = clean_color

        project = api.add_project(name=clean_name, **kwargs)

        color_str = message("project.created.color_line", color=project.color) if getattr(project, "color", None) else ""
        url_str = message("project.created.url_line", url=project.url) if getattr(project, "url", None) else ""

        return message(
            "project.created",
            id=project.id,
            name=project.name,
            parent_line=parent_display,
            color_line=color_str,
            url_line=url_str,
        )
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to create project in Todoist (name=%s, error_type=%s)",
            clean_name,
            type(e).__name__,
            exc_info=False,
        )
        return failure_message


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
        return message("invalid.project_identifier_empty")
    if len(clean_identifier) > MAX_PROJECT_NAME_LENGTH:
        return message("invalid.project_identifier_too_long", limit=MAX_PROJECT_NAME_LENGTH)

    clean_name = name.strip() if isinstance(name, str) else None
    if clean_name is not None and not clean_name:
        return message("invalid.new_project_name_empty")
    if clean_name is not None and len(clean_name) > MAX_PROJECT_NAME_LENGTH:
        return message("invalid.new_project_name_too_long", limit=MAX_PROJECT_NAME_LENGTH)

    clean_color = color.strip().lower() if isinstance(color, str) else None
    if clean_color and len(clean_color) > MAX_COLOR_LENGTH:
        return message("invalid.color_too_long", limit=MAX_COLOR_LENGTH)

    if clean_name is None and clean_color is None:
        return message("project.update.no_fields")

    failure_message = message("project.update_failed", name=clean_identifier)
    try:
        api = client.get_api_client()
        resolved = resolve_project(api, clean_identifier)

        if isinstance(resolved, LookupFailed):
            return failure_message
        if isinstance(resolved, Ambiguous):
            return ambiguous_message(resolved, "ambiguous.project")
        if isinstance(resolved, NotFound):
            return message("project.update.not_found", name=clean_identifier)
        project_id = resolved.id

        kwargs = {}
        updated_fields = []
        if clean_name is not None:
            kwargs["name"] = clean_name
            updated_fields.append(message("project.update.change.name", value=clean_name))
        if clean_color is not None:
            kwargs["color"] = clean_color
            updated_fields.append(message("project.update.change.color", value=clean_color))

        api.update_project(project_id=project_id, **kwargs)

        changes_summary = "\n".join([f"• {field}" for field in updated_fields])
        return message("project.updated", id=project_id, changes=changes_summary)
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to update project in Todoist (identifier=%s, error_type=%s)",
            clean_identifier,
            type(e).__name__,
            exc_info=False,
        )
        return failure_message


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
        return message("invalid.project_identifier_empty")
    if len(clean_identifier) > MAX_PROJECT_NAME_LENGTH:
        return message("invalid.project_identifier_too_long", limit=MAX_PROJECT_NAME_LENGTH)

    failure_message = message("project.delete_failed", name=clean_identifier)
    try:
        api = client.get_api_client()
        resolved = resolve_project(api, clean_identifier)

        if isinstance(resolved, LookupFailed):
            return failure_message
        if isinstance(resolved, Ambiguous):
            return ambiguous_message(resolved, "ambiguous.project")
        if isinstance(resolved, NotFound):
            return message("project.delete.not_found", name=clean_identifier)
        project_id, project_name = resolved.id, resolved.name

        success = api.delete_project(project_id=project_id)
        display_name = message("display.named", name=project_name, id=project_id) if project_name else message("display.id_only", id=project_id)

        if success:
            return message("project.deleted", target=display_name)
        else:
            return message("project.delete_unconfirmed", target=display_name)
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete project in Todoist (identifier=%s, error_type=%s)",
            clean_identifier,
            type(e).__name__,
            exc_info=False,
        )
        return failure_message
