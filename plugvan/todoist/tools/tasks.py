"""Todoist task tools."""

import logging
from datetime import date
from typing import Annotated, Optional

from pydantic import Field

from plugvan.todoist import client
from plugvan.todoist.limits import (
    MAX_CONTENT_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_PROJECT_NAME_LENGTH,
    MAX_DUE_STRING_LENGTH,
    MAX_FILTER_QUERY_LENGTH,
    MAX_TASK_ID_LENGTH,
    MAX_SECTION_NAME_LENGTH,
)
from plugvan.todoist.resolvers import (
    _find_project_id,
    _resolve_section,
)

logger = logging.getLogger("todoist_mcp")


def _log_http_error_detail(e: Exception) -> None:
    """Logs the raw HTTP status and response body for an API error (server-side only, never returned to the client)."""
    response = getattr(e, "response", None)
    if response is not None:
        logger.error("Todoist API error detail: status=%s body=%s", response.status_code, response.text)


def _is_deadline_plan_restriction(e: Exception, deadline_date_requested: bool) -> bool:
    """True if the error is a 403 on a request that included deadline_date (Deadlines require Pro/Business)."""
    if not deadline_date_requested:
        return False
    response = getattr(e, "response", None)
    return response is not None and response.status_code == 403


def create_task(
    content: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_CONTENT_LENGTH,
            description="The text content/title of the task (required).",
        ),
    ],
    description: Annotated[
        str,
        Field(
            default="",
            max_length=MAX_DESCRIPTION_LENGTH,
            description="Detailed description or notes for the task (optional).",
        ),
    ] = "",
    project_name: Annotated[
        str,
        Field(
            default="Gelen Kutusu",
            max_length=MAX_PROJECT_NAME_LENGTH,
            description="Target Todoist project name (defaults to 'Gelen Kutusu' / Inbox).",
        ),
    ] = "Gelen Kutusu",
    due_string: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_DUE_STRING_LENGTH,
            description="Natural language due date/time or recurring schedule (e.g. 'tomorrow at 14:00', 'every Monday').",
        ),
    ] = None,
    priority: Annotated[
        int,
        Field(
            default=1,
            ge=1,
            le=4,
            description="Task priority level from 1 (Normal) to 4 (Urgent).",
        ),
    ] = 1,
    labels: Annotated[
        Optional[list[str]],
        Field(
            default=None,
            description="List of label names to attach to the task (e.g. ['work', 'urgent'], optional).",
        ),
    ] = None,
    section_name_or_id: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_SECTION_NAME_LENGTH,
            description="Target section name or ID within the project (optional).",
        ),
    ] = None,
    parent_id: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_TASK_ID_LENGTH,
            description="Bu görevi belirtilen Todoist görev ID'sinin alt görevi (subtask) yapar (opsiyonel).",
        ),
    ] = None,
    deadline_date: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "Optional official deadline date in YYYY-MM-DD format (e.g. '2026-09-01'). "
                "This is independent from due_string: due_string controls when the task is "
                "scheduled to be worked on, while deadline_date sets Todoist's separate "
                "'Deadline' — a hard due-by date shown distinctly in the UI (optional)."
            ),
        ),
    ] = None,
) -> str:
    """Creates a new task in Todoist with smart project, section, label, and due date resolution.

    Args:
        content: Task title/content (must not be empty, max 500 chars).
        description: Task notes or description (max 4096 chars).
        project_name: Target project name (max 120 chars, defaults to 'Gelen Kutusu').
        due_string: Natural language date string (e.g. 'tomorrow at 14:00', max 150 chars).
        priority: Priority integer strictly between 1 (normal) and 4 (urgent).
        labels: Optional list of label strings to attach to the task.
        section_name_or_id: Optional target section name or ID within the project.
        parent_id: Optional Todoist task ID to create this task as a subtask of (max 100 chars).
        deadline_date: Optional official deadline date (YYYY-MM-DD), distinct from due_string.
    """
    clean_content = content.strip() if isinstance(content, str) else ""
    if not clean_content:
        return "❌ Invalid input: Task content cannot be empty or whitespace."
    if len(clean_content) > MAX_CONTENT_LENGTH:
        return f"❌ Invalid input: Task content exceeds maximum length of {MAX_CONTENT_LENGTH} characters."

    clean_description = description.strip() if isinstance(description, str) else ""
    if len(clean_description) > MAX_DESCRIPTION_LENGTH:
        return f"❌ Invalid input: Task description exceeds maximum length of {MAX_DESCRIPTION_LENGTH} characters."

    clean_project_name = project_name.strip() if isinstance(project_name, str) else ""
    if len(clean_project_name) > MAX_PROJECT_NAME_LENGTH:
        return f"❌ Invalid input: Project name exceeds maximum length of {MAX_PROJECT_NAME_LENGTH} characters."

    clean_due_string = due_string.strip() if isinstance(due_string, str) else None
    if clean_due_string and len(clean_due_string) > MAX_DUE_STRING_LENGTH:
        return f"❌ Invalid input: Due date string exceeds maximum length of {MAX_DUE_STRING_LENGTH} characters."

    if not isinstance(priority, int) or priority < 1 or priority > 4:
        return "❌ Invalid input: Priority must be an integer between 1 (Normal) and 4 (Urgent)."

    clean_labels = None
    if labels is not None:
        if isinstance(labels, list):
            clean_labels = [str(l).strip().lstrip("@") for l in labels if str(l).strip()]
        else:
            return "❌ Invalid input: Labels must be a list of strings."

    clean_section = section_name_or_id.strip() if isinstance(section_name_or_id, str) else None
    if clean_section and len(clean_section) > MAX_SECTION_NAME_LENGTH:
        return f"❌ Invalid input: Section identifier exceeds maximum length of {MAX_SECTION_NAME_LENGTH} characters."

    clean_parent_id = parent_id.strip() if isinstance(parent_id, str) else None
    if clean_parent_id and len(clean_parent_id) > MAX_TASK_ID_LENGTH:
        return f"❌ Invalid input: Parent task ID exceeds maximum length of {MAX_TASK_ID_LENGTH} characters."

    clean_deadline_date = deadline_date.strip() if isinstance(deadline_date, str) else None
    parsed_deadline_date = None
    if clean_deadline_date:
        try:
            parsed_deadline_date = date.fromisoformat(clean_deadline_date)
        except ValueError:
            return f"❌ Invalid input: deadline_date must be in YYYY-MM-DD format (received: '{clean_deadline_date}')."

    try:
        api = client.get_api_client()
        project_id = _find_project_id(api, clean_project_name) if clean_project_name else None

        section_id = None
        section_display_name = ""
        if clean_section:
            section_id, section_display_name = _resolve_section(api, clean_section, project_id=project_id)
            if not section_id:
                return f"⚠️ Belirtilen bölüm bulunamadı: '{clean_section}'."

        task_kwargs = {
            "content": clean_content,
            "description": clean_description or None,
            "project_id": project_id,
            "due_string": clean_due_string or None,
            "priority": priority,
        }
        if section_id:
            task_kwargs["section_id"] = section_id
        if clean_labels:
            task_kwargs["labels"] = clean_labels
        if clean_parent_id:
            task_kwargs["parent_id"] = clean_parent_id
        if parsed_deadline_date:
            task_kwargs["deadline_date"] = parsed_deadline_date

        task = api.add_task(**task_kwargs)

        due_info = task.due.string if task.due and task.due.string else (clean_due_string or "Belirtilmedi")
        project_display = clean_project_name if clean_project_name else "Gelen Kutusu"
        section_display = f"\n• Bölüm: {section_display_name} (ID: {section_id})" if section_id else ""
        labels_display = f"\n• Etiketler: {', '.join(['@' + l for l in task.labels])}" if getattr(task, "labels", None) else ""
        deadline_display = f"\n• Son Teslim Tarihi (Deadline): {clean_deadline_date}" if clean_deadline_date else ""

        return (
            f"✅ Görev başarıyla oluşturuldu!\n"
            f"• ID: {task.id}\n"
            f"• Başlık: {task.content}\n"
            f"• Proje: {project_display}"
            f"{section_display}\n"
            f"• Öncelik: p{task.priority}\n"
            f"• Tarih / Tekrar: {due_info}"
            f"{deadline_display}"
            f"{labels_display}\n"
            f"• URL: {task.url}"
        )
    except Exception as e:
        logger.error(
            "Failed to create task in Todoist (content_len=%d, error_type=%s)",
            len(clean_content),
            type(e).__name__,
            exc_info=False,
        )
        _log_http_error_detail(e)
        if _is_deadline_plan_restriction(e, parsed_deadline_date is not None):
            return "❌ Deadline özelliği Todoist Free/Beginner planında desteklenmiyor — Pro veya Business plan gerekiyor (403 Forbidden)."
        return "❌ Todoist task creation failed. Check server logs for details."


def list_tasks(
    filter_query: Annotated[
        str,
        Field(
            default="today",
            min_length=1,
            max_length=MAX_FILTER_QUERY_LENGTH,
            description="Todoist filter query (e.g. 'today', 'tomorrow', 'overdue', 'p1', 'all', '@work').",
        ),
    ] = "today",
) -> str:
    """Lists open tasks in Todoist matching the specified filter query.

    Args:
        filter_query: Todoist filter query (e.g. 'today', 'p1', 'overdue', '@work', max 500 chars).
    """
    clean_query = filter_query.strip() if isinstance(filter_query, str) else ""
    if not clean_query:
        return "❌ Invalid input: Filter query cannot be empty or whitespace."
    if len(clean_query) > MAX_FILTER_QUERY_LENGTH:
        return f"❌ Invalid input: Filter query exceeds maximum length of {MAX_FILTER_QUERY_LENGTH} characters."

    try:
        api = client.get_api_client()
        tasks = []
        for batch in api.filter_tasks(query=clean_query):
            tasks.extend(batch)

        if not tasks:
            return f"ℹ️ '{clean_query}' filtresine uygun açık görev bulunamadı."

        priority_labels = {4: "🔴 p4 (Çok Acil)", 3: "🟠 p3 (Yüksek)", 2: "🔵 p2 (Orta)", 1: "⚪ p1 (Normal)"}

        lines = [f"📋 Açık Görevler (Filtre: '{clean_query}', Toplam: {len(tasks)}):", ""]
        for idx, task in enumerate(tasks, start=1):
            due_str = task.due.string if task.due and task.due.string else "Tarih yok"
            p_str = priority_labels.get(task.priority, f"p{task.priority}")
            labels_str = f" [{' '.join(['@' + l for l in task.labels])}]" if getattr(task, "labels", None) else ""
            lines.append(f"{idx}. [{task.id}] {task.content}{labels_str}")
            lines.append(f"   • Öncelik: {p_str}")
            lines.append(f"   • Tarih: {due_str}")
            if task.description:
                lines.append(f"   • Açıklama: {task.description}")
            lines.append("")

        return "\n".join(lines).strip()
    except Exception as e:
        logger.error(
            "Failed to retrieve tasks from Todoist (filter_len=%d, error_type=%s)",
            len(clean_query),
            type(e).__name__,
            exc_info=False,
        )
        return "❌ Failed to retrieve tasks from Todoist. Check server logs for details."


def get_task(
    task_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_TASK_ID_LENGTH,
            description="The Todoist Task ID to retrieve (required).",
        ),
    ],
) -> str:
    """Retrieves a single Todoist task by its ID, showing all its fields (parent_id, due date, labels, description, priority, project/section IDs, etc.).

    Args:
        task_id: The ID of the Todoist task to retrieve (max 100 chars).
    """
    clean_task_id = str(task_id).strip() if task_id is not None else ""
    if not clean_task_id:
        return "❌ Invalid input: Task ID cannot be empty or whitespace."
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return f"❌ Invalid input: Task ID exceeds maximum length of {MAX_TASK_ID_LENGTH} characters."

    try:
        api = client.get_api_client()
        task = api.get_task(task_id=clean_task_id)

        due_info = task.due.string if task.due and task.due.string else "Belirlenmedi"
        labels_display = ", ".join(["@" + l for l in task.labels]) if getattr(task, "labels", None) else "Yok"
        description_display = task.description if task.description else "Yok"
        parent_display = task.parent_id if task.parent_id else "Yok (üst seviye görev)"
        section_display = task.section_id if task.section_id else "Yok"

        return (
            f"📄 Görev Detayları (ID: {task.id})\n"
            f"• Başlık: {task.content}\n"
            f"• Açıklama: {description_display}\n"
            f"• Proje ID: {task.project_id}\n"
            f"• Bölüm ID: {section_display}\n"
            f"• Üst Görev ID (parent_id): {parent_display}\n"
            f"• Öncelik: p{task.priority}\n"
            f"• Tarih / Tekrar: {due_info}\n"
            f"• Etiketler: {labels_display}\n"
            f"• URL: {task.url}"
        )
    except Exception as e:
        logger.error(
            "Failed to retrieve task from Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        return f"❌ Failed to retrieve task from Todoist (ID: {clean_task_id}). Check server logs for details."


def complete_task(
    task_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_TASK_ID_LENGTH,
            description="The Todoist Task ID to complete (required).",
        ),
    ],
) -> str:
    """Marks an existing Todoist task as completed.

    Args:
        task_id: The ID of the Todoist task to mark as completed (max 100 chars).
    """
    clean_task_id = str(task_id).strip() if task_id is not None else ""
    if not clean_task_id:
        return "❌ Invalid input: Task ID cannot be empty or whitespace."
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return f"❌ Invalid input: Task ID exceeds maximum length of {MAX_TASK_ID_LENGTH} characters."

    try:
        api = client.get_api_client()
        success = api.complete_task(task_id=clean_task_id)
        if success:
            return f"✅ Görev başarıyla tamamlandı (ID: {clean_task_id})."
        else:
            return f"⚠️ Görev tamamlanamadı veya zaten tamamlanmış olabilir (ID: {clean_task_id})."
    except Exception as e:
        logger.error(
            "Failed to complete task in Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        return f"❌ Failed to complete task in Todoist (ID: {clean_task_id}). Check server logs for details."


def reopen_task(
    task_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_TASK_ID_LENGTH,
            description="The Todoist Task ID to reopen/uncomplete (required).",
        ),
    ],
) -> str:
    """Reopens an existing completed Todoist task (makes it active again).

    Args:
        task_id: The ID of the completed Todoist task to reopen.
    """
    clean_task_id = str(task_id).strip() if task_id is not None else ""
    if not clean_task_id:
        return "❌ Invalid input: Task ID cannot be empty or whitespace."
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return f"❌ Invalid input: Task ID exceeds maximum length of {MAX_TASK_ID_LENGTH} characters."

    try:
        api = client.get_api_client()
        success = api.uncomplete_task(task_id=clean_task_id)
        if success:
            return f"🔄 Görev başarıyla yeniden açıldı (ID: {clean_task_id})."
        else:
            return f"⚠️ Görev yeniden açılamadı veya zaten açık olabilir (ID: {clean_task_id})."
    except Exception as e:
        logger.error(
            "Failed to reopen task in Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        return f"❌ Failed to reopen task in Todoist (ID: {clean_task_id}). Check server logs for details."


def update_task(
    task_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_TASK_ID_LENGTH,
            description="The Todoist Task ID to update (required).",
        ),
    ],
    content: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_CONTENT_LENGTH,
            description="New title/content for the task (optional).",
        ),
    ] = None,
    description: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_DESCRIPTION_LENGTH,
            description="New description or notes for the task (optional).",
        ),
    ] = None,
    project_name: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_PROJECT_NAME_LENGTH,
            description="Target project name to move the task into (optional).",
        ),
    ] = None,
    due_string: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_DUE_STRING_LENGTH,
            description="New natural language due date/time (e.g. 'tomorrow at 15:00', 'no date', optional).",
        ),
    ] = None,
    priority: Annotated[
        Optional[int],
        Field(
            default=None,
            ge=1,
            le=4,
            description="New priority level from 1 (Normal) to 4 (Urgent) (optional).",
        ),
    ] = None,
    labels: Annotated[
        Optional[list[str]],
        Field(
            default=None,
            description="New list of label names for the task (replaces existing labels, optional).",
        ),
    ] = None,
    section_name_or_id: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_SECTION_NAME_LENGTH,
            description="Target section name or ID to move the task into (optional).",
        ),
    ] = None,
    parent_id: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_TASK_ID_LENGTH,
            description=(
                "New parent Todoist task ID to make this task a subtask of. "
                "Pass an empty string (\"\") to remove the current parent and move the task "
                "back to the top level (optional). Omit entirely to leave the parent unchanged."
            ),
        ),
    ] = None,
    deadline_date: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "New official deadline date in YYYY-MM-DD format (e.g. '2026-09-01'). "
                "This is independent from due_string: due_string controls when the task is "
                "scheduled to be worked on, while deadline_date sets Todoist's separate "
                "'Deadline' — a hard due-by date shown distinctly in the UI (optional)."
            ),
        ),
    ] = None,
) -> str:
    """Updates an existing Todoist task's title, description, due date, deadline, priority, labels, or moves it to another project/section/parent.

    Args:
        task_id: The ID of the Todoist task to update (required).
        content: New title/content for the task.
        description: New description or notes for the task.
        project_name: Name of target project to move task into.
        due_string: New natural language due date or schedule.
        priority: Priority integer between 1 (Normal) and 4 (Urgent).
        labels: New list of label names for the task.
        section_name_or_id: Target section name or ID to move task into.
        parent_id: New parent task ID (subtask), or "" to promote the task back to the top level.
        deadline_date: New official deadline date (YYYY-MM-DD), distinct from due_string.
    """
    clean_task_id = str(task_id).strip() if task_id is not None else ""
    if not clean_task_id:
        return "❌ Invalid input: Task ID cannot be empty or whitespace."
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return f"❌ Invalid input: Task ID exceeds maximum length of {MAX_TASK_ID_LENGTH} characters."

    clean_content = content.strip() if isinstance(content, str) else None
    if clean_content is not None and len(clean_content) > MAX_CONTENT_LENGTH:
        return f"❌ Invalid input: Task content exceeds maximum length of {MAX_CONTENT_LENGTH} characters."

    clean_description = description.strip() if isinstance(description, str) else None
    if clean_description is not None and len(clean_description) > MAX_DESCRIPTION_LENGTH:
        return f"❌ Invalid input: Task description exceeds maximum length of {MAX_DESCRIPTION_LENGTH} characters."

    clean_project_name = project_name.strip() if isinstance(project_name, str) else None
    if clean_project_name is not None and len(clean_project_name) > MAX_PROJECT_NAME_LENGTH:
        return f"❌ Invalid input: Project name exceeds maximum length of {MAX_PROJECT_NAME_LENGTH} characters."

    clean_due_string = due_string.strip() if isinstance(due_string, str) else None
    if clean_due_string is not None and len(clean_due_string) > MAX_DUE_STRING_LENGTH:
        return f"❌ Invalid input: Due date string exceeds maximum length of {MAX_DUE_STRING_LENGTH} characters."

    if priority is not None and (not isinstance(priority, int) or priority < 1 or priority > 4):
        return "❌ Invalid input: Priority must be an integer between 1 (Normal) and 4 (Urgent)."

    clean_labels = None
    if labels is not None:
        if isinstance(labels, list):
            clean_labels = [str(l).strip().lstrip("@") for l in labels if str(l).strip()]
        else:
            return "❌ Invalid input: Labels must be a list of strings."

    clean_section = section_name_or_id.strip() if isinstance(section_name_or_id, str) else None
    if clean_section is not None and len(clean_section) > MAX_SECTION_NAME_LENGTH:
        return f"❌ Invalid input: Section identifier exceeds maximum length of {MAX_SECTION_NAME_LENGTH} characters."

    # None = untouched; "" (after strip) = explicit "remove parent" request; non-empty = new parent ID.
    clean_parent_id = parent_id.strip() if isinstance(parent_id, str) else None
    if clean_parent_id is not None and len(clean_parent_id) > MAX_TASK_ID_LENGTH:
        return f"❌ Invalid input: Parent task ID exceeds maximum length of {MAX_TASK_ID_LENGTH} characters."

    clean_deadline_date = deadline_date.strip() if isinstance(deadline_date, str) else None
    parsed_deadline_date = None
    if clean_deadline_date:
        try:
            parsed_deadline_date = date.fromisoformat(clean_deadline_date)
        except ValueError:
            return f"❌ Invalid input: deadline_date must be in YYYY-MM-DD format (received: '{clean_deadline_date}')."

    if (
        clean_content is None
        and clean_description is None
        and clean_project_name is None
        and clean_due_string is None
        and priority is None
        and clean_labels is None
        and clean_section is None
        and clean_parent_id is None
        and clean_deadline_date is None
    ):
        return "⚠️ Güncellenecek hiçbir alan belirtilmedi. Lütfen en az bir parametre (content, description, project_name, due_string, priority, labels, section_name_or_id, parent_id, deadline_date) girin."

    try:
        api = client.get_api_client()
        updated_fields = []

        # 1. Update task attributes if provided
        update_kwargs = {}
        if clean_content is not None:
            update_kwargs["content"] = clean_content
            updated_fields.append(f"Başlık: '{clean_content}'")
        if clean_description is not None:
            update_kwargs["description"] = clean_description
            updated_fields.append(f"Açıklama: '{clean_description}'")
        if clean_due_string is not None:
            update_kwargs["due_string"] = clean_due_string
            updated_fields.append(f"Tarih: '{clean_due_string}'")
        if priority is not None:
            update_kwargs["priority"] = priority
            updated_fields.append(f"Öncelik: p{priority}")
        if clean_labels is not None:
            update_kwargs["labels"] = clean_labels
            updated_fields.append(f"Etiketler: {', '.join(['@' + l for l in clean_labels]) if clean_labels else 'Temizlendi'}")
        if parsed_deadline_date is not None:
            update_kwargs["deadline_date"] = parsed_deadline_date
            updated_fields.append(f"Son Teslim Tarihi (Deadline): '{clean_deadline_date}'")

        if update_kwargs:
            api.update_task(task_id=clean_task_id, **update_kwargs)

        # 2. Move task to target project / section if requested
        target_project_id = None
        if clean_project_name is not None:
            target_project_id = _find_project_id(api, clean_project_name)
            if not target_project_id:
                return f"⚠️ Görev güncellendi fakat hedef proje bulunamadı: '{clean_project_name}'."

        target_section_id = None
        if clean_section is not None:
            target_section_id, sec_name = _resolve_section(api, clean_section, project_id=target_project_id)
            if not target_section_id:
                return f"⚠️ Görev güncellendi fakat hedef bölüm bulunamadı: '{clean_section}'."

        # Todoist's update endpoint does not accept parent_id; changing it requires the
        # dedicated move endpoint. That endpoint also has no "clear parent" value (it drops
        # any None field before sending, and there is no documented empty/null parent_id
        # behavior) — the verified way to promote a subtask back to the top level is to move
        # it to an explicit project_id instead, so we resolve the task's current project first.
        target_parent_id = clean_parent_id if clean_parent_id else None
        unparent_requested = clean_parent_id == ""
        if unparent_requested and target_project_id is None and target_section_id is None:
            current_task = api.get_task(task_id=clean_task_id)
            target_project_id = current_task.project_id

        if target_project_id is not None or target_section_id is not None or target_parent_id is not None:
            move_kwargs = {}
            if target_project_id is not None:
                move_kwargs["project_id"] = target_project_id
                if clean_project_name is not None:
                    updated_fields.append(f"Hedef Proje: '{clean_project_name}' (ID: {target_project_id})")
            if target_section_id is not None:
                move_kwargs["section_id"] = target_section_id
                updated_fields.append(f"Hedef Bölüm: '{sec_name}' (ID: {target_section_id})")
            if target_parent_id is not None:
                move_kwargs["parent_id"] = target_parent_id
                updated_fields.append(f"Üst Görev (parent_id): '{target_parent_id}'")
            elif unparent_requested:
                updated_fields.append("Üst Görev: Kaldırıldı (görev üst seviyeye taşındı)")

            api.move_task(task_id=clean_task_id, **move_kwargs)

        changes_summary = "\n".join([f"• {field}" for field in updated_fields])
        return (
            f"✅ Görev başarıyla güncellendi (ID: {clean_task_id})!\n"
            f"Yapılan değişiklikler:\n"
            f"{changes_summary}"
        )
    except Exception as e:
        logger.error(
            "Failed to update task in Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        _log_http_error_detail(e)
        if _is_deadline_plan_restriction(e, parsed_deadline_date is not None):
            return "❌ Deadline özelliği Todoist Free/Beginner planında desteklenmiyor — Pro veya Business plan gerekiyor (403 Forbidden)."
        return f"❌ Failed to update task in Todoist (ID: {clean_task_id}). Check server logs for details."


def delete_task(
    task_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_TASK_ID_LENGTH,
            description="The Todoist Task ID to delete permanently (required).",
        ),
    ],
) -> str:
    """Permanently deletes a task from Todoist by ID.

    Args:
        task_id: The ID of the Todoist task to delete permanently.
    """
    clean_task_id = str(task_id).strip() if task_id is not None else ""
    if not clean_task_id:
        return "❌ Invalid input: Task ID cannot be empty or whitespace."
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return f"❌ Invalid input: Task ID exceeds maximum length of {MAX_TASK_ID_LENGTH} characters."

    try:
        api = client.get_api_client()
        success = api.delete_task(task_id=clean_task_id)
        if success:
            return f"🗑️ Görev kalıcı olarak silindi (ID: {clean_task_id})."
        else:
            return f"⚠️ Görev silinemedi (ID: {clean_task_id}). Görev zaten silinmiş veya bulunamıyor olabilir."
    except Exception as e:
        logger.error(
            "Failed to delete task in Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        return f"❌ Failed to delete task in Todoist (ID: {clean_task_id}). Check server logs for details."
