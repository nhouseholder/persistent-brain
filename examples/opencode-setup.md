# OpenCode setup

## 1. MCP servers

Edit `~/.opencode/settings.json`. Under the top-level object, add an `mcpServers` key (merge if it already exists):

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

Append the contents of `config/AGENTS.md` to `~/.opencode/OPENCODE.md`, or include it verbatim. The rules route memory writes correctly between engram and mempalace.

## 3. Session-start hook (recommended)

Register `hooks/session-start.sh` in `~/.opencode/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "command": "~/.opencode/hooks/persistent-brain-session-start.sh" }
    ]
  }
}
```

`install.sh` copies the script to `~/.opencode/hooks/persistent-brain-session-start.sh` automatically — you only need to add the registration block.

## 4. Verify

```bash
# Inside OpenCode
/mcp

# Expected: both "engram" and "mempalace" listed, each with several tools.
```

## 5. Smoke test

Ask OpenCode: *"Remember: I prefer semicolons in TypeScript."* It should call `engram.mem_save`.

Then in a fresh session: *"What do I prefer for TS formatting?"* — the answer should pull from engram without asking.
