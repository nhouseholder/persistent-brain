#!/bin/bash
# unified-brain session start hook
# Loads context, checks GRAPH_REPORT.md, sets up session tracking.

set -e

PROJECT="${BRAIN_PROJECT:-$(basename "$(pwd)")}"
STATE_DIR="${HOME}/.unified-brain"
STATE_FILE="${STATE_DIR}/session_state.json"
GRAPH_REPORT="$(pwd)/.codecartographer/GRAPH_REPORT.md"

echo "[unified-brain] Session start for project: $PROJECT"

# ---------- 1. Initialize session state ----------
mkdir -p "$STATE_DIR"
SESSION_ID="session-${PROJECT}-$(date +%s)"
cat > "$STATE_FILE" <<EOF
{
  "session_id": "$SESSION_ID",
  "project": "$PROJECT",
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "tool_calls": 0,
  "last_checkpoint_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "last_checkpoint_calls": 0,
  "checkpoints": 0
}
EOF
echo "[unified-brain] ✓ Session state: $SESSION_FILE"

# ---------- 2. Check engram DB ----------
ENGRAM_DB="${HOME}/.engram/${PROJECT}.db"
[ -f "$ENGRAM_DB" ] || ENGRAM_DB="${HOME}/.engram/engram.db"
if [ -f "$ENGRAM_DB" ]; then
    echo "[unified-brain] ✓ Engram DB: $ENGRAM_DB"
else
    echo "[unified-brain] ⚠️ No engram DB found. Run: ./scripts/brain-init.sh $(pwd)"
fi

# ---------- 3. Check GRAPH_REPORT.md ----------
if [ -f "$GRAPH_REPORT" ]; then
    AGE_DAYS=$(echo "$(date +%s) - $(stat -f %m "$GRAPH_REPORT" 2>/dev/null || stat -c %Y "$GRAPH_REPORT" 2>/dev/null)" | bc 2>/dev/null || echo "0")
    AGE_DAYS=$(echo "$AGE_DAYS / 86400" | bc 2>/dev/null || echo "0")
    if [ "$AGE_DAYS" -gt 7 ]; then
        echo "[unified-brain] ⚠️ GRAPH_REPORT.md is ${AGE_DAYS} days old (>7). Consider regenerating:"
        echo "[unified-brain]   brain_codebase_index(path=\".\", force_reindex=true)"
    else
        echo "[unified-brain] ✓ GRAPH_REPORT.md: $GRAPH_REPORT (${AGE_DAYS} days old)"
    fi
else
    echo "[unified-brain] ⚠️ No GRAPH_REPORT.md found. Generate it:"
    echo "[unified-brain]   brain_codebase_index(path=\".\")"
fi

# ---------- 4. Agent instructions ----------
echo ""
echo "[unified-brain] === Agent Instructions ==="
echo "  1. Call brain_context before your first reply."
echo "  2. Call brain_codebase_index --check to load/generate GRAPH_REPORT.md."
echo "  3. Use brain_validate before brain_save to ensure Compiled Truth + Auto-Links."
echo "  4. Checkpoint auto-suggested after 10 tool calls or 15 minutes."
echo "  5. Call brain_session_end before saying 'done'."
echo ""
echo "[unified-brain] Session start complete."
