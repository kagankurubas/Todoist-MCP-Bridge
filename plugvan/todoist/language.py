"""Output language selection: PLUGVAN_LANG, read from the environment on every call."""

import logging
import os

logger = logging.getLogger("todoist_mcp")

SUPPORTED_LANGUAGES = ("en", "tr")
DEFAULT_LANGUAGE = "tr"
MAX_LOGGED_LANGUAGE_VALUE_LENGTH = 32

_unsupported_value_warned = False


def current_language() -> str:
    """Returns the selected output language: PLUGVAN_LANG trimmed and lowercased if it is a
    supported code, otherwise the default. An unsupported value is logged once per process."""
    global _unsupported_value_warned
    raw = os.getenv("PLUGVAN_LANG")
    if raw is None or not raw.strip():
        return DEFAULT_LANGUAGE
    language = raw.strip().lower()
    if language in SUPPORTED_LANGUAGES:
        return language
    if not _unsupported_value_warned:
        _unsupported_value_warned = True
        logger.warning(
            "Unsupported PLUGVAN_LANG value %r; using %r",
            raw[:MAX_LOGGED_LANGUAGE_VALUE_LENGTH],
            DEFAULT_LANGUAGE,
        )
    return DEFAULT_LANGUAGE
