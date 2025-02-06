#!/usr/bin/env bash

set -euo pipefail

THEME_DIR="theme"
DEFAULT_THEME_REPO="https://github.com/informed-governance-project/default-theme.git"
REPO_URL=${THEME_REPO_URL:-$DEFAULT_THEME_REPO}
BRANCH=${THEME_VERSION:-}

if [[ -z "$REPO_URL" ]]; then
    echo "ERROR: THEME_REPO_URL is not set." >&2
    exit 1
fi

if [[ -z "$BRANCH" ]]; then
    echo "Fetching latest release from $REPO_URL..."
    REPO_OWNER=$(echo "$REPO_URL" | sed 's/.*github.com\/\([^\/]*\)\/\([^\/]*\).*/\1/')
    REPO_NAME=$(echo "$REPO_URL" | sed 's/.*github.com\/\([^\/]*\)\/\([^\/]*\).*/\2/')
    REPO_NAME=${REPO_NAME%.git}
    RELEASE_TAG=$(curl -s "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/latest" | \
    sed -n 's/.*"tag_name": "\([^"]*\)".*/\1/p')

    if [[ -z "$RELEASE_TAG" || "$RELEASE_TAG" == "null" ]]; then
        echo "ERROR: Could not fetch the latest release tag." >&2
        exit 2
    fi

    echo "Using theme release: $RELEASE_TAG"
    BRANCH="$RELEASE_TAG"
else
    echo "Using theme release: $BRANCH"
fi

if [[ -d "$THEME_DIR" ]]; then
    echo "Removing existing theme directory..."
    rm -rf "$THEME_DIR"
fi

echo "Cloning theme from $REPO_URL (version: $BRANCH)..."
if git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$THEME_DIR"; then
    echo "Theme cloned successfully."
else
    echo "ERROR: Failed to clone theme." >&2
    exit 3
fi

python manage.py collectstatic --noinput > /dev/null
python manage.py migrate
python manage.py compilemessages

exec gunicorn governanceplatform.wsgi --workers "$APP_WORKERS" --bind "$APP_BIND_ADDRESS:$APP_PORT"
