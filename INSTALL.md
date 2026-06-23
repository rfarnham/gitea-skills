# Installing Gitea Skills

This guide explains how to install the `gitea-skills` package to enable the local agentic development loop in any project.

## Quick Install

```bash
# Install from GitHub
pip install git+https://github.com/<owner>/friendly-davinci.git

# Set up a project
cd /path/to/your/project
python -m gitea_skills.install --target-dir .
```

## What the installer does

1. Creates `.agentic_dev/` in your project with template configuration files.
2. Creates a symlink in `~/.gemini/config/plugins/gitea-skills` so the Antigravity IDE agent discovers the skill automatically in every conversation.
3. Adds `.agentic_dev/` to your `.gitignore`.

## Configuration

The installer sets up a **global configuration file** for your Gitea tokens so you only have to configure them once per machine.

Edit `~/.gitea_skills.env` with your Gitea credentials:

```env
GITEA_URL=http://localhost:3000
REPO_OWNER=admin
REPO_NAME=your-repo-name
DEVELOPER_AGENT_TOKEN=<from setup.sh>
REVIEWER_AGENT_TOKEN=<from setup.sh>
ADMIN_TOKEN=<from setup.sh>
```

You can optionally override these on a per-project basis by creating `.agentic_dev/tokens.env` in a specific project.

## Usage with SDK Agents

For programmatic agents using `google-antigravity`:

```python
import os
import gitea_skills
from google.antigravity import Agent, LocalAgentConfig

os.environ["GITEA_SKILLS_PROJECT_DIR"] = str(project_dir)

config = LocalAgentConfig(
    skills_paths=[str(gitea_skills.get_skills_path())],
    tools=[
        gitea_skills.pr_create,
        gitea_skills.ci_get_status,
        gitea_skills.worktree_create,
        gitea_skills.worktree_remove,
    ],
)
```

## Usage with Antigravity IDE Agent

Once installed, the skill is automatically available. Just tell the agent:

> "Use the gitea-agentic-loop skill to create a feature branch and implement..."

The agent will see the skill in its available skills list and follow the instructions in SKILL.md.

---

## Troubleshooting

### 1. GitHub API Access Forbidden (403)
If the CLI reports `Resource not accessible by personal access token` when attempting to create a Pull Request on GitHub, it means your GitHub Fine-grained Personal Access Token (PAT) lacks the required permissions.
- **Fix**: Go to your GitHub Developer Settings, edit the token, and ensure it has **Repository permissions -> "Pull requests": Read and write** enabled.

### 2. macOS Keychain Caching & Permission Denied (403) on Push
On macOS, Git's global credential helper (`osxkeychain`) might cache a GitHub token/password that doesn't have write access to your new repository. Git will prioritize the cached global token and fail with `403 Permission Denied` before Gitea-skills' helper can run.
- **Fix**: Run `gitea-skills install` to set up the repository. This automatically runs `git config --local credential.helper ""` to ignore global helpers for the repository.
- **Manual Fix**: You can manually clear the global helper inheritance by running:
  ```bash
  git config --local credential.helper ""
  ```
  To completely clear a cached credential for GitHub from your macOS Keychain, run:
  ```bash
  echo -e "host=github.com\nprotocol=https" | git credential-osxkeychain erase
  ```

