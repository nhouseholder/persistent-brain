# Claude Code setup

## 1. MCP servers

Edit `~/.claude.json`. Under the top-level object, add an `mcpServers` key (merge if it already exists):

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

Per-project overrides live in `<project>/.mcp.json` (written for you by `./scripts/brain-init.sh`).

## 2. Agent rules

Append the contents of `config/AGENTS.md` to `~/.claude/CLAUDE.md`, or include it verbatim. The rules route memory writes correctly between engram and mempalace.

## 3. Session-start hook (recommended)

Register `hooks/session-start.sh` in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "command": "~/.claude/hooks/persistent-brain-session-start.sh" }
    ]
  }
}
```

`install.sh` copies the script to `~/.claude/hooks/persistent-brain-session-start.sh` automatically — you only need to add the registration block.

## 4. Verify

```bash
# Inside Claude Code
/mcp

# Expected: both "engram" and "mempalace" listed, each with several tools.
```

## 5. Smoke test

Ask Claude: *"Remember: I prefer semicolons in TypeScript."* It should call `engram.mem_save`.

Then in a fresh session: *"What do I prefer for TS formatting?"* — the answer should pull from engram without asking.
