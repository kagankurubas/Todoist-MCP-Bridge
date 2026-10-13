"""Entry point: python -m plugvan.todoist (STDIO transport)."""

import logging

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

from plugvan.todoist.server import mcp  # imported after env/logging setup

if __name__ == "__main__":
    mcp.run()
