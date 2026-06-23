import os
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from gitea_skills import gitea_api, core
from gitea_skills.core import repo_create

@patch("gitea_skills.gitea_api._request")
def test_get_user(mock_request):
    mock_request.return_value = {"username": "testuser"}
    res = gitea_api.get_user("testtoken")
    assert res["username"] == "testuser"
    mock_request.assert_called_once_with("GET", "/user", "testtoken")

@patch("gitea_skills.gitea_api.get_user")
@patch("gitea_skills.gitea_api._request")
def test_create_repo_user_owned(mock_request, mock_get_user):
    # Test repository creation owned by the user (no owner specified)
    mock_request.return_value = {"clone_url": "http://localhost:3000/admin/testrepo.git"}
    
    res = gitea_api.create_repo("token", "testrepo", "desc", auto_init=True, private=True)
    assert res["clone_url"] == "http://localhost:3000/admin/testrepo.git"
    mock_request.assert_called_once_with("POST", "/user/repos", "token", {
        "name": "testrepo",
        "description": "desc",
        "private": True,
        "auto_init": True,
        "default_branch": "main"
    })
    mock_get_user.assert_not_called()

@patch("gitea_skills.gitea_api.get_user")
@patch("gitea_skills.gitea_api._request")
def test_create_repo_user_owned_matching_owner(mock_request, mock_get_user):
    # Test repository creation where owner matches authenticated username
    mock_get_user.return_value = {"username": "admin"}
    mock_request.return_value = {"clone_url": "http://localhost:3000/admin/testrepo.git"}
    
    res = gitea_api.create_repo("token", "testrepo", "desc", auto_init=False, private=False, owner="admin")
    assert res["clone_url"] == "http://localhost:3000/admin/testrepo.git"
    mock_request.assert_called_once_with("POST", "/user/repos", "token", {
        "name": "testrepo",
        "description": "desc",
        "private": False,
        "auto_init": False,
        "default_branch": "main"
    })
    mock_get_user.assert_called_once_with("token")

@patch("gitea_skills.gitea_api.get_user")
@patch("gitea_skills.gitea_api._request")
def test_create_repo_org_owned(mock_request, mock_get_user):
    # Test repository creation under an organization (owner differs from user)
    mock_get_user.return_value = {"username": "admin"}
    mock_request.return_value = {"clone_url": "http://localhost:3000/myorg/testrepo.git"}
    
    res = gitea_api.create_repo("token", "testrepo", "desc", auto_init=False, private=False, owner="myorg")
    assert res["clone_url"] == "http://localhost:3000/myorg/testrepo.git"
    mock_request.assert_called_once_with("POST", "/orgs/myorg/repos", "token", {
        "name": "testrepo",
        "description": "desc",
        "private": False,
        "auto_init": False,
        "default_branch": "main"
    })

@patch("gitea_skills.core._load_env", return_value={"ADMIN_TOKEN": "token", "GITEA_URL": "http://localhost:3000"})
@patch("gitea_skills.gitea_api.add_collaborator")
@patch("gitea_skills.gitea_api.create_repo")
def test_repo_create_core_no_origin(mock_create_repo, mock_add_collaborator, mock_load_env):
    mock_create_repo.return_value = {
        "clone_url": "http://localhost:3000/admin/test.git",
        "owner": {"username": "admin"}
    }
    
    msg = repo_create("test", "desc", private=False, auto_init=False)
    assert "Repository 'test' created successfully!" in msg
    assert "Clone URL: http://localhost:3000/admin/test.git" in msg
    assert "Added 'developer-agent' and 'reviewer-agent' as collaborators" in msg
    mock_create_repo.assert_called_once_with(
        token="token",
        name="test",
        description="desc",
        auto_init=False,
        private=False,
        owner=None
    )
    assert mock_add_collaborator.call_count == 2
    mock_add_collaborator.assert_any_call("token", "admin", "test", "developer-agent", "write")
    mock_add_collaborator.assert_any_call("token", "admin", "test", "reviewer-agent", "write")

@patch("gitea_skills.core._load_env", return_value={"ADMIN_TOKEN": "token", "GITEA_URL": "http://localhost:3000"})
@patch("gitea_skills.gitea_api.add_collaborator")
@patch("gitea_skills.gitea_api.create_repo")
@patch("subprocess.run")
def test_repo_create_core_set_origin_new(mock_run, mock_create_repo, mock_add_collaborator, mock_load_env):
    mock_create_repo.return_value = {
        "clone_url": "http://localhost:3000/admin/test.git",
        "owner": {"username": "admin"}
    }
    
    # Mock git check: inside worktree=true, origin check fails (no origin remote exists)
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="true\n"),  # git rev-parse --is-inside-work-tree
        MagicMock(returncode=1, stdout=""),        # git remote get-url origin
        MagicMock(returncode=0)                    # git remote add origin ...
    ]
    
    msg = repo_create("test", set_origin=True)
    assert "Added new git remote 'origin' pointing to the repository clone URL." in msg
    assert mock_run.call_count == 3
    # Check that remote add origin was called
    mock_run.assert_any_call(["git", "remote", "add", "origin", "http://localhost:3000/admin/test.git"], cwd=str(Path.cwd().resolve()), check=True)
    assert mock_add_collaborator.call_count == 2

@patch("gitea_skills.core._load_env", return_value={"ADMIN_TOKEN": "token", "GITEA_URL": "http://localhost:3000"})
@patch("gitea_skills.gitea_api.add_collaborator")
@patch("gitea_skills.gitea_api.create_repo")
@patch("subprocess.run")
def test_repo_create_core_set_origin_exists(mock_run, mock_create_repo, mock_add_collaborator, mock_load_env):
    mock_create_repo.return_value = {
        "clone_url": "http://localhost:3000/admin/test.git",
        "owner": {"username": "admin"}
    }
    
    # Mock git check: inside worktree=true, origin check succeeds (origin remote already exists)
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="true\n"),  # git rev-parse --is-inside-work-tree
        MagicMock(returncode=0, stdout="http://old-url.git\n"), # git remote get-url origin
        MagicMock(returncode=0)                    # git remote set-url origin ...
    ]
    
    msg = repo_create("test", set_origin=True)
    assert "Updated existing git remote 'origin' to the new repository clone URL." in msg
    assert mock_run.call_count == 3
    # Check that remote set-url origin was called
    mock_run.assert_any_call(["git", "remote", "set-url", "origin", "http://localhost:3000/admin/test.git"], cwd=str(Path.cwd().resolve()), check=True)
    assert mock_add_collaborator.call_count == 2
