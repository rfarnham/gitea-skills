#!/usr/bin/env bash
# push_to_github.sh — Push the local main branch to your personal GitHub repo.
#
# Usage:
#   ./scripts/push_to_github.sh [GITHUB_REPO_URL]
#
# If the 'github' remote doesn't exist yet, pass the URL as an argument
# (e.g. git@github.com:user/repo.git) and this script will add it for you.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# ── Check prerequisites ──────────────────────────────────────────────────
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "ERROR: Not inside a git repository." >&2
    exit 1
fi

# ── Ensure 'github' remote exists ────────────────────────────────────────
if ! git remote get-url github &>/dev/null; then
    if [ $# -ge 1 ]; then
        GITHUB_URL="$1"
        echo "Adding 'github' remote → $GITHUB_URL"
        git remote add github "$GITHUB_URL"
    else
        echo "ERROR: No 'github' remote configured."
        echo ""
        echo "Add it by running one of:"
        echo "  ./scripts/push_to_github.sh git@github.com:<user>/<repo>.git   # SSH"
        echo "  ./scripts/push_to_github.sh https://github.com/<user>/<repo>.git  # HTTPS"
        exit 1
    fi
fi

GITHUB_URL="$(git remote get-url github)"
echo "GitHub remote: $GITHUB_URL"

# ── Check & Acquire Credentials ──────────────────────────────────────────
# If the URL is HTTPS, ensure we have the token stored in the Keychain.
if [[ "$GITHUB_URL" =~ ^https:// ]]; then
    # Run the secure auth helper to check or prompt for the token.
    # We execute it in the current shell so it can prompt the user interactively.
    "$SCRIPT_DIR/github_auth.py"
fi

# ── Verify authentication ───────────────────────────────────────────────
echo "Verifying GitHub authentication..."

PUSH_CMD=("git")
# If HTTPS, use our custom credential helper
if [[ "$GITHUB_URL" =~ ^https:// ]]; then
    PUSH_CMD+=("-c" "credential.helper=$SCRIPT_DIR/github_credential_helper.py")
fi

if ! "${PUSH_CMD[@]}" ls-remote github &>/dev/null; then
    echo "ERROR: Cannot authenticate with GitHub."
    echo ""
    echo "Ensure your credentials are configured:"
    echo "  • SSH:   ssh-keygen && add key to https://github.com/settings/keys"
    echo "  • HTTPS: Verify your token matches and has 'repo' scopes."
    exit 1
fi

# ── Push to Sync Branch & Create Pull Request ────────────────────────────
CURRENT_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo "main")"
SYNC_BRANCH="sync/gitea-$CURRENT_BRANCH"

echo "Pushing local $CURRENT_BRANCH branch to GitHub remote as $SYNC_BRANCH..."
"${PUSH_CMD[@]}" push -f github "$CURRENT_BRANCH:refs/heads/$SYNC_BRANCH"

echo ""
echo "Creating Pull Request on GitHub..."
"$SCRIPT_DIR/github_api.py" \
    --head "$SYNC_BRANCH" \
    --base "$CURRENT_BRANCH" \
    --title "Sync $CURRENT_BRANCH from Gitea" \
    --body "Automated Pull Request syncing changes from local Gitea."

echo ""
echo "Done! Code pushed and Pull Request processed for: $GITHUB_URL"
