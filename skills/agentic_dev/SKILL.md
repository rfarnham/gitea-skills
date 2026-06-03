---
name: agentic-dev-loop
description: "Skills and tools for managing git worktrees, Gitea pull requests, CI builds, reviews, and merging within the local agentic development loop."
---

# Agentic Development Loop Skill

This skill equips agents with Gitea and Git lifecycle management capabilities. It allows the agent to:
1. Create and manage isolated workspaces using `git worktree`.
2. Inspect Gitea pull requests, view diffs, and check CI statuses.
3. Submit pull request reviews with inline comments.
4. Merge pull requests and clean up branches.

## Available Tools

The following tools are implemented in `gitea_skills.py` and should be registered in `LocalAgentConfig`:

- `worktree_create(branch)`: Prepare a clean workspace directory for a specific feature branch.
- `worktree_remove(branch)`: Safely discard an isolated workspace directory.
- `pr_create(branch, title, body)`: Open a Gitea pull request from the feature branch.
- `pr_get_diff(pr_index)`: Retrieve the diff content of the pull request.
- `pr_get_details(pr_index)`: Retrieve metadata for the pull request.
- `ci_get_status(ref)`: Retrieve the status check (e.g. pending, success, failure) of a commit or branch.
- `submit_review(pr_index, verdict, body, comments)`: Submit a review with comments.
- `merge_pr(pr_index, style)`: Merge the PR.

## Conventions

- **Branch Naming**: Use the format `agent/<ticket>-<slug>`.
- **Commits**: Follow Conventional Commits format.
- **Cleanup**: Always call `worktree_remove` after a branch is merged.
