#!/usr/bin/env bash
# setup.sh — Fully automated, idempotent bootstrap for the local agentic dev loop.
#
# What it does:
#   1. Starts the Gitea container and waits for it to be healthy.
#   2. Creates three Gitea users: admin, developer-agent, reviewer-agent.
#   3. Generates API tokens for each user.
#   4. Creates the project repository on Gitea.
#   5. Adds agent users as repo collaborators.
#   6. Configures the local git remote ('origin') to point at Gitea.
#   7. Pushes existing code to Gitea.
#   8. Registers and starts the Gitea Actions CI runner.
#
# This script is idempotent — safe to run multiple times.
#
# Usage:
#   scripts/setup.sh
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — edit these if you like
# ---------------------------------------------------------------------------
ADMIN_USER="admin"
ADMIN_PASSWORD="admin1234"
ADMIN_EMAIL="admin@localhost"

DEV_AGENT_USER="developer-agent"
DEV_AGENT_PASSWORD="devagent1234"
DEV_AGENT_EMAIL="developer@localhost"

REVIEW_AGENT_USER="reviewer-agent"
REVIEW_AGENT_PASSWORD="reviewagent1234"
REVIEW_AGENT_EMAIL="reviewer@localhost"

GITEA_URL="http://localhost:3000"

# Repository name defaults to the project directory name
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
AGENTIC_DIR="$PROJECT_DIR/.agentic_dev"
REPO_NAME="${REPO_NAME:-$(basename "$PROJECT_DIR")}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { printf "\033[1;34m▸ %s\033[0m\n" "$*"; }
ok()    { printf "\033[1;32m✓ %s\033[0m\n" "$*"; }
warn()  { printf "\033[1;33m⚠ %s\033[0m\n" "$*"; }
fail()  { printf "\033[1;31m✗ %s\033[0m\n" "$*" >&2; exit 1; }

ensure_dir() { mkdir -p "$1"; }

# ---------------------------------------------------------------------------
# 0. Prerequisites
# ---------------------------------------------------------------------------
command -v docker  >/dev/null || fail "docker is not installed."
command -v curl    >/dev/null || fail "curl is not installed."
command -v python3 >/dev/null || fail "python3 is not installed."
command -v git     >/dev/null || fail "git is not installed."

ensure_dir "$AGENTIC_DIR"

# ---------------------------------------------------------------------------
# 1. Start Gitea
# ---------------------------------------------------------------------------
info "Starting Gitea container..."

# Create a placeholder runner.env so docker-compose doesn't fail on first run
if [ ! -f "$AGENTIC_DIR/runner.env" ]; then
    echo "GITEA_RUNNER_REGISTRATION_TOKEN=placeholder" > "$AGENTIC_DIR/runner.env"
fi

# Start only the gitea service (runner comes later after we have a real token)
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d gitea

info "Waiting for Gitea to become healthy..."
for i in $(seq 1 90); do
    if curl -sf "$GITEA_URL/api/v1/version" >/dev/null 2>&1; then
        ok "Gitea is ready."
        break
    fi
    if [ "$i" -eq 90 ]; then
        fail "Gitea did not start within 90 seconds."
    fi
    sleep 1
done

# ---------------------------------------------------------------------------
# 2. Create users
# ---------------------------------------------------------------------------
create_user() {
    local user="$1" pass="$2" email="$3" admin_flag="${4:-}"
    info "Creating user '$user'..."
    if docker exec -u git gitea gitea admin user create \
        --username "$user" \
        --password "$pass" \
        --email "$email" \
        $admin_flag \
        --must-change-password=false 2>/dev/null; then
        ok "User '$user' created."
    else
        warn "User '$user' may already exist — continuing."
    fi
}

create_user "$ADMIN_USER"        "$ADMIN_PASSWORD"        "$ADMIN_EMAIL"        "--admin"
create_user "$DEV_AGENT_USER"    "$DEV_AGENT_PASSWORD"    "$DEV_AGENT_EMAIL"    ""
create_user "$REVIEW_AGENT_USER" "$REVIEW_AGENT_PASSWORD" "$REVIEW_AGENT_EMAIL" ""

# ---------------------------------------------------------------------------
# 3. Generate API tokens
# ---------------------------------------------------------------------------
create_api_token() {
    local user="$1" pass="$2" name="$3"

    # Delete any existing token with the same name (ignore errors)
    curl -sf -X DELETE \
        "$GITEA_URL/api/v1/users/$user/tokens/$name" \
        -u "$user:$pass" >/dev/null 2>&1 || true

    # Create a new token
    local response
    response=$(curl -sf -X POST \
        "$GITEA_URL/api/v1/users/$user/tokens" \
        -u "$user:$pass" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"$name\", \"scopes\": [\"all\"]}")

    # Extract the token value (field name varies by Gitea version)
    python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
print(d.get('sha1') or d.get('token') or '')
" <<< "$response"
}

info "Generating API tokens..."
ADMIN_TOKEN=$(create_api_token "$ADMIN_USER"        "$ADMIN_PASSWORD"        "setup-token")
DEV_TOKEN=$(create_api_token   "$DEV_AGENT_USER"    "$DEV_AGENT_PASSWORD"    "agent-token")
REVIEW_TOKEN=$(create_api_token "$REVIEW_AGENT_USER" "$REVIEW_AGENT_PASSWORD" "agent-token")

[ -n "$ADMIN_TOKEN" ]  || fail "Failed to create admin token."
[ -n "$DEV_TOKEN" ]    || fail "Failed to create developer-agent token."
[ -n "$REVIEW_TOKEN" ] || fail "Failed to create reviewer-agent token."
ok "API tokens generated."

# Write tokens to a file that other scripts will source
cat > "$AGENTIC_DIR/tokens.env" <<EOF
# Generated by setup.sh — do not commit this file.
GITEA_URL=$GITEA_URL
REPO_NAME=$REPO_NAME
REPO_OWNER=$ADMIN_USER
ADMIN_TOKEN=$ADMIN_TOKEN
DEVELOPER_AGENT_TOKEN=$DEV_TOKEN
REVIEWER_AGENT_TOKEN=$REVIEW_TOKEN
EOF
ok "Tokens written to $AGENTIC_DIR/tokens.env"

# ---------------------------------------------------------------------------
# 4. Create repository on Gitea
# ---------------------------------------------------------------------------
info "Creating repository '$REPO_NAME' on Gitea..."
curl -sf -X POST "$GITEA_URL/api/v1/user/repos" \
    -H "Authorization: token $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$REPO_NAME\", \"default_branch\": \"main\", \"auto_init\": false}" \
    >/dev/null 2>&1 \
    && ok "Repository created." \
    || warn "Repository may already exist — continuing."

# ---------------------------------------------------------------------------
# 5. Add agents as collaborators
# ---------------------------------------------------------------------------
add_collaborator() {
    local user="$1"
    curl -sf -X PUT \
        "$GITEA_URL/api/v1/repos/$ADMIN_USER/$REPO_NAME/collaborators/$user" \
        -H "Authorization: token $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"permission": "write"}' >/dev/null 2>&1 || true
}

info "Adding agents as repository collaborators..."
add_collaborator "$DEV_AGENT_USER"
add_collaborator "$REVIEW_AGENT_USER"
ok "Collaborators configured."

# ---------------------------------------------------------------------------
# 6. Configure git remote and push
# ---------------------------------------------------------------------------
cd "$PROJECT_DIR"

GITEA_REMOTE="http://$ADMIN_USER:$ADMIN_TOKEN@localhost:3000/$ADMIN_USER/$REPO_NAME.git"

# Remove old origin if it exists, then set the new one
if git remote get-url origin &>/dev/null; then
    git remote set-url origin "$GITEA_REMOTE"
    info "Updated 'origin' remote to Gitea."
else
    git remote add origin "$GITEA_REMOTE"
    info "Added 'origin' remote pointing to Gitea."
fi

info "Pushing to Gitea..."
# Determine current branch
CURRENT_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo "main")"
git push -u origin "$CURRENT_BRANCH" 2>/dev/null \
    && ok "Code pushed to Gitea." \
    || warn "Push failed — you may need to commit first or resolve conflicts."

# ---------------------------------------------------------------------------
# 7. Register and start the CI runner
# ---------------------------------------------------------------------------
info "Generating runner registration token..."
RUNNER_TOKEN=$(docker exec -u git gitea gitea actions generate-runner-token 2>/dev/null || echo "")

if [ -n "$RUNNER_TOKEN" ]; then
    echo "GITEA_RUNNER_REGISTRATION_TOKEN=$RUNNER_TOKEN" > "$AGENTIC_DIR/runner.env"
    info "Starting CI runner..."
    docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d runner
    ok "CI runner started."
else
    warn "Could not generate runner token. CI runner not started."
    warn "You can re-run this script later or register the runner manually."
fi

# ---------------------------------------------------------------------------
# 8. Create default config
# ---------------------------------------------------------------------------
if [ ! -f "$AGENTIC_DIR/config.env" ]; then
    cat > "$AGENTIC_DIR/config.env" <<EOF
# User-editable configuration for the agentic dev loop.
# Test command used by the developer agent after implementing changes.
TEST_COMMAND=pytest
EOF
    ok "Default config created at $AGENTIC_DIR/config.env"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  Setup complete!"
echo "══════════════════════════════════════════════════════════════"
echo ""
echo "  Gitea UI:       $GITEA_URL"
echo "  Admin login:    $ADMIN_USER / $ADMIN_PASSWORD"
echo "  Repository:     $GITEA_URL/$ADMIN_USER/$REPO_NAME"
echo ""
echo "  Agent accounts:"
echo "    developer-agent   (token in .agentic_dev/tokens.env)"
echo "    reviewer-agent    (token in .agentic_dev/tokens.env)"
echo ""
echo "  Next steps:"
echo "    • Open $GITEA_URL in your browser"
echo "    • Run:  ./scripts/run_developer.py --task \"your task\""
echo "    • Run:  ./scripts/run_reviewer.py --pr 1"
echo "══════════════════════════════════════════════════════════════"
