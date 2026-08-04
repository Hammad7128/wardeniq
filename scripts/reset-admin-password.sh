#!/usr/bin/env bash
# Reset the local admin password inside the running warden-app container.
#
# Usage:
#   ./scripts/reset-admin-password.sh                  (interactive prompt)
#   ./scripts/reset-admin-password.sh "NewPassword123" (non-interactive)
set -uo pipefail

NEW_PASSWORD="${1:-}"
USERNAME="${2:-admin}"

APP_CONTAINER="$(docker ps --filter name=warden-app -q | head -1)"
[ -z "$APP_CONTAINER" ] && APP_CONTAINER="$(docker ps --filter name=wardeniq -q | head -1)"

if [ -z "$APP_CONTAINER" ]; then
  echo "!! Could not find a running warden-app container. Is the stack running?"
  exit 1
fi

if [ -z "$NEW_PASSWORD" ]; then
  docker exec -it "$APP_CONTAINER" python reset_password.py "$USERNAME"
else
  docker exec -i "$APP_CONTAINER" python reset_password.py "$USERNAME" "$NEW_PASSWORD"
fi
