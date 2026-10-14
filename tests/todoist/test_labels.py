"""
Unit and security tests for the Todoist FastMCP Server: label tools.
All tests use mocks to ensure zero network calls and deterministic results.
"""

import logging
from unittest.mock import MagicMock, patch
from plugvan.todoist.limits import (
    MAX_LABEL_NAME_LENGTH,
)
from plugvan.todoist.tools.labels import (
    create_label,
    delete_label,
    list_labels,
    update_label,
)
from tests.todoist.helpers import (
    MockLabel,
    _make_http_status_error,
    write_call_count,
)


# =====================================================================
# LABELS (LIST_LABELS, CREATE_LABEL, UPDATE_LABEL, DELETE_LABEL) TESTS
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_list_labels_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    lbl1 = MockLabel("lbl_1", "önemli", color="berry_red", is_favorite=True)
    lbl2 = MockLabel("lbl_2", "iş", color="blue")
    mock_api.get_labels.return_value = [[lbl1, lbl2]]

    result = list_labels()
    assert "🏷️ Available Labels (Total: 2):" in result
    assert "1. [lbl_1] @önemli ⭐, Color: berry_red" in result
    assert "2. [lbl_2] @iş, Color: blue" in result


@patch("plugvan.todoist.client.get_api_client")
def test_list_labels_empty(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_labels.return_value = [[]]

    result = list_labels()
    assert "ℹ️ No labels found in your Todoist account." in result


@patch("plugvan.todoist.client.get_api_client")
def test_list_labels_sanitizes_exception(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_labels.side_effect = Exception("TODOIST_API_TOKEN=SECRET")

    result = list_labels()
    assert result == "❌ Failed to list labels from Todoist. Check server logs for details."
    assert "SECRET" not in result


@patch("plugvan.todoist.client.get_api_client")
def test_create_label_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.add_label.return_value = MockLabel("lbl_new_1", "odak", color="mint_green")

    result = create_label(name="@odak", color="mint_green")
    assert "✅ Label created successfully!" in result
    assert "ID: lbl_new_1" in result
    assert "Name: @odak" in result
    assert "Color: mint_green" in result
    mock_api.add_label.assert_called_once_with(name="odak", color="mint_green")


def test_create_label_empty_name():
    result = create_label(name="   ")
    assert "❌ Invalid input: Label name cannot be empty" in result


def test_create_label_name_too_long():
    long_name = "L" * (MAX_LABEL_NAME_LENGTH + 1)
    result = create_label(name=long_name)
    assert "❌ Invalid input: Label name exceeds maximum length" in result


@patch("plugvan.todoist.client.get_api_client")
def test_create_label_sanitizes_exception(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.add_label.side_effect = Exception("TODOIST_API_TOKEN=SECRET")

    result = create_label(name="error_label")
    assert result == "❌ Failed to create label '@error_label' in Todoist. Check server logs for details."
    assert "SECRET" not in result


@patch("plugvan.todoist.client.get_api_client")
def test_update_label_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    lbl = MockLabel("lbl_100", "eski_ad")
    mock_api.get_labels.return_value = [[lbl]]

    result = update_label(label_name_or_id="eski_ad", new_name="yeni_ad", color="charcoal")
    assert "✅ Label updated successfully (ID: lbl_100)!" in result
    assert "Name: '@yeni_ad'" in result
    assert "Color: 'charcoal'" in result
    mock_api.update_label.assert_called_once_with(label_id="lbl_100", name="yeni_ad", color="charcoal")


@patch("plugvan.todoist.client.get_api_client")
def test_update_label_not_found(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_labels.return_value = [[]]

    result = update_label(label_name_or_id="olmayan_etiket", new_name="yeni_ad")
    assert "⚠️ Label to update not found: '@olmayan_etiket'." in result


def test_update_label_no_fields():
    result = update_label(label_name_or_id="lbl_1")
    assert "⚠️ No fields to update were specified" in result


@patch("plugvan.todoist.client.get_api_client")
def test_delete_label_success(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    lbl = MockLabel("lbl_200", "silinecek")
    mock_api.get_labels.return_value = [[lbl]]
    mock_api.delete_label.return_value = True

    result = delete_label(label_name_or_id="silinecek")
    assert "🗑️ Label deleted successfully: '@silinecek' (ID: lbl_200)." in result
    mock_api.delete_label.assert_called_once_with(label_id="lbl_200")


@patch("plugvan.todoist.client.get_api_client")
def test_delete_label_not_found(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_labels.return_value = [[]]

    result = delete_label(label_name_or_id="olmayan_etiket")
    assert "⚠️ Label to delete not found: '@olmayan_etiket'." in result


# =====================================================================
# DELETE_LABEL / UPDATE_LABEL: EXACT NAME OR ID, AMBIGUITY, NO WRITE ON ERROR
# =====================================================================

@patch("plugvan.todoist.client.get_api_client")
def test_delete_and_update_label_case_fold_duplicates_are_ambiguous(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_labels.return_value = [[MockLabel("lbl_1", "Work"), MockLabel("lbl_2", "work")]]

    deleted = delete_label(label_name_or_id="@work")
    updated = update_label(label_name_or_id="WORK", color="teal")

    expected = (
        "⚠️ Multiple labels found for '@work'; please use the label ID:\n"
        "• Work (lbl_1)\n"
        "• work (lbl_2)"
    )
    assert deleted == expected
    assert updated.startswith("⚠️ Multiple labels found for '@WORK'")
    assert write_call_count(mock_api) == 0


@patch("plugvan.todoist.client.get_api_client")
def test_delete_and_update_label_partial_name_is_not_found(mock_get_client):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_labels.return_value = [[MockLabel("lbl_1", "önemli")]]

    assert delete_label(label_name_or_id="önem") == "⚠️ Label to delete not found: '@önem'."
    assert update_label(label_name_or_id="önem", new_name="x") == "⚠️ Label to update not found: '@önem'."
    assert write_call_count(mock_api) == 0


@patch("plugvan.todoist.client.get_api_client")
def test_delete_and_update_label_lookup_failure_is_generic_error(mock_get_client, caplog):
    mock_api = MagicMock()
    mock_get_client.return_value = mock_api
    mock_api.get_labels.side_effect = _make_http_status_error(500, "upstream secret body")

    with caplog.at_level(logging.ERROR, logger="todoist_mcp"):
        deleted = delete_label(label_name_or_id="iş")
        updated = update_label(label_name_or_id="iş", new_name="x")

    assert deleted == "❌ Failed to delete label '@iş' in Todoist. Check server logs for details."
    assert updated == "❌ Failed to update label '@iş' in Todoist. Check server logs for details."
    assert write_call_count(mock_api) == 0
    for text in (deleted, updated, caplog.text):
        assert "upstream secret body" not in text
        assert "500 error" not in text
    assert "error_type=HTTPStatusError" in caplog.text
