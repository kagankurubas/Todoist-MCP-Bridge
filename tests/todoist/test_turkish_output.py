"""
Turkish output tests: a small explicit set run with PLUGVAN_LANG=tr.
The default output language is English and the rest of the suite asserts English text; this
module guards that PLUGVAN_LANG=tr still gives the exact Turkish messages, with one
representative message per category instead of a duplicated suite.
All tests use mocks to ensure zero network calls and deterministic results.
"""

import logging
from unittest.mock import MagicMock

import pytest

from plugvan.todoist import client
from plugvan.todoist.tools.projects import delete_project, get_project, list_projects
from plugvan.todoist.tools.tasks import create_task, list_tasks, update_task
from tests.todoist.helpers import (
    MockProject,
    MockSection,
    MockTask,
    _make_http_status_error,
    write_call_count,
)


@pytest.fixture(autouse=True)
def turkish_output(monkeypatch):
    monkeypatch.setenv("PLUGVAN_LANG", "tr")


@pytest.fixture
def mock_api(monkeypatch):
    api = MagicMock()
    monkeypatch.setattr(client, "get_api_client", lambda: api)
    return api


def _create_success(api):
    api.get_projects.return_value = [[MockProject("proj_100", "Odak & Gelişim")]]
    api.get_sections.return_value = [[MockSection("sec_200", "Acil İşler", project_id="proj_100")]]
    api.add_task.return_value = MockTask(
        task_id="task_001",
        content="Read 10 pages",
        priority=2,
        due_string="tomorrow at 10:00",
        labels=["kitap", "odak"],
        section_id="sec_200",
    )
    return create_task(
        content="Read 10 pages",
        project_name="Odak & Gelişim",
        section_name_or_id="Acil İşler",
        due_string="tomorrow at 10:00",
        priority=2,
        labels=["@kitap", "odak"],
    )


def _update_change_summary(api):
    api.get_projects.return_value = [[MockProject("proj_99", "İş")]]
    api.get_sections.return_value = [[MockSection("sec_55", "Tamamlananlar", project_id="proj_99")]]
    return update_task(
        task_id="task_123",
        content="Yeni Başlık",
        description="Yeni Açıklama",
        project_name="İş",
        section_name_or_id="Tamamlananlar",
        due_string="yarın 15:00",
        priority=3,
        labels=["@önemli", "proje"],
    )


def _delete_success(api):
    api.get_projects.return_value = [[MockProject("proj_123", "Eski Proje")]]
    api.delete_project.return_value = True
    return delete_project(project_name_or_id="proj_123")


def _section_not_found(api):
    api.get_projects.return_value = [[MockProject("p1", "Yazılım")]]
    api.get_sections.return_value = [[MockSection("sec_1", "Backlog", project_id="p1")]]
    return create_task(content="X", project_name="Yazılım", section_name_or_id="Back")


def _ambiguous_project(api):
    api.get_projects.return_value = [[MockProject("p1", "Proje A"), MockProject("p2", "Proje B")]]
    return create_task(content="X", project_name="Proje")


def _empty_project_list(api):
    api.get_projects.return_value = [[]]
    return list_projects()


def _task_list(api):
    api.filter_tasks.return_value = [[
        MockTask("t1", "First task", priority=4, due_string="today", description="Note 1", labels=["acil"]),
        MockTask("t2", "Second task", priority=1, due_string=None),
    ]]
    return list_tasks(filter_query="today")


def _project_detail(api):
    api.get_project.return_value = MockProject(
        "proj_777",
        "İş Projesi",
        color="berry_red",
        parent_id="proj_parent_1",
        is_favorite=True,
        view_style="board",
    )
    return get_project(project_id="proj_777")


def _priority_labels(api):
    api.filter_tasks.return_value = [[MockTask(f"t{p}", f"Task {p}", priority=p) for p in (4, 3, 2, 1)]]
    return list_tasks(filter_query="all")


def _deadline_plan_restricted(api):
    api.get_projects.return_value = [[]]
    api.add_task.side_effect = _make_http_status_error(403, text="Forbidden")
    return create_task(content="Son teslimli görev", deadline_date="2026-09-01")


def _inbox_display_name(api):
    api.get_projects.return_value = [[MockProject("p2", "Inbox Zero")]]
    api.add_task.return_value = MockTask(task_id="task_new", content="X", priority=1)
    return create_task(content="X")


def _inbox_marker(api):
    api.get_projects.return_value = [[
        MockProject("p1", "Gelen Kutusu", is_inbox=True),
        MockProject("p2", "İş", color="berry_red"),
    ]]
    return list_projects()


# Each case: the tool call, then either the exact message (str) or fragments it must contain (list).
TURKISH_CASES = [
    pytest.param(
        _create_success,
        [
            "✅ Görev başarıyla oluşturuldu!",
            "Başlık: Read 10 pages",
            "Proje: Odak & Gelişim",
            "Bölüm: Acil İşler (ID: sec_200)",
            "Öncelik: p2",
            "Etiketler: @kitap, @odak",
        ],
        id="create-success",
    ),
    pytest.param(
        _update_change_summary,
        [
            "✅ Görev başarıyla güncellendi (ID: task_123)!",
            "Başlık: 'Yeni Başlık'",
            "Açıklama: 'Yeni Açıklama'",
            "Tarih: 'yarın 15:00'",
            "Öncelik: p3",
            "Etiketler: @önemli, @proje",
            "Hedef Proje: 'İş' (ID: proj_99)",
            "Hedef Bölüm: 'Tamamlananlar' (ID: sec_55)",
        ],
        id="update-change-summary",
    ),
    pytest.param(_delete_success, "🗑️ Proje başarıyla silindi: 'Eski Proje' (ID: proj_123).", id="delete-success"),
    pytest.param(_section_not_found, "⚠️ Belirtilen bölüm bulunamadı: 'Back'.", id="not-found"),
    pytest.param(
        _ambiguous_project,
        "⚠️ 'Proje' için birden fazla proje bulundu; lütfen proje ID'sini kullanın:\n"
        "• Proje A (p1)\n"
        "• Proje B (p2)",
        id="ambiguity-with-candidates",
    ),
    pytest.param(_empty_project_list, "ℹ️ Todoist hesabınızda herhangi bir proje bulunamadı.", id="empty-list"),
    pytest.param(
        _task_list,
        ["📋 Açık Görevler (Filtre: 'today', Toplam: 2):", "Açıklama: Note 1", "Tarih: Tarih yok"],
        id="list-header",
    ),
    pytest.param(
        _project_detail,
        [
            "📁 Proje Detayları (ID: proj_777)",
            "İsim: İş Projesi",
            "Renk: berry_red",
            "Üst Proje ID (parent_id): proj_parent_1",
            "Favori mi: Evet",
            "Görünüm Stili: board",
        ],
        id="detail-view",
    ),
    pytest.param(
        _priority_labels,
        ["🔴 p4 (Çok Acil)", "🟠 p3 (Yüksek)", "🔵 p2 (Orta)", "⚪ p1 (Normal)"],
        id="priority-labels",
    ),
    pytest.param(
        _deadline_plan_restricted,
        "❌ Deadline özelliği Todoist Free/Beginner planında desteklenmiyor "
        "— Pro veya Business plan gerekiyor (403 Forbidden).",
        id="deadline-plan-restriction",
    ),
    pytest.param(_inbox_display_name, ["• Proje: Gelen Kutusu"], id="inbox-display-name"),
    pytest.param(_inbox_marker, ["1. [p1] Gelen Kutusu [Gelen Kutusu]", "2. [p2] İş, Renk: berry_red"], id="inbox-marker"),
]


@pytest.mark.parametrize("call, expected", TURKISH_CASES)
def test_turkish_messages(mock_api, call, expected):
    result = call(mock_api)

    if isinstance(expected, str):
        assert result == expected
    else:
        for fragment in expected:
            assert fragment in result


def test_turkish_lookup_failure_stays_generic_and_sanitized(mock_api, caplog):
    mock_api.get_projects.return_value = [[MockProject("p1", "Yazılım")]]
    mock_api.get_sections.side_effect = _make_http_status_error(500, "upstream secret body")

    with caplog.at_level(logging.ERROR, logger="todoist_mcp"):
        result = create_task(content="X", project_name="Yazılım", section_name_or_id="Backlog")

    assert result == "❌ Todoist task creation failed. Check server logs for details."
    assert write_call_count(mock_api) == 0
    for text in (result, caplog.text):
        assert "upstream secret body" not in text
        assert "500 error" not in text
    assert "error_type=HTTPStatusError" in caplog.text
