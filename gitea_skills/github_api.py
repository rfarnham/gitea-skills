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
