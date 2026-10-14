"""
Surface snapshot test for the Todoist FastMCP Server.
Compares the published tool list (name, description, input and output schema) against a
fixture recorded once from the original single-file server. The fixture is the behavior
baseline for the package move and must never be regenerated; editing it means accepting a
behavior change. The surface does not depend on the output language.
"""

import asyncio
import json
from pathlib import Path

from plugvan.todoist.server import mcp

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "todoist_mcp_tool_surface.json"
COMPARED_FIELDS = ("description", "inputSchema", "outputSchema")


def _load_expected() -> dict:
    with FIXTURE_PATH.open(encoding="utf-8") as f:
        return {tool["name"]: tool for tool in json.load(f)}


def _load_actual() -> dict:
    tools = asyncio.run(mcp.list_tools())
    return {
        tool.name: {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.inputSchema,
            "outputSchema": tool.outputSchema,
        }
        for tool in tools
    }


def test_tool_names_match_snapshot():
    expected = _load_expected()
    actual = _load_actual()

    assert len(expected) == 22
    assert sorted(actual) == sorted(expected), (
        f"missing: {sorted(set(expected) - set(actual))}, unexpected: {sorted(set(actual) - set(expected))}"
    )


def _definition_mismatches() -> list[str]:
    expected = _load_expected()
    actual = _load_actual()
    return [
        f"{name}.{field}"
        for name in sorted(expected.keys() & actual.keys())
        for field in COMPARED_FIELDS
        if actual[name][field] != expected[name][field]
    ]


def test_tool_definitions_match_snapshot():
    mismatches = _definition_mismatches()
    assert not mismatches, f"Tool surface differs from snapshot: {mismatches}"


def test_tool_definitions_match_snapshot_in_turkish(monkeypatch):
    monkeypatch.setenv("PLUGVAN_LANG", "tr")

    mismatches = _definition_mismatches()
    assert not mismatches, f"Tool surface differs from snapshot with PLUGVAN_LANG=tr: {mismatches}"
