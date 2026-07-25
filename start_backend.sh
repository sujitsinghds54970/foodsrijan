#!/bin/bash

# Root-level backend launcher wrapper.
# Keeps existing backend startup behavior unchanged by delegating to backend/start_backend.sh.

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_SCRIPT="$ROOT_DIR/backend/start_backend.sh"

if [ ! -f "$BACKEND_SCRIPT" ]; then
  echo "Backend startup script not found: $BACKEND_SCRIPT"
  exit 1
fi

cd "$ROOT_DIR/backend"
exec bash "$BACKEND_SCRIPT"
