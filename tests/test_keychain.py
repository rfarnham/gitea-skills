import os
import sys
import platform
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from gitea_skills.github_auth import get_service_name, check_keychain, save_keychain, get_github_token
from gitea_skills.github_credential_helper import get_token
from gitea_skills import github_api

def test_get_service_name_custom():
    # Test service name when REPO_NAME is present
    mock_env = {"REPO_NAME": "my-special-repo"}
    with patch("gitea_skills.github_auth._load_env", return_value=mock_env):
        assert get_service_name() == "gitea-skills-github-my-special-repo"

def test_get_service_name_fallback():
    # Test service name fallback when REPO_NAME is missing
    with patch("gitea_skills.github_auth._load_env", return_value={}):
        assert get_service_name() == "friendly-davinci-github"
        
    # Test service name fallback when exception occurs
    with patch("gitea_skills.github_auth._load_env", side_effect=Exception("load failed")):
        assert get_service_name() == "friendly-davinci-github"

@patch("platform.system", return_value="Darwin")
@patch("subprocess.run")
def test_check_keychain_scoped_success(mock_run, mock_system):
    # If project-scoped keychain query succeeds, return it immediately
    mock_run.return_value = MagicMock(stdout="scoped-token\n")
    mock_env = {"REPO_NAME": "scoped-repo"}
    
    with patch("gitea_skills.github_auth._load_env", return_value=mock_env):
        token = check_keychain()
        assert token == "scoped-token"
        
        # Verify it only searched for the scoped service
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "gitea-skills-github-scoped-repo" in args

@patch("platform.system", return_value="Darwin")
@patch("subprocess.run")
def test_check_keychain_fallback_success(mock_run, mock_system):
    import subprocess
    # If project-scoped fails but legacy succeeds
    def side_effect(cmd, *args, **kwargs):
        if "gitea-skills-github-scoped-repo" in cmd:
            raise subprocess.CalledProcessError(1, cmd)
        return MagicMock(stdout="legacy-token\n")
        
    mock_run.side_effect = side_effect
    mock_env = {"REPO_NAME": "scoped-repo"}
    
    with patch("gitea_skills.github_auth._load_env", return_value=mock_env):
        token = check_keychain()
        assert token == "legacy-token"
        assert mock_run.call_count == 2
        
        # Verify first call is scoped, second call is legacy
        first_call_args = mock_run.call_args_list[0][0][0]
        assert "gitea-skills-github-scoped-repo" in first_call_args
        
        second_call_args = mock_run.call_args_list[1][0][0]
        assert "friendly-davinci-github" in second_call_args

@patch("platform.system", return_value="Darwin")
@patch("subprocess.run")
def test_save_keychain_scoped(mock_run, mock_system):
    mock_run.return_value = MagicMock()
    mock_env = {"REPO_NAME": "scoped-repo"}
    
    with patch("gitea_skills.github_auth._load_env", return_value=mock_env):
        success = save_keychain("new-token")
        assert success is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "gitea-skills-github-scoped-repo" in args
        assert "new-token" in args

def test_credential_helper_gets_token():
    with patch("gitea_skills.github_credential_helper.get_github_token", return_value="helper-token") as mock_check:
        assert get_token() == "helper-token"
        mock_check.assert_called_once()

@patch("urllib.request.urlopen")
def test_get_github_token_env_var(mock_urlopen):
    # Mock successful response
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b'{"login": "testuser"}'
    
    # Priority 1: GITHUB_TOKEN env var
    with patch.dict(os.environ, {"GITHUB_TOKEN": "env-token", "GITHUB_PAT": "ignored-pat"}):
        assert get_github_token(verbose=False) == "env-token"
        
    with patch.dict(os.environ, {"GITHUB_PAT": "pat-token"}):
        if "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]
        assert get_github_token(verbose=False) == "pat-token"

@patch("urllib.request.urlopen")
def test_get_github_token_config_file(mock_urlopen):
    # Mock successful response
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b'{"login": "testuser"}'
    
    # Priority 2: local/global config
    mock_env = {"GITHUB_TOKEN": "config-token"}
    with patch.dict(os.environ, {}), patch("gitea_skills.github_auth._load_env", return_value=mock_env):
        if "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]
        if "GITHUB_PAT" in os.environ:
            del os.environ["GITHUB_PAT"]
        assert get_github_token(verbose=False) == "config-token"

@patch("urllib.request.urlopen")
@patch("gitea_skills.github_auth.check_keychain", return_value="keychain-token")
def test_get_github_token_keychain_fallback(mock_check_keychain, mock_urlopen):
    # Mock successful response
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b'{"login": "testuser"}'
    
    # Priority 3: macOS Keychain fallback
    with patch.dict(os.environ, {}), patch("gitea_skills.github_auth._load_env", return_value={}):
        if "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]
        if "GITHUB_PAT" in os.environ:
            del os.environ["GITHUB_PAT"]
        assert get_github_token(verbose=False) == "keychain-token"
        mock_check_keychain.assert_called_once()

@patch("urllib.request.urlopen")
@patch("gitea_skills.github_auth.check_keychain", return_value="keychain-token")
def test_get_github_token_validation_fallback(mock_check_keychain, mock_urlopen):
    import urllib.error
    # Mock urlopen: first call (env var) raises 401 HTTPError, second call (keychain) succeeds
    fp = MagicMock()
    fp.read.return_value = b'{"message": "Unauthorized"}'
    error = urllib.error.HTTPError("url", 401, "Unauthorized", {}, fp)
    
    success_resp = MagicMock()
    success_resp.read.return_value = b'{"login": "testuser"}'
    
    mock_urlopen.side_effect = [error, success_resp.__enter__.return_value]
    
    # Set env var
    with patch.dict(os.environ, {"GITHUB_TOKEN": "invalid-env-token"}):
        if "GITHUB_PAT" in os.environ:
            del os.environ["GITHUB_PAT"]
        token = get_github_token(verbose=True)
        # Should fall back to Keychain
        assert token == "keychain-token"
        assert mock_urlopen.call_count == 2

@patch("urllib.request.urlopen")
@patch("gitea_skills.github_api.check_existing_pull_request", return_value=None)
def test_github_api_403_troubleshooting(mock_check_pr, mock_urlopen, capsys):
    import urllib.error
    # Mock HTTP 403 Forbidden with permission issue string in response body
    response_body = b'{"message": "Resource not accessible by personal access token"}'
    
    # Create mock HTTPError
    fp = MagicMock()
    fp.read.return_value = response_body
    error = urllib.error.HTTPError("url", 403, "Forbidden", {}, fp)
    mock_urlopen.side_effect = error
    
    success = github_api.create_pull_request(
        owner="owner",
        repo="repo",
        token="token",
        head="head",
        base="base",
        title="title",
        body="body"
    )
    assert success is False
    captured = capsys.readouterr()
    assert "ERROR: GitHub API Access Forbidden (403)" in captured.err
    assert "Repository permissions -> 'Pull requests': Read and write" in captured.err
