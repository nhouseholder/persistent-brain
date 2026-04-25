# Routing Rules

## Architecture (v1.0 — Two-Layer Memory)

```
Agent  ──MCP──▶  brain-router  ──▶  engram     (structured facts, SQLite/FTS5)
                    │
                    ├──▶  codegraphcontext  (structural memory, graph DB)
                    │       └── FalkorDB Lite — files, functions, call graphs
                    │
                    └──▶  mempalace  (verbatim recall, ChromaDB vectors)
                            └── STRIPPED in v0.5.0 — not operational
```

## Two-Layer Memory Decision Tree

When the agent asks a question, route to the right layer:

```
Question about...
│
├─ Code structure? ("Who calls X?", "Where is Y defined?", "How complex is Z?")
│   └─ Route to: brain_diagram, brain_callers, brain_structure → CodeGraphContext
│
├─ Past work / decisions? ("What did we do about X?", "How did we fix Y?")
│   └─ Route to: brain_query, brain_context → engram
│
└─ Both? ("Should we refactor the props pipeline?")
   └─ Route to: CGC first (structural facts), then engram (historical context)
```

## How brain-router routes queries

### Temporal queries (past work, decisions, bugs)

When an agent calls `brain_query`:

1. **Always search engram first** — it's fast (<50ms, SQLite FTS5) and returns curated facts.
2. **Search global engram** for cross-project patterns.
3. **Merge and deduplicate** — results returned with source attribution.

### Structural queries (code structure, relationships)

When an agent calls `brain_diagram`, `brain_callers`, or `brain_structure`:

1. **Query CodeGraphContext** — graph database of the codebase.
2. **Return structural facts** — file counts, function counts, call graphs, complexity.
3. **Cross-reference with engram** — for historical context about the structure.

### Unified query (brain_query with structural intent)

If `brain_query` detects a structural question (keywords: "calls", "defines", "hierarchy", "complexity", "dead code"):

1. Search engram first (may have cached structural insights).
2. If no results OR stale (>7 days) → fallback to `brain_diagram`.
3. Return combined results with source attribution.

## Tool Reference

| Tool | Layer | Use Case |
|---|---|---|
| `brain_query` | engram (temporal) | ANY memory lookup — decisions, preferences, past work |
| `brain_save` | engram (temporal) | Save structured fact with conflict detection |
| `brain_context` | engram (temporal) | Session-start context (project + global) |
| `brain_correct` | engram (temporal) | Fix a wrong memory |
| `brain_forget` | engram (temporal) | Delete a memory |
| `brain_diagram` | CGC (structural) | Generate codebase architecture map |
| `brain_callers` | CGC (structural) | Find who calls a function |
| `brain_structure` | CGC (structural) | Get repo stats (files, functions, classes) |

## When to use direct stores

Use `brain_*` tools for 95% of operations. Use direct stores only for:

| Store | Direct Tool | Use Case |
|---|---|---|
| engram | `engram.mem_timeline` | Chronological context around observation |
| engram | `engram.mem_stats` | Memory system health check |
| engram | `engram.mem_merge_projects` | Consolidate project name drift |
| CGC | `cgc analyze complexity` | Detailed complexity analysis |
| CGC | `cgc analyze dead-code` | Find unused code |
| CGC | `cgc find_code` | Advanced code search |

## Conflict Detection

When `brain_save` is called with a `topic_key`, the router:

1. Searches engram for existing entries with the same topic_key
2. If a match is found with different content → flags as potential conflict
3. Returns conflict info so agent can decide whether to supersede

This catches contradictions without false positives.

## Memory Types

| Type | Example | Store |
|---|---|---|
| `decision` | "We chose GraphQL over REST" | engram |
| `preference` | "User prefers dark mode" | engram (global) |
| `architecture` | "Auth uses JWT with refresh tokens" | engram |
| `bugfix` | "OOM was caused by unbounded cache" | engram |
| `pattern` | "Standardized on kebab-case" | engram |
| `config` | "Added ENGRAM_DATA_DIR env var" | engram |
| `learning` | "ESM imports need .js extensions" | engram |
| `manual` | Any other curated knowledge | engram |
| (structural) | "gradePicks called by 3 graders" | engram + CGC |

## Session-End Auto-Distillation

**DISABLED in v0.5.0** — was producing 55.9% noise. Agents must explicitly save via `brain_save`.

The `session-end.sh` hook still:
1. Closes session timeline in engram
2. Runs `engram sync` if configured

## CGC Graph Maintenance

After major refactors, run:
```bash
cgc add_code_to_graph path=. is_dependency=false
```

The graph must stay current for structural queries to be accurate.
