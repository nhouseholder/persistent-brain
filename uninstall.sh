#!/usr/bin/env bash
# persistent-brain uninstaller — removes binaries and (optionally) data
set -euo pipefail

ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }
info() { printf "\033[36m→\033[0m %s\n" "$*"; }
warn() { printf "\033[33m!\033[0m %s\n" "$*"; }

info "This removes the engram + mempalace binaries."
info "Your brain data in ~/.engram/ and ~/.mempalace/ is PRESERVED by default."
read -rp "Continue? [y/N] " yn
[[ "$yn" =~ ^[Yy]$ ]] || exit 0

if command -v engram >/dev/null 2>&1; then
  brew uninstall engram 2>/dev/null && ok "engram removed" || warn "engram uninstall failed"
fi
if command -v mempalace >/dev/null 2>&1; then
  pipx uninstall mempalace 2>/dev/null && ok "mempalace removed" || warn "mempalace uninstall failed"
fi

echo
read -rp "Also delete ~/.engram/ and ~/.mempalace/ data? THIS IS IRREVERSIBLE [y/N] " yn
if [[ "$yn" =~ ^[Yy]$ ]]; then
  rm -rf "$HOME/.engram" "$HOME/.mempalace"
  ok "Brain data deleted."
else
  ok "Brain data preserved in ~/.engram/ and ~/.mempalace/"
fi

info "Remember to unwire MCP servers in your agent configs (~/.claude.json, ~/.codex/config.toml, etc.)"
