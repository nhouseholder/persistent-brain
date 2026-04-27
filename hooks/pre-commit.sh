#!/usr/bin/env bash
# unified-brain pre-commit hook
# Auto-reindexes codebase with CGC and regenerates GRAPH_REPORT.md if code changed.
set +e

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

PROJECT="${BRAIN_PROJECT:-$(basename "$(pwd)")}"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

echo "[unified-brain] Pre-commit check for: $PROJECT"

# Only run if there are staged code changes
STAGED=$(git diff --cached --name-only 2>/dev/null | grep -E '\.(ts|tsx|js|jsx|py|go|rs|java|md)$' | head -20)
if [ -z "$STAGED" ]; then
    echo "[unified-brain] No code changes staged — skipping reindex."
    exit 0
fi

echo "[unified-brain] Staged code files changed:"
echo "$STAGED" | while read -r f; do echo "  - $f"; done

# ---------- CGC reindex ----------
if command -v cgc >/dev/null 2>&1; then
    echo "[unified-brain] Reindexing with CGC..."
    cgc add_code_to_graph "$REPO_ROOT" --is-dependency=false >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "[unified-brain] ✓ CGC reindex complete"
    else
        echo "[unified-brain] ⚠️ CGC reindex failed (non-fatal)"
    fi
else
    echo "[unified-brain] ⚠️ cgc not installed — skipping reindex"
fi

# ---------- CodeCartographer diagram refresh ----------
if command -v codecartographer >/dev/null 2>&1; then
    echo "[unified-brain] Refreshing GRAPH_REPORT.md..."
    codecartographer diagram "$REPO_ROOT" --backend memory >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "[unified-brain] ✓ GRAPH_REPORT.md refreshed"
        # Stage the updated report
        git add "$REPO_ROOT/.codecartographer/GRAPH_REPORT.md" 2>/dev/null || true
    else
        echo "[unified-brain] ⚠️ GRAPH_REPORT.md refresh failed (non-fatal)"
    fi
else
    echo "[unified-brain] ⚠️ codecartographer not installed — skipping diagram refresh"
fi

exit 0
