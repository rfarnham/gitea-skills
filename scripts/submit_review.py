#!/usr/bin/env python3
"""Helper script to submit PR reviews on Gitea.

Usage:
    python scripts/submit_review.py [pr_index] [APPROVED|REQUEST_CHANGES|COMMENT] "Review body"
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
    parser = argparse.ArgumentParser(description="Submit PR review on Gitea")
    parser.add_argument("index", type=int, help="PR index number")
    parser.add_argument("event", choices=["APPROVED", "REQUEST_CHANGES", "COMMENT"], help="Review verdict")
    parser.add_argument("body", help="Review body / summary comment")
    args = parser.parse_args()

    agentic_dir = SCRIPTS_DIR.parent / ".agentic_dev"
    tokens = load_env(agentic_dir / "tokens.env")
    
    gitea_url = tokens.get("GITEA_URL", "http://localhost:3000")
    repo_owner = tokens.get("REPO_OWNER", "admin")
    repo_name = tokens.get("REPO_NAME", "friendly-davinci")
    token = tokens.get("REVIEWER_AGENT_TOKEN", "")
    
    gitea_api.GITEA_URL = gitea_url
    
    try:
        res = gitea_api.submit_review(
            token=token,
            owner=repo_owner,
            repo=repo_name,
            index=args.index,
            body=args.body,
            event=args.event
        )
        print(f"Success! Submitted review verdict {args.event} on PR #{args.index}.")
    except Exception as e:
        print(f"Error submitting review: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
