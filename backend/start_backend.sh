#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$SCRIPT_DIR"

if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
  . "$REPO_ROOT/.venv/bin/activate"
elif [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
  . "$SCRIPT_DIR/.venv/bin/activate"
elif [ -f "$REPO_ROOT/venv/bin/activate" ]; then
  . "$REPO_ROOT/venv/bin/activate"
elif [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
  . "$SCRIPT_DIR/venv/bin/activate"
fi

export PYTHONUNBUFFERED=1
export PORT="${PORT:-8000}"

python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level info 2>&1 | tee backend.log
