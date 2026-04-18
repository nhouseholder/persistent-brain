# Qwen Code setup

Qwen Code (Alibaba's coding CLI) supports MCP via its config file.

## 1. MCP servers

Edit `~/.qwen/config.json` (or the Qwen-equivalent — check `qwen --help` for the config path on your version). Add:

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

## 2. Agent rules

Copy `config/AGENTS.md` to `~/.qwen/AGENTS.md` (or whichever instruction-file convention Qwen uses — newer versions support a `context` directive in the config that points at a rules file).

Project-level override lives in `<project>/AGENTS.md` (written by `brain-init.sh`).

## 3. Verify

```bash
qwen
# Ask: "list your MCP tools"
# Expected: engram.* and mempalace.* tools present.
```

## 4. Notes

- Qwen's MCP client is still maturing. If stdio tools don't register, try launching with `QWEN_MCP_DEBUG=1 qwen` and check logs.
- Engram + mempalace both expose stdio MCP, which is the baseline Qwen supports.
