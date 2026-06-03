# Friendly Davinci — Local Agentic Development Loop

A lightweight, reproducible setup for running AI coding agents locally with
full git workflow, code review, and CI — powered by [Gitea](https://gitea.com)
and Docker.

## What You Get

- **Gitea** — a local, GitHub-like web UI for browsing code, reviewing diffs,
  and managing pull requests. Runs in Docker.
- **Distinct agent identities** — `developer-agent` and `reviewer-agent` appear
  as separate users in Gitea, each with their own comments and activity.
- **Parallel workspaces** — agents work in isolated `git worktree` directories,
  so they never interfere with your editor or each other.
- **CI via Gitea Actions** — tests run automatically on every push and PR, with
  status checks visible in the Gitea UI.
- **GitHub sync** — push your reviewed, merged code to GitHub whenever you're
  ready.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Python 3.10+
- Git
- A `GEMINI_API_KEY` environment variable (get one at
  [Google AI Studio](https://aistudio.google.com/app/api-keys))

## Quick Start

```bash
# 1. Clone this repository
git clone <repo-url> && cd friendly-davinci

# 2. Run the automated setup (starts Gitea, creates users, configures git)
bash scripts/setup.sh

# 3. Open Gitea in your browser
open http://localhost:3000    # Login: admin / admin1234

# 4. Install the gitea-skills package and dependencies
pip install -e .
pip install -r requirements.txt

# 5. Launch a developer agent
./scripts/run_developer.py --task "Create a calculator module with add, subtract, and tests"

# 6. Review the PR in Gitea, or launch the reviewer agent
./scripts/run_reviewer.py --pr 1

# 7. Merge in Gitea, then push to GitHub
gitea-skills push-to-github git@github.com:<you>/<repo>.git
```

## Project Structure

```
.
├── pyproject.toml              # Python package definition
├── INSTALL.md                  # Detailed installation guide
├── docker-compose.yml          # Gitea + CI runner containers
├── requirements.txt            # Python dependencies
├── AGENT_GUIDELINES.md         # Instructions agents read and follow
├── README.md                   # This file
├── .gitea/
│   └── workflows/
│       └── ci.yml              # Gitea Actions CI workflow
├── gitea_skills/               # Installable Python package
│   ├── __init__.py             # Version, path helpers, re-exports
│   ├── plugin.json             # Antigravity plugin manifest
│   ├── core.py                 # Tool functions (worktree, PR, CI, review, merge)
│   ├── gitea_api.py            # Gitea REST API client (stdlib only)
│   ├── github_api.py           # GitHub REST API client
│   ├── github_auth.py          # macOS Keychain credential management
│   ├── github_credential_helper.py  # Git credential helper for HTTPS
│   ├── cli.py                  # Unified CLI entry point
│   ├── install.py              # Project setup / plugin registration
│   └── skills/
│       └── gitea_agentic_loop/
│           ├── SKILL.md        # Agent-facing skill instructions
│           └── scripts/
│               └── push_to_github.sh
├── scripts/
│   ├── setup.sh                # One-command bootstrap
│   ├── run_developer.py        # Developer agent launcher
│   └── run_reviewer.py         # Reviewer agent launcher
└── .agentic_dev/               # (git-ignored) local state
    ├── tokens.env              # API tokens for each user
    ├── config.env              # User-editable config (test command, etc.)
    ├── runner.env              # CI runner registration token
    ├── gitea_data/             # Gitea database and config
    ├── runner_data/            # CI runner state
    └── worktrees/              # Agent git worktrees
```

## Usage

### Create a new task

```bash
./scripts/run_developer.py --task "Add input validation to the API"
```

The developer agent will:
1. Create a git worktree on a new branch.
2. Implement the feature and write tests.
3. Push the branch and open a PR on Gitea.

### Review a PR

```bash
./scripts/run_reviewer.py --pr 2
```

The reviewer agent will:
1. Fetch the PR diff from Gitea.
2. Analyze the code for correctness, testing, and style.
3. Post review comments under the `reviewer-agent` user.

### Revise after review feedback

```bash
./scripts/run_developer.py --pr 2 --revise --branch agent/42-add-validation
```

### CLI Commands

The `gitea-skills` CLI provides direct access to all operations:

```bash
# Worktree management
gitea-skills worktree create agent/my-feature
gitea-skills worktree remove agent/my-feature

# Pull request management
gitea-skills pr create --branch agent/my-feature --title "feat: add feature" --body "Description"
gitea-skills pr diff 1
gitea-skills pr details 1

# Code review
gitea-skills review submit 1 APPROVED "Looks good!"

# Merge
gitea-skills merge 1 --style squash

# CI status
gitea-skills ci status agent/my-feature

# Push to GitHub
gitea-skills push-to-github git@github.com:username/repo.git
```

### Tear down

```bash
docker compose down            # Stop containers
docker compose down -v         # Stop and remove volumes
rm -rf .agentic_dev/           # Remove all local state
```

## Configuration

Edit `.agentic_dev/config.env` after running setup:

```env
TEST_COMMAND=pytest             # Change to your test runner
```

Edit the user credentials in `scripts/setup.sh` before first run if you want
different passwords.

## How It Works

```
┌──────────────┐     git push     ┌───────────┐    Gitea Actions    ┌──────────┐
│  Developer   │ ───────────────► │           │ ──────────────────► │ CI       │
│  Agent       │                  │  Gitea    │                     │ Runner   │
└──────────────┘                  │  (Docker) │ ◄────────────────── └──────────┘
                                  │           │    status check
┌──────────────┐   review API     │           │
│  Reviewer    │ ───────────────► │           │
│  Agent       │                  └───────────┘
└──────────────┘                       ▲
                                       │  browse & merge
                                  ┌────┴────┐
                                  │  Human  │
                                  └─────────┘
```

## License

MIT
