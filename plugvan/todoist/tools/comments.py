"""Todoist comment tools."""

import logging
from typing import Annotated

from pydantic import Field

from plugvan.todoist import client
from plugvan.todoist.limits import (
    MAX_TASK_ID_LENGTH,
    MAX_COMMENT_LENGTH,
)

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
        return "❌ Invalid input: Task ID cannot be empty or whitespace."
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return f"❌ Invalid input: Task ID exceeds maximum length of {MAX_TASK_ID_LENGTH} characters."

    clean_content = content.strip() if isinstance(content, str) else ""
    if not clean_content:
        return "❌ Invalid input: Comment content cannot be empty or whitespace."
    if len(clean_content) > MAX_COMMENT_LENGTH:
        return f"❌ Invalid input: Comment content exceeds maximum length of {MAX_COMMENT_LENGTH} characters."

    try:
        api = client.get_api_client()
        comment = api.add_comment(content=clean_content, task_id=clean_task_id)

        posted_str = f"\n• Tarih: {comment.posted_at}" if getattr(comment, "posted_at", None) else ""

        return (
            f"💬 Yorum başarıyla eklendi!\n"
            f"• Yorum ID: {comment.id}\n"
            f"• Görev ID: {clean_task_id}\n"
            f"• İçerik: {comment.content}"
            f"{posted_str}"
        )
    except Exception as e:
        logger.error(
            "Failed to add comment to task in Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        return f"❌ Failed to add comment to task (ID: {clean_task_id}) in Todoist. Check server logs for details."


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
        return "❌ Invalid input: Task ID cannot be empty or whitespace."
    if len(clean_task_id) > MAX_TASK_ID_LENGTH:
        return f"❌ Invalid input: Task ID exceeds maximum length of {MAX_TASK_ID_LENGTH} characters."

    try:
        api = client.get_api_client()
        comments = []
        for batch in api.get_comments(task_id=clean_task_id):
            comments.extend(batch)

        if not comments:
            return f"ℹ️ Göreve ait (ID: {clean_task_id}) herhangi bir yorum veya not bulunamadı."

        lines = [f"💬 Görev Yorumları (Görev ID: {clean_task_id}, Toplam: {len(comments)}):", ""]
        for idx, comment in enumerate(comments, start=1):
            posted = f" [{comment.posted_at}]" if getattr(comment, "posted_at", None) else ""
            lines.append(f"{idx}. [{comment.id}]{posted} {comment.content}")

        return "\n".join(lines).strip()
    except Exception as e:
        logger.error(
            "Failed to retrieve comments from Todoist (task_id=%s, error_type=%s)",
            clean_task_id,
            type(e).__name__,
            exc_info=False,
        )
        return f"❌ Failed to retrieve comments for task (ID: {clean_task_id}) from Todoist. Check server logs for details."
