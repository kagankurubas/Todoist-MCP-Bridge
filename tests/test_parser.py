import pytest
from parser import TaskParseError, clean_json_text, parse_tasks_from_json


def test_clean_json_text_markdown_fence():
    raw = "```json\n[{\"content\": \"Test Task\"}]\n```"
    assert clean_json_text(raw) == '[{"content": "Test Task"}]'


def test_clean_json_text_generic_fence():
    raw = "```\n{\"tasks\": []}\n```"
    assert clean_json_text(raw) == '{"tasks": []}'


def test_clean_json_text_plain():
    raw = '  [{"content": "No Fences"}]  '
    assert clean_json_text(raw) == '[{"content": "No Fences"}]'


def test_parse_tasks_from_json_list():
    raw = """[
        {"content": "Task 1", "project_name": "Inbox", "priority": 3, "due_string": "today"},
        {"content": "Task 2", "priority": 1}
    ]"""
    tasks = parse_tasks_from_json(raw)
    assert len(tasks) == 2
    assert tasks[0].content == "Task 1"
    assert tasks[0].project_name == "Inbox"
    assert tasks[0].priority == 3
    assert tasks[0].due_string == "today"
    assert tasks[1].content == "Task 2"
    assert tasks[1].project_name == "Odak & Gelişim"  # Default


def test_parse_tasks_from_json_batch_dict():
    raw = '{"tasks": [{"content": "Batch Item 1", "priority": 4}]}'
    tasks = parse_tasks_from_json(raw)
    assert len(tasks) == 1
    assert tasks[0].content == "Batch Item 1"
    assert tasks[0].priority == 4


def test_parse_tasks_from_json_single_dict():
    raw = '{"content": "Single Task", "due_string": "tomorrow"}'
    tasks = parse_tasks_from_json(raw)
    assert len(tasks) == 1
    assert tasks[0].content == "Single Task"
    assert tasks[0].due_string == "tomorrow"


def test_parse_tasks_invalid_json():
    with pytest.raises(TaskParseError, match="Invalid JSON format"):
        parse_tasks_from_json("invalid json string {]")


def test_parse_tasks_validation_error_priority_out_of_bounds():
    # priority must be between 1 and 4
    with pytest.raises(TaskParseError, match="Data validation failed"):
        parse_tasks_from_json('{"content": "Bad Priority", "priority": 5}')
