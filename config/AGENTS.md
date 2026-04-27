# Unified Brain — Memory Protocol

You have a **three-layer memory system** available via the **brain-router** MCP server:

- **engram** — temporal memory: what we DID, decisions, bugfixes, preferences, session history
- **CodeGraphContext (CGC)** — structural memory: what the code IS, call graphs, complexity, dead code
- **CodeCartographer** — enriched structural memory: GRAPH_REPORT.md, hybrid search (BM25 + embeddings), typed relationships (TESTS/EXPORTS/EXTENDS/IMPLEMENTS)

The router handles routing automatically. You don't need to pick the store manually.

## Three-Layer Decision Tree

```
Question about...
├─ Code structure? ("Who calls X?", "Where is Y?", "How complex is Z?")
│   └─ CGC: brain_diagram, brain_callers, brain_structure
├─ Code search? ("Find all places that handle auth", "Where is the props pipeline?")
│   └─ CodeCartographer: brain_codebase_search
├─ Past work? ("What did we do about X?", "How did we fix Y?")
│   └─ engram: brain_query, brain_context
└─ Both? ("Should we refactor the props pipeline?")
   └─ CGC/CodeCartographer first (structural facts), then engram (historical context)
```

## Tools

| Tool | Store | When to use |
|---|---|---|
| `brain_query` | engram | **ANY** memory lookup — decisions, preferences, past conversations, architecture facts, bug fixes |
| `brain_save` | engram | Save a structured fact — decisions, preferences, architecture, fix takeaways, deadlines |
| `brain_context` | engram | Load session-start context (call this before your first reply) |
| `brain_correct` | engram | Fix a wrong memory — automatically supersedes the old entry |
| `brain_forget` | engram | Remove a memory the user wants deleted |
| `brain_validate` | engram | Validate observation content for Compiled Truth + Auto-Links before saving |
| `brain_diagram` | CGC | Generate codebase architecture map — files, functions, complexity, dead code |
| `brain_callers` | CGC | Find who calls a function or uses a symbol |
| `brain_structure` | CGC | Get repo stats: files, functions, classes, modules |
| `brain_codebase_index` | CGC + CodeCartographer | Index a project and generate GRAPH_REPORT.md |
| `brain_codebase_search` | CodeCartographer | Hybrid semantic search across indexed code (BM25 + embeddings + RRF) |

> **Use `brain_*` tools by default.** Fall back to direct store tools only for advanced operations:
> - engram: timeline browsing (`mem_timeline`), stats (`mem_stats`), project merge (`mem_merge_projects`)
> - CGC: detailed complexity analysis, dead code detection, Cypher queries
> - CodeCartographer: direct diagram generation, skill extraction

## Session Start Protocol

Before your first substantive reply in a new session:

1. Call `brain_context` → loads project memories (up to 20) + global preferences (up to 5).
2. Call `brain_codebase_index --check` → loads or generates GRAPH_REPORT.md for the project.
3. Treat the returned memories as authoritative. Do not ask the user to repeat anything already in them.
4. Do **not** preemptively search for conversations — only query when the user asks about prior sessions.

## Codebase Diagram Protocol

**Generate once, reuse forever.** Every project needs a codebase architecture diagram stored under `topic_key="codebase/diagram/{PROJECT_NAME}"`.

```
STEP 1: brain_query(query="codebase diagram", topic_key="codebase/diagram/{PROJECT_NAME}")
    ├─ FOUND → Check staleness (>7 days OR major refactor?)
    │          ├─ FRESH → Use it
    │          └─ STALE → Regenerate via brain_codebase_index
    └─ NOT FOUND → Regenerate via brain_codebase_index

brain_codebase_index method (preferred):
  brain_codebase_index(path=".", force_reindex=false)
  → Indexes with CGC + generates GRAPH_REPORT.md with CodeCartographer
  → Saves to engram with topic_key="codebase/diagram/{PROJECT_NAME}"

Fallback (if brain-router unavailable):
  cgc add_code_to_graph . --is-dependency=false
  codecartographer diagram . --backend memory
  Synthesize → brain_save(topic_key="codebase/diagram/{PROJECT_NAME}", type="architecture")
```

**Stale criteria**: >7 days old, new top-level dirs, framework/build system changed, >20% file churn, new API layer or database, auth/deployment architecture changed.

## Save Rules

When you complete significant work (bugfix, architecture decision, preference learned, etc.):

1. **Validate first**: Call `brain_validate` with your draft content to check Compiled Truth + Auto-Links.
2. **Then save**: Call `brain_save` with a clear title, the content, and a `type`.
3. Include a `topic_key` when the fact belongs to a category (e.g., `database`, `auth-flow`, `deploy-target`). This enables automatic conflict detection.
4. **Never double-write.** One fact, one save.

## Compiled Truth + Timeline Format

All observations must use this structured format:

```
## Compiled Truth
**What**: [concise description of what was done]
**Why**: [the reasoning, user request, or problem that drove it]
**Where**: [files/paths affected]
**Learned**: [gotchas, edge cases, or decisions made — omit if none]

---
## Timeline
- 2026-04-26T17:00:00: Initial implementation
- 2026-04-26T18:00:00: Discovered edge case, fixed

## Auto-Links
- src/auth/refresh.ts
- TokenRefreshQueue
- myproject
```

## Memory Quality Checklist

Before calling `brain_save`, verify:

- [ ] **Type is valid**: `decision`, `architecture`, `bugfix`, `pattern`, `config`, `learning`, `discovery`, or `manual`
- [ ] **topic_key provided** (required for `decision`, `architecture`, `bugfix`, `pattern`, `config`)
- [ ] **topic_key format**: lowercase, hyphens, slashes only (e.g., `project/mmalogic/bugfix/auth-loop`)
- [ ] **Content has `## Compiled Truth`** section
- [ ] **Content has `## Timeline`** section (recommended)
- [ ] **Content has `## Auto-Links`** section (for code-relevant types: bugfix, decision, architecture, pattern, discovery, manual)

**Example:**
```json
{
  "title": "Fixed auth loop on token refresh",
  "content": "## Compiled Truth\n**What**: Replaced synchronous token refresh with async queue to prevent race conditions\n**Why**: Multiple concurrent requests triggered overlapping refreshes, invalidating each other's tokens\n**Where**: src/auth/refresh.ts, src/middleware/auth.ts\n**Learned**: Always debounce token refresh; never rely on client-side clock for expiry\n\n---\n## Timeline\n- 2026-04-26T17:00:00: Initial fix deployed\n\n## Auto-Links\n- src/auth/refresh.ts\n- src/middleware/auth.ts\n- TokenRefreshQueue",
  "type": "bugfix",
  "topic_key": "project/myapp/bugfix/auth-refresh-race"
}
```

## Corrections

If the user corrects something:

1. Call `brain_correct` immediately — don't wait until session end.
2. It automatically finds the old entry, marks it superseded, and saves the corrected version.

## Scope Hierarchy

Every project has its own memory store. There's also a global store for user-level preferences and role facts.

- **Project facts** (architecture, tech stack, bugs) → stay in the project brain.
- **User preferences** (coding style, tool preferences, communication tone) → go to global brain.
- **Never cross-write.** Don't put global facts in a project brain or project facts in global.

## Session End Protocol

Before saying "done" / "that's it" / "finished":

1. Save checkpoint if due (15+ min or 10+ tool calls elapsed).
2. Call `brain_session_summary` with complete Goal/Instructions/Discoveries/Accomplished/Next Steps/Relevant Files.
3. Call `brain_session_end` to formally close the session.

## Token Economy

- `brain_context` is cheap (~2K tokens). Call it every session.
- `brain_query` searches engram directly (fast, FTS5 full-text search).
- `brain_validate` is cheap (~500 tokens). Use it before every `brain_save`.
- `brain_codebase_search` is moderate cost (~3K tokens). Use when you need to find code patterns.
- If you only need a quick fact check, use `brain_query` with the default settings.
- For chronological context around a specific observation, use `engram_mem_timeline` directly.
