# Agent Setup Guide

unified-brain works with any MCP-capable agent. This guide covers the most common ones.

## Quick Reference

All agents need the same MCP servers block. Copy from `config/mcp-servers.json`:

```json
{
  "mcpServers": {
    "brain-router": {
      "command": "brain-router",
      "env": {
        "BRAIN_PROJECT": "my-project",
        "ENGRAM_DB": "/Users/you/.engram/my-project.db"
      }
    },
    "engram": {
      "command": "engram",
      "args": ["mcp"],
      "env": { "ENGRAM_DB": "/Users/you/.engram/my-project.db" }
    }
  }
}
```

## Claude Code

Config file: `~/.claude.json`

```bash
# Merge the mcpServers block into ~/.claude.json
jq -s '.[0] * .[1]' ~/.claude.json config/mcp-servers.json > /tmp/claude.json && mv /tmp/claude.json ~/.claude.json
```

Or manually edit `~/.claude.json` and add the `mcpServers` block.

**Hooks:**
```bash
mkdir -p ~/.claude/hooks
cp hooks/session-start.sh ~/.claude/hooks/unified-brain-session-start.sh
cp hooks/session-end.sh ~/.claude/hooks/unified-brain-session-end.sh
cp hooks/pre-compact.sh ~/.claude/hooks/unified-brain-pre-compact.sh
chmod +x ~/.claude/hooks/unified-brain-*.sh
```

Register in `~/.claude.json`:
```json
{
  "hooks": {
    "SessionStart": "~/.claude/hooks/unified-brain-session-start.sh",
    "SessionEnd": "~/.claude/hooks/unified-brain-session-end.sh",
    "PreCompact": "~/.claude/hooks/unified-brain-pre-compact.sh"
  }
}
```

## Codex

Config file: `~/.codex/config.toml`

```toml
[mcpServers.brain-router]
command = "brain-router"
env = { BRAIN_PROJECT = "my-project", ENGRAM_DB = "/Users/you/.engram/my-project.db" }

[mcpServers.engram]
command = "engram"
args = ["mcp"]
env = { ENGRAM_DB = "/Users/you/.engram/my-project.db" }
```

## Kimi CLI

Config file: `~/.kimi/config.toml`

```toml
[mcp]
servers = [
  { name = "brain-router", command = "brain-router", env = { BRAIN_PROJECT = "my-project" } },
  { name = "engram", command = "engram", args = ["mcp"] }
]
```

**Skills:** Copy the memory-protocol skill:
```bash
mkdir -p ~/.kimi/skills/unified-brain
cp config/AGENTS.md ~/.kimi/skills/unified-brain/SKILL.md
```

## Cursor

Cursor uses `.cursor/rules/` for agent instructions and `.mcp.json` for MCP config.

**Agent rules:**
```bash
mkdir -p .cursor/rules
cp config/AGENTS.md .cursor/rules/unified-brain.mdc
```

**MCP config:** Add to your global Cursor MCP settings or project `.cursor/mcp.json`.

## OpenCode

Config file: `~/.opencode/settings.json`

Add the `mcpServers` block from `config/mcp-servers.json`.

**Hooks:**
```bash
mkdir -p ~/.opencode/hooks
cp hooks/session-start.sh ~/.opencode/hooks/unified-brain-session-start.sh
cp hooks/session-end.sh ~/.opencode/hooks/unified-brain-session-end.sh
chmod +x ~/.opencode/hooks/unified-brain-*.sh
```

Register in `~/.opencode/settings.json`:
```json
{
  "hooks": {
    "SessionStart": "~/.opencode/hooks/unified-brain-session-start.sh",
    "SessionEnd": "~/.opencode/hooks/unified-brain-session-end.sh"
  }
}
```

## Qwen Code

🔄 Planned — contributions welcome.

## Aider

🔄 Planned — Aider supports `.aider.conf.yml` for MCP configuration. Contributions welcome.

## Generic MCP Client

Any client supporting MCP stdio transport:

1. Set environment variables:
   ```bash
   export BRAIN_PROJECT="my-project"
   export ENGRAM_DB="$HOME/.engram/my-project.db"
   ```

2. Start the server:
   ```bash
   brain-router
   ```

3. Send JSON-RPC requests over stdin.

## Per-Project Configuration

Run `./scripts/brain-init.sh /path/to/project` to auto-generate:
- `.mcp.json` — MCP server config with correct project name
- `AGENTS.md` — Agent instructions for this project
- `.unified-brainignore` — Files to exclude from indexing

Then launch your agent from the project directory.

## Troubleshooting Agent Connection

| Symptom | Fix |
|---|---|
| "brain-router not found" | Ensure `~/.local/bin` is in PATH |
| "engram DB not found" | Run `./scripts/brain-init.sh <project-path>` |
| "Unknown tool: brain_query" | Check MCP config has brain-router server registered |
| Hooks not firing | Verify hook paths in agent config and chmod +x |
