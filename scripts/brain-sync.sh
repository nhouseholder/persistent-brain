#!/usr/bin/env bash
# brain-sync.sh — sync engram across machines (git) + optional mempalace rsync
# Usage:
#   brain-sync.sh              # engram sync only
#   brain-sync.sh --rsync user@host:/path/to/mempalace  # also rsync mempalace
set -euo pipefail

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }
info() { printf "\033[36m→\033[0m %s\n" "$*"; }
die()  { printf "\033[31m✗\033[0m %s\n" "$*" >&2; exit 1; }

command -v engram >/dev/null 2>&1 || die "engram not installed"

RSYNC_TARGET=""
while [ $# -gt 0 ]; do
  case "$1" in
    --rsync) RSYNC_TARGET="$2"; shift 2 ;;
    *) die "Unknown arg: $1" ;;
  esac
done

info "Syncing engram chunks (local → ~/.engram/chunks/)…"
engram sync
ok "engram sync done"

if [ -n "$RSYNC_TARGET" ]; then
  command -v rsync >/dev/null 2>&1 || die "rsync required for --rsync"
  info "rsync $HOME/.mempalace/ → $RSYNC_TARGET"
  rsync -avz --delete "$HOME/.mempalace/" "$RSYNC_TARGET"
  ok "mempalace rsync done"
fi

info "For cross-machine engram sync, commit ~/.engram/chunks/ to a git remote you control."
info "See docs/sync-strategy.md."
