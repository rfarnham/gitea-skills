#!/usr/bin/env python3
"""CLI tool for managing git worktrees for development branches.

Usage:
    ./scripts/worktree_helper.py create [branch_name]
    ./scripts/worktree_helper.py remove [branch_name]
"""

import sys
import argparse
from pathlib import Path

# Allow importing from skills/agentic_dev
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(PROJECT_DIR / "skills" / "agentic_dev"))
import gitea_skills

def main():
    parser = argparse.ArgumentParser(description="Manage development worktrees")
    parser.add_argument("action", choices=["create", "remove"], help="Action to perform")
    parser.add_argument("branch", help="Git branch name")
    args = parser.parse_args()

    try:
        if args.action == "create":
            res = gitea_skills.worktree_create(args.branch)
            print(res)
        elif args.action == "remove":
            res = gitea_skills.worktree_remove(args.branch)
            print(res)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
