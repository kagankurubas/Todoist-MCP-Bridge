"""
Unit tests for the Todoist FastMCP Server name-resolution helpers.
All tests use mocks to ensure zero network calls and deterministic results.
"""

from unittest.mock import MagicMock
from plugvan.todoist.resolvers import (
    _find_project_id,
)
from tests.todoist.helpers import (
    MockProject,
)


# =====================================================================
# PROJECT RESOLUTION TESTS
# =====================================================================

def test_find_project_id_exact_and_case_insensitive():
    mock_api = MagicMock()
    mock_api.get_projects.return_value = [
        [
            MockProject("p1", "Inbox", is_inbox=True),
            MockProject("p2", "Odak & Gelişim"),
            MockProject("p3", "Kişisel Projeler"),
        ]
    ]

    assert _find_project_id(mock_api, "Odak & Gelişim") == "p2"
    assert _find_project_id(mock_api, "odak & gelişim") == "p2"
    assert _find_project_id(mock_api, "KİŞİSEL PROJELER") == "p3"


def test_find_project_id_inbox_aliases():
    mock_api = MagicMock()
    mock_api.get_projects.return_value = [
        [MockProject("inbox_99", "Gelen Kutusu", is_inbox=True)]
    ]

    assert _find_project_id(mock_api, "Inbox") == "inbox_99"
    assert _find_project_id(mock_api, "gelen kutusu") == "inbox_99"
    assert _find_project_id(mock_api, "GelenKutusu") == "inbox_99"


def test_find_project_id_partial_match_fallback():
    mock_api = MagicMock()
    mock_api.get_projects.return_value = [
        [MockProject("p_sub", "Yazılım Geliştirme Çalışmaları")]
    ]

    assert _find_project_id(mock_api, "Yazılım Geliştirme") == "p_sub"


def test_find_project_id_api_failure_fallback():
    mock_api = MagicMock()
    mock_api.get_projects.side_effect = RuntimeError("Network timeout")

    assert _find_project_id(mock_api, "Nonexistent") is None
