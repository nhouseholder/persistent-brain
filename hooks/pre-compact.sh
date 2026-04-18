#!/usr/bin/env bash
# Claude Code PreCompact hook — timestamp marker so the daily log reflects when
# context got compressed. Non-blocking, does not read transcripts.
set +e

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

PROJECT_NAME="$(basename "${CLAUDE_PROJECT_DIR:-${PWD}}")"
MEMPALACE_PROJECT="${HOME}/.mempalace/${PROJECT_NAME}"
MEMPALACE_GLOBAL="${HOME}/.mempalace/global"
PALACE="$MEMPALACE_PROJECT"
[ -d "$PALACE" ] || PALACE="$MEMPALACE_GLOBAL"

if command -v mempalace >/dev/null 2>&1 && [ -d "$PALACE" ]; then
  mempalace --palace "$PALACE" compress >/dev/null 2>&1 &
fi

exit 0
