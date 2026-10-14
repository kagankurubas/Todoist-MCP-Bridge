"""
Tests for the message catalog's missing-key contract.
A key missing in the selected language must surface as an error, never as a generic
user-facing failure message.
"""

import ast
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from plugvan.todoist.messages import CATALOGS, MissingMessageError
from plugvan.todoist.server import mcp
from tests.todoist.helpers import MockProject, write_call_count

PACKAGE_DIR = Path(__file__).resolve().parents[2] / "plugvan" / "todoist"


@patch("plugvan.todoist.client.get_api_client")
def test_missing_key_surfaces_as_tool_error_not_generic_failure(mock_get_client, monkeypatch):
    mock_api = MagicMock()
    mock_api.get_projects.return_value = [[MockProject("p1", "Proje A"), MockProject("p2", "Proje B")]]
    mock_get_client.return_value = mock_api
    monkeypatch.delitem(CATALOGS["tr"], "ambiguous.project")

    with pytest.raises(ToolError) as exc_info:
        asyncio.run(mcp.call_tool("create_task", {"content": "X", "project_name": "Proje"}))

    cause = exc_info.value.__cause__
    assert isinstance(cause, MissingMessageError)
    assert str(cause) == "No 'ambiguous.project' message for language 'tr'"
    assert str(exc_info.value) == "Error executing tool create_task: No 'ambiguous.project' message for language 'tr'"
    assert "Check server logs" not in str(exc_info.value)
    assert write_call_count(mock_api) == 0


def _is_reraise_of_missing_message(handler: ast.ExceptHandler) -> bool:
    return (
        isinstance(handler.type, ast.Name)
        and handler.type.id == "MissingMessageError"
        and len(handler.body) == 1
        and isinstance(handler.body[0], ast.Raise)
        and handler.body[0].exc is None
    )


def test_every_broad_handler_reraises_missing_message_first():
    checked = 0
    violations = []
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            for index, handler in enumerate(node.handlers):
                if isinstance(handler.type, ast.Name) and handler.type.id == "Exception":
                    checked += 1
                    if index == 0 or not _is_reraise_of_missing_message(node.handlers[index - 1]):
                        violations.append(f"{path.relative_to(PACKAGE_DIR)}:{handler.lineno}")

    assert checked > 0
    assert violations == []
