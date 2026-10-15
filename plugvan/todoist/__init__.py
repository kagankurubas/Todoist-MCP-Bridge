"""Todoist MCP integration. run() starts the STDIO server for both entry points:
`python -m plugvan.todoist` and the `plugvan-mcp todoist` console script."""

import logging


def configure_logging() -> None:
    """Logs to stderr at INFO. Calling it again is a no-op (logging.basicConfig)."""
    logging.basicConfig(level=logging.INFO)


def run() -> None:
    """Configures logging, then imports and runs the Todoist server over STDIO.

    Logging is configured before the server module is imported: the SDK's FastMCP()
    constructor calls logging.basicConfig with its own handler, and the first configuration
    wins. Never reads .env; only `python -m plugvan.todoist` does that, before calling run().
    """
    configure_logging()
    from plugvan.todoist.server import mcp

    mcp.run()
