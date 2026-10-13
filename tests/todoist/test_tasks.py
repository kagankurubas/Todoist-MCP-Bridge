"""
Unit and security tests for the Todoist FastMCP Server: task tools.
All tests use mocks to ensure zero network calls and deterministic results.
"""

from datetime import date
from unittest.mock import MagicMock, patch
import pytest
from plugvan.todoist.limits import (
    MAX_CONTENT_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_DUE_STRING_LENGTH,
    MAX_FILTER_QUERY_LENGTH,
    MAX_PROJECT_NAME_LENGTH,
    MAX_TASK_ID_LENGTH,
)
from plugvan.todoist.tools.tasks import (
    complete_task,
    create_task,
    delete_task,
    get_task,
    list_tasks,
    reopen_task,
    update_task,
)
from tests.todoist.helpers import (
    MockProject,
    MockSection,
    _make_http_status_error,
    MockTask,
)


# =====================================================================
# CREATE_TASK TESTS
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_create_task_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    mock_project = MockProject("proj_100", "Odak & Gelişim")
    mock_section = MockSection("sec_200", "Acil İşler", project_id="proj_100")
    mock_api.get_projects.return_value = [[mock_project]]
    mock_api.get_sections.return_value = [[mock_section]]
    mock_api.add_task.return_value = MockTask(
        task_id="task_001",
        content="Read 10 pages",
        priority=2,
        due_string="tomorrow at 10:00",
        labels=["kitap", "odak"],
        section_id="sec_200",
    )

    result = create_task(
        content="Read 10 pages",
        description="Daily habit",
        project_name="Odak & Gelişim",
        section_name_or_id="Acil İşler",
        due_string="tomorrow at 10:00",
        priority=2,
        labels=["@kitap", "odak"],
    )

    assert "✅ Görev başarıyla oluşturuldu!" in result
    assert "ID: task_001" in result
    assert "Başlık: Read 10 pages" in result
    assert "Proje: Odak & Gelişim" in result
    assert "Bölüm: Acil İşler (ID: sec_200)" in result
    assert "Öncelik: p2" in result
    assert "Etiketler: @kitap, @odak" in result
    mock_api.add_task.assert_called_once_with(
        content="Read 10 pages",
        description="Daily habit",
        project_id="proj_100",
        section_id="sec_200",
        due_string="tomorrow at 10:00",
        priority=2,
        labels=["kitap", "odak"],
    )


@patch("plugvan.todoist.client.get_api_client")
def test_create_task_section_not_found(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_project = MockProject("proj_100", "İş")
    mock_api.get_projects.return_value = [[mock_project]]
    mock_api.get_sections.return_value = [[]]

    result = create_task(
        content="Task without section",
        project_name="İş",
        section_name_or_id="Olmayan Bölüm",
    )
    assert "⚠️ Belirtilen bölüm bulunamadı: 'Olmayan Bölüm'." in result


@patch("plugvan.todoist.client.get_api_client")
def test_create_task_inbox_default(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    mock_inbox = MockProject("inbox_id", "Inbox", is_inbox=True)
    mock_api.get_projects.return_value = [[mock_inbox]]
    mock_api.add_task.return_value = MockTask(
        task_id="task_002",
        content="General Task",
        priority=1,
    )

    result = create_task(content="General Task", project_name="Gelen Kutusu")
    assert "✅ Görev başarıyla oluşturuldu!" in result
    assert "ID: task_002" in result
    mock_api.add_task.assert_called_once_with(
        content="General Task",
        description=None,
        project_id="inbox_id",
        due_string=None,
        priority=1,
    )


@patch("plugvan.todoist.client.get_api_client")
def test_create_task_with_parent_id(mock_get_client):
    """parent_id verildiğinde SDK çağrısına dahil edilmelidir (alt görev/subtask)."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    mock_api.get_projects.return_value = [[]]
    mock_api.add_task.return_value = MockTask(
        task_id="task_child_001",
        content="Alt görev",
        priority=1,
    )

    result = create_task(content="Alt görev", parent_id="task_parent_999")

    assert "✅ Görev başarıyla oluşturuldu!" in result
    mock_api.add_task.assert_called_once_with(
        content="Alt görev",
        description=None,
        project_id=None,
        due_string=None,
        priority=1,
        parent_id="task_parent_999",
    )


@patch("plugvan.todoist.client.get_api_client")
def test_create_task_without_parent_id_omitted(mock_get_client):
    """parent_id verilmediğinde SDK çağrısında hiç yer almamalıdır."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    mock_api.get_projects.return_value = [[]]
    mock_api.add_task.return_value = MockTask(
        task_id="task_003",
        content="Bağımsız görev",
        priority=1,
    )

    create_task(content="Bağımsız görev")

    call_kwargs = mock_api.add_task.call_args.kwargs
    assert "parent_id" not in call_kwargs


@patch("plugvan.todoist.client.get_api_client")
def test_create_task_with_deadline_date(mock_get_client):
    """deadline_date verildiğinde bir date nesnesine çevrilip SDK çağrısına dahil edilmelidir."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    mock_api.get_projects.return_value = [[]]
    mock_api.add_task.return_value = MockTask(
        task_id="task_deadline_001",
        content="Son teslimli görev",
        priority=1,
    )

    result = create_task(content="Son teslimli görev", deadline_date="2026-09-01")

    assert "✅ Görev başarıyla oluşturuldu!" in result
    assert "Son Teslim Tarihi (Deadline): 2026-09-01" in result
    mock_api.add_task.assert_called_once_with(
        content="Son teslimli görev",
        description=None,
        project_id=None,
        due_string=None,
        priority=1,
        deadline_date=date(2026, 9, 1),
    )


@patch("plugvan.todoist.client.get_api_client")
def test_create_task_without_deadline_date_omitted(mock_get_client):
    """deadline_date verilmediğinde SDK çağrısında hiç yer almamalıdır."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    mock_api.get_projects.return_value = [[]]
    mock_api.add_task.return_value = MockTask(
        task_id="task_004",
        content="Son teslimsiz görev",
        priority=1,
    )

    create_task(content="Son teslimsiz görev")

    call_kwargs = mock_api.add_task.call_args.kwargs
    assert "deadline_date" not in call_kwargs


def test_create_task_invalid_deadline_date_format():
    result = create_task(content="Task", deadline_date="01-09-2026")
    assert "❌ Invalid input: deadline_date must be in YYYY-MM-DD format" in result


@patch("plugvan.todoist.client.get_api_client")
def test_create_task_due_string_and_deadline_date_together(mock_get_client):
    """due_string ve deadline_date aynı anda verildiğinde birbirini geçersiz kılmadan,
    ikisi de bağımsız alanlar olarak SDK çağrısına dahil edilmelidir."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    mock_api.get_projects.return_value = [[]]
    mock_api.add_task.return_value = MockTask(
        task_id="task_both_001",
        content="Hem tarihli hem son teslimli görev",
        priority=1,
        due_string="tomorrow at 10:00",
    )

    result = create_task(
        content="Hem tarihli hem son teslimli görev",
        due_string="tomorrow at 10:00",
        deadline_date="2026-09-01",
    )

    assert "✅ Görev başarıyla oluşturuldu!" in result
    assert "Tarih / Tekrar: tomorrow at 10:00" in result
    assert "Son Teslim Tarihi (Deadline): 2026-09-01" in result
    mock_api.add_task.assert_called_once_with(
        content="Hem tarihli hem son teslimli görev",
        description=None,
        project_id=None,
        due_string="tomorrow at 10:00",
        priority=1,
        deadline_date=date(2026, 9, 1),
    )


@patch("plugvan.todoist.client.get_api_client")
def test_create_task_deadline_date_403_reports_plan_restriction(mock_get_client):
    """deadline_date verilen bir istek 403 Forbidden ile reddedilirse, Free/Beginner planında
    Deadline özelliğinin desteklenmediğini açıklayan özel bir hata mesajı dönmelidir."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    mock_api.get_projects.return_value = [[]]
    mock_api.add_task.side_effect = _make_http_status_error(403, text="Forbidden")

    result = create_task(content="Son teslimli görev", deadline_date="2026-09-01")

    assert result == (
        "❌ Deadline özelliği Todoist Free/Beginner planında desteklenmiyor "
        "— Pro veya Business plan gerekiyor (403 Forbidden)."
    )


@patch("plugvan.todoist.client.get_api_client")
def test_create_task_403_without_deadline_date_uses_generic_message(mock_get_client):
    """deadline_date verilmeden gelen bir 403, plan-kısıtlaması mesajını değil genel hata
    mesajını dönmelidir (deadline dışı 403 sebepleri etkilenmemeli)."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    mock_api.get_projects.return_value = [[]]
    mock_api.add_task.side_effect = _make_http_status_error(403, text="Forbidden")

    result = create_task(content="Son teslimsiz görev")

    assert result == "❌ Todoist task creation failed. Check server logs for details."


def test_create_task_empty_content():
    result = create_task(content="   ")
    assert "❌ Invalid input: Task content cannot be empty" in result


def test_create_task_content_too_long():
    long_content = "A" * (MAX_CONTENT_LENGTH + 1)
    result = create_task(content=long_content)
    assert "❌ Invalid input: Task content exceeds maximum length" in result


def test_create_task_description_too_long():
    long_desc = "D" * (MAX_DESCRIPTION_LENGTH + 1)
    result = create_task(content="Valid title", description=long_desc)
    assert "❌ Invalid input: Task description exceeds maximum length" in result


def test_create_task_project_name_too_long():
    long_proj = "P" * (MAX_PROJECT_NAME_LENGTH + 1)
    result = create_task(content="Valid title", project_name=long_proj)
    assert "❌ Invalid input: Project name exceeds maximum length" in result


def test_create_task_due_string_too_long():
    long_due = "T" * (MAX_DUE_STRING_LENGTH + 1)
    result = create_task(content="Valid title", due_string=long_due)
    assert "❌ Invalid input: Due date string exceeds maximum length" in result


@pytest.mark.parametrize("invalid_priority", [0, 5, -1, 999, "high"])
def test_create_task_invalid_priority_rejected(invalid_priority):
    result = create_task(content="Valid task", priority=invalid_priority)
    assert "❌ Invalid input: Priority must be an integer between 1" in result


def test_create_task_invalid_labels_type():
    result = create_task(content="Valid task", labels="not_a_list")
    assert "❌ Invalid input: Labels must be a list of strings" in result


@patch("plugvan.todoist.client.get_api_client")
def test_create_task_sanitizes_exception_and_logs_cleanly(mock_get_client, caplog):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = []
    mock_api.add_task.side_effect = Exception(
        "TODOIST_API_TOKEN=SUPER_SECRET_TOKEN_123 failed Authorization: Bearer SUPER_SECRET_TOKEN_123"
    )

    with caplog.at_level("INFO"):
        result = create_task(content="Test Task")

    assert result == "❌ Todoist task creation failed. Check server logs for details."
    assert "SUPER_SECRET_TOKEN_123" not in result
    assert "Bearer" not in result
    assert "SUPER_SECRET_TOKEN_123" not in caplog.text
    assert "Bearer" not in caplog.text


# =====================================================================
# LIST_TASKS TESTS
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_list_tasks_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    task1 = MockTask("t1", "First task", priority=4, due_string="today", description="Note 1", labels=["acil"])
    task2 = MockTask("t2", "Second task", priority=1, due_string=None)
    mock_api.filter_tasks.return_value = [[task1, task2]]

    result = list_tasks(filter_query="today")
    assert "📋 Açık Görevler (Filtre: 'today', Toplam: 2):" in result
    assert "[t1] First task [@acil]" in result
    assert "🔴 p4 (Çok Acil)" in result
    assert "Tarih: today" in result
    assert "Açıklama: Note 1" in result
    assert "[t2] Second task" in result
    assert "⚪ p1 (Normal)" in result
    assert "Tarih: Tarih yok" in result


@patch("plugvan.todoist.client.get_api_client")
def test_list_tasks_empty_result(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.filter_tasks.return_value = [[]]

    result = list_tasks(filter_query="overdue")
    assert "ℹ️ 'overdue' filtresine uygun açık görev bulunamadı." in result


def test_list_tasks_empty_filter():
    result = list_tasks(filter_query="   ")
    assert "❌ Invalid input: Filter query cannot be empty" in result


def test_list_tasks_filter_too_long():
    long_filter = "Q" * (MAX_FILTER_QUERY_LENGTH + 1)
    result = list_tasks(filter_query=long_filter)
    assert "❌ Invalid input: Filter query exceeds maximum length" in result


@patch("plugvan.todoist.client.get_api_client")
def test_list_tasks_sanitizes_exception_and_logs_cleanly(mock_get_client, caplog):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.filter_tasks.side_effect = RuntimeError(
        "TODOIST_API_TOKEN=SUPER_SECRET_TOKEN_123 failed Authorization: Bearer SUPER_SECRET_TOKEN_123"
    )

    with caplog.at_level("INFO"):
        result = list_tasks(filter_query="today")

    assert result == "❌ Failed to retrieve tasks from Todoist. Check server logs for details."
    assert "SUPER_SECRET_TOKEN_123" not in result
    assert "SUPER_SECRET_TOKEN_123" not in caplog.text


# =====================================================================
# GET_TASK TESTS
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_get_task_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_task.return_value = MockTask(
        task_id="task_777",
        content="Sub-task example",
        priority=3,
        due_string="tomorrow at 09:00",
        description="Details here",
        labels=["work", "urgent"],
        section_id="sec_10",
        project_id="proj_20",
        parent_id="task_parent_5",
    )

    result = get_task(task_id="task_777")

    assert "📄 Görev Detayları (ID: task_777)" in result
    assert "Başlık: Sub-task example" in result
    assert "Açıklama: Details here" in result
    assert "Proje ID: proj_20" in result
    assert "Bölüm ID: sec_10" in result
    assert "Üst Görev ID (parent_id): task_parent_5" in result
    assert "Öncelik: p3" in result
    assert "Tarih / Tekrar: tomorrow at 09:00" in result
    assert "Etiketler: @work, @urgent" in result
    mock_api.get_task.assert_called_once_with(task_id="task_777")


@patch("plugvan.todoist.client.get_api_client")
def test_get_task_without_parent_shows_top_level(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_task.return_value = MockTask(
        task_id="task_888",
        content="Standalone task",
        project_id="proj_20",
    )

    result = get_task(task_id="task_888")
    assert "Üst Görev ID (parent_id): Yok (üst seviye görev)" in result
    assert "Bölüm ID: Yok" in result
    assert "Açıklama: Yok" in result
    assert "Etiketler: Yok" in result


def test_get_task_empty_id():
    result = get_task(task_id="   ")
    assert "❌ Invalid input: Task ID cannot be empty or whitespace." in result


def test_get_task_id_too_long():
    result = get_task(task_id="x" * (MAX_TASK_ID_LENGTH + 1))
    assert f"❌ Invalid input: Task ID exceeds maximum length of {MAX_TASK_ID_LENGTH} characters." in result


@patch("plugvan.todoist.client.get_api_client")
def test_get_task_sanitizes_exception_and_logs_cleanly(mock_get_client, caplog):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_task.side_effect = Exception(
        "TODOIST_API_TOKEN=SUPER_SECRET_TOKEN_123 failed Authorization: Bearer SUPER_SECRET_TOKEN_123"
    )

    with caplog.at_level("INFO"):
        result = get_task(task_id="task_err")

    assert result == "❌ Failed to retrieve task from Todoist (ID: task_err). Check server logs for details."
    assert "SUPER_SECRET_TOKEN_123" not in result
    assert "SUPER_SECRET_TOKEN_123" not in caplog.text


# =====================================================================
# COMPLETE_TASK & REOPEN_TASK TESTS
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_complete_task_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.complete_task.return_value = True

    result = complete_task(task_id="  task_abc123  ")
    assert "✅ Görev başarıyla tamamlandı (ID: task_abc123)." in result
    mock_api.complete_task.assert_called_once_with(task_id="task_abc123")


@patch("plugvan.todoist.client.get_api_client")
def test_complete_task_unsuccessful(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.complete_task.return_value = False

    result = complete_task(task_id="task_not_found")
    assert "⚠️ Görev tamamlanamadı veya zaten tamamlanmış olabilir (ID: task_not_found)." in result


def test_complete_task_empty_id():
    result = complete_task(task_id="   ")
    assert "❌ Invalid input: Task ID cannot be empty" in result


def test_complete_task_id_too_long():
    long_id = "X" * (MAX_TASK_ID_LENGTH + 1)
    result = complete_task(task_id=long_id)
    assert "❌ Invalid input: Task ID exceeds maximum length" in result


@patch("plugvan.todoist.client.get_api_client")
def test_complete_task_sanitizes_exception_and_logs_cleanly(mock_get_client, caplog):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.complete_task.side_effect = Exception(
        "TODOIST_API_TOKEN=SUPER_SECRET_TOKEN_123 failed Authorization: Bearer SUPER_SECRET_TOKEN_123"
    )

    with caplog.at_level("INFO"):
        result = complete_task(task_id="task_error_123")

    assert result == "❌ Failed to complete task in Todoist (ID: task_error_123). Check server logs for details."
    assert "SUPER_SECRET_TOKEN_123" not in result
    assert "SUPER_SECRET_TOKEN_123" not in caplog.text


@patch("plugvan.todoist.client.get_api_client")
def test_reopen_task_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.uncomplete_task.return_value = True

    result = reopen_task(task_id="  task_reopen_1  ")
    assert "🔄 Görev başarıyla yeniden açıldı (ID: task_reopen_1)." in result
    mock_api.uncomplete_task.assert_called_once_with(task_id="task_reopen_1")


@patch("plugvan.todoist.client.get_api_client")
def test_reopen_task_unsuccessful(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.uncomplete_task.return_value = False

    result = reopen_task(task_id="task_already_active")
    assert "⚠️ Görev yeniden açılamadı veya zaten açık olabilir (ID: task_already_active)." in result


def test_reopen_task_empty_id():
    result = reopen_task(task_id="   ")
    assert "❌ Invalid input: Task ID cannot be empty" in result


@patch("plugvan.todoist.client.get_api_client")
def test_reopen_task_sanitizes_exception(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.uncomplete_task.side_effect = Exception("TODOIST_API_TOKEN=SECRET")

    result = reopen_task(task_id="task_err")
    assert result == "❌ Failed to reopen task in Todoist (ID: task_err). Check server logs for details."
    assert "SECRET" not in result


# =====================================================================
# UPDATE_TASK TESTS
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_update_task_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_project = MockProject("proj_99", "İş")
    mock_section = MockSection("sec_55", "Tamamlananlar", project_id="proj_99")
    mock_api.get_projects.return_value = [[mock_project]]
    mock_api.get_sections.return_value = [[mock_section]]

    result = update_task(
        task_id="task_123",
        content="Yeni Başlık",
        description="Yeni Açıklama",
        project_name="İş",
        section_name_or_id="Tamamlananlar",
        due_string="yarın 15:00",
        priority=3,
        labels=["@önemli", "proje"],
    )

    assert "✅ Görev başarıyla güncellendi (ID: task_123)!" in result
    assert "Başlık: 'Yeni Başlık'" in result
    assert "Açıklama: 'Yeni Açıklama'" in result
    assert "Tarih: 'yarın 15:00'" in result
    assert "Öncelik: p3" in result
    assert "Etiketler: @önemli, @proje" in result
    assert "Hedef Proje: 'İş' (ID: proj_99)" in result
    assert "Hedef Bölüm: 'Tamamlananlar' (ID: sec_55)" in result

    mock_api.update_task.assert_called_once_with(
        task_id="task_123",
        content="Yeni Başlık",
        description="Yeni Açıklama",
        due_string="yarın 15:00",
        priority=3,
        labels=["önemli", "proje"],
    )
    mock_api.move_task.assert_called_once_with(task_id="task_123", project_id="proj_99", section_id="sec_55")


def test_update_task_no_fields_provided():
    result = update_task(task_id="task_123")
    assert "⚠️ Güncellenecek hiçbir alan belirtilmedi" in result


def test_update_task_invalid_priority():
    result = update_task(task_id="task_123", priority=5)
    assert "❌ Invalid input: Priority must be an integer between 1" in result


def test_update_task_invalid_labels_type():
    result = update_task(task_id="task_123", labels="not_a_list")
    assert "❌ Invalid input: Labels must be a list of strings" in result


@patch("plugvan.todoist.client.get_api_client")
def test_update_task_sanitizes_exception(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.update_task.side_effect = Exception("TODOIST_API_TOKEN=SECRET")

    result = update_task(task_id="task_err", content="Updated Content")
    assert result == "❌ Failed to update task in Todoist (ID: task_err). Check server logs for details."
    assert "SECRET" not in result


def test_update_task_parent_id_too_long():
    result = update_task(task_id="task_123", parent_id="x" * (MAX_TASK_ID_LENGTH + 1))
    assert f"❌ Invalid input: Parent task ID exceeds maximum length of {MAX_TASK_ID_LENGTH} characters." in result


@patch("plugvan.todoist.client.get_api_client")
def test_update_task_sets_parent_id(mock_get_client):
    """parent_id dolu bir string olarak verildiğinde move_task ile yeni üst görev atanmalı."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    result = update_task(task_id="task_child", parent_id="task_parent_1")

    assert "✅ Görev başarıyla güncellendi (ID: task_child)!" in result
    assert "Üst Görev (parent_id): 'task_parent_1'" in result
    mock_api.get_task.assert_not_called()
    mock_api.update_task.assert_not_called()
    mock_api.move_task.assert_called_once_with(task_id="task_child", parent_id="task_parent_1")


@patch("plugvan.todoist.client.get_api_client")
def test_update_task_unparent_with_empty_string(mock_get_client):
    """parent_id="" verildiğinde, görevin mevcut projesi (api.get_task ile) çekilip
    move_task(project_id=...) ile üst seviyeye taşınmalı (Todoist API'de parent_id'yi
    null yaparak unparent etme desteklenmediği için)."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_task.return_value = MagicMock(project_id="proj_999")

    result = update_task(task_id="task_child", parent_id="")

    assert "✅ Görev başarıyla güncellendi (ID: task_child)!" in result
    assert "Üst Görev: Kaldırıldı (görev üst seviyeye taşındı)" in result
    mock_api.get_task.assert_called_once_with(task_id="task_child")
    mock_api.move_task.assert_called_once_with(task_id="task_child", project_id="proj_999")


@patch("plugvan.todoist.client.get_api_client")
def test_update_task_unparent_with_project_name_skips_current_project_lookup(mock_get_client):
    """parent_id="" ile aynı anda project_name de verilirse, hedef proje zaten
    resolve edildiğinden api.get_task ile mevcut proje sorgusu yapılmamalı."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_project = MockProject("proj_42", "Kişisel")
    mock_api.get_projects.return_value = [[mock_project]]

    result = update_task(task_id="task_child", project_name="Kişisel", parent_id="")

    assert "Hedef Proje: 'Kişisel' (ID: proj_42)" in result
    assert "Üst Görev: Kaldırıldı (görev üst seviyeye taşındı)" in result
    mock_api.get_task.assert_not_called()
    mock_api.move_task.assert_called_once_with(task_id="task_child", project_id="proj_42")


@patch("plugvan.todoist.client.get_api_client")
def test_update_task_with_deadline_date(mock_get_client):
    """deadline_date verildiğinde bir date nesnesine çevrilip api.update_task çağrısına dahil edilmelidir."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    result = update_task(task_id="task_123", deadline_date="2026-09-01")

    assert "✅ Görev başarıyla güncellendi (ID: task_123)!" in result
    assert "Son Teslim Tarihi (Deadline): '2026-09-01'" in result
    mock_api.update_task.assert_called_once_with(task_id="task_123", deadline_date=date(2026, 9, 1))


@patch("plugvan.todoist.client.get_api_client")
def test_update_task_without_deadline_date_omitted(mock_get_client):
    """deadline_date verilmediğinde api.update_task çağrısında hiç yer almamalıdır."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    update_task(task_id="task_123", content="Yeni Başlık")

    call_kwargs = mock_api.update_task.call_args.kwargs
    assert "deadline_date" not in call_kwargs


def test_update_task_invalid_deadline_date_format():
    result = update_task(task_id="task_123", deadline_date="01-09-2026")
    assert "❌ Invalid input: deadline_date must be in YYYY-MM-DD format" in result


@patch("plugvan.todoist.client.get_api_client")
def test_update_task_due_string_and_deadline_date_together(mock_get_client):
    """due_string ve deadline_date aynı anda güncellendiğinde birbirini geçersiz kılmadan,
    ikisi de bağımsız alanlar olarak tek bir api.update_task çağrısına dahil edilmelidir."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api

    result = update_task(
        task_id="task_123",
        due_string="tomorrow at 10:00",
        deadline_date="2026-09-01",
    )

    assert "✅ Görev başarıyla güncellendi (ID: task_123)!" in result
    assert "Tarih: 'tomorrow at 10:00'" in result
    assert "Son Teslim Tarihi (Deadline): '2026-09-01'" in result
    mock_api.update_task.assert_called_once_with(
        task_id="task_123",
        due_string="tomorrow at 10:00",
        deadline_date=date(2026, 9, 1),
    )


@patch("plugvan.todoist.client.get_api_client")
def test_update_task_deadline_date_403_reports_plan_restriction(mock_get_client):
    """deadline_date güncellenirken 403 Forbidden alınırsa, Free/Beginner planında Deadline
    özelliğinin desteklenmediğini açıklayan özel bir hata mesajı dönmelidir."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.update_task.side_effect = _make_http_status_error(403, text="Forbidden")

    result = update_task(task_id="task_123", deadline_date="2026-09-01")

    assert result == (
        "❌ Deadline özelliği Todoist Free/Beginner planında desteklenmiyor "
        "— Pro veya Business plan gerekiyor (403 Forbidden)."
    )


@patch("plugvan.todoist.client.get_api_client")
def test_update_task_403_without_deadline_date_uses_generic_message(mock_get_client):
    """deadline_date olmadan gelen bir 403, plan-kısıtlaması mesajını değil görev-kimliğini
    içeren genel hata mesajını dönmelidir (deadline dışı 403 sebepleri etkilenmemeli)."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.update_task.side_effect = _make_http_status_error(403, text="Forbidden")

    result = update_task(task_id="task_123", content="Updated Content")

    assert result == "❌ Failed to update task in Todoist (ID: task_123). Check server logs for details."


# =====================================================================
# DELETE_TASK TESTS
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_delete_task_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.delete_task.return_value = True

    result = delete_task(task_id="task_to_del")
    assert "🗑️ Görev kalıcı olarak silindi (ID: task_to_del)." in result
    mock_api.delete_task.assert_called_once_with(task_id="task_to_del")


@patch("plugvan.todoist.client.get_api_client")
def test_delete_task_unsuccessful(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.delete_task.return_value = False

    result = delete_task(task_id="task_missing")
    assert "⚠️ Görev silinemedi (ID: task_missing)." in result


def test_delete_task_empty_id():
    result = delete_task(task_id="   ")
    assert "❌ Invalid input: Task ID cannot be empty" in result


@patch("plugvan.todoist.client.get_api_client")
def test_delete_task_sanitizes_exception(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.delete_task.side_effect = Exception("TODOIST_API_TOKEN=SECRET")

    result = delete_task(task_id="task_err")
    assert result == "❌ Failed to delete task in Todoist (ID: task_err). Check server logs for details."
    assert "SECRET" not in result
