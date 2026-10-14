"""Todoist section tools."""

import logging
from typing import Annotated, Optional

from pydantic import Field

from plugvan.todoist import client
from plugvan.todoist.limits import (
    MAX_PROJECT_NAME_LENGTH,
    MAX_SECTION_NAME_LENGTH,
)
from plugvan.todoist.messages import MissingMessageError, message
from plugvan.todoist.resolvers import (
    Ambiguous,
    LookupFailed,
    NotFound,
    _get_all_sections,
    ambiguous_message,
    resolve_project,
    resolve_section,
)

logger = logging.getLogger("todoist_mcp")


def create_section(
    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_SECTION_NAME_LENGTH,
            description="The name of the new section/column (required, e.g. 'In Progress', 'Done').",
        ),
    ],
    project_name_or_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_PROJECT_NAME_LENGTH,
            description="The name or ID of the parent project where the section will be created (required).",
        ),
    ],
) -> str:
    """Creates a new section (column / Kanban list) in a Todoist project.

    Args:
        name: Name of the section (must not be empty, max 120 chars).
        project_name_or_id: Target project name or ID.
    """
    clean_name = name.strip() if isinstance(name, str) else ""
    if not clean_name:
        return message("invalid.section_name_empty")
    if len(clean_name) > MAX_SECTION_NAME_LENGTH:
        return message("invalid.section_name_too_long", limit=MAX_SECTION_NAME_LENGTH)

    clean_project = str(project_name_or_id).strip() if project_name_or_id is not None else ""
    if not clean_project:
        return message("invalid.project_identifier_empty")
    if len(clean_project) > MAX_PROJECT_NAME_LENGTH:
        return message("invalid.project_identifier_too_long", limit=MAX_PROJECT_NAME_LENGTH)

    failure_message = message("section.create_failed", name=clean_name)
    try:
        api = client.get_api_client()
        project = resolve_project(api, clean_project, allow_partial=True, allow_inbox_alias=True)

        if isinstance(project, LookupFailed):
            return failure_message
        if isinstance(project, Ambiguous):
            return ambiguous_message(project, "ambiguous.project")
        # Found(None, ...) is an Inbox alias with no listed Inbox: a section needs a real project ID.
        if isinstance(project, NotFound) or project.id is None:
            return message("section.create.project_not_found", name=clean_project)
        project_id, project_name = project.id, project.name

        section = api.add_section(name=clean_name, project_id=project_id)

        return message(
            "section.created", id=section.id, name=section.name, project=project_name, project_id=project_id
        )
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to create section in Todoist (name=%s, error_type=%s)",
            clean_name,
            type(e).__name__,
            exc_info=False,
        )
        return failure_message


def list_sections(
    project_name_or_id: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_PROJECT_NAME_LENGTH,
            description="Optional project name or ID to list sections specifically for that project.",
        ),
    ] = None,
) -> str:
    """Lists sections (Kanban columns) in Todoist for a specific project or across all projects."""
    clean_project = project_name_or_id.strip() if isinstance(project_name_or_id, str) else None
    if clean_project and len(clean_project) > MAX_PROJECT_NAME_LENGTH:
        return message("invalid.project_identifier_too_long", limit=MAX_PROJECT_NAME_LENGTH)

    failure_message = message("section.list_failed")
    try:
        api = client.get_api_client()
        project_id = None
        project_name = None

        if clean_project:
            project = resolve_project(api, clean_project, allow_partial=True, allow_inbox_alias=True)
            if isinstance(project, LookupFailed):
                return failure_message
            if isinstance(project, Ambiguous):
                return ambiguous_message(project, "ambiguous.project")
            # Found(None, ...) is an Inbox alias with no listed Inbox: listing all sections would be wrong.
            if isinstance(project, NotFound) or project.id is None:
                return message("project.not_found", name=clean_project)
            project_id, project_name = project.id, project.name

        sections = _get_all_sections(api, project_id=project_id)

        if not sections:
            if project_name:
                return message("section.list.empty_in_project", project=project_name)
            return message("section.list.empty_all")

        if project_name:
            header = message("section.list.header_project", project=project_name, count=len(sections))
        else:
            header = message("section.list.header_all", count=len(sections))
        lines = [header, ""]

        for idx, section in enumerate(sections, start=1):
            lines.append(
                message("section.list.line", index=idx, id=section.id, name=section.name, project_id=section.project_id)
            )

        return "\n".join(lines).strip()
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to list sections from Todoist (error_type=%s)",
            type(e).__name__,
            exc_info=False,
        )
        return failure_message


def update_section(
    section_name_or_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_SECTION_NAME_LENGTH,
            description="The Todoist Section ID or current Section Name to rename (required).",
        ),
    ],
    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_SECTION_NAME_LENGTH,
            description="The new name for the section (required).",
        ),
    ],
    project_name_or_id: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_PROJECT_NAME_LENGTH,
            description="Optional project name or ID to disambiguate when several projects have a section with the same name.",
        ),
    ] = None,
) -> str:
    """Renames an existing section (column / Kanban list) in Todoist.

    Args:
        section_name_or_id: ID or current name of the section to rename.
        name: New section name (must not be empty, max 120 chars).
        project_name_or_id: Optional project scope used to resolve the section by name.
    """
    clean_identifier = str(section_name_or_id).strip() if section_name_or_id is not None else ""
    if not clean_identifier:
        return message("invalid.section_identifier_empty")
    if len(clean_identifier) > MAX_SECTION_NAME_LENGTH:
        return message("invalid.section_identifier_too_long", limit=MAX_SECTION_NAME_LENGTH)

    clean_name = name.strip() if isinstance(name, str) else ""
    if not clean_name:
        return message("invalid.new_section_name_empty")
    if len(clean_name) > MAX_SECTION_NAME_LENGTH:
        return message("invalid.new_section_name_too_long", limit=MAX_SECTION_NAME_LENGTH)

    clean_project = project_name_or_id.strip() if isinstance(project_name_or_id, str) else None
    if clean_project and len(clean_project) > MAX_PROJECT_NAME_LENGTH:
        return message("invalid.project_identifier_too_long", limit=MAX_PROJECT_NAME_LENGTH)

    failure_message = message("section.update_failed", name=clean_identifier)
    section_not_found = message("section.update.not_found", name=clean_identifier)
    try:
        api = client.get_api_client()

        project_id = None
        if clean_project:
            project = resolve_project(api, clean_project, allow_inbox_alias=True)
            if isinstance(project, LookupFailed):
                return failure_message
            if isinstance(project, Ambiguous):
                return ambiguous_message(project, "ambiguous.project")
            if isinstance(project, NotFound):
                return message("project.not_found", name=clean_project)
            if project.id is None:
                # Inbox alias without a listed Inbox project: there is no ID to scope the search to.
                return section_not_found
            project_id = project.id

        section = resolve_section(api, clean_identifier, project_id=project_id)
        if isinstance(section, LookupFailed):
            return failure_message
        if isinstance(section, Ambiguous):
            return ambiguous_message(section, "ambiguous.section")
        if isinstance(section, NotFound):
            return section_not_found
        section_id, old_name = section.id, section.name

        api.update_section(section_id=section_id, name=clean_name)

        return message("section.updated", id=section_id, old_name=old_name, new_name=clean_name)
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to update section in Todoist (identifier=%s, error_type=%s)",
            clean_identifier,
            type(e).__name__,
            exc_info=False,
        )
        return failure_message


def delete_section(
    section_name_or_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_SECTION_NAME_LENGTH,
            description="The Todoist Section ID or Name to delete (required).",
        ),
    ],
) -> str:
    """Deletes a section from Todoist by its ID or name.

    Args:
        section_name_or_id: The ID or name of the section to delete.
    """
    clean_identifier = str(section_name_or_id).strip() if section_name_or_id is not None else ""
    if not clean_identifier:
        return message("invalid.section_identifier_empty")
    if len(clean_identifier) > MAX_SECTION_NAME_LENGTH:
        return message("invalid.section_identifier_too_long", limit=MAX_SECTION_NAME_LENGTH)

    failure_message = message("section.delete_failed", name=clean_identifier)
    try:
        api = client.get_api_client()
        section = resolve_section(api, clean_identifier)

        if isinstance(section, LookupFailed):
            return failure_message
        if isinstance(section, Ambiguous):
            return ambiguous_message(section, "ambiguous.section")
        if isinstance(section, NotFound):
            return message("section.delete.not_found", name=clean_identifier)
        section_id, section_name = section.id, section.name

        success = api.delete_section(section_id=section_id)
        display_name = message("display.named", name=section_name, id=section_id) if section_name else message("display.id_only", id=section_id)

        if success:
            return message("section.deleted", target=display_name)
        else:
            return message("section.delete_unconfirmed", target=display_name)
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete section in Todoist (identifier=%s, error_type=%s)",
            clean_identifier,
            type(e).__name__,
            exc_info=False,
        )
        return failure_message
