"""
Tests that the test session never sees real credentials.
tests/conftest.py assigns fake values before config.py builds its settings at import time.
"""

import os
import subprocess
import sys
from pathlib import Path

FAKE_TODOIST_API_TOKEN = "test-todoist-token-not-real"
FAKE_WEBHOOK_SECRET_TOKEN = "test-webhook-secret-not-real"

# Shaped like a real Todoist token (40 hex chars); not a real credential.
REAL_LOOKING_TODOIST_API_TOKEN = "0f1e2d3c4b5a69788796a5b4c3d2e1f00f1e2d3c"
REAL_LOOKING_WEBHOOK_SECRET_TOKEN = "Zx9-real-looking-webhook-secret-Qw7"

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_settings_use_fake_test_credentials():
    from config import settings

    assert os.environ["TODOIST_API_TOKEN"] == FAKE_TODOIST_API_TOKEN
    assert os.environ["WEBHOOK_SECRET_TOKEN"] == FAKE_WEBHOOK_SECRET_TOKEN
    assert settings.TODOIST_API_TOKEN == FAKE_TODOIST_API_TOKEN
    assert settings.WEBHOOK_SECRET_TOKEN == FAKE_WEBHOOK_SECRET_TOKEN


def test_real_looking_token_in_shell_never_reaches_tests():
    """Runs the test above in a fresh pytest process whose environment holds real-looking
    credentials: the conftest must overwrite them before config.py is imported."""
    env = {
        **os.environ,
        "TODOIST_API_TOKEN": REAL_LOOKING_TODOIST_API_TOKEN,
        "WEBHOOK_SECRET_TOKEN": REAL_LOOKING_WEBHOOK_SECRET_TOKEN,
    }

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
            f"{Path(__file__).resolve()}::test_settings_use_fake_test_credentials",
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
    assert REAL_LOOKING_TODOIST_API_TOKEN not in result.stdout
