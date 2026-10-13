"""
Unit and security tests for the Todoist FastMCP Server: section tools.
All tests use mocks to ensure zero network calls and deterministic results.
"""

import logging
from unittest.mock import MagicMock, patch
from plugvan.todoist.limits import (
    MAX_SECTION_NAME_LENGTH,
)
from plugvan.todoist.tools.sections import (
    create_section,
    delete_section,
    list_sections,
    update_section,
)
from tests.todoist.helpers import (
    MockProject,
    MockSection,
    _make_http_status_error,
    write_call_count,
)


# =====================================================================
# SECTIONS (CREATE_SECTION, LIST_SECTIONS, UPDATE_SECTION, DELETE_SECTION) TESTS
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_create_section_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_proj = MockProject("proj_10", "Yazılım")
    mock_api.get_projects.return_value = [[mock_proj]]
    mock_api.add_section.return_value = MockSection("sec_101", "In Progress", project_id="proj_10")

    result = create_section(name="In Progress", project_name_or_id="Yazılım")
    assert "✅ Bölüm başarıyla oluşturuldu!" in result
    assert "ID: sec_101" in result
    assert "İsim: In Progress" in result
    assert "Proje: 'Yazılım' (ID: proj_10)" in result
    mock_api.add_section.assert_called_once_with(name="In Progress", project_id="proj_10")


@patch("plugvan.todoist.client.get_api_client")
def test_create_section_project_not_found(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = [[]]

    result = create_section(name="In Progress", project_name_or_id="Olmayan Proje")
    assert "⚠️ Bölüm oluşturulacak hedef proje bulunamadı: 'Olmayan Proje'." in result


@patch("plugvan.todoist.client.get_api_client")
def test_list_sections_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_proj = MockProject("proj_10", "Yazılım")
    mock_api.get_projects.return_value = [[mock_proj]]
    sec1 = MockSection("sec_1", "Backlog", project_id="proj_10")
    sec2 = MockSection("sec_2", "Done", project_id="proj_10")
    mock_api.get_sections.return_value = [[sec1, sec2]]

    result = list_sections(project_name_or_id="Yazılım")
    assert "📑 Mevcut Bölümler ('Yazılım' Projesi, Toplam: 2):" in result
    assert "1. [sec_1] Backlog" in result
    assert "2. [sec_2] Done" in result


@patch("plugvan.todoist.client.get_api_client")
def test_list_sections_empty(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_sections.return_value = [[]]

    result = list_sections()
    assert "ℹ️ Todoist hesabınızda herhangi bir bölüm bulunamadı." in result


@patch("plugvan.todoist.client.get_api_client")
def test_update_section_rename_by_name(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_sections.return_value = [[MockSection("sec_7", "Backlog", project_id="proj_10")]]

    result = update_section(section_name_or_id="Backlog", name="Yapılacaklar")
    assert "✅ Bölüm başarıyla güncellendi (ID: sec_7)!" in result
    assert "Eski isim: 'Backlog'" in result
    assert "Yeni isim: 'Yapılacaklar'" in result
    mock_api.update_section.assert_called_once_with(section_id="sec_7", name="Yapılacaklar")


@patch("plugvan.todoist.client.get_api_client")
def test_update_section_rename_by_id(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_sections.return_value = [[MockSection("sec_8", "Done", project_id="proj_10")]]

    result = update_section(section_name_or_id="sec_8", name="Bitti")
    assert "✅ Bölüm başarıyla güncellendi (ID: sec_8)!" in result
    mock_api.update_section.assert_called_once_with(section_id="sec_8", name="Bitti")


@patch("plugvan.todoist.client.get_api_client")
def test_update_section_scoped_to_project(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = [[MockProject("proj_10", "Yazılım")]]
    mock_api.get_sections.return_value = [[MockSection("sec_9", "Backlog", project_id="proj_10")]]

    result = update_section(section_name_or_id="Backlog", name="Icebox", project_name_or_id="Yazılım")
    assert "✅ Bölüm başarıyla güncellendi" in result
    mock_api.get_sections.assert_called_once_with(project_id="proj_10")
    mock_api.update_section.assert_called_once_with(section_id="sec_9", name="Icebox")


@patch("plugvan.todoist.client.get_api_client")
def test_update_section_project_not_found(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = [[]]

    result = update_section(section_name_or_id="Backlog", name="Icebox", project_name_or_id="Olmayan Proje")
    assert "⚠️ Belirtilen proje bulunamadı: 'Olmayan Proje'." in result
    mock_api.update_section.assert_not_called()


@patch("plugvan.todoist.client.get_api_client")
def test_update_section_not_found(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_sections.return_value = [[]]

    result = update_section(section_name_or_id="Olmayan Bölüm", name="Yeni")
    assert "⚠️ Güncellenecek bölüm bulunamadı: 'Olmayan Bölüm'." in result
    mock_api.update_section.assert_not_called()


def test_update_section_empty_new_name():
    result = update_section(section_name_or_id="Backlog", name="   ")
    assert "❌ Invalid input: New section name cannot be empty" in result


def test_update_section_empty_identifier():
    result = update_section(section_name_or_id="   ", name="Yeni")
    assert "❌ Invalid input: Section identifier cannot be empty" in result


def test_update_section_name_too_long():
    result = update_section(section_name_or_id="Backlog", name="x" * (MAX_SECTION_NAME_LENGTH + 1))
    assert "New section name exceeds maximum length" in result


@patch("plugvan.todoist.client.get_api_client")
def test_update_section_sanitizes_exception(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_sections.return_value = [[MockSection("sec_1", "Backlog")]]
    mock_api.update_section.side_effect = Exception("TODOIST_API_TOKEN=SECRET")

    result = update_section(section_name_or_id="Backlog", name="Yeni")
    assert "❌ Failed to update section 'Backlog' in Todoist." in result
    assert "SECRET" not in result


@patch("plugvan.todoist.client.get_api_client")
def test_delete_section_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    sec = MockSection("sec_123", "Eski Bölüm")
    mock_api.get_sections.return_value = [[sec]]
    mock_api.delete_section.return_value = True

    result = delete_section(section_name_or_id="Eski Bölüm")
    assert "🗑️ Bölüm başarıyla silindi: 'Eski Bölüm' (ID: sec_123)." in result
    mock_api.delete_section.assert_called_once_with(section_id="sec_123")


@patch("plugvan.todoist.client.get_api_client")
def test_delete_section_not_found(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_sections.return_value = [[]]

    result = delete_section(section_name_or_id="Olmayan Bölüm")
    assert "⚠️ Silinecek bölüm bulunamadı: 'Olmayan Bölüm'." in result


# =====================================================================
# DELETE_SECTION / UPDATE_SECTION: EXACT NAME OR ID, AMBIGUITY, NO WRITE ON ERROR
# =====================================================================

def _two_backlogs():
    return [[
        MockSection("sec_1", "Backlog", project_id="proj_1"),
        MockSection("sec_2", "Backlog", project_id="proj_2"),
    ]]


@patch("plugvan.todoist.client.get_api_client")
def test_delete_section_same_name_in_two_projects_is_ambiguous(mock_get_client):
    """With two 'Backlog' sections, delete_section must not delete the first one it finds."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_sections.return_value = _two_backlogs()

    result = delete_section(section_name_or_id="Backlog")

    assert result == (
        "⚠️ 'Backlog' için birden fazla bölüm bulundu; lütfen bölüm ID'sini kullanın:\n"
        "• Backlog (sec_1)\n"
        "• Backlog (sec_2)"
    )
    mock_api.delete_section.assert_not_called()


@patch("plugvan.todoist.client.get_api_client")
def test_update_section_same_name_unscoped_is_ambiguous(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_sections.return_value = _two_backlogs()

    result = update_section(section_name_or_id="Backlog", name="Icebox")

    assert result.startswith("⚠️ 'Backlog' için birden fazla bölüm bulundu; lütfen bölüm ID'sini kullanın:")
    assert "• Backlog (sec_2)" in result
    assert write_call_count(mock_api) == 0


@patch("plugvan.todoist.client.get_api_client")
def test_update_section_scope_selects_section_of_that_project(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = [[MockProject("proj_1", "Yazılım"), MockProject("proj_2", "Ev")]]
    mock_api.get_sections.return_value = _two_backlogs()

    result = update_section(section_name_or_id="Backlog", name="Icebox", project_name_or_id="Ev")

    assert "✅ Bölüm başarıyla güncellendi (ID: sec_2)!" in result
    mock_api.update_section.assert_called_once_with(section_id="sec_2", name="Icebox")


@patch("plugvan.todoist.client.get_api_client")
def test_delete_and_update_section_partial_name_is_not_found(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_sections.return_value = [[MockSection("sec_1", "Backlog", project_id="proj_1")]]

    assert delete_section(section_name_or_id="Back") == "⚠️ Silinecek bölüm bulunamadı: 'Back'."
    assert update_section(section_name_or_id="Back", name="X") == "⚠️ Güncellenecek bölüm bulunamadı: 'Back'."
    assert write_call_count(mock_api) == 0


@patch("plugvan.todoist.client.get_api_client")
def test_update_section_partial_project_scope_is_not_found(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = [[MockProject("proj_1", "Yazılım Geliştirme")]]
    mock_api.get_sections.return_value = [[MockSection("sec_1", "Backlog", project_id="proj_1")]]

    result = update_section(section_name_or_id="Backlog", name="X", project_name_or_id="Yazılım")

    assert result == "⚠️ Belirtilen proje bulunamadı: 'Yazılım'."
    assert write_call_count(mock_api) == 0


@patch("plugvan.todoist.client.get_api_client")
def test_update_section_ambiguous_project_scope_writes_nothing(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = [[MockProject("proj_1", "Ev"), MockProject("proj_2", "ev")]]

    result = update_section(section_name_or_id="Backlog", name="X", project_name_or_id="Ev")

    assert result.startswith("⚠️ 'Ev' için birden fazla proje bulundu; lütfen proje ID'sini kullanın:")
    assert write_call_count(mock_api) == 0


@patch("plugvan.todoist.client.get_api_client")
def test_update_section_inbox_scope_without_listed_inbox_is_not_found(mock_get_client):
    """An Inbox alias with no Inbox project listed has no ID to scope by, so the section is not searched globally."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = [[MockProject("proj_1", "Yazılım")]]
    mock_api.get_sections.return_value = _two_backlogs()

    result = update_section(section_name_or_id="Backlog", name="X", project_name_or_id="Inbox")

    assert result == "⚠️ Güncellenecek bölüm bulunamadı: 'Backlog'."
    mock_api.get_sections.assert_not_called()
    assert write_call_count(mock_api) == 0


@patch("plugvan.todoist.client.get_api_client")
def test_delete_and_update_section_lookup_failure_is_generic_error(mock_get_client, caplog):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_sections.side_effect = _make_http_status_error(503, "upstream secret body")
    mock_api.get_projects.side_effect = RuntimeError("project list secret")

    with caplog.at_level(logging.ERROR, logger="todoist_mcp"):
        deleted = delete_section(section_name_or_id="Backlog")
        updated = update_section(section_name_or_id="Backlog", name="X")
        scoped = update_section(section_name_or_id="Backlog", name="X", project_name_or_id="Ev")

    assert deleted == "❌ Failed to delete section 'Backlog' in Todoist. Check server logs for details."
    assert updated == "❌ Failed to update section 'Backlog' in Todoist. Check server logs for details."
    assert scoped == updated
    assert write_call_count(mock_api) == 0
    for text in (deleted, updated, scoped, caplog.text):
        assert "upstream secret body" not in text
        assert "503 error" not in text
        assert "project list secret" not in text
    assert "error_type=HTTPStatusError" in caplog.text
    assert "error_type=RuntimeError" in caplog.text


# =====================================================================
# CREATE_SECTION / LIST_SECTIONS: TASK PROJECT RULE (UNIQUE PARTIAL, AMBIGUITY, NO WRITE ON ERROR)
# =====================================================================

def _homework_and_workshop():
    return [[MockProject("p1", "Homework"), MockProject("p2", "Workshop")]]


@patch("plugvan.todoist.client.get_api_client")
def test_create_section_ambiguous_project_creates_nothing(mock_get_client):
    """'Work' partially matches both 'Homework' and 'Workshop'; the first one must not be picked."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = _homework_and_workshop()

    result = create_section(name="In Progress", project_name_or_id="Work")

    assert result == (
        "⚠️ 'Work' için birden fazla proje bulundu; lütfen proje ID'sini kullanın:\n"
        "• Homework (p1)\n"
        "• Workshop (p2)"
    )
    mock_api.add_section.assert_not_called()


@patch("plugvan.todoist.client.get_api_client")
def test_list_sections_ambiguous_project_lists_nothing(mock_get_client):
    """'Work' partially matches both 'Homework' and 'Workshop'; the first one must not be listed."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = _homework_and_workshop()
    mock_api.get_sections.return_value = [[MockSection("sec_1", "Backlog", project_id="p1")]]

    result = list_sections(project_name_or_id="Work")

    assert result == (
        "⚠️ 'Work' için birden fazla proje bulundu; lütfen proje ID'sini kullanın:\n"
        "• Homework (p1)\n"
        "• Workshop (p2)"
    )
    mock_api.get_sections.assert_not_called()


@patch("plugvan.todoist.client.get_api_client")
def test_create_section_and_list_sections_unique_partial_show_resolved_name(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = [[MockProject("p1", "Yazılım Geliştirme"), MockProject("p2", "Ev")]]
    mock_api.add_section.return_value = MockSection("sec_new", "In Progress", project_id="p1")
    mock_api.get_sections.return_value = [[MockSection("sec_new", "In Progress", project_id="p1")]]

    created = create_section(name="In Progress", project_name_or_id="yazılım")
    listed = list_sections(project_name_or_id="yazılım")

    assert "Proje: 'Yazılım Geliştirme' (ID: p1)" in created
    mock_api.add_section.assert_called_once_with(name="In Progress", project_id="p1")
    assert "📑 Mevcut Bölümler ('Yazılım Geliştirme' Projesi, Toplam: 1):" in listed
    mock_api.get_sections.assert_called_once_with(project_id="p1")


@patch("plugvan.todoist.client.get_api_client")
def test_create_section_and_list_sections_inbox_alias(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.add_section.return_value = MockSection("sec_new", "Backlog", project_id="inbox_1")
    mock_api.get_sections.return_value = [[MockSection("sec_new", "Backlog", project_id="inbox_1")]]

    mock_api.get_projects.return_value = [[MockProject("inbox_1", "Inbox", is_inbox=True)]]
    assert "Proje: 'Inbox' (ID: inbox_1)" in create_section(name="Backlog", project_name_or_id="Gelen Kutusu")
    assert "('Inbox' Projesi, Toplam: 1)" in list_sections(project_name_or_id="inbox")

    mock_api.add_section.reset_mock()
    mock_api.get_sections.reset_mock()
    mock_api.get_projects.return_value = [[MockProject("p2", "Ev")]]
    assert create_section(name="Backlog", project_name_or_id="Inbox") == (
        "⚠️ Bölüm oluşturulacak hedef proje bulunamadı: 'Inbox'."
    )
    assert list_sections(project_name_or_id="Inbox") == "⚠️ Belirtilen proje bulunamadı: 'Inbox'."
    mock_api.get_sections.assert_not_called()
    assert write_call_count(mock_api) == 0


@patch("plugvan.todoist.client.get_api_client")
def test_create_section_and_list_sections_not_found_list_no_candidates(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = _homework_and_workshop()

    created = create_section(name="Backlog", project_name_or_id="Okul")
    listed = list_sections(project_name_or_id="Okul")

    assert created == "⚠️ Bölüm oluşturulacak hedef proje bulunamadı: 'Okul'."
    assert listed == "⚠️ Belirtilen proje bulunamadı: 'Okul'."
    mock_api.get_sections.assert_not_called()
    assert write_call_count(mock_api) == 0


@patch("plugvan.todoist.client.get_api_client")
def test_create_section_and_list_sections_lookup_failure_is_generic_error(mock_get_client, caplog):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.side_effect = _make_http_status_error(500, "upstream secret body")

    with caplog.at_level(logging.DEBUG, logger="todoist_mcp"):
        created = create_section(name="Backlog", project_name_or_id="Yazılım")
        listed = list_sections(project_name_or_id="Yazılım")

    assert created == "❌ Failed to create section 'Backlog' in Todoist. Check server logs for details."
    assert listed == "❌ Failed to list sections from Todoist. Check server logs for details."
    mock_api.get_sections.assert_not_called()
    assert write_call_count(mock_api) == 0
    for text in (created, listed, caplog.text):
        assert "upstream secret body" not in text
        assert "500" not in text
    assert "error_type=HTTPStatusError" in caplog.text
