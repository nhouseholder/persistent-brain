# Kimi K2 setup (via Cline or OpenCode)

Kimi K2 (Moonshot AI) is typically reached through an MCP-capable frontend — Cline (VS Code extension), OpenCode, or Aider — pointed at Moonshot's API. All of those frontends handle MCP, so the persistent brain plugs in the same way.

## Path A: Cline (VS Code)

Open Cline's MCP settings (command palette → "Cline: Open MCP Settings"). Add:

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

Set Cline's model to `kimi-k2` (Moonshot provider). Drop `config/AGENTS.md` into Cline's custom instructions field.

## Path B: OpenCode

```bash
engram setup opencode
```

Then manually add mempalace to `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "mempalace": {
      "type": "local",
      "command": ["mempalace-mcp"]
    }
  }
}
```

Config `config/AGENTS.md` goes into `AGENTS.md` in your project root — OpenCode reads it automatically.

## Path C: Aider

Aider supports MCP via its `--mcp` flag or `.aider.conf.yml`:

```yaml
mcp:
  engram:
    command: engram
    args: [mcp]
  mempalace:
    command: mempalace-mcp
```

Model: `aider --model openrouter/moonshotai/kimi-k2`.

## Verify

In whichever frontend you picked, ask Kimi: *"What MCP tools do you have access to?"* — it should list engram and mempalace tools.

## Notes

- Kimi K2's tool-calling is strong but strict about schemas. If you see errors, bump engram/mempalace versions — newer releases tightened JSON schema compliance.
- Moonshot's context is very large (128K+), so you can safely expose more `mem_context` entries than you would with smaller models.
