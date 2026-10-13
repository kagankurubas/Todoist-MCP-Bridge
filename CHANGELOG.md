# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `update_section` MCP tool: rename a Todoist section by ID or name.
  Optional `project_name_or_id` scopes name resolution so same-named
  sections in different projects can't be confused.
- 9 tests for `update_section` (rename by name/ID, project scoping,
  not-found, empty/too-long input, sanitized error). Suite: 172 → 181.

### Backlog
- `update_section`: expose `order` and `collapsed` (supported by the SDK).
- `project_move`: needs the Sync API's separate command.
