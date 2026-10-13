"""
Unit tests for the Todoist FastMCP Server name-resolution helpers.
All tests use mocks to ensure zero network calls and deterministic results.
"""

import logging
from unittest.mock import MagicMock

from plugvan.todoist.resolvers import (
    INBOX_DISPLAY_NAME,
    MAX_AMBIGUOUS_CANDIDATES,
    Ambiguous,
    Candidate,
    Found,
    LookupFailed,
    NotFound,
    _find_project_id,
    _resolve_label,
    _resolve_project,
    _resolve_section,
    resolve_label,
    resolve_project,
    resolve_section,
)
from tests.todoist.helpers import (
    MockLabel,
    MockProject,
    MockSection,
)


def _api_with_projects(*projects):
    mock_api = MagicMock()
    mock_api.get_projects.return_value = [list(projects)]
    return mock_api


def _api_with_sections(*sections):
    mock_api = MagicMock()
    mock_api.get_sections.return_value = [list(sections)]
    return mock_api


def _api_with_labels(*labels):
    mock_api = MagicMock()
    mock_api.get_labels.return_value = [list(labels)]
    return mock_api


# =====================================================================
# PROJECT RESOLUTION TESTS
# =====================================================================

def test_resolve_project_exact_and_case_insensitive():
    mock_api = _api_with_projects(
        MockProject("p1", "Inbox", is_inbox=True),
        MockProject("p2", "Odak & Gelişim"),
        MockProject("p3", "Kişisel Projeler"),
    )

    assert resolve_project(mock_api, "Odak & Gelişim") == Found("p2", "Odak & Gelişim")
    assert resolve_project(mock_api, "odak & gelişim") == Found("p2", "Odak & Gelişim")
    assert resolve_project(mock_api, "KİŞİSEL PROJELER") == Found("p3", "Kişisel Projeler")


def test_resolve_project_inbox_aliases():
    mock_api = _api_with_projects(MockProject("inbox_99", "Gelen Kutusu", is_inbox=True))

    for alias in ("Inbox", "gelen kutusu", "GelenKutusu"):
        assert resolve_project(mock_api, alias, allow_inbox_alias=True) == Found("inbox_99", "Gelen Kutusu")


def test_resolve_project_unique_partial_match():
    mock_api = _api_with_projects(MockProject("p_sub", "Yazılım Geliştirme Çalışmaları"))

    assert resolve_project(mock_api, "Yazılım Geliştirme", allow_partial=True) == Found(
        "p_sub", "Yazılım Geliştirme Çalışmaları"
    )


def test_resolve_project_api_failure_is_not_reported_as_not_found(caplog):
    """An API error must never look like "no such project" to the caller."""
    failing_api = MagicMock()
    failing_api.get_projects.side_effect = RuntimeError("secret-token-123 connection reset")
    empty_api = _api_with_projects()

    with caplog.at_level(logging.ERROR, logger="todoist_mcp"):
        failed = resolve_project(failing_api, "İş")
    not_found = resolve_project(empty_api, "İş")

    assert failed == LookupFailed("RuntimeError")
    assert not_found == NotFound("İş")
    assert failed != not_found
    assert "secret-token-123" not in repr(failed)
    assert "secret-token-123" not in caplog.text
    assert "error_type=RuntimeError" in caplog.text


def test_resolve_project_by_id():
    mock_api = _api_with_projects(MockProject("2203306141", "Work"))

    assert resolve_project(mock_api, " 2203306141 ") == Found("2203306141", "Work")


def test_resolve_project_not_found_carries_cleaned_query():
    mock_api = _api_with_projects(MockProject("p1", "Work"))

    assert resolve_project(mock_api, "  Wrok  ") == NotFound("Wrok")


def test_resolve_project_empty_input_is_not_found_without_api_call():
    mock_api = _api_with_projects(MockProject("p1", "Work"))

    assert resolve_project(mock_api, "   ") == NotFound("")
    mock_api.get_projects.assert_not_called()


def test_resolve_project_partial_disabled_by_default():
    mock_api = _api_with_projects(MockProject("p1", "Homework"))

    assert resolve_project(mock_api, "Work") == NotFound("Work")


def test_resolve_project_exact_beats_partial_candidates():
    mock_api = _api_with_projects(
        MockProject("p1", "Homework"),
        MockProject("p2", "Work"),
        MockProject("p3", "Workshop"),
    )

    assert resolve_project(mock_api, "work", allow_partial=True) == Found("p2", "Work")


def test_resolve_project_partial_with_two_hits_is_ambiguous():
    mock_api = _api_with_projects(
        MockProject("p1", "Homework"),
        MockProject("p2", "Workshop"),
    )

    result = resolve_project(mock_api, "Work", allow_partial=True)

    assert result == Ambiguous(
        query="Work",
        candidates=(Candidate("p1", "Homework"), Candidate("p2", "Workshop")),
        has_more=False,
    )
    assert result.candidate_lines() == ["Homework (p1)", "Workshop (p2)"]


def test_resolve_project_duplicate_exact_names_are_ambiguous_without_partial_fallthrough():
    mock_api = _api_with_projects(
        MockProject("p1", "Work"),
        MockProject("p2", "work"),
        MockProject("p3", "Homework"),
    )

    result = resolve_project(mock_api, "Work", allow_partial=True)

    assert isinstance(result, Ambiguous)
    assert result.candidates == (Candidate("p1", "Work"), Candidate("p2", "work"))


def test_resolve_project_ambiguous_caps_candidates_with_more_marker():
    projects = [MockProject(f"p{i}", f"Proje {i}") for i in range(1, 8)]
    mock_api = _api_with_projects(*projects)

    result = resolve_project(mock_api, "Proje", allow_partial=True)

    assert isinstance(result, Ambiguous)
    assert len(result.candidates) == MAX_AMBIGUOUS_CANDIDATES == 5
    assert result.has_more is True
    assert result.candidate_lines()[-1] == "…"
    assert result.candidate_lines()[0] == "Proje 1 (p1)"


def test_resolve_project_inbox_alias_disabled_by_default():
    mock_api = _api_with_projects(MockProject("inbox_1", "Gelen Kutusu", is_inbox=True))

    assert resolve_project(mock_api, "Inbox") == NotFound("Inbox")


def test_resolve_project_inbox_alias_prefers_real_inbox():
    mock_api = _api_with_projects(
        MockProject("p_named", "Inbox"),
        MockProject("inbox_1", "Gelen Kutusu", is_inbox=True),
    )

    assert resolve_project(mock_api, "inbox", allow_inbox_alias=True) == Found("inbox_1", "Gelen Kutusu")


def test_resolve_project_inbox_alias_without_listed_inbox_is_found_without_id():
    mock_api = _api_with_projects(MockProject("p1", "Inbox Zero Method"))

    result = resolve_project(mock_api, "GELEN KUTUSU", allow_inbox_alias=True, allow_partial=True)

    assert result == Found(None, INBOX_DISPLAY_NAME)


# =====================================================================
# SECTION RESOLUTION TESTS
# =====================================================================

def test_resolve_section_by_id_and_exact_name():
    mock_api = _api_with_sections(MockSection("sec_1", "Backlog", project_id="proj_1"))

    assert resolve_section(mock_api, "sec_1") == Found("sec_1", "Backlog")
    assert resolve_section(mock_api, "backlog") == Found("sec_1", "Backlog")


def test_resolve_section_never_matches_partially():
    mock_api = _api_with_sections(MockSection("sec_1", "Backlog", project_id="proj_1"))

    assert resolve_section(mock_api, "Back") == NotFound("Back")


def test_resolve_section_same_name_in_two_projects_is_ambiguous_when_unscoped():
    mock_api = _api_with_sections(
        MockSection("sec_1", "Backlog", project_id="proj_1"),
        MockSection("sec_2", "Backlog", project_id="proj_2"),
    )

    result = resolve_section(mock_api, "Backlog")

    assert isinstance(result, Ambiguous)
    assert result.candidate_lines() == ["Backlog (sec_1)", "Backlog (sec_2)"]


def test_resolve_section_scoped_excludes_other_projects():
    mock_api = _api_with_sections(
        MockSection("sec_1", "Backlog", project_id="proj_1"),
        MockSection("sec_2", "Backlog", project_id="proj_2"),
    )

    assert resolve_section(mock_api, "Backlog", project_id="proj_2") == Found("sec_2", "Backlog")
    assert resolve_section(mock_api, "sec_1", project_id="proj_2") == NotFound("sec_1")
    mock_api.get_sections.assert_called_with(project_id="proj_2")


def test_resolve_section_api_failure_is_lookup_failed(caplog):
    mock_api = MagicMock()
    mock_api.get_sections.side_effect = ConnectionError("upstream body: internal detail")

    with caplog.at_level(logging.ERROR, logger="todoist_mcp"):
        result = resolve_section(mock_api, "Backlog")

    assert result == LookupFailed("ConnectionError")
    assert "internal detail" not in caplog.text
    assert "error_type=ConnectionError" in caplog.text


# =====================================================================
# LABEL RESOLUTION TESTS
# =====================================================================

def test_resolve_label_strips_at_prefix_and_matches_exactly():
    mock_api = _api_with_labels(MockLabel("lbl_1", "önemli"), MockLabel("lbl_2", "iş"))

    assert resolve_label(mock_api, "@önemli") == Found("lbl_1", "önemli")
    assert resolve_label(mock_api, "lbl_2") == Found("lbl_2", "iş")
    assert resolve_label(mock_api, "önem") == NotFound("önem")


def test_resolve_label_case_fold_duplicates_are_ambiguous():
    mock_api = _api_with_labels(MockLabel("lbl_1", "Work"), MockLabel("lbl_2", "work"))

    result = resolve_label(mock_api, "@WORK")

    assert isinstance(result, Ambiguous)
    assert result.candidate_lines() == ["Work (lbl_1)", "work (lbl_2)"]


def test_resolve_label_api_failure_is_lookup_failed(caplog):
    mock_api = MagicMock()
    mock_api.get_labels.side_effect = TimeoutError("token=abc123")

    with caplog.at_level(logging.ERROR, logger="todoist_mcp"):
        result = resolve_label(mock_api, "iş")

    assert result == LookupFailed("TimeoutError")
    assert "abc123" not in caplog.text


# =====================================================================
# COMPATIBILITY WRAPPERS (legacy behavior, removed in #14)
# =====================================================================

def test_legacy_find_project_id_returns_none_on_api_failure():
    mock_api = MagicMock()
    mock_api.get_projects.side_effect = RuntimeError("Network timeout")

    assert _find_project_id(mock_api, "Nonexistent") is None


def test_legacy_resolve_project_keeps_first_wins_partial_match():
    mock_api = _api_with_projects(
        MockProject("p1", "Homework"),
        MockProject("p2", "Workshop"),
    )

    assert _resolve_project(mock_api, "Work") == ("p1", "Homework")
    assert _find_project_id(mock_api, "Work") == "p1"


def test_legacy_resolve_section_keeps_first_wins_across_projects():
    mock_api = _api_with_sections(
        MockSection("sec_1", "Backlog", project_id="proj_1"),
        MockSection("sec_2", "Backlog", project_id="proj_2"),
    )

    assert _resolve_section(mock_api, "Backlog") == ("sec_1", "Backlog")


def test_legacy_resolve_label_returns_none_pair_when_missing():
    mock_api = _api_with_labels(MockLabel("lbl_1", "önemli"))

    assert _resolve_label(mock_api, "@önemli") == ("lbl_1", "önemli")
    assert _resolve_label(mock_api, "olmayan") == (None, None)
