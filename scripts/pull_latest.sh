#!/bin/bash
set -euo pipefail

APP_ROOT="/opt/raspi-ai"
APP_DIR="$APP_ROOT/app"
VENV_DIR="$APP_ROOT/venv"
REPO_URL="${RASPI_AI_REPO_URL:-git@github.com:shuwa-kawamura-cont/raspi-ai.git}"
BRANCH="${RASPI_AI_BRANCH:-main}"
SERVICE_NAME="${RASPI_AI_SERVICE_NAME:-raspi-ai}"
LOCK_FILE="${RASPI_AI_LOCK_FILE:-/run/lock/raspi-ai-update.lock}"
HOSTNAME=$(hostname)

SLACK_WEBHOOK="${RASPI_AI_SLACK_WEBHOOK:-}"
SLACK_USERNAME="${RASPI_AI_SLACK_USERNAME:-raspi-ai deployer}"
SLACK_ICON="${RASPI_AI_SLACK_ICON:-:satellite:}"
SLACK_CHANNEL="${RASPI_AI_SLACK_CHANNEL:-}"
SUCCESS_EMOJI="${RASPI_AI_SLACK_SUCCESS_EMOJI:-:white_check_mark:}"
FAILURE_EMOJI="${RASPI_AI_SLACK_FAILURE_EMOJI:-:x:}"
SLACK_NOTIFY_ON_SUCCESS="${RASPI_AI_SLACK_NOTIFY_ON_SUCCESS:-true}"
SLACK_NOTIFY_ON_FAILURE="${RASPI_AI_SLACK_NOTIFY_ON_FAILURE:-true}"
SLACK_NOTIFY_ON_NOOP="${RASPI_AI_SLACK_NOTIFY_ON_NOOP:-false}"

CURRENT_STEP="initializing"

send_slack() {
    [ -z "$SLACK_WEBHOOK" ] && return 0
    local text="$1"

    if ! python3 - "$SLACK_WEBHOOK" "$text" "$SLACK_USERNAME" "$SLACK_ICON" "$SLACK_CHANNEL" <<'PY'; then
        echo "Failed to send Slack notification" >&2
    fi
import json
import sys
import urllib.request

webhook, text, username, icon, channel = sys.argv[1:6]
payload = {"text": text}
if username:
    payload["username"] = username
if icon:
    if icon.startswith(":") and icon.endswith(":"):
        payload["icon_emoji"] = icon
    else:
        payload["icon_url"] = icon
if channel:
    payload["channel"] = channel

data = json.dumps(payload).encode("utf-8")
request = urllib.request.Request(
    webhook,
    data=data,
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(request, timeout=10) as resp:
    resp.read()
PY
    fi
}

notify_success() {
    [ "$SLACK_NOTIFY_ON_SUCCESS" = "true" ] || return 0
    local commit="$1"
    send_slack "$SUCCESS_EMOJI [$HOSTNAME] raspi-ai updated to \`$commit\` on *$BRANCH*."
}

notify_noop() {
    [ "$SLACK_NOTIFY_ON_NOOP" = "true" ] || return 0
    local commit="$1"
    send_slack "$SUCCESS_EMOJI [$HOSTNAME] raspi-ai already up-to-date (\`$commit\`)."
}

notify_failure() {
    [ "$SLACK_NOTIFY_ON_FAILURE" = "true" ] || return 0
    local exit_code="$1"
    local step="$2"
    send_slack "$FAILURE_EMOJI [$HOSTNAME] raspi-ai update failed during *$step* (exit $exit_code)."
}

failure_handler() {
    local exit_code=$?
    trap - ERR
    log "Update failed (step: $CURRENT_STEP, exit: $exit_code)"
    notify_failure "$exit_code" "$CURRENT_STEP"
    exit "$exit_code"
}
trap failure_handler ERR


log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

umask 022

CURRENT_STEP="acquiring lock"
mkdir -p "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "Another update is running; exiting."
    exit 0
fi

mkdir -p "$APP_ROOT"

CURRENT_STEP="ensuring repository"
if [ ! -d "$APP_DIR/.git" ]; then
    log "Repository missing. Cloning $REPO_URL (branch: $BRANCH)."
    rm -rf "$APP_DIR"
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

CURRENT_STEP="configuring remote"
ORIGIN_URL=$(git remote get-url origin)
if [ "$ORIGIN_URL" != "$REPO_URL" ]; then
    log "Updating origin remote URL to $REPO_URL"
    git remote set-url origin "$REPO_URL"
fi

CURRENT_STEP="fetching latest commits"
log "Fetching latest commits..."
git fetch --prune origin "$BRANCH"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/"$BRANCH")
SHORT_LOCAL=$(git rev-parse --short HEAD)
SHORT_REMOTE=$(git rev-parse --short origin/"$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    log "Already up-to-date ($LOCAL)."
    notify_noop "$SHORT_LOCAL"
    exit 0
fi

CURRENT_STEP="resetting working tree"
log "Resetting working tree to origin/$BRANCH"
git reset --hard "origin/$BRANCH"
SHORT_REMOTE=$(git rev-parse --short origin/"$BRANCH")

if [ -x "$VENV_DIR/bin/pip" ] && [ -f "requirements.txt" ]; then
    CURRENT_STEP="installing python dependencies"
    log "Installing Python dependencies..."
    "$VENV_DIR/bin/pip" install --upgrade -r requirements.txt
fi

CURRENT_STEP="restarting service"
log "Restarting $SERVICE_NAME service"
sudo systemctl restart "$SERVICE_NAME"
CURRENT_STEP="complete"
log "Update complete."
notify_success "$SHORT_REMOTE"
