# Cursor setup

## 1. MCP servers

Cursor → Settings → MCP → Add new MCP server. Paste:

```json
{
  "mcpServers": {
    "engram": {
      "command": "engram",
      "args": ["mcp"]
    },
    "mempalace": {
      "command": "mempalace-mcp"
    }
  }
}
```

Or edit `~/.cursor/mcp.json` directly with the block above.

## 2. Agent rules

Create `.cursor/rules/persistent-brain.mdc` in your project root with `alwaysApply: true` frontmatter, then paste the contents of `config/AGENTS.md`:

```markdown
---
description: Persistent memory routing between engram and mempalace
alwaysApply: true
---

<paste config/AGENTS.md here>
```

Cursor injects this into every conversation automatically — no hook needed.

## 3. Verify

Open any project with Cursor, start a composer/chat, and ask: *"List your available MCP tools."* Engram + mempalace should both appear.

## 4. Notes

- Cursor's MCP support is stable in recent versions. If nothing shows up, check Settings → MCP → status (should be green).
- Cursor does not expose session hooks — the `.cursor/rules/*.mdc` file IS the always-on mechanism.
