"""The `plugvan-mcp` console script: `plugvan-mcp <integration>` starts that integration's MCP
server over STDIO. Never reads .env; configuration comes from the environment, i.e. the env
block of the MCP client config."""

import argparse
import sys
from importlib import metadata

from plugvan import todoist

DISTRIBUTION = "plugvan-mcp"

# Integration name -> its run function, looked up at call time so tests can patch it.
INTEGRATIONS = {
    "todoist": lambda: todoist.run(),
}


def _version() -> str:
    try:
        return metadata.version(DISTRIBUTION)
    except metadata.PackageNotFoundError:
        return "unknown"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=DISTRIBUTION,
        description="Run a Plugvan MCP server over STDIO.",
    )
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    subparsers = parser.add_subparsers(dest="integration", metavar="{" + ",".join(INTEGRATIONS) + "}")
    for name in INTEGRATIONS:
        subparsers.add_parser(name, help=f"run the {name.capitalize()} MCP server over STDIO")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_:  # --help (0) and usage errors (2), already printed by argparse
        return exit_.code if isinstance(exit_.code, int) else 2

    if args.version:
        print(f"{DISTRIBUTION} {_version()}")
        return 0
    if args.integration is None:
        parser.print_usage(sys.stderr)
        print(f"{DISTRIBUTION}: error: choose an integration: {', '.join(INTEGRATIONS)}", file=sys.stderr)
        return 2

    INTEGRATIONS[args.integration]()
    return 0
