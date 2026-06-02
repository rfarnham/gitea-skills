# Agent Guidelines

Instructions for AI agents participating in this repository's development loop.
Read this document in full before beginning any work.

---

## §1 — Environment

### Credentials

Agent credentials are stored in `.agentic_dev/tokens.env`. Source this file or
read it to obtain the following variables:

| Variable                 | Description                            |
|--------------------------|----------------------------------------|
| `GITEA_URL`              | Gitea server URL (default `http://localhost:3000`) |
| `REPO_OWNER`             | Repository owner (default `admin`)     |
| `REPO_NAME`              | Repository name                        |
| `DEVELOPER_AGENT_TOKEN`  | API token for the `developer-agent` user |
| `REVIEWER_AGENT_TOKEN`   | API token for the `reviewer-agent` user  |

### Git Authentication

When pushing or pulling from Gitea, use HTTP token auth in the remote URL:

```
http://<username>:<token>@localhost:3000/<owner>/<repo>.git
```

For example:
```bash
git remote set-url origin http://developer-agent:$DEVELOPER_AGENT_TOKEN@localhost:3000/admin/friendly-davinci.git
```

### Gitea API

The Gitea REST API is available at `$GITEA_URL/api/v1/`. Include the token in
the `Authorization` header:

```bash
curl -H "Authorization: token $DEVELOPER_AGENT_TOKEN" \
     "$GITEA_URL/api/v1/repos/$REPO_OWNER/$REPO_NAME"
```

Full API documentation is available at `$GITEA_URL/api/swagger`.

---

## §2 — Developer Agent Workflow

You are the `developer-agent`. Your job is to implement features, fix bugs, and
write tests on an isolated branch, then open a pull request for review.

### Step 1: Create an isolated workspace

Use `git worktree` to create a workspace without disturbing the main checkout:

```bash
BRANCH="agent/<ticket-number>-<short-slug>"
git worktree add .agentic_dev/worktrees/$BRANCH -b $BRANCH
cd .agentic_dev/worktrees/$BRANCH
```

### Step 2: Implement the task

- Write clean, well-documented code.
- Add or update tests to cover your changes.
- Follow existing code style and conventions in the repository.

### Step 3: Run tests

```bash
pytest          # or whatever TEST_COMMAND is configured in .agentic_dev/config.env
```

All tests must pass before pushing.

### Step 4: Commit

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(auth): add JWT token refresh endpoint
fix(parser): handle empty input gracefully
test(utils): add edge case coverage for parse_date
docs(readme): update setup instructions
```

Keep commits atomic — one logical change per commit.

### Step 5: Push and open a PR

```bash
git push origin $BRANCH
```

Then open a PR via the Gitea API:

```bash
curl -X POST "$GITEA_URL/api/v1/repos/$REPO_OWNER/$REPO_NAME/pulls" \
     -H "Authorization: token $DEVELOPER_AGENT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "feat(auth): add JWT token refresh endpoint",
       "body": "## Summary\n\nImplements token refresh...\n\n## Testing\n\nAdded unit tests...",
       "head": "'"$BRANCH"'",
       "base": "main"
     }'
```

### Step 6: Clean up

After the PR is merged (not before), remove the worktree:

```bash
git worktree remove .agentic_dev/worktrees/$BRANCH
```

---

## §3 — Reviewer Agent Workflow

You are the `reviewer-agent`. Your job is to review pull requests and provide
actionable feedback.

### Step 1: Fetch the PR diff

```bash
curl -H "Authorization: token $REVIEWER_AGENT_TOKEN" \
     "$GITEA_URL/api/v1/repos/$REPO_OWNER/$REPO_NAME/pulls/<PR_NUMBER>.diff"
```

You can also fetch the list of changed files:

```bash
curl -H "Authorization: token $REVIEWER_AGENT_TOKEN" \
     "$GITEA_URL/api/v1/repos/$REPO_OWNER/$REPO_NAME/pulls/<PR_NUMBER>/files"
```

### Step 2: Analyze the changes

Evaluate the code for:

- **Correctness**: Does the logic handle expected inputs and edge cases?
- **Test coverage**: Are new code paths tested? Are there missing test cases?
- **Security**: Are there injection risks, exposed secrets, or unsafe operations?
- **Style**: Does the code follow the repository's conventions?
- **Documentation**: Are public functions/classes documented?

### Step 3: Submit your review

Use the Gitea API to post a formal review with inline comments:

```bash
curl -X POST "$GITEA_URL/api/v1/repos/$REPO_OWNER/$REPO_NAME/pulls/<PR_NUMBER>/reviews" \
     -H "Authorization: token $REVIEWER_AGENT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "body": "Overall assessment of the PR...",
       "event": "COMMENT",
       "comments": [
         {
           "path": "src/auth.py",
           "body": "This token expiry check should use `>=` not `>` to handle exact-boundary cases.",
           "new_position": 42
         }
       ]
     }'
```

The `event` field must be one of:

| Value              | Meaning                                    |
|--------------------|--------------------------------------------|
| `APPROVED`         | Changes look good, ready to merge.         |
| `REQUEST_CHANGES`  | Changes needed before merging.             |
| `COMMENT`          | General feedback, no approval/rejection.   |

When requesting changes, be specific about what needs to be fixed.

---

## §4 — Responding to Review Feedback

When the reviewer requests changes:

1. Read the review comments:
   ```bash
   curl -H "Authorization: token $DEVELOPER_AGENT_TOKEN" \
        "$GITEA_URL/api/v1/repos/$REPO_OWNER/$REPO_NAME/pulls/<PR_NUMBER>/reviews"
   ```
2. Check out the existing branch (re-create the worktree if it was cleaned up):
   ```bash
   git worktree add .agentic_dev/worktrees/$BRANCH $BRANCH
   cd .agentic_dev/worktrees/$BRANCH
   ```
3. Address each comment and commit:
   ```
   fix(auth): address review feedback — use >= for expiry check
   ```
4. Push. CI and the reviewer will be re-triggered automatically.

---

## §5 — Conventions

### Branch naming
```
agent/<ticket>-<short-slug>
```
Examples: `agent/12-add-auth`, `agent/7-fix-parser-crash`

### Commit messages
Follow [Conventional Commits](https://www.conventionalcommits.org/). Use a scope
when it clarifies the change.

### Pull request descriptions
Include:
- **Summary**: What the PR does and why.
- **Testing**: How the changes were tested.
- **Related issues**: Reference ticket numbers if applicable.

### Rules
- One branch per task. One PR per branch.
- PRs always target `main`.
- Never force-push.
- All tests must pass before requesting review.
