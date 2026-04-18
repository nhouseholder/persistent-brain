#!/usr/bin/env bash
# persistent-brain installer — engram + mempalace + MCP wiring
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLOBAL_ENGRAM_DB="${HOME}/.engram/engram.db"
GLOBAL_MEMPALACE="${HOME}/.mempalace/global"
ENGRAM_VERSION_PIN="1.12.0"
MEMPALACE_VERSION_PIN="3.3.0"

ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }
info() { printf "\033[36m→\033[0m %s\n" "$*"; }
warn() { printf "\033[33m!\033[0m %s\n" "$*"; }
die()  { printf "\033[31m✗\033[0m %s\n" "$*" >&2; exit 1; }

# ---------- 1. OS check ----------
case "$(uname -s)" in
  Darwin|Linux) ok "OS: $(uname -s)" ;;
  *) die "Unsupported OS. macOS and Linux only (Windows → use WSL)." ;;
esac

# ---------- 2. Prereqs ----------
command -v brew >/dev/null 2>&1 || die "Homebrew required. Install from https://brew.sh"
command -v python3 >/dev/null 2>&1 || die "python3 required (3.10+)"

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

# ---------- 5. Symlink the mempalace-mcp wrapper into PATH ----------
mkdir -p "$HOME/.local/bin"
ln -sf "$REPO_DIR/bin/mempalace-mcp" "$HOME/.local/bin/mempalace-mcp"
chmod +x "$REPO_DIR/bin/mempalace-mcp"
ok "mempalace-mcp wrapper linked to $HOME/.local/bin/mempalace-mcp"

# ---------- 6. Init global brains ----------
mkdir -p "$(dirname "$GLOBAL_ENGRAM_DB")"
if [ ! -f "$GLOBAL_ENGRAM_DB" ]; then
  info "Initialising global engram DB at $GLOBAL_ENGRAM_DB"
  engram save "persistent-brain installed" "Global engram brain created by persistent-brain installer on $(date -u +%Y-%m-%dT%H:%M:%SZ)." >/dev/null 2>&1 || true
fi
ok "Global engram DB ready: $GLOBAL_ENGRAM_DB"

mkdir -p "$GLOBAL_MEMPALACE"
if [ ! -f "$GLOBAL_MEMPALACE/mempalace.yaml" ]; then
  info "Initialising global mempalace palace at $GLOBAL_MEMPALACE"
  mempalace init "$GLOBAL_MEMPALACE" --yes >/dev/null 2>&1 || true
fi
ok "Global mempalace palace ready: $GLOBAL_MEMPALACE"

# ---------- 7. MCP config wiring (non-destructive prompts) ----------
CONFIG_SNIPPET="$REPO_DIR/config/mcp-servers.json"
[ -f "$CONFIG_SNIPPET" ] || die "Missing $CONFIG_SNIPPET"

wire_claude_code() {
  local target="${HOME}/.claude.json"
  if [ ! -f "$target" ]; then
    warn "$target not found — skipping Claude Code wiring. Run \`claude\` once to create it, then rerun this script."
    return
  fi
  if grep -q '"engram"' "$target" 2>/dev/null; then
    ok "Claude Code: engram+mempalace already wired in $target"
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
  if grep -q 'engram' "$target" 2>/dev/null; then
    ok "Codex: engram already wired in $target"
    return
  fi
  warn "Codex: see examples/codex-setup.md for the TOML snippet to add to $target"
}

wire_claude_code
wire_codex

# ---------- 8. Session-start hook (Claude Code) ----------
HOOK_SRC="$REPO_DIR/hooks/session-start.sh"
HOOK_DEST="${HOME}/.claude/hooks/persistent-brain-session-start.sh"
if [ -f "$HOOK_SRC" ] && [ -d "${HOME}/.claude/hooks" ]; then
  cp "$HOOK_SRC" "$HOOK_DEST"
  chmod +x "$HOOK_DEST"
  ok "Installed session-start hook at $HOOK_DEST"
  warn "Register it in ~/.claude/settings.json under \"hooks\" → \"SessionStart\" (see examples/claude-code-setup.md)"
fi

# ---------- 9. Agent-agnostic rules ----------
info "Copy config/AGENTS.md into your agent's instruction file:"
echo "   • Claude Code  → append to ~/.claude/CLAUDE.md"
echo "   • Codex        → append to ~/.codex/AGENTS.md"
echo "   • Cursor       → drop into .cursor/rules/persistent-brain.mdc"
echo "   • Qwen / Kimi  → see examples/ for each platform"

# ---------- Done ----------
echo
ok "persistent-brain installed."
echo
echo "Next steps:"
echo "  1. Wire MCP config for each agent you use (see examples/)"
echo "  2. For each project:  ./scripts/brain-init.sh <project-path>"
echo "  3. Verify with:       ./scripts/brain-status.sh"
