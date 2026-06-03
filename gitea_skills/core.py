import os
import sys
import subprocess
from pathlib import Path

from gitea_skills import gitea_api

def _get_project_dir() -> Path:
    """Resolve the active project directory.
    
    Priority: GITEA_SKILLS_PROJECT_DIR env var > cwd.
    """
    env_dir = os.environ.get("GITEA_SKILLS_PROJECT_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    return Path.cwd().resolve()

def _get_agentic_dir() -> Path:
    return _get_project_dir() / ".agentic_dev"

def _load_env():
    env = {}
    
    def parse_file(file_path):
        if file_path.exists():
            for line in file_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()

    # Read global tokens first
    global_path = Path.home() / ".gitea_skills.env"
    parse_file(global_path)

    # Allow local project overrides
    local_path = _get_agentic_dir() / "tokens.env"
    parse_file(local_path)
    
    return env

# Expose tools as Python functions with clear docstrings:

def worktree_create(branch: str) -> str:
    """Creates a new git worktree for a specific branch.

    Args:
        branch: The git branch name to check out (e.g. "agent/add-feature").
    """
    env = _load_env()
    dev_token = env.get("DEVELOPER_AGENT_TOKEN", "")
    repo_owner = env.get("REPO_OWNER", "admin")
    repo_name = env.get("REPO_NAME", "friendly-davinci")

    dest = _get_agentic_dir() / "worktrees" / branch.replace("/", "__")
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if branch exists on origin
    res = subprocess.run(["git", "ls-remote", "--heads", "origin", branch], cwd=str(_get_project_dir()), capture_output=True, text=True)
    if branch in res.stdout:
        # Fetch and checkout existing remote branch
        subprocess.run(["git", "fetch", "origin"], cwd=str(_get_project_dir()), check=True)
        subprocess.run(["git", "worktree", "add", str(dest), branch], cwd=str(_get_project_dir()), check=True)
    else:
        # Create a new branch
        subprocess.run(["git", "worktree", "add", str(dest), "-b", branch], cwd=str(_get_project_dir()), check=True)
        
    # Configure agent credentials in the worktree
    remote_url = f"http://developer-agent:{dev_token}@localhost:3000/{repo_owner}/{repo_name}.git"
    subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=str(dest), check=True)
    
    return f"Created worktree for branch '{branch}' at: {dest}"

def worktree_remove(branch: str) -> str:
    """Safely removes the git worktree for a specific branch.

    Args:
        branch: The git branch name of the worktree to remove (e.g. "agent/add-feature").
    """
    dest = _get_agentic_dir() / "worktrees" / branch.replace("/", "__")
    if dest.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(dest)], cwd=str(_get_project_dir()), check=True)
        return f"Successfully removed worktree for branch '{branch}'."
    return f"No worktree found for branch '{branch}'."

def pr_create(branch: str, title: str, body: str) -> str:
    """Opens a pull request on Gitea from the specified branch to 'main'.

    Args:
        branch: The head branch name containing the changes.
        title: The title of the pull request (follow conventional commits).
        body: The description of the changes.
    """
    env = _load_env()
    token = env.get("DEVELOPER_AGENT_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME", "friendly-davinci")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")
    
    # First ensure everything is pushed
    dest = _get_agentic_dir() / "worktrees" / branch.replace("/", "__")
    if dest.exists():
        subprocess.run(["git", "push", "origin", branch], cwd=str(dest), check=True)
    else:
        subprocess.run(["git", "push", "origin", branch], cwd=str(_get_project_dir()), check=True)
        
    res = gitea_api.create_pull_request(
        token=token,
        owner=owner,
        repo=repo,
        title=title,
        body=body,
        head=branch,
        base="main"
    )
    return f"Pull request created successfully! PR Index: {res.get('number')}"

def pr_get_diff(pr_index: int) -> str:
    """Retrieves the unified diff of a pull request.

    Args:
        pr_index: The index number of the pull request on Gitea.
    """
    env = _load_env()
    token = env.get("REVIEWER_AGENT_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME", "friendly-davinci")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")
    
    return gitea_api.get_pr_diff(token, owner, repo, pr_index)

def pr_get_details(pr_index: int) -> str:
    """Retrieves the metadata details of a pull request.

    Args:
        pr_index: The index number of the pull request on Gitea.
    """
    env = _load_env()
    token = env.get("REVIEWER_AGENT_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME", "friendly-davinci")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")
    
    res = gitea_api.get_pull_request(token, owner, repo, pr_index)
    import json
    return json.dumps(res, indent=2)

def ci_get_status(ref: str) -> str:
    """Checks the CI status for a commit hash or branch name.

    Args:
        ref: The commit SHA or branch name (e.g. "agent/add-feature" or "1fff5f98").
    """
    env = _load_env()
    token = env.get("REVIEWER_AGENT_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME", "friendly-davinci")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")
    
    res = gitea_api._request(
        'GET',
        f'/repos/{owner}/{repo}/commits/{ref}/statuses',
        token=token
    )
    import json
    return json.dumps(res, indent=2)

def submit_review(pr_index: int, verdict: str, body: str, comments: list[dict] = None) -> str:
    """Submits a pull request review with a verdict and comments.

    Args:
        pr_index: The index number of the pull request on Gitea.
        verdict: The review verdict (APPROVED, REQUEST_CHANGES, or COMMENT).
        body: The summary review message.
        comments: Optional list of dictionaries for inline comments, e.g.:
                  [{"path": "src/calculator.py", "body": "Fix this logic", "new_position": 3}]
    """
    env = _load_env()
    token = env.get("REVIEWER_AGENT_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME", "friendly-davinci")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")
    
    gitea_api.submit_review(
        token=token,
        owner=owner,
        repo=repo,
        index=pr_index,
        body=body,
        event=verdict,
        comments=comments
    )
    return f"Successfully submitted review '{verdict}' on PR #{pr_index}."

def merge_pr(pr_index: int, style: str = "merge") -> str:
    """Merges a Gitea pull request (admin token required).

    Args:
        pr_index: The index number of the pull request on Gitea.
        style: The merge style (merge, rebase, rebase-merge, or squash).
    """
    env = _load_env()
    token = env.get("ADMIN_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME", "friendly-davinci")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")
    
    payload = {
        "Do": style,
        "delete_branch_after_merge": True
    }
    gitea_api._request(
        'POST',
        f'/repos/{owner}/{repo}/pulls/{pr_index}/merge',
        token=token,
        data=payload
    )
    return f"Successfully merged PR #{pr_index} using style '{style}'."
