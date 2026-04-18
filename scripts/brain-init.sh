#!/usr/bin/env bash
# brain-init.sh <project-path> — create a per-project engram DB + mempalace palace,
# and drop .mcp.json + AGENTS.md into the project so any agent auto-wires correctly.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }
info() { printf "\033[36m→\033[0m %s\n" "$*"; }
die()  { printf "\033[31m✗\033[0m %s\n" "$*" >&2; exit 1; }

PROJECT_PATH="${1:-}"
[ -n "$PROJECT_PATH" ] || die "Usage: brain-init.sh <project-path>"
[ -d "$PROJECT_PATH" ] || die "Directory does not exist: $PROJECT_PATH"

PROJECT_PATH="$(cd "$PROJECT_PATH" && pwd)"
PROJECT_NAME="$(basename "$PROJECT_PATH")"

ENGRAM_DB="${HOME}/.engram/${PROJECT_NAME}.db"
MEMPALACE_DIR="${HOME}/.mempalace/${PROJECT_NAME}"

command -v engram    >/dev/null 2>&1 || die "engram not installed — run ./install.sh first"
command -v mempalace >/dev/null 2>&1 || die "mempalace not installed — run ./install.sh first"

# Engram: create project DB (lazy; first save creates the file)
mkdir -p "$(dirname "$ENGRAM_DB")"
if [ ! -f "$ENGRAM_DB" ]; then
  ENGRAM_DB="$ENGRAM_DB" engram save "${PROJECT_NAME} brain initialised" "Project engram brain for ${PROJECT_NAME} created $(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null 2>&1 || true
fi
ok "engram DB: $ENGRAM_DB"

# Mempalace: create project palace
mkdir -p "$MEMPALACE_DIR"
if [ ! -f "$MEMPALACE_DIR/mempalace.yaml" ]; then
  mempalace init "$MEMPALACE_DIR" --yes >/dev/null 2>&1 \
    || die "mempalace init failed for $MEMPALACE_DIR"
fi
ok "mempalace palace: $MEMPALACE_DIR"

# Write project .mcp.json — pointed at the project brain via env
MCP_JSON="${PROJECT_PATH}/.mcp.json"
if [ -f "$MCP_JSON" ] && grep -q engram "$MCP_JSON" 2>/dev/null; then
  info "$MCP_JSON already wired — leaving alone"
else
  cat > "$MCP_JSON" <<EOF
{
  "mcpServers": {
    "engram": {
      "command": "engram",
      "args": ["mcp"],
      "env": { "ENGRAM_DB": "${ENGRAM_DB}" }
    },
    "mempalace": {
      "command": "mempalace-mcp",
      "env": { "MEMPALACE_PALACE": "${MEMPALACE_DIR}" }
    }
  }
}
EOF
  ok "wrote $MCP_JSON"
fi

# Write project AGENTS.md — project-scoped addendum to the global routing rules
AGENTS_MD="${PROJECT_PATH}/AGENTS.md"
if [ ! -f "$AGENTS_MD" ]; then
  cat > "$AGENTS_MD" <<EOF
# ${PROJECT_NAME} — Agent Instructions

## Memory

Two MCP servers are wired for this project via \`.mcp.json\`:

- **engram** — project DB: \`${ENGRAM_DB}\`
- **mempalace** — project palace: \`${MEMPALACE_DIR}\`

Follow the routing rules in the global persistent-brain config:
https://github.com/nhouseholder/persistent-brain/blob/main/config/AGENTS.md

Key rules:
1. Save structured facts (decisions, preferences, architecture, fixes) to \`engram.mem_save\`.
2. Search prior conversations with \`mempalace.search\`.
3. On session start, call \`engram.mem_context\` for project + global brain.
4. Never double-write. Corrections update engram immediately.
EOF
  ok "wrote $AGENTS_MD"
else
  info "$AGENTS_MD exists — leaving alone (add memory section manually if needed)"
fi

echo
ok "Project '${PROJECT_NAME}' brain initialised."
echo "  Launch your agent from ${PROJECT_PATH} and both MCP servers will auto-load."
