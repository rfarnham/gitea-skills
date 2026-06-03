#!/usr/bin/env python3
"""Lightweight GitHub REST API client using only Python stdlib to create Pull Requests.

Retrieves credentials securely from the macOS Keychain.
"""

import sys
import os
import re
import json
import urllib.request
import urllib.error
from pathlib import Path

from gitea_skills import github_auth
from gitea_skills import gitea_api
from gitea_skills.core import _load_env, _get_project_dir

def parse_github_url(url: str):
    """Extract owner and repo name from GitHub URL (SSH or HTTPS)."""
    match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?$", url)
    if match:
        owner = match.group(1)
        repo = match.group(2)
        return owner, repo
    return None, None

def get_git_remote_url():
    """Retrieve the GitHub remote URL using git CLI."""
    import subprocess
    try:
        res = subprocess.run(
            ["git", "remote", "get-url", "github"],
            capture_output=True, text=True, check=True
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def create_pull_request(owner: str, repo: str, token: str, head: str, base: str, title: str, body: str):
    """Call GitHub REST API to create a pull request."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json"
    }
    payload = {
        "title": title,
        "body": body,
        "head": head,
        "base": base
    }
    
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as resp:
            res_data = json.loads(resp.read().decode())
            print(f"Pull request created successfully on GitHub!")
            print(f"PR URL: {res_data.get('html_url')}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            err_json = json.loads(error_body)
            # Check if it's a duplicate PR error
            if "errors" in err_json:
                for err in err_json["errors"]:
                    msg = err.get("message", "")
                    if "A pull request already exists" in msg:
                        print("A pull request already exists on GitHub for this branch.")
                        return True
                    if "No commits between" in msg:
                        print("No commits between the base and head branches. GitHub remote is already up to date.")
                        return True
            print(f"GitHub API Error: {err_json.get('message', error_body)}", file=sys.stderr)
            if "errors" in err_json:
                print(f"Details: {json.dumps(err_json['errors'], indent=2)}", file=sys.stderr)
        except Exception:
            print(f"GitHub API Error {e.code}: {error_body}", file=sys.stderr)
        return False

def get_merged_pr_metadata(base_branch="main"):
    """Gathers merged Gitea PR details, comments, and reviews since the last sync."""
    try:
        env = _load_env()
    except Exception as e:
        print(f"Warning: Could not load Gitea environment settings: {e}", file=sys.stderr)
        return ""

    gitea_url = env.get("GITEA_URL", "http://localhost:3000")
    token = env.get("ADMIN_TOKEN") or env.get("DEVELOPER_AGENT_TOKEN") or env.get("REVIEWER_AGENT_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME")
    
    if not repo:
        print("Warning: Gitea REPO_NAME not configured, skipping Gitea metadata capture.", file=sys.stderr)
        return ""

    gitea_api.GITEA_URL = gitea_url
    project_dir = _get_project_dir()

    # 1. Fetch github remote to ensure we have current remote tracking branches
    import subprocess
    print("Fetching from 'github' remote...")
    subprocess.run(["git", "fetch", "github"], cwd=str(project_dir), capture_output=True)

    # 2. Find commit differences between github/{base_branch} and HEAD
    commit_shas = []
    commit_messages = []
    try:
        # Get commit SHAs and messages
        res = subprocess.run(
            ["git", "log", f"github/{base_branch}..HEAD", "--format=%H %s"],
            cwd=str(project_dir), capture_output=True, text=True, check=True
        )
        for line in res.stdout.strip().splitlines():
            if line:
                sha, msg = line.split(" ", 1)
                commit_shas.append(sha)
                commit_messages.append(msg)
    except subprocess.CalledProcessError:
        # Fallback: if github tracking branch is not found, check the last 20 commits
        try:
            res = subprocess.run(
                ["git", "log", "-n", "20", "--format=%H %s"],
                cwd=str(project_dir), capture_output=True, text=True, check=True
            )
            for line in res.stdout.strip().splitlines():
                if line:
                    sha, msg = line.split(" ", 1)
                    commit_shas.append(sha)
                    commit_messages.append(msg)
        except subprocess.CalledProcessError:
            pass

    # 3. Extract Gitea PR numbers from commit messages
    pr_indices = set()
    for msg in commit_messages:
        # Search for (#<number>) or similar
        match = re.search(r"#(\d+)", msg)
        if match:
            pr_indices.add(int(match.group(1)))

    # 4. Fetch Gitea closed pull requests and cross-reference
    matching_prs = []
    try:
        closed_prs = gitea_api.list_pull_requests(token, owner, repo, state="closed") or []
        for pr in closed_prs:
            if not pr.get("merged"):
                continue
            pr_idx = pr.get("number")
            sha = pr.get("merge_commit_sha") or pr.get("merged_commit_id")
            
            # Match if the PR index is in our parsed list OR its merge SHA matches one of our local commit SHAs
            if pr_idx in pr_indices or (sha and sha in commit_shas):
                matching_prs.append(pr)
    except Exception as e:
        print(f"Warning: Could not retrieve PR list from Gitea: {e}", file=sys.stderr)

    # 5. Fallback: If no matching PRs were found, fetch the single most recently merged PR
    if not matching_prs:
        try:
            closed_prs = gitea_api.list_pull_requests(token, owner, repo, state="closed") or []
            merged_prs = [pr for pr in closed_prs if pr.get("merged")]
            if merged_prs:
                # Sort by merged_at descending if available, or number descending
                merged_prs.sort(key=lambda p: p.get("merged_at") or "", reverse=True)
                matching_prs.append(merged_prs[0])
        except Exception as e:
            print(f"Warning: Could not retrieve recently merged PR from Gitea: {e}", file=sys.stderr)

    # If still no PRs found, return empty
    if not matching_prs:
        return ""

    # Sort matching PRs by index ascending
    matching_prs.sort(key=lambda p: p.get("number", 0))

    # 6. Gather details, comments, and reviews for each PR and build markdown
    markdown_sections = []
    for pr in matching_prs:
        idx = pr.get("number")
        title = pr.get("title", "Untitled PR")
        body = pr.get("body") or "No description provided."
        url = pr.get("html_url", "")
        author = pr.get("user", {}).get("username") or pr.get("user", {}).get("login") or "unknown"
        merged_at = pr.get("merged_at", "")

        section = []
        section.append(f"## Gitea PR [#{idx}]({url}): {title}")
        section.append(f"- **Author:** @{author}")
        if merged_at:
            section.append(f"- **Merged At:** {merged_at}")
        section.append("\n### Description\n" + body)

        # Gather general comments
        try:
            comments = gitea_api.get_pr_comments(token, owner, repo, idx) or []
            # Gitea issues comments may include system actions or empty ones, filter them
            user_comments = [c for c in comments if c.get("body") and not c.get("body").startswith("merged commit")]
            if user_comments:
                section.append("\n### Discussion & Comments")
                for c in user_comments:
                    c_author = c.get("user", {}).get("username") or c.get("user", {}).get("login") or "unknown"
                    c_time = c.get("created_at", "")
                    c_body = c.get("body", "").strip()
                    # Indent body to format nicely as a blockquote
                    blockquote_body = "\n".join(f"> {line}" for line in c_body.splitlines())
                    section.append(f"- **@{c_author}** ({c_time}):\n{blockquote_body}")
        except Exception as e:
            print(f"Warning: Could not retrieve comments for Gitea PR #{idx}: {e}", file=sys.stderr)

        # Gather reviews and review comments
        try:
            reviews = gitea_api.get_pr_reviews(token, owner, repo, idx) or []
            if reviews:
                section.append("\n### Review Activity")
                for r in reviews:
                    r_author = r.get("user", {}).get("username") or r.get("user", {}).get("login") or "unknown"
                    r_state = r.get("state", "COMMENT")
                    r_body = r.get("body", "").strip()
                    r_time = r.get("submitted_at", "")
                    
                    review_msg = f"- **@{r_author}** ({r_state} review at {r_time})"
                    if r_body:
                        blockquote_body = "\n".join(f"> {line}" for line in r_body.splitlines())
                        review_msg += f":\n{blockquote_body}"
                    section.append(review_msg)
                    
                    # Fetch inline comments for this specific review
                    r_id = r.get("id")
                    if r_id:
                        try:
                            r_comments = gitea_api.get_review_comments(token, owner, repo, idx, r_id) or []
                            for rc in r_comments:
                                rc_body = rc.get("body", "").strip()
                                rc_path = rc.get("path", "")
                                rc_pos = rc.get("position") or rc.get("new_position") or "?"
                                if rc_body:
                                    rc_blockquote = "\n".join(f"  > {line}" for line in rc_body.splitlines())
                                    section.append(f"  - *In `{rc_path}` line {rc_pos}*:\n{rc_blockquote}")
                        except Exception as e:
                            print(f"Warning: Could not retrieve comments for review {r_id}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not retrieve reviews for Gitea PR #{idx}: {e}", file=sys.stderr)

        markdown_sections.append("\n".join(section))

    full_markdown = "\n\n---\n\n".join(markdown_sections)
    return full_markdown

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Create a Pull Request on GitHub")
    parser.add_argument("--head", required=True, help="The name of the branch where your changes are implemented")
    parser.add_argument("--base", default="main", help="The name of the branch you want the changes pulled into")
    parser.add_argument("--title", help="The title of the pull request")
    parser.add_argument("--body", help="The description of the pull request")
    args = parser.parse_args()

    remote_url = get_git_remote_url()
    if not remote_url:
        print("Error: Could not retrieve 'github' remote URL from git.", file=sys.stderr)
        sys.exit(1)

    owner, repo = parse_github_url(remote_url)
    if not owner or not repo:
        print(f"Error: Could not parse owner/repo from remote URL: {remote_url}", file=sys.stderr)
        sys.exit(1)

    # Securely retrieve the token from macOS Keychain
    token = github_auth.check_keychain()
    if not token:
        print("Error: No GitHub token found in macOS Keychain. Please run ./scripts/github_auth.py first.", file=sys.stderr)
        sys.exit(1)

    title = args.title or f"sync: merge {args.head} into {args.base}"
    
    # Try to fetch Gitea PR metadata if no custom body is provided
    gitea_metadata = ""
    if not args.body:
        print("Fetching merged PR metadata from Gitea...")
        gitea_metadata = get_merged_pr_metadata(args.base)
        
    if gitea_metadata:
        body = f"Automated Pull Request syncing changes from local Gitea.\n\n# Sync Gitea Metadata\n\n{gitea_metadata}"
    else:
        body = args.body or "Automated pull request to sync Gitea changes to GitHub."

    success = create_pull_request(
        owner=owner,
        repo=repo,
        token=token,
        head=args.head,
        base=args.base,
        title=title,
        body=body
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
