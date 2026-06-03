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
