#!/usr/bin/env bash
# push_to_github.sh — Push the local main branch to your personal GitHub repo.
#
# Usage:
#   gitea-skills push-to-github [GITHUB_REPO_URL]
#
# If the 'github' remote doesn't exist yet, pass the URL as an argument
# (e.g. git@github.com:user/repo.git) and this script will add it for you.
set -euo pipefail

# Resolve the gitea_skills package directory for helper scripts
PACKAGE_DIR="$(python3 -c "import gitea_skills; print(gitea_skills.get_plugin_path())")"

# ── Check prerequisites ──────────────────────────────────────────────────
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "ERROR: Not inside a git repository." >&2
    exit 1
fi

# ── Parse arguments ──────────────────────────────────────────────────────
TOKEN_OVERRIDE=""
GITHUB_URL_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --token)
            if [ -n "${2:-}" ]; then
                TOKEN_OVERRIDE="$2"
                shift 2
            else
                echo "ERROR: --token requires a value" >&2
                exit 1
            fi
            ;;
        *)
            if [ -z "$GITHUB_URL_ARG" ]; then
                GITHUB_URL_ARG="$1"
                shift
            else
                echo "ERROR: Unknown argument: $1" >&2
                exit 1
            fi
            ;;
    esac
done

if [ -n "$TOKEN_OVERRIDE" ]; then
    export GITHUB_TOKEN="$TOKEN_OVERRIDE"
fi

# ── Ensure 'github' remote exists ────────────────────────────────────────
if ! git remote get-url github &>/dev/null; then
    if [ -n "$GITHUB_URL_ARG" ]; then
        echo "Adding 'github' remote → $GITHUB_URL_ARG"
        git remote add github "$GITHUB_URL_ARG"
    else
        echo "ERROR: No 'github' remote configured."
        echo ""
        echo "Add it by running one of:"
        echo "  gitea-skills push-to-github git@github.com:<user>/<repo>.git   # SSH"
        echo "  gitea-skills push-to-github https://github.com/<user>/<repo>.git  # HTTPS"
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
    python3 "$PACKAGE_DIR/github_auth.py"
fi

# ── Verify authentication ───────────────────────────────────────────────
echo "Verifying GitHub authentication..."

PUSH_CMD=("git")
# If HTTPS, use our custom credential helper
if [[ "$GITHUB_URL" =~ ^https:// ]]; then
    PUSH_CMD+=("-c" "credential.helper=$PACKAGE_DIR/github_credential_helper.py")
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

# Check if the base branch exists on the remote repository
REMOTE_HEADS="$( "${PUSH_CMD[@]}" ls-remote --heads github 2>/dev/null || true )"

if [ -z "$REMOTE_HEADS" ] || ! echo "$REMOTE_HEADS" | grep -q "refs/heads/$CURRENT_BRANCH"; then
    echo "Remote repository is empty or missing the '$CURRENT_BRANCH' branch."
    echo "Performing a direct push to initialize '$CURRENT_BRANCH' on GitHub..."
    "${PUSH_CMD[@]}" push -u github "$CURRENT_BRANCH"
    echo "Done! Initial branch '$CURRENT_BRANCH' created on GitHub. Skipping Pull Request creation."
    exit 0
fi

echo "Pushing local $CURRENT_BRANCH branch to GitHub remote as $SYNC_BRANCH..."
"${PUSH_CMD[@]}" push -f github "$CURRENT_BRANCH:refs/heads/$SYNC_BRANCH"

echo ""
echo "Creating Pull Request on GitHub..."
python3 "$PACKAGE_DIR/github_api.py" \
    --head "$SYNC_BRANCH" \
    --base "$CURRENT_BRANCH" \
    --title "Sync $CURRENT_BRANCH from Gitea"

echo ""
echo "Done! Code pushed and Pull Request processed for: $GITHUB_URL"
