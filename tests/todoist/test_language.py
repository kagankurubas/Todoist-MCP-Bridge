"""
Unit tests for output language selection (PLUGVAN_LANG).
tests/conftest.py removes PLUGVAN_LANG before the session, so each test sets it explicitly.
"""

import logging

import pytest

from plugvan.todoist import language
from plugvan.todoist.language import (
    DEFAULT_LANGUAGE,
    MAX_LOGGED_LANGUAGE_VALUE_LENGTH,
    current_language,
)


@pytest.fixture(autouse=True)
def _fresh_warning_state(monkeypatch):
    monkeypatch.setattr(language, "_unsupported_value_warned", False)


def _language_warnings(caplog):
    return [r for r in caplog.records if r.name == "todoist_mcp" and r.levelno == logging.WARNING]


def test_default_language_is_tr_until_the_switch():
    assert DEFAULT_LANGUAGE == "tr"


def test_unset_uses_default(monkeypatch):
    monkeypatch.delenv("PLUGVAN_LANG", raising=False)
    assert current_language() == DEFAULT_LANGUAGE


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_uses_default_without_warning(monkeypatch, caplog, value):
    monkeypatch.setenv("PLUGVAN_LANG", value)
    with caplog.at_level(logging.WARNING, logger="todoist_mcp"):
        assert current_language() == DEFAULT_LANGUAGE
    assert _language_warnings(caplog) == []


@pytest.mark.parametrize(
    "value, expected",
    [("en", "en"), (" EN ", "en"), ("tr", "tr"), ("TR", "tr"), ("\ttr\n", "tr")],
)
def test_supported_values_are_honored(monkeypatch, caplog, value, expected):
    monkeypatch.setenv("PLUGVAN_LANG", value)
    with caplog.at_level(logging.WARNING, logger="todoist_mcp"):
        assert current_language() == expected
    assert _language_warnings(caplog) == []


@pytest.mark.parametrize("value", ["de", "tr_TR", "tr-TR", "turkish"])
def test_unsupported_value_falls_back_with_one_warning(monkeypatch, caplog, value):
    monkeypatch.setenv("PLUGVAN_LANG", value)
    with caplog.at_level(logging.WARNING, logger="todoist_mcp"):
        results = [current_language() for _ in range(5)]

    assert results == [DEFAULT_LANGUAGE] * 5
    warnings = _language_warnings(caplog)
    assert len(warnings) == 1
    assert repr(value) in warnings[0].getMessage()


def test_logged_unsupported_value_is_capped(monkeypatch, caplog):
    long_value = "x" * 500
    monkeypatch.setenv("PLUGVAN_LANG", long_value)
    with caplog.at_level(logging.WARNING, logger="todoist_mcp"):
        assert current_language() == DEFAULT_LANGUAGE

    message = _language_warnings(caplog)[0].getMessage()
    assert repr("x" * MAX_LOGGED_LANGUAGE_VALUE_LENGTH) in message
    assert "x" * (MAX_LOGGED_LANGUAGE_VALUE_LENGTH + 1) not in message


def test_language_is_read_on_every_call(monkeypatch):
    monkeypatch.setenv("PLUGVAN_LANG", "en")
    assert current_language() == "en"
    monkeypatch.setenv("PLUGVAN_LANG", "tr")
    assert current_language() == "tr"
