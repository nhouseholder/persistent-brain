#!/bin/bash
# Generate or refresh codebase diagram via CodeGraphContext
# Usage: brain-diagram.sh [project-path]

set -e

PROJECT="${BRAIN_PROJECT:-$(basename "$(pwd)")}"
PATH_ARG="${1:-.}"

echo "=== Brain Diagram: $PROJECT ==="

if ! command -v cgc &>/dev/null; then
    echo "ERROR: CodeGraphContext not installed."
    echo "Install: uv tool install codegraphcontext"
    exit 1
fi

# Check if graph exists
if ! cgc list 2>/dev/null | grep -q "$PROJECT"; then
    echo "No graph found. Indexing..."
    cgc add_code_to_graph "$PATH_ARG" --is-dependency=false
fi

echo ""
echo "--- Repository Stats ---"
cgc stats "$PATH_ARG" 2>/dev/null || echo "Failed to get stats"

echo ""
echo "--- Top 10 Complexity Hotspots ---"
cgc analyze complexity --limit 10 "$PATH_ARG" 2>/dev/null || echo "Failed to get complexity"

echo ""
echo "--- Dead Code Candidates ---"
cgc analyze dead-code "$PATH_ARG" 2>/dev/null || echo "Failed to get dead code"

echo ""
echo "=== Tip: Save this to engram ==="
echo "brain_save title=\"$PROJECT Codebase Diagram\" type=architecture topic_key=codebase/diagram/$PROJECT"
