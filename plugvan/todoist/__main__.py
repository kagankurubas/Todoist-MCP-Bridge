"""Entry point: python -m plugvan.todoist (STDIO transport).

The only place that reads .env: load_dotenv() with its defaults, so variables already set
(for example by the MCP client's env block) are not overridden. The `plugvan-mcp todoist`
console script never imports this module and never reads .env.
"""

from dotenv import load_dotenv

from plugvan import todoist

if __name__ == "__main__":
    todoist.configure_logging()
    load_dotenv()
    todoist.run()
