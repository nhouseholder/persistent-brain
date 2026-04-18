#!/usr/bin/env bash
# Claude Code SessionEnd hook — flush mempalace, sync engram. Non-blocking.
set +e

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

PROJECT_NAME="$(basename "${CLAUDE_PROJECT_DIR:-${PWD}}")"
MEMPALACE_PROJECT="${HOME}/.mempalace/${PROJECT_NAME}"
MEMPALACE_GLOBAL="${HOME}/.mempalace/global"

PALACE="$MEMPALACE_PROJECT"
[ -d "$PALACE" ] || PALACE="$MEMPALACE_GLOBAL"

# Best-effort flush + index compression. Silent on failure.
if command -v mempalace >/dev/null 2>&1 && [ -d "$PALACE" ]; then
  mempalace --palace "$PALACE" compress >/dev/null 2>&1 &
fi

# Export engram chunks for git sync (if user has enabled sync)
if command -v engram >/dev/null 2>&1; then
  engram sync >/dev/null 2>&1 &
fi

exit 0
