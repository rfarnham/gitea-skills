import os
import sys
import subprocess
from pathlib import Path

from gitea_skills import gitea_api

def _get_project_dir() -> Path:
    """Get the root project directory.
    Priority: GITEA_SKILLS_PROJECT_DIR env var > nearest parent with .agentic_dev > cwd.
    """
    env_dir = os.environ.get("GITEA_SKILLS_PROJECT_DIR")
    if env_dir:
        return Path(env_dir).resolve()
        
    # Traverse upwards looking for .agentic_dev
    current = Path.cwd().resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".agentic_dev" / "tokens.env").exists():
            return parent
            
    # Fallback to cwd if not found (e.g. for install/init commands)
    return current

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


def pr_get_comments(pr_index: int, as_json: bool = False) -> str:
    """Retrieves general comments on a pull request.

    Args:
        pr_index: The index number of the pull request on Gitea.
        as_json: Output raw JSON if True.
    """
    env = _load_env()
    token = env.get("REVIEWER_AGENT_TOKEN", "") or env.get("DEVELOPER_AGENT_TOKEN", "") or env.get("ADMIN_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME", "friendly-davinci")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")
    
    comments = gitea_api.get_pr_comments(token, owner, repo, pr_index)
    if as_json:
        import json
        return json.dumps(comments, indent=2)
        
    if not comments:
        return "No comments found."
        
    def format_timestamp(ts_str):
        if not ts_str:
            return ""
        ts_str = ts_str.replace("T", " ")
        for char in [".", "Z", "+"]:
            ts_str = ts_str.split(char)[0]
        return ts_str.strip()

    lines = []
    for c in comments:
        username = c.get("user", {}).get("username") or c.get("user", {}).get("login") or "unknown"
        created_at = format_timestamp(c.get("created_at", ""))
        body = c.get("body", "")
        lines.append(f"[{username}] {created_at}:")
        lines.append(body)
        lines.append("-" * 50)
    return "\n".join(lines)


def pr_get_reviews(pr_index: int, as_json: bool = False) -> str:
    """Retrieves reviews and inline comments on a pull request.

    Args:
        pr_index: The index number of the pull request on Gitea.
        as_json: Output raw JSON if True.
    """
    env = _load_env()
    token = env.get("REVIEWER_AGENT_TOKEN", "") or env.get("DEVELOPER_AGENT_TOKEN", "") or env.get("ADMIN_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME", "friendly-davinci")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")
    
    reviews = gitea_api.get_pr_reviews(token, owner, repo, pr_index)
    if as_json:
        extended_reviews = []
        for r in reviews:
            r_copy = dict(r)
            r_id = r.get("id")
            if r_id:
                try:
                    r_comments = gitea_api.get_review_comments(token, owner, repo, pr_index, r_id) or []
                    r_copy["comments"] = r_comments
                except Exception:
                    r_copy["comments"] = []
            else:
                r_copy["comments"] = []
            extended_reviews.append(r_copy)
        import json
        return json.dumps(extended_reviews, indent=2)

    if not reviews:
        return "No reviews found."

    from collections import defaultdict
    lines = []
    for r in reviews:
        review_id = r.get("id")
        author = r.get("user", {}).get("username") or r.get("user", {}).get("login") or "unknown"
        state = r.get("state", "COMMENT")
        body = r.get("body", "")
        
        lines.append("=" * 80)
        lines.append(f"Review ID {review_id} by [{author}] ({state})")
        lines.append("=" * 80)
        
        if body.strip():
            lines.append(body.strip())
            lines.append("")
            
        if review_id:
            try:
                inline_comments = gitea_api.get_review_comments(token, owner, repo, pr_index, review_id) or []
            except Exception:
                inline_comments = []
            
            if inline_comments:
                comments_by_location = defaultdict(list)
                for comment in inline_comments:
                    path = comment.get("path", "")
                    position = comment.get("position") or 0
                    comments_by_location[(path, position)].append(comment)
                
                sorted_locations = sorted(comments_by_location.keys(), key=lambda x: (x[0], x[1] or 0))
                
                for path, position in sorted_locations:
                    loc_comments = comments_by_location[(path, position)]
                    first_comment = loc_comments[0]
                    original_position = first_comment.get("original_position")
                    diff_hunk = first_comment.get("diff_hunk", "")
                    
                    lines.append(f"File: {path}")
                    line_str = f"Line: {position}" if position else "Line: ?"
                    if original_position:
                        line_str += f" (Original Line: {original_position})"
                    lines.append(line_str)
                    
                    if diff_hunk.strip():
                        lines.append("Diff:")
                        lines.append(diff_hunk.strip())
                        
                    for comment in loc_comments:
                        c_body = comment.get("body", "")
                        lines.append(f"Comment: {c_body}")
                    lines.append("-" * 80)
    return "\n".join(lines)


def repo_create(name: str, description: str = "", private: bool = False, auto_init: bool = False, owner: str = None, set_origin: bool = False) -> str:
    """Creates a new Gitea repository.

    Args:
        name: The name of the Gitea repository to create.
        description: A brief description of the repository.
        private: If True, creates a private repository. (Default: False)
        auto_init: Initialize the repository with an initial commit containing a default README.md and .gitignore.
        owner: Creates the repository under a specific organization or user name instead of the default authenticated user.
        set_origin: If run inside a local Git directory, automatically run `git remote add origin` (or `set-url` if it exists) using the newly created repository clone URL.
    """
    env = _load_env()
    token = env.get("ADMIN_TOKEN") or env.get("DEVELOPER_AGENT_TOKEN") or env.get("REVIEWER_AGENT_TOKEN", "")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")
    
    res = gitea_api.create_repo(
        token=token,
        name=name,
        description=description,
        auto_init=auto_init,
        private=private,
        owner=owner
    )
    
    clone_url = res.get("clone_url")
    msg = f"Repository '{name}' created successfully! Clone URL: {clone_url}"
    
    # Automatically add developer-agent and reviewer-agent as collaborators if ADMIN_TOKEN is available
    admin_token = env.get("ADMIN_TOKEN")
    if admin_token:
        repo_owner = res.get("owner", {}).get("username") or owner or env.get("REPO_OWNER") or "admin"
        try:
            gitea_api.add_collaborator(admin_token, repo_owner, name, "developer-agent", "write")
            gitea_api.add_collaborator(admin_token, repo_owner, name, "reviewer-agent", "write")
            msg += "\nAdded 'developer-agent' and 'reviewer-agent' as collaborators with write permission."
        except Exception as e:
            msg += f"\nWarning: Could not configure agent collaborators: {e}"
    
    if set_origin:
        # Check if inside git repository
        current_dir = Path.cwd().resolve()
        git_check = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=str(current_dir), capture_output=True, text=True)
        if git_check.returncode == 0 and git_check.stdout.strip() == "true":
            # Check if origin remote already exists
            origin_check = subprocess.run(["git", "remote", "get-url", "origin"], cwd=str(current_dir), capture_output=True, text=True)
            if origin_check.returncode == 0:
                subprocess.run(["git", "remote", "set-url", "origin", clone_url], cwd=str(current_dir), check=True)
                msg += "\nUpdated existing git remote 'origin' to the new repository clone URL."
            else:
                subprocess.run(["git", "remote", "add", "origin", clone_url], cwd=str(current_dir), check=True)
                msg += "\nAdded new git remote 'origin' pointing to the repository clone URL."
        else:
            msg += "\nWarning: --set-origin was specified but not running inside a git repository."
            
    return msg


def issue_create(title: str, body: str, labels: list = None) -> str:
    """Creates a new issue on Gitea.

    Args:
        title: The title of the issue.
        body: The detailed description of the issue.
        labels: Optional list of labels to assign.
    """
    env = _load_env()
    token = env.get("DEVELOPER_AGENT_TOKEN") or env.get("ADMIN_TOKEN") or env.get("REVIEWER_AGENT_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME", "friendly-davinci")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")

    # Map label names (strings) to Gitea Label IDs (int64)
    label_ids = []
    if labels:
        try:
            existing_labels = gitea_api.list_repo_labels(token, owner, repo) or []
            label_map = {l["name"].lower(): l["id"] for l in existing_labels}
            for name in labels:
                name_lower = name.lower()
                if name_lower in label_map:
                    label_ids.append(label_map[name_lower])
                else:
                    # Try to create label if it doesn't exist
                    try:
                        new_label = gitea_api.create_repo_label(token, owner, repo, name)
                        if new_label and "id" in new_label:
                            label_ids.append(new_label["id"])
                    except Exception:
                        pass
        except Exception:
            pass

    res = gitea_api.create_issue(token, owner, repo, title, body, label_ids)
    return f"Issue created successfully! Issue Index: {res.get('number')}"


def issue_list(state: str = "open") -> str:
    """Lists issues in the Gitea repository.

    Args:
        state: The state of the issues (open, closed, all).
    """
    env = _load_env()
    token = env.get("DEVELOPER_AGENT_TOKEN") or env.get("ADMIN_TOKEN") or env.get("REVIEWER_AGENT_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME", "friendly-davinci")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")

    issues = gitea_api.list_issues(token, owner, repo, state=state, type="issues")
    if not issues:
        return f"No {state} issues found."

    lines = []
    for issue in issues:
        idx = issue.get("number")
        title = issue.get("title")
        labels = ", ".join(l.get("name") for l in issue.get("labels", []))
        labels_str = f" [{labels}]" if labels else ""
        lines.append(f"#{idx}: {title}{labels_str}")
    return "\n".join(lines)


def issue_details(index: int) -> str:
    """Retrieves the details of a specific Gitea issue.

    Args:
        index: The index number of the issue.
    """
    env = _load_env()
    token = env.get("DEVELOPER_AGENT_TOKEN") or env.get("ADMIN_TOKEN") or env.get("REVIEWER_AGENT_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME", "friendly-davinci")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")

    issue = gitea_api.get_issue(token, owner, repo, index)
    title = issue.get("title")
    state = issue.get("state")
    body = issue.get("body") or "No description provided."
    labels = ", ".join(l.get("name") for l in issue.get("labels", []))
    labels_str = f" [{labels}]" if labels else ""

    lines = [
        f"Issue #{index}: {title}{labels_str}",
        f"State: {state}",
        f"Description:",
        body
    ]
    return "\n".join(lines)


def issue_close(index: int) -> str:
    """Closes a Gitea issue.

    Args:
        index: The index number of the issue to close.
    """
    env = _load_env()
    token = env.get("DEVELOPER_AGENT_TOKEN") or env.get("ADMIN_TOKEN") or env.get("REVIEWER_AGENT_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME", "friendly-davinci")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")

    gitea_api.update_issue(token, owner, repo, index, state="closed")
    return f"Issue #{index} closed successfully."


def issue_dedup() -> str:
    """Analyze open Gitea issues and suggest duplicates."""
    from gitea_skills.dedup_issues import run_dedup
    return run_dedup()


