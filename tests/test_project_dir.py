import os
import pytest
from pathlib import Path
from unittest.mock import patch
from gitea_skills.core import _get_project_dir

def test_get_project_dir_env_var(tmp_path):
    # If env var is set, it should take precedence
    env_dir = tmp_path / "env_project"
    env_dir.mkdir()
    
    with patch.dict(os.environ, {"GITEA_SKILLS_PROJECT_DIR": str(env_dir)}):
        resolved = _get_project_dir()
        assert resolved == env_dir

def test_get_project_dir_traverse_up(tmp_path):
    # Create mock project structure
    project_root = tmp_path / "my_project"
    agentic_dir = project_root / ".agentic_dev"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "tokens.env").write_text("GITEA_URL=http://localhost:3000")
    
    nested_dir = project_root / ".agentic_dev" / "worktrees" / "agent__feature"
    nested_dir.mkdir(parents=True)
    
    # Mock cwd to the nested directory and ensure env var is not set
    with patch.dict(os.environ, {}), patch("pathlib.Path.cwd", return_value=nested_dir):
        # Clear env var if present in environment
        if "GITEA_SKILLS_PROJECT_DIR" in os.environ:
            del os.environ["GITEA_SKILLS_PROJECT_DIR"]
            
        resolved = _get_project_dir()
        assert resolved == project_root

def test_get_project_dir_fallback(tmp_path):
    # When no .agentic_dev/tokens.env exists anywhere, fallback to cwd
    random_dir = tmp_path / "random"
    random_dir.mkdir()
    
    with patch.dict(os.environ, {}), patch("pathlib.Path.cwd", return_value=random_dir):
        if "GITEA_SKILLS_PROJECT_DIR" in os.environ:
            del os.environ["GITEA_SKILLS_PROJECT_DIR"]
            
        resolved = _get_project_dir()
        assert resolved == random_dir
