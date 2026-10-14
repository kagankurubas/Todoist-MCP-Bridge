"""Todoist comment tools."""

import logging
from typing import Annotated

from pydantic import Field

from plugvan.todoist import client
from plugvan.todoist.limits import (
    MAX_TASK_ID_LENGTH,
    MAX_COMMENT_LENGTH,
)
from plugvan.todoist.messages import MissingMessageError, message

logger = logging.getLogger("todoist_mcp")


def add_comment(
    task_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_TASK_ID_LENGTH,
            description="The Todoist Task ID to attach the comment to (required).",
        ),
    ],
    content: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_COMMENT_LENGTH,
            description="The text content or markdown note of the comment (required).",
        ),
    ],
) -> str:
    """Adds a comment or note to an existing Todoist task.

    Args:
        task_id: ID of the task to attach the comment to.
        content: Comment text or markdown notes (max 4096 chars).
    """
    clean_task_id = str(task_id).strip() if task_id is not None else ""
    if not clean_task_id:
        return message("invalid.task_id_empty")
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return message("invalid.task_id_too_long", limit=MAX_TASK_ID_LENGTH)

    clean_content = content.strip() if isinstance(content, str) else ""
    if not clean_content:
        return message("invalid.comment_content_empty")
    if len(clean_content) > MAX_COMMENT_LENGTH:
        return message("invalid.comment_content_too_long", limit=MAX_COMMENT_LENGTH)

    try:
        api = client.get_api_client()
        comment = api.add_comment(content=clean_content, task_id=clean_task_id)

        posted_str = message("comment.added.posted_line", posted_at=comment.posted_at) if getattr(comment, "posted_at", None) else ""

        return message(
            "comment.added", id=comment.id, task_id=clean_task_id, content=comment.content, posted_line=posted_str
        )
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to add comment to task in Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        return message("comment.add_failed", task_id=clean_task_id)


def get_comments(
    task_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_TASK_ID_LENGTH,
            description="The Todoist Task ID to retrieve comments for (required).",
        ),
    ],
) -> str:
    """Retrieves all comments and notes attached to a specific Todoist task.

    Args:
        task_id: The ID of the task whose comments will be retrieved.
    """
    clean_task_id = str(task_id).strip() if task_id is not None else ""
    if not clean_task_id:
        return message("invalid.task_id_empty")
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return message("invalid.task_id_too_long", limit=MAX_TASK_ID_LENGTH)

    try:
        api = client.get_api_client()
        comments = []
        for batch in api.get_comments(task_id=clean_task_id):
            comments.extend(batch)

        if not comments:
            return message("comment.list.empty", task_id=clean_task_id)

        lines = [message("comment.list.header", task_id=clean_task_id, count=len(comments)), ""]
        for idx, comment in enumerate(comments, start=1):
            posted = f" [{comment.posted_at}]" if getattr(comment, "posted_at", None) else ""
            lines.append(f"{idx}. [{comment.id}]{posted} {comment.content}")

        return "\n".join(lines).strip()
    except MissingMessageError:
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve comments from Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        return message("comment.list_failed", task_id=clean_task_id)
