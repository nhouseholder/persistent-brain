# Getting Started with unified-brain

## Prerequisites

- macOS or Linux (Windows → WSL)
- Homebrew
- Python 3.10+
- Node.js 18+
- Git

## Step 1: Install

```bash
git clone https://github.com/nhouseholder/unified-brain ~/unified-brain
cd ~/unified-brain
./install.sh
```

The installer will:
1. Check OS and prerequisites
2. Install `engram` via Homebrew tap
3. Install `cgc` via `uv tool install codegraphcontext` (or pipx fallback)
4. Install `codecartographer` via npm (local build or registry)
5. Link `brain-router` into `~/.local/bin`
6. Create `~/.unified-brain/config.yaml`
7. Install session hooks

If you have a legacy `persistent-brain` install, the installer detects it and preserves your existing engram DBs.

## Step 2: Verify

```bash
./scripts/brain-status.sh
```

You should see:
- ✅ engram: v1.12.0+
- ✅ cgc: installed
- ✅ codecartographer: installed
- ✅ brain-router: responds

## Step 3: Init Your First Project

```bash
./scripts/brain-init.sh ~/ProjectsHQ/my-project
```

This will:
1. Create `~/.engram/my-project.db`
2. Index the codebase with CGC (`cgc add_code_to_graph`)
3. Generate `GRAPH_REPORT.md` with CodeCartographer
4. Write `.mcp.json` in the project root
5. Write `AGENTS.md` in the project root
6. Write `.unified-brainignore` for exclusions

## Step 4: Wire Your Agent

Copy the MCP servers block from `config/mcp-servers.json` into your agent's config:

### Claude Code
```bash
# ~/.claude.json
cat config/mcp-servers.json >> ~/.claude.json
```

### Codex
```bash
# ~/.codex/config.toml
# Add the [mcpServers] block from config/mcp-servers.json
```

### Kimi CLI
```bash
# ~/.kimi/config.toml
# Add the MCP servers under [mcp]
```

### Cursor
```bash
mkdir -p ~/ProjectsHQ/my-project/.cursor/rules
cp config/AGENTS.md ~/ProjectsHQ/my-project/.cursor/rules/unified-brain.mdc
```

## Step 5: Start Coding

Launch your agent from the project directory:

```bash
cd ~/ProjectsHQ/my-project
# Launch your agent here — it will auto-load .mcp.json
```

The agent will:
1. Call `brain_context` on session start
2. Call `brain_codebase_index --check` to load/generate GRAPH_REPORT.md
3. Save facts with `brain_save` as you work
4. Get checkpoint suggestions every 10 tool calls or 15 minutes

## Step 6: End Session Properly

When you're done:
1. The agent should call `brain_session_summary` with a recap
2. Then call `brain_session_end` to close the session
3. The session-end hook syncs engram in the background

## Next Steps

- Read [config/AGENTS.md](../config/AGENTS.md) for the full agent protocol
- Read [docs/architecture.md](architecture.md) for technical details
- Read [docs/api-reference.md](api-reference.md) for all 15 tools
- Run `./scripts/brain-inspect.sh my-project` to see what the agent remembers
