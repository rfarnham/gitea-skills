#!/usr/bin/env python3
"""Unified CLI for gitea-skills.

Usage:
    gitea-skills worktree create <branch>
    gitea-skills worktree remove <branch>
    gitea-skills pr create --branch <branch> --title <title> --body <body>
    gitea-skills pr diff <pr_index>
    gitea-skills pr details <pr_index>
    gitea-skills review submit <pr_index> <verdict> <body>
    gitea-skills merge <pr_index> [--style merge|rebase|squash]
    gitea-skills ci status <ref>
    gitea-skills push-to-github [github_url]
    gitea-skills install [--target-dir <path>]
"""

import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(prog="gitea-skills", description="Gitea agentic development loop CLI")
    parser.add_argument("--project-dir", help="Project directory (default: cwd)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # worktree
    wt = subparsers.add_parser("worktree", help="Manage git worktrees")
    wt_sub = wt.add_subparsers(dest="action", required=True)
    wt_create = wt_sub.add_parser("create")
    wt_create.add_argument("branch")
    wt_remove = wt_sub.add_parser("remove")
    wt_remove.add_argument("branch")

    # pr
    pr = subparsers.add_parser("pr", help="Manage Gitea pull requests")
    pr_sub = pr.add_subparsers(dest="action", required=True)
    pr_create = pr_sub.add_parser("create")
    pr_create.add_argument("--branch", required=True)
    pr_create.add_argument("--title", required=True)
    pr_create.add_argument("--body", default="")
    pr_diff = pr_sub.add_parser("diff")
    pr_diff.add_argument("pr_index", type=int)
    pr_details = pr_sub.add_parser("details")
    pr_details.add_argument("pr_index", type=int)
    pr_comments = pr_sub.add_parser("comments", help="Retrieve general comments on a pull request")
    pr_comments.add_argument("pr_index", type=int)
    pr_comments.add_argument("--json", action="store_true", help="Output raw JSON")
    pr_reviews = pr_sub.add_parser("reviews", help="Retrieve reviews and inline comments on a pull request")
    pr_reviews.add_argument("pr_index", type=int)
    pr_reviews.add_argument("--json", action="store_true", help="Output raw JSON")

    # review
    rev = subparsers.add_parser("review", help="Submit PR reviews")
    rev_sub = rev.add_subparsers(dest="action", required=True)
    rev_submit = rev_sub.add_parser("submit")
    rev_submit.add_argument("pr_index", type=int)
    rev_submit.add_argument("verdict", choices=["APPROVED", "REQUEST_CHANGES", "COMMENT"])
    rev_submit.add_argument("body")

    # merge
    mg = subparsers.add_parser("merge", help="Merge a PR")
    mg.add_argument("pr_index", type=int)
    mg.add_argument("--style", default="merge", choices=["merge", "rebase", "rebase-merge", "squash"])

    # ci
    ci = subparsers.add_parser("ci", help="Check CI status")
    ci_sub = ci.add_subparsers(dest="action", required=True)
    ci_status = ci_sub.add_parser("status")
    ci_status.add_argument("ref")

    # push-to-github
    ptg = subparsers.add_parser("push-to-github", help="Push to GitHub and create PR")
    ptg.add_argument("github_url", nargs="?", default=None)
    ptg.add_argument("--token", help="GitHub Personal Access Token (PAT) override")

    # install
    inst = subparsers.add_parser("install", help="Set up a project for the gitea dev loop")
    inst.add_argument("--target-dir", default=".")

    # repo
    repo = subparsers.add_parser("repo", help="Manage Gitea repositories")
    repo_sub = repo.add_subparsers(dest="action", required=True)
    repo_create = repo_sub.add_parser("create", help="Create a Gitea repository")
    repo_create.add_argument("name", help="Name of the repository")
    repo_create.add_argument("--description", default="", help="Description of the repository")
    repo_create.add_argument("--private", action="store_true", help="Create a private repository")
    repo_create.add_argument("--auto-init", action="store_true", help="Auto initialize repository")
    repo_create.add_argument("--owner", help="Gitea user or organization owner")
    repo_create.add_argument("--set-origin", action="store_true", help="Set local remote origin to the new repo clone URL")

    args = parser.parse_args()

    # Set project dir env var if provided
    if args.project_dir:
        os.environ["GITEA_SKILLS_PROJECT_DIR"] = args.project_dir

    from gitea_skills import core

    if args.command == "worktree":
        if args.action == "create":
            print(core.worktree_create(args.branch))
        elif args.action == "remove":
            print(core.worktree_remove(args.branch))

    elif args.command == "pr":
        if args.action == "create":
            print(core.pr_create(args.branch, args.title, args.body))
        elif args.action == "diff":
            print(core.pr_get_diff(args.pr_index))
        elif args.action == "details":
            print(core.pr_get_details(args.pr_index))
        elif args.action == "comments":
            print(core.pr_get_comments(args.pr_index, args.json))
        elif args.action == "reviews":
            print(core.pr_get_reviews(args.pr_index, args.json))

    elif args.command == "review":
        if args.action == "submit":
            print(core.submit_review(args.pr_index, args.verdict, args.body))

    elif args.command == "merge":
        print(core.merge_pr(args.pr_index, args.style))

    elif args.command == "ci":
        if args.action == "status":
            print(core.ci_get_status(args.ref))

    elif args.command == "push-to-github":
        import subprocess
        from pathlib import Path
        script = Path(__file__).parent / "skills" / "gitea_agentic_loop" / "scripts" / "push_to_github.sh"
        cmd = ["bash", str(script)]
        if args.token:
            cmd.extend(["--token", args.token])
        if args.github_url:
            cmd.append(args.github_url)
        subprocess.run(cmd, check=True)

    elif args.command == "install":
        from gitea_skills.install import run_install
        run_install(args.target_dir)

    elif args.command == "repo":
        if args.action == "create":
            print(core.repo_create(
                name=args.name,
                description=args.description,
                private=args.private,
                auto_init=args.auto_init,
                owner=args.owner,
                set_origin=args.set_origin
            ))


if __name__ == "__main__":
    main()
