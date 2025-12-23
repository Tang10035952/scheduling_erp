#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${APP_DIR:-/opt/scheduling_erp}
BRANCH=${BRANCH:-main}

if [ ! -d "$APP_DIR/.git" ]; then
  echo "Missing git repo at $APP_DIR" >&2
  exit 1
fi

cd "$APP_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not a git repo: $APP_DIR" >&2
  exit 1
fi

git fetch origin "$BRANCH"

git pull --ff-only origin "$BRANCH"

mkdir -p certbot/www

docker compose build

docker compose up -d

printf "Deploy complete: %s\n" "$(git rev-parse --short HEAD)"
