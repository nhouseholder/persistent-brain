# Routing Rules

## Architecture

```
Agent  ──MCP──▶  brain-router  ──▶  engram     (structured facts, SQLite/FTS5)
                    │              
                    └──▶  mempalace  (verbatim recall, ChromaDB vectors)
```

## How brain-router routes queries

When an agent calls `brain_query`:

1. **Always search engram first** — it's fast (<50ms, SQLite FTS5) and returns curated facts.
2. **Search mempalace only when:**
   - Engram returned zero results, OR
   - The agent explicitly requested `include_verbatim: true`
3. **Merge and deduplicate** — results are returned with source attribution so the agent knows where each fact came from.
4. **Trust structured over verbatim** — when both stores have a match, the engram result is the curated/authoritative version.

## When to use direct stores

The agent should use `brain_query` / `brain_save` / `brain_correct` for 95% of operations. Use the direct stores only for:

| Tool | Use case |
|---|---|
| `engram.mem_context` | Timeline browsing, session metadata |
| `engram.mem_search` | FTS5 advanced queries (wildcards, phrase matching) |
| `mempalace.search` | Direct vector similarity with reranking |
| `mempalace.status` | Palace health checks |

## Conflict Detection

When `brain_save` is called with a `topic_key`, the router:

1. Searches engram for existing entries with the same topic_key
2. If a match is found with different content → flags it as a potential conflict
3. Returns the conflict info so the agent can decide whether to supersede

This catches obvious contradictions (database changes, framework migrations, preference updates) without false positives.

## Memory Types

| Type | Example | Store |
|---|---|---|
| `decision` | "We chose GraphQL over REST" | engram |
| `preference` | "User prefers dark mode" | engram (global) |
| `architecture` | "Auth uses JWT with refresh tokens" | engram |
| `fix` | "OOM was caused by unbounded cache" | engram |
| `fact` | Any other curated knowledge | engram |
| (raw transcript) | Full conversation history | mempalace (auto) |

## Session-End Auto-Distillation

The `session-end.sh` hook automatically:
1. Pulls the latest session transcript from mempalace
2. Feeds it through `engram capture-passive` to extract up to 5 key facts
3. Registers the session end in engram's timeline

This is the safety net that catches anything the agent forgot to `brain_save` during the session.
