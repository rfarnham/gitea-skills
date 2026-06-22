"""Gitea Skills — Tools for the local agentic development loop."""
from pathlib import Path

__version__ = "1.0.0"

def get_skills_path() -> Path:
    """Return the path to the skills/ directory for LocalAgentConfig.skills_paths."""
    return Path(__file__).parent / "skills"

def get_plugin_path() -> Path:
    """Return the path to this package directory (for plugin symlinking)."""
    return Path(__file__).parent

# Re-export tool functions for SDK Agent usage
from gitea_skills.core import (
    worktree_create,
    worktree_remove,
    pr_create,
    pr_get_diff,
    pr_get_details,
    pr_get_comments,
    pr_get_reviews,
    ci_get_status,
    submit_review,
    merge_pr,
    repo_create,
)
