"""
Unit and security tests for the Todoist FastMCP Server: comment tools.
All tests use mocks to ensure zero network calls and deterministic results.
"""

from unittest.mock import MagicMock, patch
from plugvan.todoist.tools.comments import (
    add_comment,
    get_comments,
)
from tests.todoist.helpers import (
    MockComment,
)


# =====================================================================
# COMMENTS (ADD_COMMENT, GET_COMMENTS) TESTS
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_add_comment_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.add_comment.return_value = MockComment(
        comment_id="comm_1",
        content="Bu görev için ilk not.",
        task_id="task_99",
        posted_at="2026-08-24T15:00:00Z",
    )

    result = add_comment(task_id="task_99", content="Bu görev için ilk not.")
    assert "💬 Yorum başarıyla eklendi!" in result
    assert "Yorum ID: comm_1" in result
    assert "Görev ID: task_99" in result
    assert "İçerik: Bu görev için ilk not." in result
    mock_api.add_comment.assert_called_once_with(content="Bu görev için ilk not.", task_id="task_99")


def test_add_comment_empty_content():
    result = add_comment(task_id="task_1", content="   ")
    assert "❌ Invalid input: Comment content cannot be empty" in result


@patch("plugvan.todoist.client.get_api_client")
def test_get_comments_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    c1 = MockComment("c1", "Not 1", task_id="task_1", posted_at="2026-08-24 10:00")
    c2 = MockComment("c2", "Not 2", task_id="task_1", posted_at="2026-08-24 11:00")
    mock_api.get_comments.return_value = [[c1, c2]]

    result = get_comments(task_id="task_1")
    assert "💬 Görev Yorumları (Görev ID: task_1, Toplam: 2):" in result
    assert "1. [c1] [2026-08-24 10:00] Not 1" in result
    assert "2. [c2] [2026-08-24 11:00] Not 2" in result


@patch("plugvan.todoist.client.get_api_client")
def test_get_comments_empty(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_comments.return_value = [[]]

    result = get_comments(task_id="task_no_comm")
    assert "ℹ️ Göreve ait (ID: task_no_comm) herhangi bir yorum veya not bulunamadı." in result
