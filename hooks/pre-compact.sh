#!/usr/bin/env bash
# Claude Code PreCompact hook — engram checkpoint before context compaction.
# Non-blocking, uses nohup to survive shell exit.
set +e

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

PROJECT_NAME="$(basename "${CLAUDE_PROJECT_DIR:-${PWD}}")"
ENGRAM_DB="${HOME}/.engram/${PROJECT_NAME}.db"
[ -f "$ENGRAM_DB" ] || ENGRAM_DB="${HOME}/.engram/engram.db"

# Sync engram before compaction (non-critical, backgrounded)
if command -v engram >/dev/null 2>&1; then
  nohup engram sync >/dev/null 2>&1 &
fi

exit 0
