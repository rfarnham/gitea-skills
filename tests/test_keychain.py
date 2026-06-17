import os
import sys
import platform
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from gitea_skills.github_auth import get_service_name, check_keychain, save_keychain
from gitea_skills.github_credential_helper import get_token

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
    with patch("gitea_skills.github_credential_helper.check_keychain", return_value="helper-token") as mock_check:
        assert get_token() == "helper-token"
        mock_check.assert_called_once()
