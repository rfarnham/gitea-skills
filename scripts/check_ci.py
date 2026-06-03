#!/usr/bin/env python3
"""Helper script to check Gitea Actions CI statuses and fetch logs.

Usage:
    ./scripts/check_ci.py [commit_sha_or_branch]
    ./scripts/check_ci.py --jobs [run_id]
    ./scripts/check_ci.py --logs [job_id]
"""

import sys
import argparse
from pathlib import Path

# Allow importing gitea_api from the scripts directory
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
    parser = argparse.ArgumentParser(description="Check CI status and logs on Gitea")
    parser.add_argument("ref", nargs="?", help="Commit SHA or branch name (default action: check statuses)")
    parser.add_argument("--jobs", type=int, help="Fetch jobs for the specified actions run_id")
    parser.add_argument("--logs", type=int, help="Fetch logs for the specified actions job_id")
    args = parser.parse_args()

    agentic_dir = SCRIPTS_DIR.parent / ".agentic_dev"
    tokens = load_env(agentic_dir / "tokens.env")
    
    gitea_url = tokens.get("GITEA_URL", "http://localhost:3000")
    repo_owner = tokens.get("REPO_OWNER", "admin")
    repo_name = tokens.get("REPO_NAME", "friendly-davinci")
    token = tokens.get("REVIEWER_AGENT_TOKEN", "")
    
    gitea_api.GITEA_URL = gitea_url
    
    import json

    try:
        if args.jobs:
            # Fetch jobs for a run
            res = gitea_api._request(
                'GET',
                f'/repos/{repo_owner}/{repo_name}/actions/runs/{args.jobs}/jobs',
                token=token
            )
            print(json.dumps(res, indent=2))
        elif args.logs:
            # Fetch logs for a job
            res = gitea_api._request(
                'GET',
                f'/repos/{repo_owner}/{repo_name}/actions/jobs/{args.logs}/logs',
                token=token
            )
            print(res)
        elif args.ref:
            # Fetch statuses for a commit or branch
            res = gitea_api._request(
                'GET',
                f'/repos/{repo_owner}/{repo_name}/commits/{args.ref}/statuses',
                token=token
            )
            print(json.dumps(res, indent=2))
        else:
            parser.print_help()
            sys.exit(1)
    except Exception as e:
        print(f"Error communicating with Gitea API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
