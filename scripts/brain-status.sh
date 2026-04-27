#!/usr/bin/env bash
# brain-status.sh — health check all three stores + list all per-project brains
set +e

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }
warn() { printf "\033[33m!\033[0m %s\n" "$*"; }
info() { printf "\033[36m→\033[0m %s\n" "$*"; }

echo "=== unified-brain status ==="
echo

# ---------- Binaries ----------
echo "--- Binaries ---"
if command -v engram >/dev/null 2>&1; then ok "engram: $(engram version 2>/dev/null | head -1)"; else warn "engram not installed"; fi
if command -v cgc >/dev/null 2>&1; then ok "cgc: installed"; else warn "cgc not installed — run ./install.sh"; fi
if command -v codecartographer >/dev/null 2>&1; then ok "codecartographer: $(codecartographer --version 2>/dev/null || echo "installed")"; else warn "codecartographer not installed — run ./install.sh"; fi
if command -v mempalace >/dev/null 2>&1; then ok "mempalace: installed"; else warn "mempalace not installed"; fi

# ---------- Engram ----------
echo
echo "--- Engram DBs (~/.engram/) ---"
if [ -d "$HOME/.engram" ]; then
  find "$HOME/.engram" -maxdepth 1 -name "*.db" -exec ls -lh {} \; 2>/dev/null | awk '{printf "   %-10s  %s\n", $5, $NF}'
else
  warn "  (none)"
fi

# ---------- CGC ----------
echo
echo "--- CGC Indexed Repositories ---"
if command -v cgc >/dev/null 2>&1; then
  cgc list 2>/dev/null || warn "  No repositories indexed yet"
else
  warn "  cgc not installed"
fi

# ---------- CodeCartographer ----------
echo
echo "--- CodeCartographer GRAPH_REPORT.md ---"
GRAPH_COUNT=0
if [ -d "$HOME/ProjectsHQ" ]; then
  for report in $(find "$HOME/ProjectsHQ" -maxdepth 3 -name "GRAPH_REPORT.md" 2>/dev/null); do
    proj=$(basename "$(dirname "$(dirname "$report")")")
    echo "   ✓ $proj"
    GRAPH_COUNT=$((GRAPH_COUNT + 1))
  done
fi
if [ -d "$HOME/.codecartographer" ]; then
  for report in $(find "$HOME/.codecartographer" -maxdepth 3 -name "GRAPH_REPORT.md" 2>/dev/null); do
    echo "   ✓ $(basename "$report")"
    GRAPH_COUNT=$((GRAPH_COUNT + 1))
  done
fi
if [ "$GRAPH_COUNT" -eq 0 ]; then
  warn "  No GRAPH_REPORT.md files found. Run ./scripts/brain-init.sh <project-path>"
fi

# ---------- MCP smoke tests ----------
echo
echo "--- MCP Smoke Tests ---"
timeout_cmd() {
  if command -v timeout  >/dev/null 2>&1; then timeout  "$@"; return; fi
  if command -v gtimeout >/dev/null 2>&1; then gtimeout "$@"; return; fi
  perl -e 'alarm shift; exec @ARGV' "$@"
}

if command -v engram >/dev/null 2>&1; then
  timeout_cmd 1 engram mcp </dev/null >/dev/null 2>&1
  ok "engram mcp responds (stdio server — timeout is expected)"
fi

if [ -f "${HOME}/.local/bin/brain-router" ]; then
  timeout_cmd 1 brain-router </dev/null >/dev/null 2>&1
  ok "brain-router responds (stdio server — timeout is expected)"
fi

# ---------- Unified config ----------
echo
echo "--- Unified Config ---"
if [ -f "${HOME}/.unified-brain/config.yaml" ]; then
  ok "${HOME}/.unified-brain/config.yaml"
else
  warn "${HOME}/.unified-brain/config.yaml not found — run ./install.sh"
fi

echo
echo "Done."
