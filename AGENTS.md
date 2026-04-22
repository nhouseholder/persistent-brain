# persistent-brain — Agent Instructions

## Memory

Three MCP servers are wired for this project via `.mcp.json`:

- **brain-router** — unified query/save interface (use this by default)
- **engram** — direct access to structured facts: `/Users/nicholashouseholder/.engram/persistent-brain.db`
- **mempalace** — direct access to conversation recall: `/Users/nicholashouseholder/.mempalace/persistent-brain`

### Quick reference

| Action | Tool |
|---|---|
| Search memories | `brain_query` |
| Save a fact | `brain_save` |
| Load session context | `brain_context` |
| Fix a wrong memory | `brain_correct` |
| Delete a memory | `brain_forget` |

### Session start protocol
1. Call `brain_context` before your first reply.
2. Treat returned memories as authoritative — don't re-ask.
3. Save structured facts with `brain_save` as you work.
4. Session-end hook auto-distills anything you missed.

Full rules: https://github.com/nhouseholder/persistent-brain/blob/main/config/AGENTS.md
