#!/bin/bash
# Session start hook for persistent-brain
# Loads brain_context + checks for CGC codebase diagram

set -e

PROJECT="${BRAIN_PROJECT:-$(basename "$(pwd)")}"
echo "[persistent-brain] Session start for project: $PROJECT"

# 1. Load temporal context from engram
echo "[persistent-brain] Loading engram context..."
# brain_context is called by the agent via MCP — this hook just logs

# 2. Check for CGC codebase diagram
echo "[persistent-brain] Checking CodeGraphContext..."
if command -v cgc &>/dev/null; then
    if cgc list 2>/dev/null | grep -q "$PROJECT"; then
        echo "[persistent-brain] ✓ CGC graph found for $PROJECT"
        echo "[persistent-brain] Stats: $(cgc stats . 2>/dev/null | grep -E 'Files|Functions|Classes' | tr '\n' ' ')"
    else
        echo "[persistent-brain] ⚠️ No CGC graph found. Consider indexing:"
        echo "[persistent-brain]   cgc add_code_to_graph path=. is_dependency=false"
    fi
else
    echo "[persistent-brain] ⚠️ CodeGraphContext not installed. Structural memory unavailable."
    echo "[persistent-brain]   Install: uv tool install codegraphcontext"
fi

echo "[persistent-brain] Session start complete. Agent should now call brain_context."
