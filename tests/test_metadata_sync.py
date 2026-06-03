import pytest
from unittest.mock import patch, MagicMock
from gitea_skills.github_api import get_merged_pr_metadata

@patch("gitea_skills.github_api._load_env")
@patch("gitea_skills.github_api._get_project_dir")
@patch("gitea_skills.github_api.gitea_api")
@patch("subprocess.run")
def test_get_merged_pr_metadata(mock_run, mock_gitea_api, mock_project_dir, mock_load_env):
    # Mock environment settings
    mock_load_env.return_value = {
        "GITEA_URL": "http://localhost:3000",
        "REPO_OWNER": "admin",
        "REPO_NAME": "friendly-davinci",
        "ADMIN_TOKEN": "mock-token"
    }
    mock_project_dir.return_value = "/mock/project"

    # Mock subprocess.run for git fetch and git log
    # Git log returns a list of mock commits
    mock_log_result = MagicMock()
    mock_log_result.stdout = "sha123 Merge pull request 'feat: cool feature' (#42) from branch into main\n"
    mock_run.return_value = mock_log_result

    # Mock Gitea API responses
    mock_gitea_api.list_pull_requests.return_value = [
        {
            "number": 42,
            "title": "feat: cool feature",
            "body": "This is a cool feature.",
            "html_url": "http://localhost:3000/admin/friendly-davinci/pulls/42",
            "merged": True,
            "merged_at": "2026-06-03T00:00:00Z",
            "merge_commit_sha": "sha123",
            "user": {"username": "developer-agent"}
        }
    ]

    mock_gitea_api.get_pr_comments.return_value = [
        {
            "user": {"username": "reviewer-agent"},
            "created_at": "2026-06-03T01:00:00Z",
            "body": "This looks great!"
        }
    ]

    mock_gitea_api.get_pr_reviews.return_value = [
        {
            "id": 1,
            "user": {"username": "reviewer-agent"},
            "state": "APPROVED",
            "body": "Code is solid.",
            "submitted_at": "2026-06-03T02:00:00Z"
        }
    ]

    mock_gitea_api.get_review_comments.return_value = [
        {
            "path": "src/calculator.py",
            "position": 10,
            "body": "Ensure this case is covered."
        }
    ]

    # Execute
    metadata = get_merged_pr_metadata("main")

    # Assertions
    assert "Gitea PR [#42]" in metadata
    assert "feat: cool feature" in metadata
    assert "This is a cool feature." in metadata
    assert "@developer-agent" in metadata
    assert "Discussion & Comments" in metadata
    assert "@reviewer-agent" in metadata
    assert "This looks great!" in metadata
    assert "Review Activity" in metadata
    assert "APPROVED" in metadata
    assert "Code is solid." in metadata
    assert "src/calculator.py" in metadata
    assert "Ensure this case is covered." in metadata
