#!/usr/bin/env python3
"""Launch a Reviewer Agent to review a pull request.

Usage:
    ./scripts/run_reviewer.py --pr 3
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Allow importing skills/agentic_dev modules
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "skills" / "agentic_dev"))
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


async def run_reviewer(pr_number):
    try:
        from google.antigravity import Agent, LocalAgentConfig
        from google.antigravity.hooks import policy
    except ImportError:
        print("ERROR: google-antigravity is not installed.", file=sys.stderr)
        print("Run: pip install google-antigravity", file=sys.stderr)
        sys.exit(1)

    agentic_dir = PROJECT_DIR / ".agentic_dev"
    tokens = load_env(agentic_dir / "tokens.env")
    gitea_url = tokens.get("GITEA_URL", "http://localhost:3000")
    repo_owner = tokens.get("REPO_OWNER", "admin")
    repo_name = tokens.get("REPO_NAME", "friendly-davinci")

    # 1. Use the skill tool to fetch PR info
    print(f"Fetching PR #{pr_number} metadata and diff...")
    pr_details_json = gitea_skills.pr_get_details(pr_number)
    diff = gitea_skills.pr_get_diff(pr_number)

    print(f"Diff size: {len(diff)} bytes")

    # Load guidelines
    guidelines = (PROJECT_DIR / "AGENT_GUIDELINES.md").read_text()

    system_instructions = f"""\
You are a Reviewer Agent. Your job is to review pull requests and provide
clear, actionable feedback.

{guidelines}

Your identity and environment info:
- Gitea username: reviewer-agent
- Gitea URL: {gitea_url}
- Repo: {repo_owner}/{repo_name}
- PR ID: {pr_number}

Analyze the changes and use the 'submit_review' tool to publish your review. 

For inline comments inside the 'submit_review' payload:
- Set 'new_position' to the line number within the diff hunk (1-indexed from the start of the hunk) where the comment applies.
- Set 'path' to the relative file path.
- Set 'body' to your review comment.

Set the review verdict parameter to one of:
- APPROVED — if the code is ready to merge
- REQUEST_CHANGES — if there are issues that must be fixed
- COMMENT — if you have suggestions but no blocking concerns
"""

    agent_config = LocalAgentConfig(
        system_instructions=system_instructions,
        policies=[policy.allow_all()],
        skills_paths=[str(PROJECT_DIR / "skills" / "agentic_dev")],
        tools=[gitea_skills.submit_review],
    )

    prompt = f"""\
Review this pull request:

## PR Details (JSON)
{pr_details_json}

## Diff
```diff
{diff}
```

After performing your analysis, make a single call to the 'submit_review' tool to submit your findings.
"""

    print("Running reviewer agent...")
    async with Agent(agent_config) as agent:
        response = await agent.chat(prompt)
        print(await response.text())


def main():
    parser = argparse.ArgumentParser(description="Launch a Reviewer Agent")
    parser.add_argument("--pr", type=int, required=True, help="PR number to review")
    args = parser.parse_args()
    asyncio.run(run_reviewer(args.pr))


if __name__ == "__main__":
    main()
