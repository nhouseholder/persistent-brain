# API Reference — brain-router MCP Tools

All tools are exposed through the `brain-router` MCP server. The agent calls them via MCP stdio JSON-RPC.

## Temporal Memory (engram)

### `brain_query`

Search temporal memory using FTS5 full-text search.

**Input:**
```json
{
  "query": "auth refresh token",
  "limit": 10
}
```

**Output:**
```json
{
  "query": "auth refresh token",
  "structured": [...],
  "global": [...],
  "counts": {"structured": 5, "global": 2}
}
```

### `brain_save`

Save an observation to engram. Auto-validates Compiled Truth + Auto-Links. Auto-fixes where possible. Rejects unfixable observations.

**Input:**
```json
{
  "title": "Fixed auth loop on token refresh",
  "content": "## Compiled Truth\n**What**: ...\n**Why**: ...\n**Where**: ...\n\n---\n## Timeline\n- 2026-04-26T17:00:00: Fixed\n\n## Auto-Links\n- src/auth/refresh.ts",
  "type": "bugfix",
  "topic_key": "project/myapp/bugfix/auth-refresh",
  "scope": "project"
}
```

**Output:**
```json
{
  "saved": true,
  "id": 42,
  "format_validation": {
    "valid": true,
    "enforce": false,
    "auto_fixes": [],
    "checks": {...}
  }
}
```

**Rejection output:**
```json
{
  "saved": false,
  "error": "Observation rejected: Missing '## Compiled Truth' section...",
  "format_validation": {...},
  "suggestion": "Fix the content and call brain_validate first..."
}
```

### `brain_context`

Load session-start context — recent project memories + global preferences.

**Input:**
```json
{
  "project_limit": 20,
  "global_limit": 5
}
```

**Output:**
```json
{
  "project": "myapp",
  "project_memories": [...],
  "project_count": 12,
  "global_memories": [...],
  "global_count": 3
}
```

### `brain_correct`

Find and update an existing observation. The old entry is marked superseded.

**Input:**
```json
{
  "search_query": "auth refresh",
  "corrected_content": "...",
  "reason": "Token expiry is 30 min, not 60"
}
```

### `brain_forget`

Delete an observation. Requires `confirm: true`.

**Input:**
```json
{
  "search_query": "old incorrect fact",
  "confirm": true
}
```

### `brain_validate`

Validate observation content without saving. Returns the same format as `brain_save` validation.

**Input:**
```json
{
  "content": "...",
  "type": "bugfix"
}
```

## Structural Memory (CGC)

### `brain_diagram`

Get codebase architecture stats, complexity hotspots, and dead code candidates.

**Input:**
```json
{
  "path": ".",
  "force_regenerate": false
}
```

**Output:**
```json
{
  "source": "codegraphcontext",
  "stats": {...},
  "complexity_hotspots": [...],
  "dead_code_candidates": [...]
}
```

### `brain_callers`

Find who calls a function or uses a symbol.

**Input:**
```json
{
  "target": "calculateBuffettScore",
  "context": ""
}
```

### `brain_structure`

Get repo structural stats: files, functions, classes, modules.

**Input:**
```json
{
  "path": "."
}
```

## Enriched Memory (CodeCartographer)

### `brain_codebase_index`

Index a codebase with CGC and generate GRAPH_REPORT.md via CodeCartographer.

**Input:**
```json
{
  "path": ".",
  "force_reindex": false,
  "backend": "memory"
}
```

**Output:**
```json
{
  "source": "codebase_index_pipeline",
  "cgc_index": {...},
  "codecartographer_diagram": {...},
  "next_steps": [...]
}
```

### `brain_codebase_search`

Hybrid search (BM25 + embeddings + RRF) across indexed code.

**Input:**
```json
{
  "search_query": "auth token refresh",
  "path": ".",
  "limit": 10
}
```

## Session Management

### `brain_session_start`

Initialize a tracked session for checkpoint monitoring.

**Input:**
```json
{
  "project": "myapp"
}
```

**Output:**
```json
{
  "session_started": true,
  "session_id": "session-myapp-1714147200",
  "checkpoint_thresholds": {"calls": 10, "minutes": 15}
}
```

### `brain_session_end`

End the current tracked session. Returns final stats.

**Output:**
```json
{
  "ended": true,
  "session_id": "session-myapp-1714147200",
  "total_tool_calls": 42,
  "total_checkpoints": 3
}
```

### `brain_checkpoint`

Save a checkpoint observation. Captures current task, recent actions, and open files.

**Input:**
```json
{
  "task": "Refactoring auth middleware",
  "recent_actions": ["Extracted token logic", "Added expiry check"],
  "open_files": ["src/auth.ts", "src/middleware.ts"]
}
```

### `brain_session_stats`

Get current session statistics.

**Output:**
```json
{
  "active": true,
  "session_id": "session-myapp-1714147200",
  "elapsed_minutes": 23.5,
  "tool_calls": 42,
  "checkpoints": 3
}
```

## Checkpoint Suggestions

When a checkpoint is due (10 calls or 15 minutes), every tool response includes:

```json
{
  "_checkpoint_suggestion": "⚠️ CHECKPOINT DUE: 12 tool calls since last checkpoint. Consider calling brain_save with a checkpoint observation."
}
```

The agent should call `brain_checkpoint` when this appears.
