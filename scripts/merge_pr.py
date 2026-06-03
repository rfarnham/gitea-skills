#!/usr/bin/env python3
"""Helper script to merge pull requests on Gitea.

Usage:
    ./scripts/merge_pr.py [pr_index] [--style merge|rebase|rebase-merge|squash]
"""

import sys
import argparse
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
import gitea_api

def load_env(path):
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def main():
    parser = argparse.ArgumentParser(description="Merge PR on Gitea")
    parser.add_argument("index", type=int, help="PR index number")
    parser.add_argument("--style", default="merge", choices=["merge", "rebase", "rebase-merge", "squash"], help="Merge style")
    args = parser.parse_args()

    agentic_dir = SCRIPTS_DIR.parent / ".agentic_dev"
    tokens = load_env(agentic_dir / "tokens.env")
    
    gitea_url = tokens.get("GITEA_URL", "http://localhost:3000")
    repo_owner = tokens.get("REPO_OWNER", "admin")
    repo_name = tokens.get("REPO_NAME", "friendly-davinci")
    token = tokens.get("ADMIN_TOKEN", "") # Use admin token to merge
    
    gitea_api.GITEA_URL = gitea_url
    
    payload = {
        "Do": args.style,
        "delete_branch_after_merge": True
    }
    
    try:
        res = gitea_api._request(
            'POST',
            f'/repos/{repo_owner}/{repo_name}/pulls/{args.index}/merge',
            token=token,
            data=payload
        )
        print(f"Success! Merged PR #{args.index} using style '{args.style}' and deleted the head branch.")
    except Exception as e:
        print(f"Error merging PR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
