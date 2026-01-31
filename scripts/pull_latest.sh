#!/bin/bash
set -euo pipefail

APP_ROOT="/opt/raspi-ai"
APP_DIR="$APP_ROOT/app"
VENV_DIR="$APP_ROOT/venv"
REPO_URL="${RASPI_AI_REPO_URL:-git@github.com:shuwa-kawamura-cont/raspi-ai.git}"
BRANCH="${RASPI_AI_BRANCH:-main}"
SERVICE_NAME="${RASPI_AI_SERVICE_NAME:-raspi-ai}"
LOCK_FILE="${RASPI_AI_LOCK_FILE:-/run/lock/raspi-ai-update.lock}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

umask 022

mkdir -p "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "Another update is running; exiting."
    exit 0
fi

mkdir -p "$APP_ROOT"

if [ ! -d "$APP_DIR/.git" ]; then
    log "Repository missing. Cloning $REPO_URL (branch: $BRANCH)."
    rm -rf "$APP_DIR"
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

ORIGIN_URL=$(git remote get-url origin)
if [ "$ORIGIN_URL" != "$REPO_URL" ]; then
    log "Updating origin remote URL to $REPO_URL"
    git remote set-url origin "$REPO_URL"
fi

log "Fetching latest commits..."
git fetch --prune origin "$BRANCH"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/"$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    log "Already up-to-date ($LOCAL)."
    exit 0
fi

log "Resetting working tree to origin/$BRANCH"
git reset --hard "origin/$BRANCH"

if [ -x "$VENV_DIR/bin/pip" ] && [ -f "requirements.txt" ]; then
    log "Installing Python dependencies..."
    "$VENV_DIR/bin/pip" install --upgrade -r requirements.txt
fi

log "Restarting $SERVICE_NAME service"
sudo systemctl restart "$SERVICE_NAME"
log "Update complete."
