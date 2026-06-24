---
name: gitea-agentic-loop
description: >-
  Manage the local agentic development loop: create git worktrees for isolated workspaces,
  create and review Gitea pull requests, check CI status, merge PRs, and sync to GitHub.
  Use when the user asks to develop features locally using the Gitea flow, create PRs,
  review code, or push to GitHub.
---

# Gitea Agentic Development Loop

To prevent context pollution and excessive token usage in your primary conversation context, you MUST NOT execute Gitea CLI commands or manage the Gitea development loop directly if you are the main agent.

Instead, you MUST delegate this task to a subagent:
1. Call the `invoke_subagent` tool with `TypeName: "self"` (or `"research"`).
2. Set the `Role` to `"Gitea Loop Automation"`.
3. Provide a prompt instructing the subagent to read the CLI reference file and execute the Gitea task.

Example Prompt for the Subagent:
> "Read the Gitea reference document at `/Users/rfarnham/.gemini/config/plugins/gitea-skills/skills/gitea_agentic_loop/references/GITEA_CLI.md`. Then use the `gitea-skills` CLI to check CI status for the current branch."

Wait for the subagent to finish and report back, then relay the summary to the user.

## Rules for Subagents

If you are already running as a subagent (i.e. you were spawned by another agent with the role "Gitea Loop Automation" or specifically to perform a Gitea action):
1. Do NOT delegate further.
2. Immediately read the Gitea reference document at `/Users/rfarnham/.gemini/config/plugins/gitea-skills/skills/gitea_agentic_loop/references/GITEA_CLI.md` to load the CLI documentation.
3. Execute the requested Gitea CLI commands.
