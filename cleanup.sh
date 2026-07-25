#!/usr/bin/env bash
# Safe cleanup helper — moves large/env folders to a timestamped backup directory.
# Usage: ./cleanup.sh [--dry-run] [--include-build]

set -euo pipefail

DRY_RUN=0
INCLUDE_BUILD=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;; 
    --include-build) INCLUDE_BUILD=1 ;;
  esac
done

BACKUP_DIR="cleanup-backup-$(date +%Y%m%d-%H%M%S)"
echo "Backup dir: $BACKUP_DIR"

declare -a PATHS=(
  "backend/venv"
  "frontend/vaidya-vihar-frontend/node_modules"
  "node_modules"
  "backend/backend.log"
  "frontend/frontend-server.log"
  "frontend/vaidya-vihar-frontend/frontend.log"
  ".DS_Store"

)

if [ "$INCLUDE_BUILD" -eq 1 ]; then
  PATHS+=("frontend/vaidya-vihar-frontend/build")
fi

mkdir -p "$BACKUP_DIR"

for p in "${PATHS[@]}"; do
  if [ -e "$p" ]; then
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "Would move: $p -> $BACKUP_DIR/"
    else
      echo "Moving: $p -> $BACKUP_DIR/"
      mv "$p" "$BACKUP_DIR/" || echo "Failed to move $p"
    fi
  fi
done

echo "Done. To restore, move files back from $BACKUP_DIR into place."
