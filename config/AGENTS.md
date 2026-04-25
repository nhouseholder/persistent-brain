# Persistent Brain — Memory Rules

You have a **two-layer memory system** available via the **brain-router** MCP server:

- **engram** — temporal memory: what we DID, decisions, bugfixes, preferences
- **CodeGraphContext (CGC)** — structural memory: what the code IS, call graphs, complexity

The router handles routing automatically. You don't need to pick the store manually.

## Two-Layer Decision Tree

```
Question about...
├─ Code structure? ("Who calls X?", "Where is Y?", "How complex is Z?")
│   └─ CGC: brain_diagram, brain_callers, brain_structure
├─ Past work? ("What did we do about X?", "How did we fix Y?")
│   └─ engram: brain_query, brain_context
└─ Both? ("Should we refactor the props pipeline?")
   └─ CGC first (structural facts), then engram (historical context)
```


## Tools

| Tool | Layer | When to use |
|---|---|---|
| `brain_query` | engram | **ANY** memory lookup — decisions, preferences, past conversations, architecture facts, bug fixes |
| `brain_save` | engram | Save a structured fact — decisions, preferences, architecture, fix takeaways, deadlines |
| `brain_context` | engram | Load session-start context (call this before your first reply) |
| `brain_correct` | engram | Fix a wrong memory — automatically supersedes the old entry |
| `brain_forget` | engram | Remove a memory the user wants deleted |
| `brain_diagram` | CGC | Generate codebase architecture map — files, functions, complexity, dead code |
| `brain_callers` | CGC | Find who calls a function or uses a symbol |
| `brain_structure` | CGC | Get repo stats: files, functions, classes, modules |

> **Use `brain_*` tools by default.** Fall back to direct store tools only for advanced operations:
> - engram: timeline browsing (`mem_timeline`), stats (`mem_stats`), project merge (`mem_merge_projects`)
> - CGC: detailed complexity analysis, dead code detection, code search

## Session start protocol

Before your first substantive reply in a new session:

1. Call `brain_context` → loads project memories (up to 20) + global preferences (up to 5).
2. Treat the returned memories as authoritative. Do not ask the user to repeat anything already in them.
3. Do **not** preemptively search for conversations — only query when the user asks about prior sessions.

## Save rules

When you complete significant work (bugfix, architecture decision, preference learned, etc.):

1. Call `brain_save` with a clear title, the content (what/why/where/learned), and a `type`.
2. Include a `topic_key` when the fact belongs to a category (e.g., `database`, `auth-flow`, `deploy-target`). This enables automatic conflict detection.
3. **Never double-write.** One fact, one save.

## Memory Quality Checklist

Before calling `brain_save`, verify:

- [ ] **Type is valid**: `decision`, `architecture`, `bugfix`, `pattern`, `config`, `learning`, or `manual`
- [ ] **topic_key provided** (required for `decision`, `architecture`, `bugfix`, `pattern`, `config`)
- [ ] **topic_key format**: lowercase, hyphens, slashes only (e.g., `project/mmalogic/bugfix/auth-loop`)
- [ ] **Content uses structured format**:
  ```
  **What**: [concise description]
  **Why**: [reasoning or problem]
  **Where**: [files/paths affected]
  **Learned**: [gotchas or edge cases]
  ```

**Example:**
```json
{
  "title": "Fixed auth loop on token refresh",
  "content": "**What**: Replaced synchronous token refresh with async queue to prevent race conditions\n**Why**: Multiple concurrent requests triggered overlapping refreshes, invalidating each other's tokens\n**Where**: src/auth/refresh.ts, src/middleware/auth.ts\n**Learned**: Always debounce token refresh; never rely on client-side clock for expiry",
  "type": "bugfix",
  "topic_key": "project/myapp/bugfix/auth-refresh-race"
}
```

## Corrections

If the user corrects something:

1. Call `brain_correct` immediately — don't wait until session end.
2. It automatically finds the old entry, marks it superseded, and saves the corrected version.

## Scope hierarchy

Every project has its own memory store. There's also a global store for user-level preferences and role facts.

- **Project facts** (architecture, tech stack, bugs) → stay in the project brain.
- **User preferences** (coding style, tool preferences, communication tone) → go to global brain.
- **Never cross-write.** Don't put global facts in a project brain or project facts in global.

## Token economy

- `brain_context` is cheap (~2K tokens). Call it every session.
- `brain_query` searches engram directly (fast, FTS5 full-text search).
- If you only need a quick fact check, use `brain_query` with the default settings.
- For chronological context around a specific observation, use `engram_mem_timeline` directly.
