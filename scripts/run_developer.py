#!/usr/bin/env python3
"""Launch a Developer Agent to implement a task on a new branch.

Usage:
    ./scripts/run_developer.py --task "Add a fibonacci function with tests"
    ./scripts/run_developer.py --task "Fix the parser bug" --branch agent/42-fix-parser
    ./scripts/run_developer.py --pr 3 --revise   # address review feedback on existing PR
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
AGENTIC_DIR = PROJECT_DIR / ".agentic_dev"

import gitea_skills


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
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len]


async def run_developer(task, branch, revise_pr=None):
    # Import here so the script gives a clear error if not installed
    try:
        from google.antigravity import Agent, LocalAgentConfig
        from google.antigravity.hooks import policy
    except ImportError:
        print("ERROR: google-antigravity is not installed.", file=sys.stderr)
        print("Run: pip install google-antigravity", file=sys.stderr)
        sys.exit(1)

    # Set the project dir so gitea_skills.core resolves paths correctly
    os.environ["GITEA_SKILLS_PROJECT_DIR"] = str(PROJECT_DIR)

    tokens = load_env(AGENTIC_DIR / "tokens.env")
    config_env = load_env(AGENTIC_DIR / "config.env")

    gitea_url = tokens.get("GITEA_URL", "http://localhost:3000")
    repo_owner = tokens.get("REPO_OWNER", "admin")
    repo_name = tokens.get("REPO_NAME", "friendly-davinci")
    test_cmd = config_env.get("TEST_COMMAND", "pytest")

    # 1. Use the skill tool to set up the worktree
    print(f"Setting up isolated worktree for branch '{branch}'...")
    gitea_skills.worktree_create(branch)
    
    # Calculate the worktree directory path
    worktree_dir = AGENTIC_DIR / "worktrees" / branch.replace("/", "__")

    # Load agent guidelines
    guidelines = (PROJECT_DIR / "AGENT_GUIDELINES.md").read_text()

    # Build the agent prompt
    if revise_pr:
        prompt = (
            f"You are revising PR #{revise_pr} on branch '{branch}' in {worktree_dir}.\n"
            f"1. Fetch the review comments using Gitea API or inspect files.\n"
            f"2. Fix the issues inside the worktree and run tests using: {test_cmd}.\n"
            f"3. Commit the changes.\n"
            f"4. Push your changes to the remote branch.\n"
            f"5. Check the status of Gitea CI using 'ci_get_status'. If it passes, inform the user you are finished and wait for human review (DO NOT merge!)."
        )
    else:
        prompt = (
            f"Implement the following task inside the workspace {worktree_dir}:\n\n{task}\n\n"
            f"After implementing the changes:\n"
            f"1. Run tests using: {test_cmd}. Ensure they pass.\n"
            f"2. Commit the changes with a conventional commit message.\n"
            f"3. Push your branch and open a PR targeting 'main' using the 'pr_create' tool.\n"
            f"4. Poll the Gitea CI build status using the 'ci_get_status' tool. If it passes, stop and inform the user you are waiting for human review."
        )

    system_instructions = f"""\
You are a Developer Agent working in this repository: {worktree_dir}

{guidelines}

Your identity and environment info:
- Gitea username: developer-agent
- Gitea URL: {gitea_url}
- Repo owner: {repo_owner}
- Repo name: {repo_name}
- Test command: {test_cmd}
- Branch: {branch}

You have native tools registered to interact with Gitea and Git worktrees. Use them as needed.
"""

    agent_config = LocalAgentConfig(
        system_instructions=system_instructions,
        workspaces=[str(worktree_dir)],
        policies=[policy.allow_all()],
        skills_paths=[str(gitea_skills.get_skills_path())],
        tools=[
            gitea_skills.pr_create,
            gitea_skills.ci_get_status,
            gitea_skills.worktree_remove
        ],
    )

    try:
        async with Agent(agent_config) as agent:
            response = await agent.chat(prompt)
            print(await response.text())
    finally:
        print(f"\nWorktree is located at: {worktree_dir}")
        print("Once the PR has been merged by the human, run the cleanup tool:")
        print(f"  gitea-skills worktree remove {branch}")


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
