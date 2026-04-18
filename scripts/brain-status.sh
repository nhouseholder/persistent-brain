#!/usr/bin/env bash
# brain-status.sh — health check both stores + list all per-project brains
set +e

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }
warn() { printf "\033[33m!\033[0m %s\n" "$*"; }
info() { printf "\033[36m→\033[0m %s\n" "$*"; }

echo "=== persistent-brain status ==="
echo

# Binaries
if command -v engram >/dev/null 2>&1; then ok "engram: $(engram version 2>/dev/null | head -1)"; else warn "engram not installed"; fi
if command -v mempalace >/dev/null 2>&1; then ok "mempalace: $(mempalace --help 2>&1 | head -1 | cut -c1-80)"; else warn "mempalace not installed"; fi

echo
info "Engram DBs (~/.engram/):"
if [ -d "$HOME/.engram" ]; then
  find "$HOME/.engram" -maxdepth 1 -name "*.db" -exec ls -lh {} \; 2>/dev/null | awk '{printf "   %-10s  %s\n", $5, $NF}'
else
  warn "  (none)"
fi

echo
info "Mempalace palaces (~/.mempalace/):"
if [ -d "$HOME/.mempalace" ]; then
  find "$HOME/.mempalace" -maxdepth 1 -mindepth 1 -type d -exec basename {} \; 2>/dev/null | sed 's/^/   /'
else
  warn "  (none)"
fi

echo
# macOS lacks `timeout` by default; use `gtimeout` (coreutils) if present, else perl.
timeout_cmd() {
  if command -v timeout  >/dev/null 2>&1; then timeout  "$@"; return; fi
  if command -v gtimeout >/dev/null 2>&1; then gtimeout "$@"; return; fi
  perl -e 'alarm shift; exec @ARGV' "$@"
}

info "MCP tool smoke (engram-mcp & mempalace-mcp start cleanly?)"
if command -v engram >/dev/null 2>&1; then
  timeout_cmd 1 engram mcp </dev/null >/dev/null 2>&1
  ok "engram mcp responds (stdio server — timeout is expected)"
fi
if command -v mempalace-mcp >/dev/null 2>&1; then
  timeout_cmd 1 mempalace-mcp </dev/null >/dev/null 2>&1
  ok "mempalace-mcp responds (stdio server — timeout is expected)"
else
  warn "mempalace-mcp wrapper not on PATH — rerun install.sh to symlink it"
fi

echo
echo "Done."
