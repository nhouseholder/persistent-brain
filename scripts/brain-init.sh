#!/usr/bin/env bash
# brain-init.sh <project-path> — create a per-project engram DB,
# and drop .mcp.json + AGENTS.md into the project so any agent auto-wires correctly.
# Now includes the unified brain-router alongside the direct stores.
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
BRAIN_ROUTER="${REPO_DIR}/bin/brain-router"

command -v engram    >/dev/null 2>&1 || die "engram not installed — run ./install.sh first"

# Engram: create project DB (lazy; first save creates the file)
mkdir -p "$(dirname "$ENGRAM_DB")"
if [ ! -f "$ENGRAM_DB" ]; then
  ENGRAM_DB="$ENGRAM_DB" engram save "${PROJECT_NAME} brain initialised" "Project engram brain for ${PROJECT_NAME} created $(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null 2>&1 || true
fi
ok "engram DB: $ENGRAM_DB"

# Write project .mcp.json — brain-router (primary) + engram (fallback)
MCP_JSON="${PROJECT_PATH}/.mcp.json"
if [ -f "$MCP_JSON" ] && grep -q brain-router "$MCP_JSON" 2>/dev/null; then
  info "$MCP_JSON already wired with brain-router — leaving alone"
else
  cat > "$MCP_JSON" <<EOF
{
  "mcpServers": {
    "brain-router": {
      "command": "${BRAIN_ROUTER}",
      "env": {
        "BRAIN_PROJECT": "${PROJECT_NAME}",
        "ENGRAM_DB": "${ENGRAM_DB}"
      }
    },
    "engram": {
      "command": "engram",
      "args": ["mcp"],
      "env": { "ENGRAM_DB": "${ENGRAM_DB}" }
    }
  }
}
EOF
  ok "wrote $MCP_JSON (brain-router + engram)"
fi

# Write project AGENTS.md
AGENTS_MD="${PROJECT_PATH}/AGENTS.md"
if [ ! -f "$AGENTS_MD" ]; then
  cat > "$AGENTS_MD" <<EOF
# ${PROJECT_NAME} — Agent Instructions

## Memory

Two MCP servers are wired for this project via \`.mcp.json\`:

- **brain-router** — unified query/save interface (use this by default)
- **engram** — direct access to structured facts: \`${ENGRAM_DB}\`

### Quick reference

| Action | Tool |
|---|---|
| Search memories | \`brain_query\` |
| Save a fact | \`brain_save\` |
| Load session context | \`brain_context\` |
| Fix a wrong memory | \`brain_correct\` |
| Delete a memory | \`brain_forget\` |

### Session start protocol
1. Call \`brain_context\` before your first reply.
2. Treat returned memories as authoritative — don't re-ask.
3. Save structured facts with \`brain_save\` as you work.
4. Session-end hook auto-distills anything you missed.

Full rules: https://github.com/nhouseholder/persistent-brain/blob/main/config/AGENTS.md
EOF
  ok "wrote $AGENTS_MD"
else
  info "$AGENTS_MD exists — leaving alone (add memory section manually if needed)"
fi

echo
ok "Project '${PROJECT_NAME}' brain initialised."
echo "  Launch your agent from ${PROJECT_PATH} and brain-router will auto-load."
echo "  Inspect with: ./scripts/brain-inspect.sh ${PROJECT_NAME}"
