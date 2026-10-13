"""Todoist SDK client factory. Tools call it as client.get_api_client() so tests can patch one target."""

import logging
import os

from todoist_api_python.api import TodoistAPI

logger = logging.getLogger("todoist_mcp")


def get_api_client() -> TodoistAPI:
    """Reads TODOIST_API_TOKEN from environment and returns a TodoistAPI client instance."""
    token = os.getenv("TODOIST_API_TOKEN")
    if not token or not token.strip():
        logger.error("TODOIST_API_TOKEN is missing or empty in environment configuration", exc_info=False)
        raise RuntimeError("Todoist API authentication token is not configured.")
    return TodoistAPI(token.strip())
