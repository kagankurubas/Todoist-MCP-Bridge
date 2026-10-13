"""
Shared mock objects and helpers for the Todoist MCP tool tests.
"""

from unittest.mock import MagicMock
import httpx


class MockProject:
    """Mock Todoist project object."""

    def __init__(
        self,
        project_id: str,
        name: str,
        is_inbox: bool = False,
        color: str = None,
        url: str = None,
        parent_id: str = None,
        is_favorite: bool = False,
        view_style: str = None,
    ):
        self.id = project_id
        self.name = name
        self.is_inbox_project = is_inbox
        self.color = color
        self.url = url or f"https://app.todoist.com/app/project/{project_id}"
        self.parent_id = parent_id
        self.is_favorite = is_favorite
        self.view_style = view_style


class MockLabel:
    """Mock Todoist label object."""

    def __init__(self, label_id: str, name: str, color: str = None, is_favorite: bool = False):
        self.id = label_id
        self.name = name
        self.color = color
        self.is_favorite = is_favorite


class MockSection:
    """Mock Todoist section object."""

    def __init__(self, section_id: str, name: str, project_id: str = "proj_default", order: int = 1):
        self.id = section_id
        self.name = name
        self.project_id = project_id
        self.order = order


class MockComment:
    """Mock Todoist comment object."""

    def __init__(self, comment_id: str, content: str, task_id: str = "task_default", posted_at: str = "2026-08-24T12:00:00Z"):
        self.id = comment_id
        self.content = content
        self.task_id = task_id
        self.posted_at = posted_at


def _make_http_status_error(status_code: int, text: str = "") -> httpx.HTTPStatusError:
    """Builds a real httpx.HTTPStatusError with a `.response` carrying the given status/body,
    matching what the todoist_api_python SDK raises on a non-2xx response."""
    request = httpx.Request("POST", "https://api.todoist.com/api/v1/tasks")
    response = httpx.Response(status_code, text=text, request=request)
    return httpx.HTTPStatusError(f"{status_code} error", request=request, response=response)


class MockTask:
    """Mock Todoist task object."""

    def __init__(
        self,
        task_id: str,
        content: str,
        priority: int = 1,
        due_string: str = None,
        description: str = "",
        url: str = None,
        labels: list = None,
        section_id: str = None,
        project_id: str = "proj_default",
        parent_id: str = None,
    ):
        self.id = task_id
        self.content = content
        self.priority = priority
        self.project_id = project_id
        self.parent_id = parent_id
        self.due = MagicMock(string=due_string) if due_string else None
        self.description = description
        self.url = url or f"https://app.todoist.com/app/task/{task_id}"
        self.labels = labels or []
        self.section_id = section_id
