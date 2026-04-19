#!/usr/bin/env bash
# brain-inspect.sh [project-name] — see exactly what the agent knows
set +e
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }
warn() { printf "\033[33m!\033[0m %s\n" "$*"; }
info() { printf "\033[36m→\033[0m %s\n" "$*"; }
dim()  { printf "\033[90m  %s\033[0m\n" "$*"; }

PROJECT_NAME="${1:-$(basename "${PWD}")}"
ENGRAM_DB="${HOME}/.engram/${PROJECT_NAME}.db"
ENGRAM_GLOBAL="${HOME}/.engram/engram.db"
MEMPALACE_PALACE="${HOME}/.mempalace/${PROJECT_NAME}"
[ -d "$MEMPALACE_PALACE" ] || MEMPALACE_PALACE="${HOME}/.mempalace/global"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  persistent-brain inspector — ${PROJECT_NAME}"
echo "╚══════════════════════════════════════════════════════╝"
echo

# ---------- 1. Session context ----------
echo "━━━ Session Context (top 10 by recency) ━━━"
if [ -f "$ENGRAM_DB" ] && command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 -header -column "$ENGRAM_DB" "
    SELECT id, type, title, substr(content,1,60) as content_preview,
           CAST(julianday('now') - julianday(updated_at) AS INTEGER) as days_ago
    FROM observations WHERE deleted_at IS NULL
    ORDER BY updated_at DESC LIMIT 10;" 2>/dev/null
  echo
  COUNT=$(sqlite3 "$ENGRAM_DB" "SELECT COUNT(*) FROM observations WHERE deleted_at IS NULL;" 2>/dev/null)
  ok "Project brain: ${COUNT:-0} active memories"
else
  warn "No project brain at $ENGRAM_DB"
fi

# ---------- 2. Memory types ----------
echo
echo "━━━ Memory Type Distribution ━━━"
if [ -f "$ENGRAM_DB" ] && command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$ENGRAM_DB" "
    SELECT type, COUNT(*) as count FROM observations
    WHERE deleted_at IS NULL GROUP BY type ORDER BY count DESC;" 2>/dev/null | while IFS='|' read -r type count; do
    printf "  %-15s %s\n" "$type" "$count"
  done
fi

# ---------- 3. Stale memories (not accessed in 60+ days) ----------
echo
echo "━━━ Stale Memories (60+ days without access) ━━━"
if [ -f "$ENGRAM_DB" ] && command -v sqlite3 >/dev/null 2>&1; then
  STALE=$(sqlite3 "$ENGRAM_DB" "
    SELECT id, title, CAST(julianday('now') - julianday(COALESCE(last_seen_at, updated_at)) AS INTEGER) as days_stale
    FROM observations
    WHERE deleted_at IS NULL AND julianday('now') - julianday(COALESCE(last_seen_at, updated_at)) > 60
    ORDER BY days_stale DESC LIMIT 10;" 2>/dev/null)
  if [ -n "$STALE" ]; then
    echo "$STALE" | while IFS='|' read -r id title days; do
      printf "  #%-4s %-40s %s days\n" "$id" "$(echo "$title" | head -c 40)" "$days"
    done
  else
    ok "No stale memories (all accessed within 60 days)"
  fi
fi

# ---------- 4. Potential conflicts (duplicate topic_keys) ----------
echo
echo "━━━ Potential Conflicts (duplicate topic_keys) ━━━"
if [ -f "$ENGRAM_DB" ] && command -v sqlite3 >/dev/null 2>&1; then
  CONFLICTS=$(sqlite3 "$ENGRAM_DB" "
    SELECT topic_key, COUNT(*) as cnt FROM observations
    WHERE deleted_at IS NULL AND topic_key IS NOT NULL AND topic_key != ''
    GROUP BY topic_key HAVING cnt > 1 ORDER BY cnt DESC LIMIT 10;" 2>/dev/null)
  if [ -n "$CONFLICTS" ]; then
    warn "Found topic_keys with multiple active entries:"
    echo "$CONFLICTS" | while IFS='|' read -r key cnt; do
      printf "  %-30s %s entries\n" "$key" "$cnt"
    done
  else
    ok "No conflicting topic_keys"
  fi
fi

# ---------- 5. MemPalace ----------
echo
echo "━━━ MemPalace ━━━"
if command -v mempalace >/dev/null 2>&1 && [ -d "$MEMPALACE_PALACE" ]; then
  mempalace --palace "$MEMPALACE_PALACE" status 2>/dev/null
else
  warn "No palace at $MEMPALACE_PALACE"
fi

# ---------- 6. Disk usage ----------
echo
echo "━━━ Disk Usage ━━━"
[ -d "$HOME/.engram" ] && printf "  engram:    %s\n" "$(du -sh "$HOME/.engram" 2>/dev/null | awk '{print $1}')"
[ -d "$HOME/.mempalace" ] && printf "  mempalace: %s\n" "$(du -sh "$HOME/.mempalace" 2>/dev/null | awk '{print $1}')"

# ---------- 7. All project brains ----------
echo
echo "━━━ All Brains ━━━"
if [ -d "$HOME/.engram" ]; then
  for DB in "$HOME"/.engram/*.db; do
    [ -f "$DB" ] || continue
    name="$(basename "$DB" .db)"
    SIZE=$(ls -lh "$DB" 2>/dev/null | awk '{print $5}')
    COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM observations WHERE deleted_at IS NULL;" 2>/dev/null)
    HAS_PALACE=" "
    [ -d "$HOME/.mempalace/$name" ] && HAS_PALACE="✓"
    printf "  [%s] %-25s %4s memories  %6s\n" "$HAS_PALACE" "$name" "${COUNT:-?}" "${SIZE:-?}"
  done
fi
dim "[✓] = has matching MemPalace"
echo
