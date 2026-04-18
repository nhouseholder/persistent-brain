# Codex (OpenAI CLI) setup

## 1. MCP servers

Edit `~/.codex/config.toml`. Add:

```toml
[mcp_servers.engram]
command = "engram"
args    = ["mcp"]

[mcp_servers.mempalace]
command = "mempalace-mcp"
args    = []
```

Also ensure `[features]` enables multi-agent if you want parallel tool use:

```toml
[features]
multi_agent = true
```

## 2. Agent rules

Append the contents of `config/AGENTS.md` to `~/.codex/AGENTS.md`. Codex reads this every session.

## 3. Verify

```bash
codex
# then at the prompt:
$engram
# should list engram tools
```

## 4. Notes

- Codex uses `$` to invoke skills, not `/`.
- Codex does support PreToolUse hooks (`~/.codex/hooks.json`) if you want `session-start.sh` to fire — adapt the Claude Code example.
- Mempalace quality depends on OpenAI not truncating long tool outputs. If you see short returns, set `max_output_tokens` higher under `[limits]`.
