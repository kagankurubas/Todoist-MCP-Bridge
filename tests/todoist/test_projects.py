"""
Unit and security tests for the Todoist FastMCP Server: project tools.
All tests use mocks to ensure zero network calls and deterministic results.
"""

from unittest.mock import MagicMock, patch
from plugvan.todoist.limits import (
    MAX_COLOR_LENGTH,
    MAX_PROJECT_NAME_LENGTH,
    MAX_TASK_ID_LENGTH,
)
from plugvan.todoist.tools.projects import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)
from tests.todoist.helpers import (
    MockProject,
)


# =====================================================================
# GET_PROJECT TESTS
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_get_project_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_project.return_value = MockProject(
        "proj_777",
        "İş Projesi",
        color="berry_red",
        parent_id="proj_parent_1",
        is_favorite=True,
        view_style="board",
    )

    result = get_project(project_id="proj_777")

    assert "📁 Proje Detayları (ID: proj_777)" in result
    assert "İsim: İş Projesi" in result
    assert "Renk: berry_red" in result
    assert "Üst Proje ID (parent_id): proj_parent_1" in result
    assert "Favori mi: Evet" in result
    assert "Görünüm Stili: board" in result
    mock_api.get_project.assert_called_once_with(project_id="proj_777")


@patch("plugvan.todoist.client.get_api_client")
def test_get_project_without_parent_shows_top_level(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_project.return_value = MockProject("proj_888", "Kişisel")

    result = get_project(project_id="proj_888")
    assert "Üst Proje ID (parent_id): Yok (üst seviye proje)" in result
    assert "Renk: Yok" in result
    assert "Favori mi: Hayır" in result
    assert "Görünüm Stili: Belirlenmedi" in result


def test_get_project_empty_id():
    result = get_project(project_id="   ")
    assert "❌ Invalid input: Project ID cannot be empty or whitespace." in result


def test_get_project_id_too_long():
    result = get_project(project_id="x" * (MAX_TASK_ID_LENGTH + 1))
    assert f"❌ Invalid input: Project ID exceeds maximum length of {MAX_TASK_ID_LENGTH} characters." in result


@patch("plugvan.todoist.client.get_api_client")
def test_get_project_sanitizes_exception_and_logs_cleanly(mock_get_client, caplog):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_project.side_effect = Exception(
        "TODOIST_API_TOKEN=SUPER_SECRET_TOKEN_123 failed Authorization: Bearer SUPER_SECRET_TOKEN_123"
    )

    with caplog.at_level("INFO"):
        result = get_project(project_id="proj_err")

    assert result == "❌ Failed to retrieve project from Todoist (ID: proj_err). Check server logs for details."
    assert "SUPER_SECRET_TOKEN_123" not in result
    assert "SUPER_SECRET_TOKEN_123" not in caplog.text


# =====================================================================
# CREATE_PROJECT & NESTED PROJECT TESTS
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_create_project_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.add_project.return_value = MockProject("proj_new_1", "Yeni Proje", color="berry_red")

    result = create_project(name="Yeni Proje", color="berry_red")
    assert "✅ Proje başarıyla oluşturuldu!" in result
    assert "ID: proj_new_1" in result
    assert "İsim: Yeni Proje" in result
    assert "Renk: berry_red" in result
    mock_api.add_project.assert_called_once_with(name="Yeni Proje", color="berry_red")


@patch("plugvan.todoist.client.get_api_client")
def test_create_project_with_parent_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    parent_proj = MockProject("parent_123", "Ana Kategori")
    mock_api.get_projects.return_value = [[parent_proj]]
    mock_api.add_project.return_value = MockProject("child_456", "Alt Kategori", parent_id="parent_123")

    result = create_project(
        name="Alt Kategori",
        parent_project_name_or_id="Ana Kategori",
    )
    assert "✅ Proje başarıyla oluşturuldu!" in result
    assert "ID: child_456" in result
    assert "İsim: Alt Kategori" in result
    assert "Üst Proje: 'Ana Kategori' (ID: parent_123)" in result
    mock_api.add_project.assert_called_once_with(name="Alt Kategori", parent_id="parent_123")


@patch("plugvan.todoist.client.get_api_client")
def test_create_project_parent_not_found(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = [[]]

    result = create_project(name="Alt Kategori", parent_project_name_or_id="Olmayan Proje")
    assert "⚠️ Belirtilen üst proje bulunamadı: 'Olmayan Proje'." in result


def test_create_project_empty_name():
    result = create_project(name="   ")
    assert "❌ Invalid input: Project name cannot be empty" in result


def test_create_project_name_too_long():
    long_name = "N" * (MAX_PROJECT_NAME_LENGTH + 1)
    result = create_project(name=long_name)
    assert "❌ Invalid input: Project name exceeds maximum length" in result


def test_create_project_color_too_long():
    long_color = "C" * (MAX_COLOR_LENGTH + 1)
    result = create_project(name="Valid Project", color=long_color)
    assert "❌ Invalid input: Color name exceeds maximum length" in result


@patch("plugvan.todoist.client.get_api_client")
def test_create_project_sanitizes_exception(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.add_project.side_effect = Exception("TODOIST_API_TOKEN=SECRET")

    result = create_project(name="ErrProj")
    assert result == "❌ Failed to create project 'ErrProj' in Todoist. Check server logs for details."
    assert "SECRET" not in result


# =====================================================================
# UPDATE_PROJECT TESTS
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_update_project_name_only(mock_get_client):
    """Sadece name verildiğinde body'de yalnızca name gönderilmeli."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_project = MockProject("proj_1", "Eski İsim")
    mock_api.get_projects.return_value = [[mock_project]]

    result = update_project(project_name_or_id="proj_1", name="Yeni İsim")

    assert "✅ Proje başarıyla güncellendi (ID: proj_1)!" in result
    assert "İsim: 'Yeni İsim'" in result
    assert "Renk:" not in result
    mock_api.update_project.assert_called_once_with(project_id="proj_1", name="Yeni İsim")


@patch("plugvan.todoist.client.get_api_client")
def test_update_project_color_only(mock_get_client):
    """Sadece color verildiğinde body'de yalnızca color gönderilmeli."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_project = MockProject("proj_2", "Proje İsmi")
    mock_api.get_projects.return_value = [[mock_project]]

    result = update_project(project_name_or_id="Proje İsmi", color="teal")

    assert "✅ Proje başarıyla güncellendi (ID: proj_2)!" in result
    assert "Renk: 'teal'" in result
    assert "İsim:" not in result
    mock_api.update_project.assert_called_once_with(project_id="proj_2", color="teal")


@patch("plugvan.todoist.client.get_api_client")
def test_update_project_name_and_color(mock_get_client):
    """İkisi birden verildiğinde body'de her ikisi de gönderilmeli."""
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_project = MockProject("proj_3", "Eski İsim")
    mock_api.get_projects.return_value = [[mock_project]]

    result = update_project(project_name_or_id="proj_3", name="Güncel İsim", color="mint_green")

    assert "✅ Proje başarıyla güncellendi (ID: proj_3)!" in result
    assert "İsim: 'Güncel İsim'" in result
    assert "Renk: 'mint_green'" in result
    mock_api.update_project.assert_called_once_with(project_id="proj_3", name="Güncel İsim", color="mint_green")


def test_update_project_no_fields_provided():
    """Hiçbir alan verilmeden çağrıldığında API'ye hiç gitmeden uyarı dönmeli (no-op)."""
    result = update_project(project_name_or_id="proj_4")
    assert "⚠️ Güncellenecek hiçbir alan belirtilmedi" in result


def test_update_project_empty_identifier():
    result = update_project(project_name_or_id="   ", name="Yeni İsim")
    assert "❌ Invalid input: Project identifier cannot be empty" in result


@patch("plugvan.todoist.client.get_api_client")
def test_update_project_not_found(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = [[]]

    result = update_project(project_name_or_id="Olmayan Proje", name="Yeni İsim")
    assert "⚠️ Güncellenecek proje bulunamadı: 'Olmayan Proje'." in result
    mock_api.update_project.assert_not_called()


@patch("plugvan.todoist.client.get_api_client")
def test_update_project_sanitizes_exception(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_project = MockProject("proj_5", "Proje")
    mock_api.get_projects.return_value = [[mock_project]]
    mock_api.update_project.side_effect = Exception("TODOIST_API_TOKEN=SECRET")

    result = update_project(project_name_or_id="proj_5", name="Yeni İsim")
    assert result == "❌ Failed to update project 'proj_5' in Todoist. Check server logs for details."
    assert "SECRET" not in result


# =====================================================================
# DELETE_PROJECT TESTS
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_delete_project_by_id_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_project = MockProject("proj_123", "Eski Proje")
    mock_api.get_projects.return_value = [[mock_project]]
    mock_api.delete_project.return_value = True

    result = delete_project(project_name_or_id="proj_123")
    assert "🗑️ Proje başarıyla silindi: 'Eski Proje' (ID: proj_123)." in result
    mock_api.delete_project.assert_called_once_with(project_id="proj_123")


@patch("plugvan.todoist.client.get_api_client")
def test_delete_project_by_name_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_project = MockProject("proj_456", "Silinecek Proje")
    mock_api.get_projects.return_value = [[mock_project]]
    mock_api.delete_project.return_value = True

    result = delete_project(project_name_or_id="Silinecek Proje")
    assert "🗑️ Proje başarıyla silindi: 'Silinecek Proje' (ID: proj_456)." in result
    mock_api.delete_project.assert_called_once_with(project_id="proj_456")


@patch("plugvan.todoist.client.get_api_client")
def test_delete_project_not_found(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = [[]]

    result = delete_project(project_name_or_id="Nonexistent")
    assert "⚠️ Silinecek proje bulunamadı: 'Nonexistent'." in result


def test_delete_project_empty_identifier():
    result = delete_project(project_name_or_id="   ")
    assert "❌ Invalid input: Project identifier cannot be empty" in result


# =====================================================================
# LIST_PROJECTS TESTS (HIERARCHICAL)
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_list_projects_hierarchical(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    p1 = MockProject("p1", "Gelen Kutusu", is_inbox=True)
    p2 = MockProject("p2", "İş", color="berry_red")
    p3 = MockProject("p3", "Alt Görevler", parent_id="p2")
    mock_api.get_projects.return_value = [[p1, p2, p3]]

    result = list_projects()
    assert "📁 Mevcut Projeler (Toplam: 3):" in result
    assert "1. [p1] Gelen Kutusu [Gelen Kutusu]" in result
    assert "2. [p2] İş, Renk: berry_red" in result
    assert "└── [p3] Alt Görevler" in result


@patch("plugvan.todoist.client.get_api_client")
def test_list_projects_empty(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_projects.return_value = [[]]

    result = list_projects()
    assert "ℹ️ Todoist hesabınızda herhangi bir proje bulunamadı." in result
