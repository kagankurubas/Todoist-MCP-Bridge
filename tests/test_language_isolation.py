"""
Tests that a PLUGVAN_LANG value in the shell never reaches the test session.
tests/conftest.py removes PLUGVAN_LANG before any test runs, so every test starts from the
code's default output language.
"""

import os
import subprocess
import sys
from pathlib import Path

from plugvan.todoist.language import current_language

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_session_starts_from_default_language():
    # A boolean with a fixed message, so a failure can never echo the process environment.
    leaked = "PLUGVAN_LANG" in os.environ
    assert not leaked, "PLUGVAN_LANG from the environment reached the test session"
    assert current_language() == "en"


def test_plugvan_lang_in_shell_never_reaches_tests():
    """Runs the test above in a fresh pytest process whose environment selects the
    non-default language: the conftest must remove it before any test runs."""
    env = {**os.environ, "PLUGVAN_LANG": "tr"}

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
            f"{Path(__file__).resolve()}::test_session_starts_from_default_language",
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
