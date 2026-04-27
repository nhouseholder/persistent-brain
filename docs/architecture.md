# unified-brain Architecture

## Core Principle: ONE Router, THREE Stores

The agent interacts with **only one interface** — `brain-router` — which routes queries to the appropriate store.

```
Agent ──MCP──► brain-router ──┬──► engram (temporal)
                              ├──► CGC (structural)
                              └──► CodeCartographer (enrichment)
```

This design means:
- **Any MCP-capable agent** works immediately
- **No store-specific knowledge** required by the agent
- **Consistent interface** across all memory types

## The Three Stores

### 1. engram — Temporal Memory

**What it stores:** What we DID — decisions, bugfixes, preferences, session history, architecture facts.

**Technology:** SQLite + FTS5 full-text search. One `.db` file per project + one global `.db`.

**Key features:**
- Compiled Truth + Timeline format
- Auto-Link extraction
- Session lifecycle tracking
- Checkpoint suggestions
- Conflict detection on write

**Access:** Direct SQLite from brain_router.py (zero subprocess overhead).

### 2. CGC (CodeGraphContext) — Structural Memory

**What it stores:** What the code IS — files, functions, classes, modules, call graphs, complexity metrics, dead code candidates.

**Technology:** FalkorDB (RedisGraph-compatible) with Cypher queries.

**Key features:**
- `cgc add_code_to_graph` — index a codebase
- `cgc stats` — repo statistics
- `cgc analyze complexity` — top complexity hotspots
- `cgc analyze dead-code` — unused function detection
- `cgc find_code` — symbol lookup

**Access:** Subprocess calls from brain_router.py with timeouts (avoids direct FalkorDB connection issues on large repos).

### 3. CodeCartographer — Enriched Structural Memory

**What it stores:** Enriched code intelligence — GRAPH_REPORT.md, hybrid search index, typed relationships.

**Technology:** TypeScript AST parser + BM25 + embeddings + RRF (Reciprocal Rank Fusion).

**Key features:**
- `codecartographer diagram` — generates GRAPH_REPORT.md (~2KB lazy-load artifact)
- `codecartographer search` — hybrid BM25 + embeddings + RRF
- Typed edges: TESTS, EXPORTS, EXTENDS, IMPLEMENTS
- Alias resolution for TypeScript/TSX

**Access:** Subprocess calls from brain_router.py with timeouts.

## brain-router Design

### Zero Dependencies

brain_router.py is pure Python 3.10+ stdlib:
- `json` — MCP protocol
- `sqlite3` — engram direct access
- `subprocess` — CGC + CodeCartographer calls
- `re` — pattern matching
- `os`, `sys`, `datetime` — utilities

No pip install, no venv, no package management headaches.

### Modular Router Structure

```
router/
├── brain_router.py          # MCP server, 15 tool handlers
├── session_manager.py       # Tool-call tracking, checkpoint triggers
├── observation_validator.py # Compiled Truth + Auto-Links validation
├── auto_linker.py           # Link extraction from observation content
└── codebase_manager.py      # (planned) CGC + CodeCartographer orchestration
```

### Session Automation

Session state is persisted in `~/.unified-brain/session_state.json`:
```json
{
  "session_id": "session-myapp-1714147200",
  "project": "myapp",
  "started_at": "2026-04-26T17:00:00+00:00",
  "tool_calls": 42,
  "last_checkpoint_at": "2026-04-26T17:30:00+00:00",
  "last_checkpoint_calls": 30,
  "checkpoints": 2
}
```

- Checkpoint suggested at **10 tool calls** or **15 minutes**
- Suggestion injected as `_checkpoint_suggestion` field in MCP responses
- Agent sees the suggestion and can call `brain_checkpoint`

### Observation Validation Pipeline

```
brain_save(title, content, type)
    ↓
validate(content, type)
    ├─ Compiled Truth missing + no What/Why → REJECT
    ├─ Compiled Truth missing + has What/Why → auto-add header
    ├─ Timeline missing → auto-add separator + timestamp
    ├─ Auto-Links missing + extractable links → auto-extract
    └─ Auto-Links missing + no links → warn only
    ↓
engram_save(title, fixed_content, type, topic_key)
```

## Data Flow

### Session Start

```
Agent launches
    ↓
MCP initialize → brain_router auto-inits session
    ↓
Hook: session-start.sh
    ├─ Write session_state.json
    ├─ Check engram DB
    ├─ Check GRAPH_REPORT.md freshness
    └─ Output agent instructions
    ↓
Agent calls brain_context → loads memories
Agent calls brain_codebase_index --check → loads/generates diagram
```

### Normal Operation

```
Agent calls brain_query
    ↓
brain_router → engram_search (SQLite FTS5)
    ↓
Return results + _checkpoint_suggestion (if due)
```

### Session End

```
Agent says "done"
    ↓
Hook: session-end.sh
    ├─ Read session stats
    ├─ Close sessions in engram SQLite
    ├─ Output stats + suggest summary
    └─ Sync engram (background)
    ↓
Agent calls brain_session_summary
Agent calls brain_session_end
```

## Performance

| Operation | Latency | Notes |
|---|---|---|
| `brain_query` | <50ms | SQLite FTS5, no subprocess |
| `brain_save` | <20ms | SQLite INSERT |
| `brain_context` | <30ms | Two SELECTs with LIMIT |
| `brain_validate` | <5ms | In-memory regex |
| `brain_diagram` | 1-3s | CGC subprocess |
| `brain_codebase_index` | 5-30s | CGC index + CodeCartographer diagram |
| `brain_codebase_search` | 2-5s | CodeCartographer hybrid search |

## Security

- All data stays local (SQLite files in `~/.engram/`)
- No network calls from brain_router.py
- CGC/CodeCartographer subprocesses only access local filesystem
- MCP stdio interface — no open ports
