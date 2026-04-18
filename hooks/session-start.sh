#!/usr/bin/env bash
# Claude Code SessionStart hook — emits a brain summary to stdout (injected into the agent's context).
# Non-blocking: fails silent so a missing binary never blocks a session.
set +e

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

PROJECT="${CLAUDE_PROJECT_DIR:-${PWD}}"
PROJECT_NAME="$(basename "$PROJECT")"
ENGRAM_PROJECT_DB="${HOME}/.engram/${PROJECT_NAME}.db"
ENGRAM_GLOBAL_DB="${HOME}/.engram/engram.db"
MEMPALACE_PROJECT="${HOME}/.mempalace/${PROJECT_NAME}"
MEMPALACE_GLOBAL="${HOME}/.mempalace/global"

PROJECT_COUNT=0
GLOBAL_COUNT=0
MEMPALACE_COUNT=0
LAST_SAVE="n/a"

if command -v engram >/dev/null 2>&1; then
  if [ -f "$ENGRAM_PROJECT_DB" ]; then
    PROJECT_COUNT=$(ENGRAM_DB="$ENGRAM_PROJECT_DB" engram stats 2>/dev/null | awk '/observations/ {print $NF; exit}' | tr -d ',')
  fi
  if [ -f "$ENGRAM_GLOBAL_DB" ]; then
    GLOBAL_COUNT=$(ENGRAM_DB="$ENGRAM_GLOBAL_DB" engram stats 2>/dev/null | awk '/observations/ {print $NF; exit}' | tr -d ',')
    LAST_SAVE=$(ENGRAM_DB="$ENGRAM_GLOBAL_DB" engram stats 2>/dev/null | awk '/last/ {print $NF; exit}')
  fi
fi

if command -v mempalace >/dev/null 2>&1; then
  PALACE="$MEMPALACE_PROJECT"
  [ -d "$PALACE" ] || PALACE="$MEMPALACE_GLOBAL"
  if [ -d "$PALACE" ]; then
    MEMPALACE_COUNT=$(mempalace --palace "$PALACE" status 2>/dev/null | awk '/sessions|drawers/ {print $NF; exit}' | tr -d ',')
  fi
fi

cat <<EOF
[persistent-brain]
  project:   ${PROJECT_NAME}
  engram:    ${PROJECT_COUNT:-0} project memories · ${GLOBAL_COUNT:-0} global · last save ${LAST_SAVE:-n/a}
  mempalace: ${MEMPALACE_COUNT:-0} sessions indexed — call mempalace.search when you need prior-conversation recall
  rules:     save structured facts to engram.mem_save · never double-write · corrections update immediately
EOF

exit 0
