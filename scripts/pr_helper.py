#!/usr/bin/env python3
"""CLI tool for interacting with Gitea Pull Requests.

Usage:
    ./scripts/pr_helper.py create [branch] [title] [body]
    ./scripts/pr_helper.py diff [pr_index]
    ./scripts/pr_helper.py details [pr_index]
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
    parser = argparse.ArgumentParser(description="Interact with Gitea Pull Requests")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create command
    create_parser = subparsers.add_parser("create", help="Create a PR")
    create_parser.add_argument("branch", help="The feature branch name")
    create_parser.add_argument("title", help="The PR title")
    create_parser.add_argument("body", help="The PR description")

    # diff command
    diff_parser = subparsers.add_parser("diff", help="Get PR diff")
    diff_parser.add_argument("index", type=int, help="PR index number")

    # details command
    details_parser = subparsers.add_parser("details", help="Get PR details")
    details_parser.add_argument("index", type=int, help="PR index number")

    args = parser.parse_args()

    try:
        if args.command == "create":
            res = gitea_skills.pr_create(args.branch, args.title, args.body)
            print(res)
        elif args.command == "diff":
            res = gitea_skills.pr_get_diff(args.index)
            print(res)
        elif args.command == "details":
            res = gitea_skills.pr_get_details(args.index)
            print(res)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
