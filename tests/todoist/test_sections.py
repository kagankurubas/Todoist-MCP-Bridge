"""
Unit and security tests for the Todoist FastMCP Server: section tools.
All tests use mocks to ensure zero network calls and deterministic results.
"""

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
