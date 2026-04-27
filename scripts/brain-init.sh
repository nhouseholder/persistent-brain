#!/usr/bin/env bash
# brain-init.sh <project-path> — create a per-project engram DB,
# index the codebase with CGC, generate GRAPH_REPORT.md with CodeCartographer,
# and drop .mcp.json + AGENTS.md into the project so any agent auto-wires correctly.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }
info() { printf "\033[36m→\033[0m %s\n" "$*"; }
warn() { printf "\033[33m!\033[0m %s\n" "$*"; }
die()  { printf "\033[31m✗\033[0m %s\n" "$*" >&2; exit 1; }

PROJECT_PATH="${1:-}"
[ -n "$PROJECT_PATH" ] || die "Usage: brain-init.sh <project-path>"
[ -d "$PROJECT_PATH" ] || die "Directory does not exist: $PROJECT_PATH"

PROJECT_PATH="$(cd "$PROJECT_PATH" && pwd)"
PROJECT_NAME="$(basename "$PROJECT_PATH")"

ENGRAM_DB="${HOME}/.engram/${PROJECT_NAME}.db"
BRAIN_ROUTER="${REPO_DIR}/bin/brain-router"
GRAPH_REPORT="${PROJECT_PATH}/.codecartographer/GRAPH_REPORT.md"

command -v engram    >/dev/null 2>&1 || die "engram not installed — run ./install.sh first"

# ---------- Engram: create project DB ----------
mkdir -p "$(dirname "$ENGRAM_DB")"
if [ ! -f "$ENGRAM_DB" ]; then
  ENGRAM_DB="$ENGRAM_DB" engram save "${PROJECT_NAME} brain initialised" "Project engram brain for ${PROJECT_NAME} created $(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null 2>&1 || true
fi
ok "engram DB: $ENGRAM_DB"

# ---------- CGC: index codebase ----------
if command -v cgc >/dev/null 2>&1; then
  info "Indexing ${PROJECT_NAME} with CGC…"
  cgc add_code_to_graph "$PROJECT_PATH" --is-dependency=false 2>/dev/null || warn "CGC indexing failed (non-fatal)"
  ok "CGC index: ${PROJECT_NAME}"
else
  warn "cgc not installed — skipping codebase indexing. Run ./install.sh"
fi

# ---------- CodeCartographer: generate GRAPH_REPORT.md ----------
if command -v codecartographer >/dev/null 2>&1; then
  info "Generating GRAPH_REPORT.md for ${PROJECT_NAME}…"
  codecartographer diagram "$PROJECT_PATH" --backend memory 2>/dev/null || warn "CodeCartographer diagram failed (non-fatal)"
  if [ -f "$GRAPH_REPORT" ]; then
    ok "GRAPH_REPORT.md: $GRAPH_REPORT"
  else
    warn "GRAPH_REPORT.md not generated — check codecartographer output"
  fi
else
  warn "codecartographer not installed — skipping diagram generation. Run ./install.sh"
fi

# ---------- Write project .mcp.json ----------
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

# ---------- Write project AGENTS.md ----------
AGENTS_MD="${PROJECT_PATH}/AGENTS.md"
if [ ! -f "$AGENTS_MD" ]; then
  cat > "$AGENTS_MD" <<EOF
# ${PROJECT_NAME} — Agent Instructions

## Memory

Two MCP servers are wired for this project via \`.mcp.json\`:

- **brain-router** — unified interface (use this by default)
- **engram** — direct access to structured facts: \`${ENGRAM_DB}\`

### Quick reference

| Action | Tool |
|---|---|
| Search memories | \`brain_query\` |
| Save a fact | \`brain_save\` |
| Load session context | \`brain_context\` |
| Fix a wrong memory | \`brain_correct\` |
| Delete a memory | \`brain_forget\` |
| Index codebase | \`brain_codebase_index\` |
| Search code | \`brain_codebase_search\` |
| Validate observation | \`brain_validate\` |

### Session start protocol
1. Call \`brain_context\` before your first reply.
2. Call \`brain_codebase_index --check\` to load or generate GRAPH_REPORT.md.
3. Treat returned memories as authoritative — don't re-ask.
4. Save structured facts with \`brain_save\` as you work.
5. Use \`brain_validate\` before saving to ensure Compiled Truth + Auto-Links.
6. Session-end hook auto-distils anything you missed.

Full rules: https://github.com/nhouseholder/persistent-brain/blob/main/config/AGENTS.md
EOF
  ok "wrote $AGENTS_MD"
else
  info "$AGENTS_MD exists — leaving alone (add memory section manually if needed)"
fi

# ---------- Write .unified-brainignore ----------
IGNORE_FILE="${PROJECT_PATH}/.unified-brainignore"
if [ ! -f "$IGNORE_FILE" ]; then
  cat > "$IGNORE_FILE" <<EOF
# Files/directories to exclude from CGC indexing and CodeCartographer analysis
node_modules/
dist/
build/
.coverage/
*.min.js
*.min.css
EOF
  ok "wrote $IGNORE_FILE"
fi

echo
ok "Project '${PROJECT_NAME}' brain initialised."
echo "  Engram DB:      ${ENGRAM_DB}"
[ -f "$GRAPH_REPORT" ] && echo "  Graph report:   ${GRAPH_REPORT}"
echo "  Launch agent from ${PROJECT_PATH} and brain-router will auto-load."
echo "  Inspect with:   ./scripts/brain-inspect.sh ${PROJECT_NAME}"
