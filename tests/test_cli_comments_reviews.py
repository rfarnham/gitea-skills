import pytest
import json
from unittest.mock import patch, MagicMock
from gitea_skills.core import pr_get_comments, pr_get_reviews
from gitea_skills.cli import main

@patch("gitea_skills.core._load_env")
@patch("gitea_skills.core.gitea_api")
def test_pr_get_comments(mock_gitea_api, mock_load_env):
    mock_load_env.return_value = {
        "GITEA_URL": "http://localhost:3000",
        "REPO_OWNER": "admin",
        "REPO_NAME": "friendly-davinci"
    }

    mock_gitea_api.get_pr_comments.return_value = [
        {
            "user": {"username": "developer-agent"},
            "created_at": "2026-06-17T11:30:00Z",
            "body": "Comment body text"
        }
    ]

    # Test formatted text output
    res = pr_get_comments(1)
    assert "[developer-agent] 2026-06-17 11:30:00:" in res
    assert "Comment body text" in res

    # Test JSON output
    res_json = pr_get_comments(1, as_json=True)
    parsed = json.loads(res_json)
    assert isinstance(parsed, list)
    assert parsed[0]["body"] == "Comment body text"

@patch("gitea_skills.core._load_env")
@patch("gitea_skills.core.gitea_api")
def test_pr_get_reviews(mock_gitea_api, mock_load_env):
    mock_load_env.return_value = {
        "GITEA_URL": "http://localhost:3000",
        "REPO_OWNER": "admin",
        "REPO_NAME": "friendly-davinci"
    }

    mock_gitea_api.get_pr_reviews.return_value = [
        {
            "id": 22,
            "user": {"username": "admin"},
            "state": "COMMENT",
            "body": ""
        }
    ]

    mock_gitea_api.get_review_comments.return_value = [
        {
            "path": "storage/pebble/pebble.go",
            "position": 46,
            "original_position": 22,
            "diff_hunk": "@@ -22,0 +46,4 @@\n+\n+\t\tentity, mtype, metric, valBytes, ts, ok := parseLine(line)\n+\t\tif !ok {\n+\t\t\terrCount++",
            "body": "We should log the failed line to ease debugging, don't you think?"
        }
    ]

    # Test formatted text output
    res = pr_get_reviews(1)
    assert "Review ID 22 by [admin] (COMMENT)" in res
    assert "File: storage/pebble/pebble.go" in res
    assert "Line: 46 (Original Line: 22)" in res
    assert "Diff:" in res
    assert "entity, mtype, metric, valBytes, ts, ok := parseLine(line)" in res
    assert "Comment: We should log the failed line to ease debugging, don't you think?" in res

    # Test JSON output
    res_json = pr_get_reviews(1, as_json=True)
    parsed = json.loads(res_json)
    assert isinstance(parsed, list)
    assert parsed[0]["id"] == 22
    assert len(parsed[0]["comments"]) == 1
    assert parsed[0]["comments"][0]["path"] == "storage/pebble/pebble.go"

@patch("gitea_skills.core.pr_get_reviews")
@patch("gitea_skills.core.pr_get_comments")
def test_cli_parsing(mock_pr_get_comments, mock_pr_get_reviews):
    # Test `gitea-skills pr comments 1`
    with patch("sys.argv", ["gitea-skills", "pr", "comments", "1"]):
        main()
        mock_pr_get_comments.assert_called_with(1, False)

    # Test `gitea-skills pr comments 1 --json`
    with patch("sys.argv", ["gitea-skills", "pr", "comments", "1", "--json"]):
        main()
        mock_pr_get_comments.assert_called_with(1, True)

    # Test `gitea-skills pr reviews 2`
    with patch("sys.argv", ["gitea-skills", "pr", "reviews", "2"]):
        main()
        mock_pr_get_reviews.assert_called_with(2, False)
