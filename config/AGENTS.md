# Persistent Brain — Memory Rules

You have a unified memory system available via the **brain-router** MCP server. It routes queries to engram (structured facts) automatically — you don't need to manage stores manually.

## Tools

| Tool | When to use |
|---|---|
| `brain_query` | **ANY** memory lookup — decisions, preferences, past conversations, architecture facts, bug fixes |
| `brain_save` | Save a structured fact — decisions, preferences, architecture, fix takeaways, deadlines |
| `brain_context` | Load session-start context (call this before your first reply) |
| `brain_correct` | Fix a wrong memory — automatically supersedes the old entry |
| `brain_forget` | Remove a memory the user wants deleted |

> **You also have direct access to `engram` MCP tools.** Use the `brain_*` tools by default — fall back to direct engram tools only for advanced operations (timeline, stats, manual session management).

## Session start protocol

Before your first substantive reply in a new session:

1. Call `brain_context` → loads project memories (up to 20) + global preferences (up to 5).
2. Treat the returned memories as authoritative. Do not ask the user to repeat anything already in them.
3. Do **not** preemptively search for conversations — only query when the user asks about prior sessions.

## Save rules

When you complete significant work (bugfix, architecture decision, preference learned, etc.):

1. Call `brain_save` with a clear title, the content (what/why/where/learned), and a `type`.
2. Include a `topic_key` when the fact belongs to a category (e.g., `database`, `auth-flow`, `deploy-target`). This enables automatic conflict detection.
3. **Never double-write.** One fact, one save. The session-end hook will auto-distill anything you missed.

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
