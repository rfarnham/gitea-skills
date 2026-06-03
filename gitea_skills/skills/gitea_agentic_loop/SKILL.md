---
name: gitea-agentic-loop
description: >-
  Manage the local agentic development loop: create git worktrees for isolated workspaces,
  create and review Gitea pull requests, check CI status, merge PRs, and sync to GitHub.
  Use when the user asks to develop features locally using the Gitea flow, create PRs,
  review code, or push to GitHub.
---

# Gitea Agentic Development Loop

This skill provides CLI commands for managing the local AI-driven development workflow.
All commands use the `gitea-skills` CLI tool which must be installed (`pip install gitea-skills`).

## Prerequisites

1. The `gitea-skills` package must be installed: `pip install gitea-skills`
2. The global Gitea tokens must be configured in `~/.gitea_skills.env`.
   Run `python -m gitea_skills.install --target-dir <project>` to generate the template and project scaffolding.
3. Docker must be running with the Gitea containers (see the project's `docker-compose.yml`).

## Core Rules

- **Always use the CLI**: Execute all Gitea operations through the `gitea-skills` CLI.
  Do NOT call Gitea APIs directly.
- **Branch naming**: Use the format `agent/<ticket>-<slug>` for feature branches.
- **Commits**: Follow Conventional Commits format.
- **Cleanup**: Always remove worktrees after a branch is merged.

## Available Commands

### Worktree Management

Create an isolated workspace for a feature branch:
```bash
gitea-skills worktree create <branch-name>
```

Remove a worktree after the branch is merged:
```bash
gitea-skills worktree remove <branch-name>
```

### Pull Request Management

Create a PR on Gitea from the feature branch to main:
```bash
gitea-skills pr create --branch <branch-name> --title "feat: add feature" --body "Description"
```

View PR diff:
```bash
gitea-skills pr diff <pr_index>
```

View PR details:
```bash
gitea-skills pr details <pr_index>
```

### Code Review

Submit a review on a PR:
```bash
gitea-skills review submit <pr_index> APPROVED|REQUEST_CHANGES|COMMENT "Review body"
```

### Merging

Merge a PR:
```bash
gitea-skills merge <pr_index> --style merge|rebase|squash
```

### CI Status

Check CI status for a branch or commit:
```bash
gitea-skills ci status <branch-or-sha>
```

### GitHub Sync

Push to GitHub and create a PR:
```bash
gitea-skills push-to-github [github-repo-url]
```

### Project Setup

Initialize a project for the gitea dev loop:
```bash
python -m gitea_skills.install --target-dir /path/to/project
```

## Conventions

- **Branch Naming**: Use the format `agent/<ticket>-<slug>`.
- **Commits**: Follow Conventional Commits format.
- **Cleanup**: Always call `gitea-skills worktree remove` after a branch is merged.
