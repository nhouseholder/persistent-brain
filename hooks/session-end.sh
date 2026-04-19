#!/usr/bin/env bash
# SessionEnd hook — auto-distill via mempalace search + engram save, flush, sync.
# All steps are best-effort and backgrounded.
set +e
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

PROJECT_NAME="$(basename "${CLAUDE_PROJECT_DIR:-${PWD}}")"
ENGRAM_DB="${HOME}/.engram/${PROJECT_NAME}.db"
[ -f "$ENGRAM_DB" ] || ENGRAM_DB="${HOME}/.engram/engram.db"
MEMPALACE_PALACE="${HOME}/.mempalace/${PROJECT_NAME}"
[ -d "$MEMPALACE_PALACE" ] || MEMPALACE_PALACE="${HOME}/.mempalace/global"

# ---------- 1. Auto-distill: capture recent context as a session summary ----------
if command -v mempalace >/dev/null 2>&1 && [ -d "$MEMPALACE_PALACE" ] && command -v engram >/dev/null 2>&1; then
  CONTEXT=$(mempalace --palace "$MEMPALACE_PALACE" search "$PROJECT_NAME" --results 3 2>/dev/null | head -c 16000)
  if [ -n "$CONTEXT" ] && [ ${#CONTEXT} -gt 50 ]; then
    engram save \
      "Session summary (auto-distilled)" \
      "$CONTEXT" \
      --type discovery \
      --project "$PROJECT_NAME" \
      >/dev/null 2>&1 &
  fi
fi

# ---------- 2. End session in engram timeline ----------
if command -v sqlite3 >/dev/null 2>&1 && [ -f "$ENGRAM_DB" ]; then
  SESSION_ID="hook-${PROJECT_NAME}"
  sqlite3 "$ENGRAM_DB" \
    "UPDATE sessions SET ended_at = datetime('now') WHERE id = '$SESSION_ID' AND ended_at IS NULL;" \
    >/dev/null 2>&1 &
fi

# ---------- 3. Compress mempalace index ----------
if command -v mempalace >/dev/null 2>&1 && [ -d "$MEMPALACE_PALACE" ]; then
  mempalace --palace "$MEMPALACE_PALACE" compress >/dev/null 2>&1 &
fi

# ---------- 4. Sync engram chunks ----------
if command -v engram >/dev/null 2>&1; then
  engram sync >/dev/null 2>&1 &
fi

exit 0
