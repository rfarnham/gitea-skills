#!/usr/bin/env python3
"""Lightweight Gitea REST API client using only Python stdlib.

All functions read GITEA_URL from the environment (default: http://localhost:3000).
Tokens are passed explicitly so callers control which identity is used.
"""

import base64
import json
import os
import urllib.error
import urllib.request

GITEA_URL = os.environ.get("GITEA_URL", "http://localhost:3000")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _request(method, path, token=None, data=None, basic_auth=None, accept=None):
    """Make an HTTP request to the Gitea API and return the parsed response."""
    url = f"{GITEA_URL}/api/v1{path}"
    headers = {"Content-Type": "application/json"}
    if accept:
        headers["Accept"] = accept
    if token:
        headers["Authorization"] = f"token {token}"
    elif basic_auth:
        creds = base64.b64encode(
            f"{basic_auth[0]}:{basic_auth[1]}".encode()
        ).decode()
        headers["Authorization"] = f"Basic {creds}"

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            if not raw:
                return None
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return json.loads(raw)
            return raw
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(
            f"Gitea API error {e.code} on {method} {path}: {error_body}"
        ) from e


# ---------------------------------------------------------------------------
# Users & tokens
# ---------------------------------------------------------------------------

def create_token(username, password, token_name):
    """Create an API access token for *username* using basic-auth credentials.

    Returns the full token response dict (the token value is in the 'sha1' key).
    """
    return _request(
        "POST",
        f"/users/{username}/tokens",
        basic_auth=(username, password),
        data={"name": token_name},
    )


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

def create_repo(token, name, description="", auto_init=False):
    """Create a repository owned by the authenticated user."""
    return _request("POST", "/user/repos", token, {
        "name": name,
        "description": description,
        "auto_init": auto_init,
        "default_branch": "main",
    })


def add_collaborator(token, owner, repo, username, permission="write"):
    """Add a collaborator to a repository."""
    return _request(
        "PUT",
        f"/repos/{owner}/{repo}/collaborators/{username}",
        token,
        {"permission": permission},
    )


# ---------------------------------------------------------------------------
# Pull requests
# ---------------------------------------------------------------------------

def create_pull_request(token, owner, repo, title, body, head, base="main"):
    """Open a new pull request."""
    return _request("POST", f"/repos/{owner}/{repo}/pulls", token, {
        "title": title,
        "body": body,
        "head": head,
        "base": base,
    })


def list_pull_requests(token, owner, repo, state="open"):
    """List pull requests (default: open)."""
    return _request("GET", f"/repos/{owner}/{repo}/pulls?state={state}", token)


def get_pull_request(token, owner, repo, index):
    """Get a single pull request by number."""
    return _request("GET", f"/repos/{owner}/{repo}/pulls/{index}", token)


def get_pr_diff(token, owner, repo, index):
    """Return the unified diff for a pull request as a string."""
    url = f"{GITEA_URL}/api/v1/repos/{owner}/{repo}/pulls/{index}.diff"
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode()


def get_pr_files(token, owner, repo, index):
    """Return the list of changed files in a pull request."""
    return _request("GET", f"/repos/{owner}/{repo}/pulls/{index}/files", token)


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

def submit_review(token, owner, repo, index, body, event, comments=None):
    """Submit a pull request review.

    Args:
        event: One of APPROVED, REQUEST_CHANGES, or COMMENT.
        comments: Optional list of inline comment dicts, each with keys:
                  path, body, new_position.
    """
    payload = {"body": body, "event": event}
    if comments:
        payload["comments"] = comments
    return _request(
        "POST", f"/repos/{owner}/{repo}/pulls/{index}/reviews", token, payload,
    )


# ---------------------------------------------------------------------------
# Commit statuses
# ---------------------------------------------------------------------------

def set_commit_status(token, owner, repo, sha, state, description, context="ci"):
    """Set a commit status (pending / success / error / failure)."""
    return _request("POST", f"/repos/{owner}/{repo}/statuses/{sha}", token, {
        "state": state,
        "description": description,
        "context": context,
    })
