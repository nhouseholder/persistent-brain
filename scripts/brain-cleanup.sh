#!/usr/bin/env bash
# brain-cleanup.sh — soft-delete auto-distilled observations
# Usage: ./brain-cleanup.sh [--execute]
set -euo pipefail
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

DRY_RUN=true
if [ "${1:-}" = "--execute" ]; then
  DRY_RUN=false
fi

ENGRAM_DB="${HOME}/.engram/engram.db"

if [ ! -f "$ENGRAM_DB" ]; then
  echo "Error: engram DB not found at $ENGRAM_DB"
  exit 1
fi

COUNT=$(sqlite3 "$ENGRAM_DB" "
  SELECT COUNT(*) FROM observations
  WHERE type = 'discovery'
    AND title = 'Session summary (auto-distilled)'
    AND deleted_at IS NULL;
")

echo "Found $COUNT auto-distilled observations to soft-delete."

if [ "$DRY_RUN" = true ]; then
  echo "DRY RUN — no changes made. Use --execute to actually delete."
  exit 0
fi

sqlite3 "$ENGRAM_DB" "
  UPDATE observations
  SET deleted_at = datetime('now')
  WHERE type = 'discovery'
    AND title = 'Session summary (auto-distilled)'
    AND deleted_at IS NULL;
"

echo "Soft-deleted $COUNT observations."
