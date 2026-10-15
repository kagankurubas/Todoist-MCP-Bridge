"""
In-process tests for the `plugvan-mcp` console script (plugvan.cli.main) and for the
`python -m plugvan.todoist` entry point.

The Todoist run function, plugvan.todoist.run, is the single patch target: no test starts a
real server. The console-script path must never read `.env`; only `python -m plugvan.todoist`
does, before calling the same run function.
"""

import runpy
import sys
from contextlib import contextmanager
from importlib import import_module, metadata
from unittest.mock import MagicMock, call, patch

import pytest

DISTRIBUTION = "plugvan-mcp"
DOTENV_FUNCTIONS = ("load_dotenv", "find_dotenv", "dotenv_values")


def _run_cli(argv, capsys):
    from plugvan import cli

    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def test_todoist_dispatches_to_the_run_function_once(capsys):
    with patch("plugvan.todoist.run") as run:
        code, out, err = _run_cli(["todoist"], capsys)

    assert code == 0
    assert run.call_args_list == [call()]
    assert out == ""


@pytest.mark.parametrize("argv", [[], ["nosuch"]], ids=["no-arguments", "unknown-integration"])
def test_missing_or_unknown_integration_is_a_usage_error_on_stderr(argv, capsys):
    with patch("plugvan.todoist.run") as run:
        code, out, err = _run_cli(argv, capsys)

    assert code == 2
    assert out == ""
    assert "usage:" in err
    assert "todoist" in err
    run.assert_not_called()


def test_version_prints_the_installed_version(capsys):
    code, out, err = _run_cli(["--version"], capsys)

    assert code == 0
    assert out == f"plugvan-mcp {metadata.version(DISTRIBUTION)}\n"
    assert err == ""


def test_version_without_package_metadata_prints_unknown(capsys):
    with patch("importlib.metadata.version", side_effect=metadata.PackageNotFoundError(DISTRIBUTION)):
        code, out, err = _run_cli(["--version"], capsys)

    assert code == 0
    assert out == "plugvan-mcp unknown\n"
    assert err == ""


def test_help_exits_zero(capsys):
    with patch("plugvan.todoist.run") as run:
        code, out, err = _run_cli(["--help"], capsys)

    assert code == 0
    assert "todoist" in out
    run.assert_not_called()


@contextmanager
def _fresh_plugvan_modules():
    """Imports plugvan modules afresh inside the block, then restores the originals, so
    import-time behaviour can be observed without disturbing the rest of the session."""
    saved = {name: module for name, module in sys.modules.items() if name == "plugvan" or name.startswith("plugvan.")}
    for name in saved:
        del sys.modules[name]
    try:
        yield
    finally:
        for name in [name for name in sys.modules if name == "plugvan" or name.startswith("plugvan.")]:
            del sys.modules[name]
        sys.modules.update(saved)


def _forbidden_dotenv():
    """Patches every dotenv entry point that can read a .env file to fail loudly."""
    mocks = {name: MagicMock(name=name, side_effect=AssertionError(f"dotenv.{name} called")) for name in DOTENV_FUNCTIONS}
    patches = [patch(f"dotenv.{name}", mock) for name, mock in mocks.items()]
    patches += [patch(f"dotenv.main.{name}", mock) for name, mock in mocks.items()]
    return mocks, patches


def test_console_script_never_reads_dotenv_at_import_or_run(capsys):
    mocks, patches = _forbidden_dotenv()
    with _fresh_plugvan_modules():
        for p in patches:
            p.start()
        try:
            cli = import_module("plugvan.cli")
            # The real run function, with the server loop and logging setup stubbed out:
            # imports the server module and starts it, as the console script does.
            with patch("mcp.server.fastmcp.FastMCP.run") as server_run, patch("logging.basicConfig"):
                code = cli.main(["todoist"])
        finally:
            for p in patches:
                p.stop()

    assert code == 0
    server_run.assert_called_once()
    assert all(mock.call_count == 0 for mock in mocks.values()), {
        name: mock.call_count for name, mock in mocks.items()
    }
    assert capsys.readouterr().out == ""


def test_python_m_entry_loads_dotenv_before_running():
    order = MagicMock()
    with patch("dotenv.load_dotenv", order.load_dotenv), patch("plugvan.todoist.run", order.run), \
            patch("logging.basicConfig"):
        runpy.run_module("plugvan.todoist", run_name="__main__")

    # Default arguments: override stays False, so variables from the MCP client's env block win.
    assert order.mock_calls == [call.load_dotenv(), call.run()]
