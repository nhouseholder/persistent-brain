#!/usr/bin/env bash
# unified-brain session end hook
# Closes session timeline, outputs stats, suggests summary.
set +e

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

PROJECT_NAME="${BRAIN_PROJECT:-$(basename "${OPENCODE_PROJECT_DIR:-${PWD}}")}"
ENGRAM_DB="${HOME}/.engram/${PROJECT_NAME}.db"
[ -f "$ENGRAM_DB" ] || ENGRAM_DB="${HOME}/.engram/engram.db"
STATE_FILE="${HOME}/.unified-brain/session_state.json"

echo "[unified-brain] Session end for project: $PROJECT_NAME"

# ---------- 1. Read session stats ----------
TOOL_CALLS=0
CHECKPOINTS=0
STARTED_AT=""
if [ -f "$STATE_FILE" ]; then
    TOOL_CALLS=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('tool_calls', 0))" 2>/dev/null || echo "0")
    CHECKPOINTS=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('checkpoints', 0))" 2>/dev/null || echo "0")
    STARTED_AT=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('started_at', ''))" 2>/dev/null || echo "")
fi

# ---------- 2. Close session in engram ----------
if command -v sqlite3 >/dev/null 2>&1 && [ -f "$ENGRAM_DB" ]; then
    # Close any open sessions for this project
    sqlite3 "$ENGRAM_DB" \
      "UPDATE sessions SET ended_at = datetime('now') WHERE id LIKE 'session-${PROJECT_NAME}-%' AND ended_at IS NULL;" \
      >/dev/null 2>&1
    echo "[unified-brain] ✓ Session timeline closed in engram"
fi

# ---------- 3. Auto-calibrate pending reasoning tasks ----------
AUTO_CALIBRATE_SCRIPT="${HOME}/ProjectsHQ/persistent-brain/scripts/auto-calibrate.py"
if [ -f "$AUTO_CALIBRATE_SCRIPT" ]; then
    python3 "$AUTO_CALIBRATE_SCRIPT" 2>/dev/null || true
elif [ -f "${HOME}/.local/bin/auto-calibrate" ]; then
    auto-calibrate 2>/dev/null || true
fi

# ---------- 4. Output session stats ----------
echo ""
echo "[unified-brain] === Session Stats ==="
echo "  Project:      $PROJECT_NAME"
echo "  Started:      ${STARTED_AT:-unknown}"
echo "  Tool calls:   $TOOL_CALLS"
echo "  Checkpoints:  $CHECKPOINTS"

# ---------- 5. Suggest next steps ----------
echo ""
echo "[unified-brain] === Next Steps ==="
if [ "$TOOL_CALLS" -gt 0 ]; then
    echo "  → If you haven't already, call brain_session_summary with your session recap."
    echo "  → Then call brain_session_end to formally close the session."
else
    echo "  → No tool calls recorded this session."
fi
echo "  → Sync engram: engram sync"

# ---------- 6. Sync engram (background) ----------
if command -v engram >/dev/null 2>&1; then
    nohup engram sync >/dev/null 2>&1 &
    echo "[unified-brain] ✓ Engram sync started (background)"
fi

# ---------- 7. Clean up session state ----------
if [ -f "$STATE_FILE" ]; then
    # Mark as ended but keep file for reference
    python3 -c "
import json
with open('$STATE_FILE') as f:
    s = json.load(f)
s['ended_at'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
with open('$STATE_FILE', 'w') as f:
    json.dump(s, f, indent=2)
" 2>/dev/null
fi

echo ""
echo "[unified-brain] Session end complete."
