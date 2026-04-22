#!/usr/bin/env bash
# SessionEnd hook — auto-distill via engram context, flush, sync.
# CRITICAL: Steps that save data run synchronously to prevent data loss on shell exit.
# Only sync (non-critical) is backgrounded.
set +e
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

PROJECT_NAME="$(basename "${OPENCODE_PROJECT_DIR:-${PWD}}")"
ENGRAM_DB="${HOME}/.engram/${PROJECT_NAME}.db"
[ -f "$ENGRAM_DB" ] || ENGRAM_DB="${HOME}/.engram/engram.db"

# ---------- 1. Auto-distill: DISABLED ----------
# Auto-distill disabled — see docs/specs/2026-04-22-memory-improvement-plan.md
# Agents must explicitly save structured facts via brain_save.
# The session-end hook only closes the session timeline and syncs.

# ---------- 2. End session in engram timeline ----------
# CRITICAL: Run synchronously — closes the session timeline properly
if command -v sqlite3 >/dev/null 2>&1 && [ -f "$ENGRAM_DB" ]; then
  # Use pattern matching for unique session IDs (hook-${PROJECT_NAME}-*)
  sqlite3 "$ENGRAM_DB" \
    "UPDATE sessions SET ended_at = datetime('now') WHERE id LIKE 'hook-${PROJECT_NAME}-%' AND ended_at IS NULL;" \
    >/dev/null 2>&1
fi

# ---------- 3. Sync engram chunks ----------
# Safe to background — non-critical optimization
if command -v engram >/dev/null 2>&1; then
  nohup engram sync >/dev/null 2>&1 &
fi

exit 0
