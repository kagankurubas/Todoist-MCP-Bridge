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
from plugvan.todoist.messages import MissingMessageError, message
from plugvan.todoist.resolvers import (
    INBOX_QUERY,
    Ambiguous,
    LookupFailed,
    NotFound,
    ambiguous_message,
    resolve_project,
    resolve_section,
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
        return message("invalid.task_content_empty")
    if len(clean_content) > MAX_CONTENT_LENGTH:
        return message("invalid.task_content_too_long", limit=MAX_CONTENT_LENGTH)

    clean_description = description.strip() if isinstance(description, str) else ""
    if len(clean_description) > MAX_DESCRIPTION_LENGTH:
        return message("invalid.task_description_too_long", limit=MAX_DESCRIPTION_LENGTH)

    clean_project_name = project_name.strip() if isinstance(project_name, str) else ""
    if len(clean_project_name) > MAX_PROJECT_NAME_LENGTH:
        return message("invalid.project_name_too_long", limit=MAX_PROJECT_NAME_LENGTH)

    clean_due_string = due_string.strip() if isinstance(due_string, str) else None
    if clean_due_string and len(clean_due_string) > MAX_DUE_STRING_LENGTH:
        return message("invalid.due_string_too_long", limit=MAX_DUE_STRING_LENGTH)

    if not isinstance(priority, int) or priority < 1 or priority > 4:
        return message("invalid.priority")

    clean_labels = None
    if labels is not None:
        if isinstance(labels, list):
            clean_labels = [str(l).strip().lstrip("@") for l in labels if str(l).strip()]
        else:
            return message("invalid.labels_not_list")

    clean_section = section_name_or_id.strip() if isinstance(section_name_or_id, str) else None
    if clean_section and len(clean_section) > MAX_SECTION_NAME_LENGTH:
        return message("invalid.section_identifier_too_long", limit=MAX_SECTION_NAME_LENGTH)

    clean_parent_id = parent_id.strip() if isinstance(parent_id, str) else None
    if clean_parent_id and len(clean_parent_id) > MAX_TASK_ID_LENGTH:
        return message("invalid.parent_task_id_too_long", limit=MAX_TASK_ID_LENGTH)

    clean_deadline_date = deadline_date.strip() if isinstance(deadline_date, str) else None
    parsed_deadline_date = None
    if clean_deadline_date:
        try:
            parsed_deadline_date = date.fromisoformat(clean_deadline_date)
        except ValueError:
            return message("invalid.deadline_date_format", value=clean_deadline_date)

    failure_message = message("task.create_failed")
    try:
        api = client.get_api_client()

        # Resolve the target fully before creating anything. An empty project name means the Inbox.
        project = resolve_project(
            api, clean_project_name or INBOX_QUERY, allow_partial=True, allow_inbox_alias=True
        )
        if isinstance(project, LookupFailed):
            return failure_message
        if isinstance(project, Ambiguous):
            return ambiguous_message(project, "ambiguous.project")
        if isinstance(project, NotFound):
            return message("project.not_found", name=clean_project_name)
        project_id = project.id

        section_id = None
        section_display_name = ""
        if clean_section:
            # Sections are only searched inside the resolved project. An Inbox alias with no
            # listed Inbox has no project ID to scope by, so the section cannot be found.
            section = resolve_section(api, clean_section, project_id=project_id) if project_id else NotFound(clean_section)
            if isinstance(section, LookupFailed):
                return failure_message
            if isinstance(section, Ambiguous):
                return ambiguous_message(section, "ambiguous.section")
            if isinstance(section, NotFound):
                return message("section.not_found", name=clean_section)
            section_id, section_display_name = section.id, section.name

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

        due_info = task.due.string if task.due and task.due.string else (clean_due_string or message("task.due_not_specified"))
        project_display = project.name
        section_display = message("task.created.section_line", name=section_display_name, id=section_id) if section_id else ""
        labels_display = message("task.created.labels_line", labels=', '.join(['@' + l for l in task.labels])) if getattr(task, "labels", None) else ""
        deadline_display = message("task.created.deadline_line", date=clean_deadline_date) if clean_deadline_date else ""

        return message(
            "task.created",
            id=task.id,
            content=task.content,
            project=project_display,
            section_line=section_display,
            priority=task.priority,
            due=due_info,
            deadline_line=deadline_display,
            labels_line=labels_display,
            url=task.url,
        )
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to create task in Todoist (content_len=%d, error_type=%s)",
            len(clean_content),
            type(e).__name__,
            exc_info=False,
        )
        _log_http_error_detail(e)
        if _is_deadline_plan_restriction(e, parsed_deadline_date is not None):
            return message("task.deadline_plan_restricted")
        return failure_message


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
        return message("invalid.filter_query_empty")
    if len(clean_query) > MAX_FILTER_QUERY_LENGTH:
        return message("invalid.filter_query_too_long", limit=MAX_FILTER_QUERY_LENGTH)

    try:
        api = client.get_api_client()
        tasks = []
        for batch in api.filter_tasks(query=clean_query):
            tasks.extend(batch)

        if not tasks:
            return message("task.list.empty", query=clean_query)

        priority_labels = {p: message(f"task.priority.{p}") for p in (4, 3, 2, 1)}

        lines = [message("task.list.header", query=clean_query, count=len(tasks)), ""]
        for idx, task in enumerate(tasks, start=1):
            due_str = task.due.string if task.due and task.due.string else message("task.list.no_due")
            p_str = priority_labels.get(task.priority, f"p{task.priority}")
            labels_str = f" [{' '.join(['@' + l for l in task.labels])}]" if getattr(task, "labels", None) else ""
            lines.append(f"{idx}. [{task.id}] {task.content}{labels_str}")
            lines.append(message("task.list.priority_line", priority=p_str))
            lines.append(message("task.list.due_line", due=due_str))
            if task.description:
                lines.append(message("task.list.description_line", description=task.description))
            lines.append("")

        return "\n".join(lines).strip()
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve tasks from Todoist (filter_len=%d, error_type=%s)",
            len(clean_query),
            type(e).__name__,
            exc_info=False,
        )
        return message("task.list_failed")


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
        return message("invalid.task_id_empty")
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return message("invalid.task_id_too_long", limit=MAX_TASK_ID_LENGTH)

    try:
        api = client.get_api_client()
        task = api.get_task(task_id=clean_task_id)

        due_info = task.due.string if task.due and task.due.string else message("task.detail.not_set")
        labels_display = ", ".join(["@" + l for l in task.labels]) if getattr(task, "labels", None) else message("task.detail.none")
        description_display = task.description if task.description else message("task.detail.none")
        parent_display = task.parent_id if task.parent_id else message("task.detail.no_parent")
        section_display = task.section_id if task.section_id else message("task.detail.none")

        return message(
            "task.detail",
            id=task.id,
            content=task.content,
            description=description_display,
            project_id=task.project_id,
            section=section_display,
            parent=parent_display,
            priority=task.priority,
            due=due_info,
            labels=labels_display,
            url=task.url,
        )
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve task from Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        return message("task.get_failed", id=clean_task_id)


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
        return message("invalid.task_id_empty")
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return message("invalid.task_id_too_long", limit=MAX_TASK_ID_LENGTH)

    try:
        api = client.get_api_client()
        success = api.complete_task(task_id=clean_task_id)
        if success:
            return message("task.completed", id=clean_task_id)
        else:
            return message("task.complete_unconfirmed", id=clean_task_id)
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to complete task in Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        return message("task.complete_failed", id=clean_task_id)


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
        return message("invalid.task_id_empty")
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return message("invalid.task_id_too_long", limit=MAX_TASK_ID_LENGTH)

    try:
        api = client.get_api_client()
        success = api.uncomplete_task(task_id=clean_task_id)
        if success:
            return message("task.reopened", id=clean_task_id)
        else:
            return message("task.reopen_unconfirmed", id=clean_task_id)
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to reopen task in Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        return message("task.reopen_failed", id=clean_task_id)


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
        return message("invalid.task_id_empty")
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return message("invalid.task_id_too_long", limit=MAX_TASK_ID_LENGTH)

    clean_content = content.strip() if isinstance(content, str) else None
    if clean_content is not None and len(clean_content) > MAX_CONTENT_LENGTH:
        return message("invalid.task_content_too_long", limit=MAX_CONTENT_LENGTH)

    clean_description = description.strip() if isinstance(description, str) else None
    if clean_description is not None and len(clean_description) > MAX_DESCRIPTION_LENGTH:
        return message("invalid.task_description_too_long", limit=MAX_DESCRIPTION_LENGTH)

    clean_project_name = project_name.strip() if isinstance(project_name, str) else None
    if clean_project_name is not None and len(clean_project_name) > MAX_PROJECT_NAME_LENGTH:
        return message("invalid.project_name_too_long", limit=MAX_PROJECT_NAME_LENGTH)

    clean_due_string = due_string.strip() if isinstance(due_string, str) else None
    if clean_due_string is not None and len(clean_due_string) > MAX_DUE_STRING_LENGTH:
        return message("invalid.due_string_too_long", limit=MAX_DUE_STRING_LENGTH)

    if priority is not None and (not isinstance(priority, int) or priority < 1 or priority > 4):
        return message("invalid.priority")

    clean_labels = None
    if labels is not None:
        if isinstance(labels, list):
            clean_labels = [str(l).strip().lstrip("@") for l in labels if str(l).strip()]
        else:
            return message("invalid.labels_not_list")

    clean_section = section_name_or_id.strip() if isinstance(section_name_or_id, str) else None
    if clean_section is not None and len(clean_section) > MAX_SECTION_NAME_LENGTH:
        return message("invalid.section_identifier_too_long", limit=MAX_SECTION_NAME_LENGTH)

    # None = untouched; "" (after strip) = explicit "remove parent" request; non-empty = new parent ID.
    clean_parent_id = parent_id.strip() if isinstance(parent_id, str) else None
    if clean_parent_id is not None and len(clean_parent_id) > MAX_TASK_ID_LENGTH:
        return message("invalid.parent_task_id_too_long", limit=MAX_TASK_ID_LENGTH)

    clean_deadline_date = deadline_date.strip() if isinstance(deadline_date, str) else None
    parsed_deadline_date = None
    if clean_deadline_date:
        try:
            parsed_deadline_date = date.fromisoformat(clean_deadline_date)
        except ValueError:
            return message("invalid.deadline_date_format", value=clean_deadline_date)

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
        return message("task.update.no_fields")

    failure_message = message("task.update_failed", id=clean_task_id)
    try:
        api = client.get_api_client()
        updated_fields = []

        # 1. Resolve the move target (project, then section) before writing anything.
        target_project_id = None
        target_project_name = None
        if clean_project_name is not None:
            project = resolve_project(api, clean_project_name, allow_partial=True, allow_inbox_alias=True)
            if isinstance(project, LookupFailed):
                return failure_message
            if isinstance(project, Ambiguous):
                return ambiguous_message(project, "ambiguous.project")
            # Found(None, ...) is an Inbox alias with no listed Inbox: moving needs a real project ID.
            if isinstance(project, NotFound) or project.id is None:
                return message("task.update.target_project_not_found", name=clean_project_name)
            target_project_id, target_project_name = project.id, project.name

        target_section_id = None
        sec_name = None
        if clean_section is not None:
            # Sections are only searched inside the target project, or the task's current one.
            scope_project_id = target_project_id
            if scope_project_id is None:
                # A resolution step: on failure log error_type only, never the HTTP status/body.
                try:
                    scope_project_id = api.get_task(task_id=clean_task_id).project_id
                except MissingMessageError:
                    raise
                except Exception as e:
                    logger.error(
                        "Failed to look up the task's current project for section resolution (task_id=%s, error_type=%s)",
                        clean_task_id,
                        type(e).__name__,
                        exc_info=False,
                    )
                    return failure_message
            section = resolve_section(api, clean_section, project_id=scope_project_id)
            if isinstance(section, LookupFailed):
                return failure_message
            if isinstance(section, Ambiguous):
                return ambiguous_message(section, "ambiguous.section")
            if isinstance(section, NotFound):
                return message("task.update.target_section_not_found", name=clean_section)
            target_section_id, sec_name = section.id, section.name

        # 2. Update task attributes if provided
        update_kwargs = {}
        if clean_content is not None:
            update_kwargs["content"] = clean_content
            updated_fields.append(message("task.update.change.content", value=clean_content))
        if clean_description is not None:
            update_kwargs["description"] = clean_description
            updated_fields.append(message("task.update.change.description", value=clean_description))
        if clean_due_string is not None:
            update_kwargs["due_string"] = clean_due_string
            updated_fields.append(message("task.update.change.due", value=clean_due_string))
        if priority is not None:
            update_kwargs["priority"] = priority
            updated_fields.append(message("task.update.change.priority", value=priority))
        if clean_labels is not None:
            update_kwargs["labels"] = clean_labels
            updated_fields.append(
                message(
                    "task.update.change.labels",
                    value=', '.join(['@' + l for l in clean_labels]) if clean_labels else message("task.update.change.labels_cleared"),
                )
            )
        if parsed_deadline_date is not None:
            update_kwargs["deadline_date"] = parsed_deadline_date
            updated_fields.append(message("task.update.change.deadline", value=clean_deadline_date))

        if update_kwargs:
            api.update_task(task_id=clean_task_id, **update_kwargs)

        # 3. Move task to target project / section / parent if requested.
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
                if target_project_name is not None:
                    updated_fields.append(message("task.update.change.project", name=target_project_name, id=target_project_id))
            if target_section_id is not None:
                move_kwargs["section_id"] = target_section_id
                updated_fields.append(message("task.update.change.section", name=sec_name, id=target_section_id))
            if target_parent_id is not None:
                move_kwargs["parent_id"] = target_parent_id
                updated_fields.append(message("task.update.change.parent", id=target_parent_id))
            elif unparent_requested:
                updated_fields.append(message("task.update.change.parent_removed"))

            api.move_task(task_id=clean_task_id, **move_kwargs)

        changes_summary = "\n".join([f"• {field}" for field in updated_fields])
        return message("task.updated", id=clean_task_id, changes=changes_summary)
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to update task in Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        _log_http_error_detail(e)
        if _is_deadline_plan_restriction(e, parsed_deadline_date is not None):
            return message("task.deadline_plan_restricted")
        return failure_message


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
        return message("invalid.task_id_empty")
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return message("invalid.task_id_too_long", limit=MAX_TASK_ID_LENGTH)

    try:
        api = client.get_api_client()
        success = api.delete_task(task_id=clean_task_id)
        if success:
            return message("task.deleted", id=clean_task_id)
        else:
            return message("task.delete_unconfirmed", id=clean_task_id)
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete task in Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        return message("task.delete_failed", id=clean_task_id)
