#!/usr/bin/env bash
# push_to_github.sh — Push the local main branch to your personal GitHub repo.
#
# Usage:
#   scripts/push_to_github.sh [GITHUB_REPO_URL]
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
        echo "  git remote add github git@github.com:<user>/<repo>.git   # SSH"
        echo "  git remote add github https://github.com/<user>/<repo>.git  # HTTPS"
        echo ""
        echo "Or pass the URL directly to this script:"
        echo "  $0 git@github.com:<user>/<repo>.git"
        exit 1
    fi
fi

GITHUB_URL="$(git remote get-url github)"
echo "GitHub remote: $GITHUB_URL"

# ── Verify authentication ───────────────────────────────────────────────
echo "Verifying GitHub authentication..."
if ! git ls-remote github &>/dev/null; then
    echo "ERROR: Cannot authenticate with GitHub."
    echo ""
    echo "Ensure your credentials are configured:"
    echo "  • SSH:   ssh-keygen && add key to https://github.com/settings/keys"
    echo "  • HTTPS: gh auth login  (GitHub CLI)"
    exit 1
fi

# ── Push ─────────────────────────────────────────────────────────────────
CURRENT_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo "main")"
echo "Pushing $CURRENT_BRANCH branch to GitHub..."
git push github "$CURRENT_BRANCH" --tags

echo ""
echo "Done! Code pushed to: $GITHUB_URL"
