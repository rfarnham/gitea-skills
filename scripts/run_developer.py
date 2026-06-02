#!/usr/bin/env python3
"""Launch a Developer Agent to implement a task on a new branch.

Usage:
    python scripts/run_developer.py --task "Add a fibonacci function with tests"
    python scripts/run_developer.py --task "Fix the parser bug" --branch agent/42-fix-parser
    python scripts/run_developer.py --pr 3 --revise   # address review feedback on existing PR
"""

import argparse
import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
AGENTIC_DIR = PROJECT_DIR / ".agentic_dev"
WORKTREES_DIR = AGENTIC_DIR / "worktrees"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_env(path):
    """Parse a KEY=VALUE env file into a dict."""
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def slugify(text, max_len=40):
    """Turn a task description into a branch-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len]


def create_worktree(branch):
    """Create a git worktree for the given branch."""
    dest = WORKTREES_DIR / branch.replace("/", "__")
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "worktree", "add", str(dest), "-b", branch],
        cwd=PROJECT_DIR, check=True,
    )
    return dest


def checkout_existing_worktree(branch):
    """Create a worktree for an existing remote branch."""
    dest = WORKTREES_DIR / branch.replace("/", "__")
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Fetch latest and create worktree from existing branch
    subprocess.run(["git", "fetch", "origin"], cwd=PROJECT_DIR, check=True)
    subprocess.run(
        ["git", "worktree", "add", str(dest), branch],
        cwd=PROJECT_DIR, check=True,
    )
    return dest


def remove_worktree(branch):
    """Remove the worktree for the given branch."""
    dest = WORKTREES_DIR / branch.replace("/", "__")
    if dest.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(dest)],
            cwd=PROJECT_DIR, check=False,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_developer(task, branch, revise_pr=None):
    # Import here so the script gives a clear error if not installed
    try:
        from google.antigravity import Agent, LocalAgentConfig
        from google.antigravity.hooks import policy
    except ImportError:
        print("ERROR: google-antigravity is not installed.", file=sys.stderr)
        print("Run: pip install google-antigravity", file=sys.stderr)
        sys.exit(1)

    tokens = load_env(AGENTIC_DIR / "tokens.env")
    config_env = load_env(AGENTIC_DIR / "config.env")

    gitea_url = tokens.get("GITEA_URL", "http://localhost:3000")
    repo_owner = tokens.get("REPO_OWNER", "admin")
    repo_name = tokens.get("REPO_NAME", "friendly-davinci")
    dev_token = tokens.get("DEVELOPER_AGENT_TOKEN", "")
    test_cmd = config_env.get("TEST_COMMAND", "pytest")

    # Set up worktree
    if revise_pr:
        worktree_dir = checkout_existing_worktree(branch)
    else:
        worktree_dir = create_worktree(branch)

    # Configure the git remote inside the worktree to use agent credentials
    subprocess.run(
        ["git", "remote", "set-url", "origin",
         f"http://developer-agent:{dev_token}@localhost:3000/{repo_owner}/{repo_name}.git"],
        cwd=worktree_dir, check=True,
    )

    # Load agent guidelines
    guidelines = (PROJECT_DIR / "AGENT_GUIDELINES.md").read_text()

    # Build the agent prompt
    if revise_pr:
        prompt = (
            f"You are revising PR #{revise_pr} on branch '{branch}'.\n"
            f"Read the review comments from the Gitea API and address them.\n"
            f"After fixing, commit and push."
        )
    else:
        prompt = (
            f"Implement the following task:\n\n{task}\n\n"
            f"You are on branch '{branch}'. After implementing and testing:\n"
            f"1. Commit with a conventional commit message.\n"
            f"2. Push to origin.\n"
            f"3. Open a PR via the Gitea API targeting 'main'."
        )

    system_instructions = f"""\
You are a Developer Agent working in this repository: {worktree_dir}

{guidelines}

Your identity:
- Gitea username: developer-agent
- API token: {dev_token}
- Gitea URL: {gitea_url}
- Repo owner: {repo_owner}
- Repo name: {repo_name}
- Test command: {test_cmd}
- Branch: {branch}
"""

    agent_config = LocalAgentConfig(
        system_instructions=system_instructions,
        workspaces=[str(worktree_dir)],
        policies=[policy.allow_all()],
    )

    try:
        async with Agent(agent_config) as agent:
            response = await agent.chat(prompt)
            print(await response.text())
    finally:
        print(f"\nWorktree at: {worktree_dir}")
        print("Run 'git worktree remove <path>' after the PR is merged.")


def main():
    parser = argparse.ArgumentParser(description="Launch a Developer Agent")
    parser.add_argument("--task", help="Task description for a new feature/fix")
    parser.add_argument("--branch", help="Branch name (auto-generated if omitted)")
    parser.add_argument("--pr", type=int, help="PR number to revise (used with --revise)")
    parser.add_argument("--revise", action="store_true", help="Revise an existing PR")
    args = parser.parse_args()

    if args.revise and not args.pr:
        parser.error("--revise requires --pr <number>")
    if not args.revise and not args.task:
        parser.error("--task is required for new work (or use --revise --pr N)")

    if args.branch:
        branch = args.branch
    elif args.task:
        branch = f"agent/{slugify(args.task)}"
    else:
        branch = f"agent/revise-pr-{args.pr}"

    asyncio.run(run_developer(args.task, branch, revise_pr=args.pr if args.revise else None))


if __name__ == "__main__":
    main()
