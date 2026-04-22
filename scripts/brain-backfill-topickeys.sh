#!/usr/bin/env bash
# brain-backfill-topickeys.sh — generate topic_keys for structured observations
# Usage: ./brain-backfill-topickeys.sh [--execute]
set -euo pipefail
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

DRY_RUN=true
if [ "${1:-}" = "--execute" ]; then
  DRY_RUN=false
fi

ENGRAM_DB="${HOME}/.engram/engram.db"

if [ ! -f "$ENGRAM_DB" ]; then
  echo "Error: engram DB not found at $ENGRAM_DB"
  exit 1
fi

# Find observations needing topic_key
ROWS=$(sqlite3 "$ENGRAM_DB" "
  SELECT id, title, type, project FROM observations
  WHERE type IN ('decision','architecture','bugfix','pattern')
    AND (topic_key IS NULL OR topic_key = '')
    AND deleted_at IS NULL;
")

if [ -z "$ROWS" ]; then
  echo "No observations need topic_key backfill."
  exit 0
fi

COUNT=$(echo "$ROWS" | wc -l | tr -d ' ')
echo "Found $COUNT observations needing topic_key backfill."

# Process each row
while IFS='|' read -r id title type project; do
  # Slugify title: lowercase, replace spaces with -, remove special chars
  slug=$(echo "$title" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/-\+/-/g' | sed 's/^-//;s/-$//')
  # Limit length
  slug=$(echo "$slug" | cut -c1-50)
  # Build topic_key
  canonical="$project"
  if [ -f "${HOME}/.engram/project-map.json" ] && command -v python3 >/dev/null 2>&1; then
    canonical=$(python3 -c "
import json
with open('${HOME}/.engram/project-map.json') as f:
  m = json.load(f)
print(m.get('$project', '$project'))
" 2>/dev/null)
  fi
  topic_key="project/${canonical}/${type}/${slug}"
  
  echo "  #$id → $topic_key"
  
  if [ "$DRY_RUN" = false ]; then
    sqlite3 "$ENGRAM_DB" "
      UPDATE observations
      SET topic_key = '$topic_key'
      WHERE id = $id;
    "
  fi
done <<< "$ROWS"

if [ "$DRY_RUN" = true ]; then
  echo "DRY RUN — no changes made. Use --execute to actually update."
else
  echo "Updated $COUNT observations with generated topic_keys."
fi
