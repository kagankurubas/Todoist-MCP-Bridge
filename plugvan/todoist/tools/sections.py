"""Todoist section tools."""

import logging
from typing import Annotated, Optional

from pydantic import Field

from plugvan.todoist import client
from plugvan.todoist.limits import (
    MAX_PROJECT_NAME_LENGTH,
    MAX_SECTION_NAME_LENGTH,
)
from plugvan.todoist.messages import MissingMessageError
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
        return "❌ Invalid input: Section name cannot be empty or whitespace."
    if len(clean_name) > MAX_SECTION_NAME_LENGTH:
        return f"❌ Invalid input: Section name exceeds maximum length of {MAX_SECTION_NAME_LENGTH} characters."

    clean_project = str(project_name_or_id).strip() if project_name_or_id is not None else ""
    if not clean_project:
        return "❌ Invalid input: Project identifier cannot be empty or whitespace."
    if len(clean_project) > MAX_PROJECT_NAME_LENGTH:
        return f"❌ Invalid input: Project identifier exceeds maximum length of {MAX_PROJECT_NAME_LENGTH} characters."

    failure_message = f"❌ Failed to create section '{clean_name}' in Todoist. Check server logs for details."
    try:
        api = client.get_api_client()
        project = resolve_project(api, clean_project, allow_partial=True, allow_inbox_alias=True)

        if isinstance(project, LookupFailed):
            return failure_message
        if isinstance(project, Ambiguous):
            return ambiguous_message(project, "ambiguous.project")
        # Found(None, ...) is an Inbox alias with no listed Inbox: a section needs a real project ID.
        if isinstance(project, NotFound) or project.id is None:
            return f"⚠️ Bölüm oluşturulacak hedef proje bulunamadı: '{clean_project}'."
        project_id, project_name = project.id, project.name

        section = api.add_section(name=clean_name, project_id=project_id)

        return (
            f"✅ Bölüm başarıyla oluşturuldu!\n"
            f"• ID: {section.id}\n"
            f"• İsim: {section.name}\n"
            f"• Proje: '{project_name}' (ID: {project_id})"
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
        return f"❌ Invalid input: Project identifier exceeds maximum length of {MAX_PROJECT_NAME_LENGTH} characters."

    failure_message = "❌ Failed to list sections from Todoist. Check server logs for details."
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
                return f"⚠️ Belirtilen proje bulunamadı: '{clean_project}'."
            project_id, project_name = project.id, project.name

        sections = _get_all_sections(api, project_id=project_id)

        if not sections:
            scope = f"'{project_name}' projesinde" if project_name else "hesabınızda"
            return f"ℹ️ Todoist {scope} herhangi bir bölüm bulunamadı."

        title_scope = f"'{project_name}' Projesi" if project_name else "Tüm Projeler"
        lines = [f"📑 Mevcut Bölümler ({title_scope}, Toplam: {len(sections)}):", ""]

        for idx, section in enumerate(sections, start=1):
            lines.append(f"{idx}. [{section.id}] {section.name} (Proje ID: {section.project_id})")

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
        return "❌ Invalid input: Section identifier cannot be empty or whitespace."
    if len(clean_identifier) > MAX_SECTION_NAME_LENGTH:
        return f"❌ Invalid input: Section identifier exceeds maximum length of {MAX_SECTION_NAME_LENGTH} characters."

    clean_name = name.strip() if isinstance(name, str) else ""
    if not clean_name:
        return "❌ Invalid input: New section name cannot be empty or whitespace."
    if len(clean_name) > MAX_SECTION_NAME_LENGTH:
        return f"❌ Invalid input: New section name exceeds maximum length of {MAX_SECTION_NAME_LENGTH} characters."

    clean_project = project_name_or_id.strip() if isinstance(project_name_or_id, str) else None
    if clean_project and len(clean_project) > MAX_PROJECT_NAME_LENGTH:
        return f"❌ Invalid input: Project identifier exceeds maximum length of {MAX_PROJECT_NAME_LENGTH} characters."

    failure_message = f"❌ Failed to update section '{clean_identifier}' in Todoist. Check server logs for details."
    section_not_found = f"⚠️ Güncellenecek bölüm bulunamadı: '{clean_identifier}'."
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
                return f"⚠️ Belirtilen proje bulunamadı: '{clean_project}'."
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

        return (
            f"✅ Bölüm başarıyla güncellendi (ID: {section_id})!\n"
            f"• Eski isim: '{old_name}'\n"
            f"• Yeni isim: '{clean_name}'"
        )
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
        return "❌ Invalid input: Section identifier cannot be empty or whitespace."
    if len(clean_identifier) > MAX_SECTION_NAME_LENGTH:
        return f"❌ Invalid input: Section identifier exceeds maximum length of {MAX_SECTION_NAME_LENGTH} characters."

    failure_message = f"❌ Failed to delete section '{clean_identifier}' in Todoist. Check server logs for details."
    try:
        api = client.get_api_client()
        section = resolve_section(api, clean_identifier)

        if isinstance(section, LookupFailed):
            return failure_message
        if isinstance(section, Ambiguous):
            return ambiguous_message(section, "ambiguous.section")
        if isinstance(section, NotFound):
            return f"⚠️ Silinecek bölüm bulunamadı: '{clean_identifier}'."
        section_id, section_name = section.id, section.name

        success = api.delete_section(section_id=section_id)
        display_name = f"'{section_name}' (ID: {section_id})" if section_name else f"ID: {section_id}"

        if success:
            return f"🗑️ Bölüm başarıyla silindi: {display_name}."
        else:
            return f"⚠️ Bölüm silinemedi: {display_name}."
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
