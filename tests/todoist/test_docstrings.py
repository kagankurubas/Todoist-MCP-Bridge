"""
Tests for tool description normalization.

Python 3.13+ strips docstring indentation at compile time; 3.10-3.12 keep it. The raw
docstrings below are what 3.10-3.12 store in __doc__, so these tests simulate the older
compilers on every version.
"""

import asyncio
import sys

import pytest

from plugvan.todoist.docstrings import clean_docstring
from plugvan.todoist.server import TOOLS, mcp

RAW_TO_CLEAN = [
    pytest.param(
        "Creates a task.\n\n    Args:\n        content: Title.\n        project: Target.\n    ",
        "Creates a task.\n\nArgs:\n    content: Title.\n    project: Target.\n",
        id="indented-args-section-keeps-trailing-newline",
    ),
    pytest.param(
        "Summary.\n\n        \n    Body line.\n    ",
        "Summary.\n\n    \nBody line.\n",
        id="whitespace-line-longer-than-margin-keeps-the-excess",
    ),
    pytest.param(
        "Summary.\n  \n    Body line.\n",
        "Summary.\n\nBody line.\n",
        id="whitespace-line-shorter-than-margin-is-emptied",
    ),
    pytest.param(
        "Lists all labels.",
        "Lists all labels.",
        id="single-line",
    ),
    pytest.param(
        "   Lists all labels.  ",
        "Lists all labels.  ",
        id="single-line-leading-spaces-stripped-trailing-kept",
    ),
    pytest.param(
        "\n    Summary on the second line.\n    ",
        "\nSummary on the second line.\n",
        id="leading-blank-line-is-kept",
    ),
    pytest.param(
        "Summary.\n\tArgs:\n\t\tx: value.\n\t",
        "Summary.\nArgs:\n        x: value.\n",
        id="tabs-expanded-before-dedent",
    ),
]


@pytest.mark.parametrize("raw, expected", RAW_TO_CLEAN)
def test_clean_docstring_matches_compiler_cleaning(raw, expected):
    assert clean_docstring(raw) == expected


@pytest.mark.parametrize("raw, expected", RAW_TO_CLEAN)
def test_clean_docstring_is_idempotent(raw, expected):
    assert clean_docstring(clean_docstring(raw)) == clean_docstring(raw)


def test_clean_docstring_without_docstring():
    def no_doc():
        pass

    assert clean_docstring(no_doc.__doc__) is None


@pytest.mark.skipif(sys.version_info < (3, 13), reason="needs the 3.13+ compiler as the reference")
@pytest.mark.parametrize("raw, expected", RAW_TO_CLEAN)
def test_expected_values_match_the_real_313_compiler(raw, expected):
    namespace: dict = {}
    exec(compile(f"def f():\n    {raw!r}\n", "<docstring>", "exec"), namespace)

    assert namespace["f"].__doc__ == expected


@pytest.mark.skipif(sys.version_info < (3, 13), reason="__doc__ is only pre-cleaned by the 3.13+ compiler")
def test_clean_docstring_is_identity_for_all_tools_on_313_plus():
    assert len(TOOLS) == 22
    changed = [tool.__name__ for tool in TOOLS if clean_docstring(tool.__doc__) != tool.__doc__]
    assert changed == []


def test_registered_descriptions_are_cleaned_docstrings():
    published = {tool.name: tool.description for tool in asyncio.run(mcp.list_tools())}

    assert published == {tool.__name__: clean_docstring(tool.__doc__) for tool in TOOLS}
