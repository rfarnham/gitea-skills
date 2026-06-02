#!/usr/bin/env python3
"""Launch a Reviewer Agent to review a pull request.

Usage:
    python scripts/run_reviewer.py --pr 3
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Allow importing sibling modules
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent
AGENTIC_DIR = PROJECT_DIR / ".agentic_dev"

sys.path.insert(0, str(SCRIPTS_DIR))
import gitea_api


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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_reviewer(pr_number):
    try:
        from google.antigravity import Agent, LocalAgentConfig
    except ImportError:
        print("ERROR: google-antigravity is not installed.", file=sys.stderr)
        print("Run: pip install google-antigravity", file=sys.stderr)
        sys.exit(1)

    try:
        import pydantic
    except ImportError:
        print("ERROR: pydantic is not installed.", file=sys.stderr)
        print("Run: pip install pydantic", file=sys.stderr)
        sys.exit(1)

    tokens = load_env(AGENTIC_DIR / "tokens.env")
    gitea_url = tokens.get("GITEA_URL", "http://localhost:3000")
    repo_owner = tokens.get("REPO_OWNER", "admin")
    repo_name = tokens.get("REPO_NAME", "friendly-davinci")
    review_token = tokens.get("REVIEWER_AGENT_TOKEN", "")

    # Set GITEA_URL for the API module
    os.environ["GITEA_URL"] = gitea_url
    gitea_api.GITEA_URL = gitea_url

    # Fetch PR metadata and diff
    print(f"Fetching PR #{pr_number}...")
    pr = gitea_api.get_pull_request(review_token, repo_owner, repo_name, pr_number)
    diff = gitea_api.get_pr_diff(review_token, repo_owner, repo_name, pr_number)

    pr_title = pr.get("title", "")
    pr_body = pr.get("body", "")

    print(f"PR: {pr_title}")
    print(f"Diff size: {len(diff)} bytes")

    # Define structured output schema
    class InlineComment(pydantic.BaseModel):
        path: str
        new_position: int
        body: str

    class ReviewResult(pydantic.BaseModel):
        verdict: str  # APPROVED, REQUEST_CHANGES, or COMMENT
        summary: str
        inline_comments: list[InlineComment] = []

    # Load guidelines (§1 and §3 only)
    guidelines = (PROJECT_DIR / "AGENT_GUIDELINES.md").read_text()

    system_instructions = f"""\
You are a Reviewer Agent. Your job is to review pull requests and provide
clear, actionable feedback.

{guidelines}

Your identity:
- Gitea username: reviewer-agent
- Gitea URL: {gitea_url}
- Repo: {repo_owner}/{repo_name}

You will receive a PR title, description, and diff. Analyze the changes and
return a structured review. Be constructive and specific.

For inline comments, set 'new_position' to the line number within the diff
hunk (1-indexed from the start of the hunk) where the comment applies.

Set 'verdict' to:
- APPROVED — if the code is ready to merge
- REQUEST_CHANGES — if there are issues that must be fixed
- COMMENT — if you have suggestions but no blocking concerns
"""

    agent_config = LocalAgentConfig(
        system_instructions=system_instructions,
        response_schema=ReviewResult,
    )

    prompt = f"""\
Review this pull request:

## Title
{pr_title}

## Description
{pr_body}

## Diff
```diff
{diff}
```
"""

    print("Running reviewer agent...")
    async with Agent(agent_config) as agent:
        response = await agent.chat(prompt)
        result = await response.structured_output()

    if not result:
        print("ERROR: Reviewer agent did not return structured output.", file=sys.stderr)
        sys.exit(1)

    # Post the review to Gitea
    verdict = result.get("verdict", "COMMENT")
    summary = result.get("summary", "")
    inline_comments = result.get("inline_comments", [])

    print(f"\nVerdict: {verdict}")
    print(f"Summary: {summary}")
    if inline_comments:
        print(f"Inline comments: {len(inline_comments)}")

    # Format comments for Gitea API
    api_comments = [
        {"path": c["path"], "body": c["body"], "new_position": c["new_position"]}
        for c in inline_comments
    ]

    gitea_api.submit_review(
        review_token, repo_owner, repo_name, pr_number,
        body=summary, event=verdict, comments=api_comments or None,
    )

    print(f"\n✓ Review posted to {gitea_url}/{repo_owner}/{repo_name}/pulls/{pr_number}")


def main():
    parser = argparse.ArgumentParser(description="Launch a Reviewer Agent")
    parser.add_argument("--pr", type=int, required=True, help="PR number to review")
    args = parser.parse_args()
    asyncio.run(run_reviewer(args.pr))


if __name__ == "__main__":
    main()
