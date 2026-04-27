#!/usr/bin/env bash
# unified-brain installer — engram + cgc + codecartographer + brain-router
# Single-command install: ./install.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLOBAL_ENGRAM_DB="${HOME}/.engram/engram.db"
GLOBAL_MEMPALACE="${HOME}/.mempalace/global"
UNIFIED_BRAIN_DIR="${HOME}/.unified-brain"
ENGRAM_VERSION_PIN="1.12.0"
MEMPALACE_VERSION_PIN="3.3.0"

ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }
info() { printf "\033[36m→\033[0m %s\n" "$*"; }
warn() { printf "\033[33m!\033[0m %s\n" "$*"; }
die()  { printf "\033[31m✗\033[0m %s\n" "$*" >&2; exit 1; }

# ---------- 0. Migration check ----------
if [ -d "${HOME}/.mempalace" ] && [ ! -d "${UNIFIED_BRAIN_DIR}" ]; then
  warn "Legacy persistent-brain detected (~/.mempalace exists)"
  info "This installer will migrate to ~/.unified-brain/ config layout"
  info "Your existing engram DBs and memories are preserved"
fi

# ---------- 1. OS check ----------
case "$(uname -s)" in
  Darwin|Linux) ok "OS: $(uname -s)" ;;
  *) die "Unsupported OS. macOS and Linux only (Windows → use WSL)." ;;
esac

# ---------- 2. Prereqs ----------
command -v brew >/dev/null 2>&1 || die "Homebrew required. Install from https://brew.sh"
command -v python3 >/dev/null 2>&1 || die "python3 required (3.10+)"
command -v node >/dev/null 2>&1 || die "Node.js required (18+). Install: brew install node"

NODE_VER=$(node --version | sed 's/v//')
NODE_MAJ=$(echo "$NODE_VER" | cut -d. -f1)
if [ "$NODE_MAJ" -lt 18 ]; then
  die "Node.js 18+ required, found $NODE_VER"
fi
ok "Node.js: $NODE_VER"

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
PY_MAJ=$(echo "$PY_VER" | cut -d. -f1)
PY_MIN=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJ" -lt 3 ] || { [ "$PY_MAJ" -eq 3 ] && [ "$PY_MIN" -lt 10 ]; }; then
  die "Python 3.10+ required, found $PY_VER"
fi
ok "Python: $PY_VER"

if ! command -v pipx >/dev/null 2>&1; then
  info "Installing pipx via Homebrew…"
  brew install pipx
  pipx ensurepath || true
  export PATH="$HOME/.local/bin:$PATH"
fi
ok "pipx: $(pipx --version)"

# Prefer uv for CGC, fallback to pipx
UV_AVAILABLE=false
if command -v uv >/dev/null 2>&1; then
  ok "uv: $(uv --version | head -1)"
  UV_AVAILABLE=true
else
  warn "uv not found — CGC will be installed via pipx (slower). Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# ---------- 3. Install engram ----------
if command -v engram >/dev/null 2>&1; then
  ok "engram already installed: $(engram version 2>/dev/null | head -1)"
else
  info "Installing engram via Homebrew tap…"
  brew tap gentleman-programming/tap
  brew install engram
  ok "engram installed: $(engram version 2>/dev/null | head -1)"
fi

# ---------- 4. Install mempalace ----------
export PATH="$HOME/.local/bin:$PATH"
if command -v mempalace >/dev/null 2>&1; then
  ok "mempalace already installed"
else
  info "Installing mempalace via pipx…"
  pipx install "mempalace==${MEMPALACE_VERSION_PIN}" || pipx install mempalace
  ok "mempalace installed"
fi

# ---------- 5. Install CGC (CodeGraphContext) ----------
if command -v cgc >/dev/null 2>&1; then
  ok "cgc (CodeGraphContext) already installed"
else
  info "Installing cgc via $(if $UV_AVAILABLE; then echo "uv"; else echo "pipx"; fi)…"
  if $UV_AVAILABLE; then
    uv tool install codegraphcontext || die "Failed to install cgc via uv"
  else
    pipx install codegraphcontext || die "Failed to install cgc via pipx"
  fi
  ok "cgc installed"
fi

# ---------- 6. Install CodeCartographer ----------
if command -v codecartographer >/dev/null 2>&1; then
  ok "codecartographer already installed: $(codecartographer --version 2>/dev/null || echo "version unknown")"
else
  info "Installing codecartographer…"
  # Check if local repo exists and is built
  LOCAL_CC="${HOME}/ProjectsHQ/codecartographer"
  if [ -f "${LOCAL_CC}/dist/cli/index.js" ]; then
    info "Local build found at ${LOCAL_CC} — linking globally…"
    (cd "$LOCAL_CC" && npm link)
    ok "codecartographer linked from ${LOCAL_CC}"
  else
    info "Installing codecartographer from npm…"
    npm install -g codecartographer || die "Failed to install codecartographer from npm"
    ok "codecartographer installed from npm"
  fi
fi

# ---------- 7. Symlink wrappers into PATH ----------
mkdir -p "$HOME/.local/bin"
ln -sf "$REPO_DIR/bin/mempalace-mcp" "$HOME/.local/bin/mempalace-mcp"
chmod +x "$REPO_DIR/bin/mempalace-mcp"
ok "mempalace-mcp wrapper linked to $HOME/.local/bin/mempalace-mcp"

ln -sf "$REPO_DIR/bin/brain-router" "$HOME/.local/bin/brain-router"
chmod +x "$REPO_DIR/bin/brain-router"
ok "brain-router wrapper linked to $HOME/.local/bin/brain-router"

# ---------- 8. Unified brain config ----------
mkdir -p "$UNIFIED_BRAIN_DIR"
if [ ! -f "${UNIFIED_BRAIN_DIR}/config.yaml" ]; then
  cat > "${UNIFIED_BRAIN_DIR}/config.yaml" <<EOF
# unified-brain global config
version: "0.5.0"
installed_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

stores:
  engram:
    db_dir: "${HOME}/.engram"
    global_db: "${HOME}/.engram/engram.db"
  cgc:
    graph_dir: "${HOME}/.codegraphcontext"
  codecartographer:
    reports_dir: "${HOME}/.codecartographer"

projects:
  # Add your projects here or use: brain init <path>
EOF
  ok "Created ${UNIFIED_BRAIN_DIR}/config.yaml"
else
  info "${UNIFIED_BRAIN_DIR}/config.yaml already exists — leaving alone"
fi

# ---------- 9. Init global brains ----------
mkdir -p "$(dirname "$GLOBAL_ENGRAM_DB")"
if [ ! -f "$GLOBAL_ENGRAM_DB" ]; then
  info "Initialising global engram DB at $GLOBAL_ENGRAM_DB"
  engram save "unified-brain installed" "Global engram brain created by unified-brain installer on $(date -u +%Y-%m-%dT%H:%M:%SZ)." >/dev/null 2>&1 || true
fi
ok "Global engram DB ready: $GLOBAL_ENGRAM_DB"

mkdir -p "$GLOBAL_MEMPALACE"
if [ ! -f "$GLOBAL_MEMPALACE/mempalace.yaml" ]; then
  info "Initialising global mempalace palace at $GLOBAL_MEMPALACE"
  mempalace init "$GLOBAL_MEMPALACE" --yes >/dev/null 2>&1 || true
fi
ok "Global mempalace palace ready: $GLOBAL_MEMPALACE"

# ---------- 10. MCP config wiring (non-destructive prompts) ----------
CONFIG_SNIPPET="$REPO_DIR/config/mcp-servers.json"
[ -f "$CONFIG_SNIPPET" ] || die "Missing $CONFIG_SNIPPET"

wire_opencode() {
  local target="${HOME}/.opencode/settings.json"
  if [ ! -f "$target" ]; then
    warn "$target not found — skipping OpenCode wiring. Run \`opencode\` once to create it, then rerun this script."
    return
  fi
  if grep -q '"brain-router"' "$target" 2>/dev/null; then
    ok "OpenCode: brain-router already wired in $target"
    return
  fi
  warn "OpenCode: add the mcpServers block from $CONFIG_SNIPPET to $target manually (we don't auto-edit your MCP config)."
}

wire_claude_code() {
  local target="${HOME}/.claude.json"
  if [ ! -f "$target" ]; then
    warn "$target not found — skipping Claude Code wiring. Run \`claude\` once to create it, then rerun this script."
    return
  fi
  if grep -q '"brain-router"' "$target" 2>/dev/null; then
    ok "Claude Code: brain-router already wired in $target"
    return
  fi
  warn "Claude Code: add the mcpServers block from $CONFIG_SNIPPET to $target manually (we don't auto-edit your MCP config)."
}

wire_codex() {
  local target="${HOME}/.codex/config.toml"
  if [ ! -f "$target" ]; then
    warn "$target not found — skipping Codex wiring."
    return
  fi
  if grep -q 'brain-router' "$target" 2>/dev/null; then
    ok "Codex: brain-router already wired in $target"
    return
  fi
  warn "Codex: see examples/codex-setup.md for the TOML snippet to add to $target"
}

wire_opencode
wire_claude_code
wire_codex

# ---------- 11. Hooks (OpenCode + Claude Code) ----------
for hooks_dir in "${HOME}/.opencode/hooks" "${HOME}/.claude/hooks"; do
  mkdir -p "$hooks_dir" 2>/dev/null || true
  for hook_file in session-start.sh session-end.sh pre-compact.sh pre-commit.sh; do
    HOOK_SRC="$REPO_DIR/hooks/$hook_file"
    HOOK_DEST="$hooks_dir/unified-brain-$hook_file"
    if [ -f "$HOOK_SRC" ]; then
      cp "$HOOK_SRC" "$HOOK_DEST"
      chmod +x "$HOOK_DEST"
      ok "Installed hook: $HOOK_DEST"
    fi
  done
done
warn "Register hooks in your agent config (see examples/):"
echo "   SessionStart → unified-brain-session-start.sh"
echo "   SessionEnd   → unified-brain-session-end.sh"
echo "   PreCompact   → unified-brain-pre-compact.sh"
echo "   PreCommit    → unified-brain-pre-commit.sh (optional, for git repos)"

# ---------- 12. Agent-agnostic rules ----------
info "Copy config/AGENTS.md into your agent's instruction file:"
echo "   • OpenCode     → append to ~/.opencode/OPENCODE.md"
echo "   • Claude Code  → append to ~/.claude/CLAUDE.md"
echo "   • Codex        → append to ~/.codex/AGENTS.md"
echo "   • Cursor       → drop into .cursor/rules/unified-brain.mdc"
echo "   • Qwen / Kimi  → see examples/ for each platform"

# ---------- Done ----------
echo
ok "unified-brain v0.5.0 installed."
echo
echo "Stores:"
echo "  • engram          → ~/.engram/"
echo "  • cgc             → ~/.codegraphcontext/"
echo "  • codecartographer → ~/.codecartographer/"
echo "  • config          → ~/.unified-brain/config.yaml"
echo
echo "Next steps:"
echo "  1. Wire MCP config for each agent you use (see examples/)"
echo "  2. For each project:  ./scripts/brain-init.sh <project-path>"
echo "  3. Verify with:       ./scripts/brain-status.sh"
echo "  4. Inspect memories:  ./scripts/brain-inspect.sh <project-name>"
echo "  5. Search code:       brain_codebase_search from any agent"
