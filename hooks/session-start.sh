#!/usr/bin/env bash
# SessionStart hook — register session + emit brain summary to agent context.
set +e
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

PROJECT="${OPENCODE_PROJECT_DIR:-${PWD}}"
PROJECT_NAME="$(basename "$PROJECT")"

# Resolve canonical project name from project-map.json
CANONICAL_NAME="$PROJECT_NAME"
if [ -f "${HOME}/.engram/project-map.json" ] && command -v python3 >/dev/null 2>&1; then
  CANONICAL_NAME=$(python3 -c "
import json, sys
with open('${HOME}/.engram/project-map.json') as f:
  m = json.load(f)
print(m.get('${PROJECT_NAME}', '${PROJECT_NAME}'))
" 2>/dev/null)
fi

ENGRAM_DB="${HOME}/.engram/${PROJECT_NAME}.db"
[ -f "$ENGRAM_DB" ] || ENGRAM_DB="${HOME}/.engram/engram.db"

PROJECT_COUNT=0; GLOBAL_COUNT=0; LAST_SAVE="n/a"

# Register session start via direct SQLite (engram has no session-start CLI)
# CRITICAL: Use unique session ID per session — static IDs collapse all sessions into one
if command -v sqlite3 >/dev/null 2>&1 && [ -f "$ENGRAM_DB" ]; then
  SESSION_ID="hook-${PROJECT_NAME}-$(date +%s)-$$"
  sqlite3 "$ENGRAM_DB" \
    "INSERT INTO sessions (id, project, directory, started_at) VALUES ('$SESSION_ID', '$PROJECT_NAME', '$PROJECT', datetime('now'));" \
    >/dev/null 2>&1
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

cat <<EOF
[persistent-brain]
  project:   ${PROJECT_NAME} (canonical: ${CANONICAL_NAME})
  engram:    ${PROJECT_COUNT:-0} project memories · ${GLOBAL_COUNT:-0} global
  router:    use brain_query for all lookups · brain_save for facts · brain_context on session start
EOF

exit 0
