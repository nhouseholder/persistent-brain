#!/usr/bin/env bash
# SessionStart hook — register session + emit brain summary to agent context.
set +e
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

PROJECT="${CLAUDE_PROJECT_DIR:-${PWD}}"
PROJECT_NAME="$(basename "$PROJECT")"
ENGRAM_DB="${HOME}/.engram/${PROJECT_NAME}.db"
[ -f "$ENGRAM_DB" ] || ENGRAM_DB="${HOME}/.engram/engram.db"
MEMPALACE_PALACE="${HOME}/.mempalace/${PROJECT_NAME}"
[ -d "$MEMPALACE_PALACE" ] || MEMPALACE_PALACE="${HOME}/.mempalace/global"

PROJECT_COUNT=0; GLOBAL_COUNT=0; MEMPALACE_COUNT=0; LAST_SAVE="n/a"

# Register session start via direct SQLite (engram has no session-start CLI)
if command -v sqlite3 >/dev/null 2>&1 && [ -f "$ENGRAM_DB" ]; then
  SESSION_ID="hook-${PROJECT_NAME}"
  sqlite3 "$ENGRAM_DB" \
    "INSERT OR IGNORE INTO sessions (id, project, directory, started_at) VALUES ('$SESSION_ID', '$PROJECT_NAME', '$PROJECT', datetime('now'));" \
    >/dev/null 2>&1 &
fi

if command -v engram >/dev/null 2>&1; then
  if [ -f "${HOME}/.engram/${PROJECT_NAME}.db" ]; then
    PROJECT_COUNT=$(ENGRAM_DB="${HOME}/.engram/${PROJECT_NAME}.db" engram stats 2>/dev/null | awk '/Observations/ {print $NF; exit}' | tr -d ',')
  fi
  GLOBAL_DB="${HOME}/.engram/engram.db"
  if [ -f "$GLOBAL_DB" ]; then
    GLOBAL_COUNT=$(ENGRAM_DB="$GLOBAL_DB" engram stats 2>/dev/null | awk '/Observations/ {print $NF; exit}' | tr -d ',')
  fi
fi

if command -v mempalace >/dev/null 2>&1 && [ -d "$MEMPALACE_PALACE" ]; then
  MEMPALACE_COUNT=$(mempalace --palace "$MEMPALACE_PALACE" status 2>/dev/null | awk '/drawer|session|file/ {sum+=$NF} END {print sum}' | tr -d ',')
fi

cat <<EOF
[persistent-brain]
  project:   ${PROJECT_NAME}
  engram:    ${PROJECT_COUNT:-0} project memories · ${GLOBAL_COUNT:-0} global
  mempalace: ${MEMPALACE_COUNT:-0} items indexed
  router:    use brain_query for all lookups · brain_save for facts · brain_context on session start
EOF

exit 0
