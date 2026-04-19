#!/usr/bin/env bash
# SessionEnd hook — auto-distill via mempalace search + engram save, flush, sync.
# CRITICAL: Steps that save data run synchronously to prevent data loss on shell exit.
# Only compress/sync (non-critical) are backgrounded.
set +e
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

PROJECT_NAME="$(basename "${CLAUDE_PROJECT_DIR:-${PWD}}")"
ENGRAM_DB="${HOME}/.engram/${PROJECT_NAME}.db"
[ -f "$ENGRAM_DB" ] || ENGRAM_DB="${HOME}/.engram/engram.db"
MEMPALACE_PALACE="${HOME}/.mempalace/${PROJECT_NAME}"
[ -d "$MEMPALACE_PALACE" ] || MEMPALACE_PALACE="${HOME}/.mempalace/global"

# ---------- 1. Auto-distill: capture recent context as a session summary ----------
# CRITICAL: Run synchronously — this is the safety net that catches unsaved facts
if command -v mempalace >/dev/null 2>&1 && [ -d "$MEMPALACE_PALACE" ] && command -v engram >/dev/null 2>&1; then
  # Search for most recent session content (not just project name)
  CONTEXT=$(mempalace --palace "$MEMPALACE_PALACE" search "session summary key decisions" --results 5 2>/dev/null | head -c 16000)
  if [ -z "$CONTEXT" ] || [ ${#CONTEXT} -le 50 ]; then
    # Fallback: search by project name if session-specific search returns nothing
    CONTEXT=$(mempalace --palace "$MEMPALACE_PALACE" search "$PROJECT_NAME" --results 3 2>/dev/null | head -c 16000)
  fi
  if [ -n "$CONTEXT" ] && [ ${#CONTEXT} -gt 50 ]; then
    engram save \
      "Session summary (auto-distilled)" \
      "$CONTEXT" \
      --type discovery \
      --project "$PROJECT_NAME" \
      >/dev/null 2>&1
  fi
fi

# ---------- 2. End session in engram timeline ----------
# CRITICAL: Run synchronously — closes the session timeline properly
if command -v sqlite3 >/dev/null 2>&1 && [ -f "$ENGRAM_DB" ]; then
  # Use pattern matching for unique session IDs (hook-${PROJECT_NAME}-*)
  sqlite3 "$ENGRAM_DB" \
    "UPDATE sessions SET ended_at = datetime('now') WHERE id LIKE 'hook-${PROJECT_NAME}-%' AND ended_at IS NULL;" \
    >/dev/null 2>&1
fi

# ---------- 3. Compress mempalace index ----------
# Safe to background — non-critical optimization
if command -v mempalace >/dev/null 2>&1 && [ -d "$MEMPALACE_PALACE" ]; then
  nohup mempalace --palace "$MEMPALACE_PALACE" compress >/dev/null 2>&1 &
fi

# ---------- 4. Sync engram chunks ----------
# Safe to background — non-critical optimization
if command -v engram >/dev/null 2>&1; then
  nohup engram sync >/dev/null 2>&1 &
fi

exit 0
