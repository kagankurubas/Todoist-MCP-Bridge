"""
Tests that the test session never sees real credentials.
tests/conftest.py assigns a fake TODOIST_API_TOKEN before any test runs, and that fake is
what plugvan.todoist.client.get_api_client() hands to the Todoist SDK.
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from plugvan.todoist import client

FAKE_TODOIST_API_TOKEN = "test-todoist-token-not-real"

# Shaped like a real Todoist token (40 hex chars); not a real credential.
REAL_LOOKING_TODOIST_API_TOKEN = "0f1e2d3c4b5a69788796a5b4c3d2e1f00f1e2d3c"

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_mcp_client_receives_fake_test_token():
    with patch.object(client, "TodoistAPI") as mock_sdk:
        api = client.get_api_client()

    mock_sdk.assert_called_once_with(FAKE_TODOIST_API_TOKEN)
    assert api is mock_sdk.return_value


def test_real_looking_token_in_shell_never_reaches_tests():
    """Runs the test above in a fresh pytest process whose environment holds a real-looking
    token: the conftest must overwrite it before the MCP client reads it."""
    env = {**os.environ, "TODOIST_API_TOKEN": REAL_LOOKING_TODOIST_API_TOKEN}

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
            f"{Path(__file__).resolve()}::test_mcp_client_receives_fake_test_token",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )

    assert result.returncode == 0, result.stdout[-3000:]
    assert "1 passed" in result.stdout, result.stdout[-3000:]
    assert REAL_LOOKING_TODOIST_API_TOKEN not in result.stdout
