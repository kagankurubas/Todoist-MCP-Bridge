"""
Todoist Model Context Protocol (MCP) Server
Integrates Todoist API tools via FastMCP over STDIO.
"""

from mcp.server.fastmcp import FastMCP

from plugvan.todoist.docstrings import clean_docstring
from plugvan.todoist.tools import tasks, projects, labels, sections, comments

mcp = FastMCP("Todoist")

# Registration order is part of the published surface; keep it stable.
TOOLS = (
    tasks.create_task,
    tasks.list_tasks,
    tasks.get_task,
    tasks.complete_task,
    tasks.reopen_task,
    tasks.update_task,
    tasks.delete_task,
    projects.list_projects,
    projects.get_project,
    projects.create_project,
    projects.update_project,
    projects.delete_project,
    labels.list_labels,
    labels.create_label,
    labels.update_label,
    labels.delete_label,
    sections.create_section,
    sections.list_sections,
    sections.update_section,
    sections.delete_section,
    comments.add_comment,
    comments.get_comments,
)

for _tool in TOOLS:
    # Python 3.13+ strips docstring indentation at compile time and 3.10-3.12 do not;
    # normalizing here makes every supported version publish the same descriptions.
    mcp.add_tool(_tool, description=clean_docstring(_tool.__doc__))
