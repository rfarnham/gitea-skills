import pytest
import os
from unittest.mock import patch, MagicMock
from gitea_skills import gitea_api, core
from gitea_skills.dedup_issues import _dedup_heuristic

# ---------------------------------------------------------------------------
# API client tests
# ---------------------------------------------------------------------------

@patch("gitea_skills.gitea_api._request")
def test_create_issue_api(mock_request):
    mock_request.return_value = {"number": 5}
    res = gitea_api.create_issue("token", "owner", "repo", "Title", "Body", ["bug"])
    assert res["number"] == 5
    mock_request.assert_called_once_with("POST", "/repos/owner/repo/issues", "token", {
        "title": "Title",
        "body": "Body",
        "labels": ["bug"]
    })

@patch("gitea_skills.gitea_api._request")
def test_list_issues_api(mock_request):
    mock_request.return_value = [{"number": 1, "title": "Issue"}]
    res = gitea_api.list_issues("token", "owner", "repo", "open", "issues")
    assert len(res) == 1
    assert res[0]["number"] == 1
    mock_request.assert_called_once_with("GET", "/repos/owner/repo/issues?state=open&type=issues", "token")

@patch("gitea_skills.gitea_api._request")
def test_get_issue_api(mock_request):
    mock_request.return_value = {"number": 1, "title": "Issue"}
    res = gitea_api.get_issue("token", "owner", "repo", 1)
    assert res["number"] == 1
    mock_request.assert_called_once_with("GET", "/repos/owner/repo/issues/1", "token")

@patch("gitea_skills.gitea_api._request")
def test_update_issue_api(mock_request):
    mock_request.return_value = {"number": 1, "state": "closed"}
    res = gitea_api.update_issue("token", "owner", "repo", 1, state="closed", title="New Title")
    assert res["state"] == "closed"
    mock_request.assert_called_once_with("PATCH", "/repos/owner/repo/issues/1", "token", {
        "state": "closed",
        "title": "New Title"
    })

# ---------------------------------------------------------------------------
# Core helpers tests
# ---------------------------------------------------------------------------

@patch("gitea_skills.core._load_env", return_value={"ADMIN_TOKEN": "token", "GITEA_URL": "http://localhost:3000"})
@patch("gitea_skills.gitea_api.list_repo_labels", return_value=[{"id": 101, "name": "bug"}])
@patch("gitea_skills.gitea_api.create_issue")
def test_issue_create_core(mock_create_issue, mock_list_repo_labels, mock_load_env):
    mock_create_issue.return_value = {"number": 10}
    msg = core.issue_create("Title", "Body", ["bug"])
    assert "Issue created successfully! Issue Index: 10" in msg
    mock_create_issue.assert_called_once_with("token", "admin", "friendly-davinci", "Title", "Body", [101])

@patch("gitea_skills.core._load_env", return_value={"ADMIN_TOKEN": "token", "GITEA_URL": "http://localhost:3000"})
@patch("gitea_skills.gitea_api.list_issues")
def test_issue_list_core(mock_list_issues, mock_load_env):
    mock_list_issues.return_value = [
        {"number": 1, "title": "Bug 1", "labels": [{"name": "bug"}]},
        {"number": 2, "title": "Feature 1", "labels": []}
    ]
    msg = core.issue_list("open")
    assert "#1: Bug 1 [bug]" in msg
    assert "#2: Feature 1" in msg
    mock_list_issues.assert_called_once_with("token", "admin", "friendly-davinci", state="open", type="issues")

@patch("gitea_skills.core._load_env", return_value={"ADMIN_TOKEN": "token", "GITEA_URL": "http://localhost:3000"})
@patch("gitea_skills.gitea_api.get_issue")
def test_issue_details_core(mock_get_issue, mock_load_env):
    mock_get_issue.return_value = {
        "number": 1,
        "title": "Bug 1",
        "state": "open",
        "body": "Body text",
        "labels": [{"name": "bug"}]
    }
    msg = core.issue_details(1)
    assert "Issue #1: Bug 1 [bug]" in msg
    assert "State: open" in msg
    assert "Description:\nBody text" in msg
    mock_get_issue.assert_called_once_with("token", "admin", "friendly-davinci", 1)

@patch("gitea_skills.core._load_env", return_value={"ADMIN_TOKEN": "token", "GITEA_URL": "http://localhost:3000"})
@patch("gitea_skills.gitea_api.update_issue")
def test_issue_close_core(mock_update_issue, mock_load_env):
    mock_update_issue.return_value = {"number": 1, "state": "closed"}
    msg = core.issue_close(1)
    assert "Issue #1 closed successfully." in msg
    mock_update_issue.assert_called_once_with("token", "admin", "friendly-davinci", 1, state="closed")

# ---------------------------------------------------------------------------
# Deduplication engine tests
# ---------------------------------------------------------------------------

def test_dedup_heuristic_duplicates():
    issues = [
        {"number": 1, "title": "Calculator crash on division by zero", "body": "It crashes when dividing by zero."},
        {"number": 2, "title": "Division by zero crashes calculator app", "body": "Dividing by zero throws crash."},
        {"number": 3, "title": "Add multiplication feature", "body": "We need multiplication in the calculator."}
    ]
    res = _dedup_heuristic(issues)
    assert "[Recommendation] Issue #2 is a duplicate of Issue #1" in res
    assert "[Recommendation] Issue #3" not in res

# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

@patch("gitea_skills.core.issue_create")
def test_cli_issue_create(mock_issue_create):
    from gitea_skills.cli import main
    # Direct CLI execution test via argument parser
    with patch("sys.argv", ["gitea-skills", "issue", "create", "--title", "Title", "--body", "Body", "--labels", "bug"]):
        with patch("builtins.print") as mock_print:
            main()
            mock_issue_create.assert_called_once_with("Title", "Body", ["bug"])
