# Troubleshooting unified-brain

## Installation Issues

### "Node.js required (18+)"

```bash
brew install node
```

Verify: `node --version` should show v18+.

### "uv not found"

CGC will fall back to pipx. To use uv (faster):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### "codecartographer not installed"

If you have a local build at `~/ProjectsHQ/codecartographer`:
```bash
cd ~/ProjectsHQ/codecartographer && npm link
```

Otherwise install from npm:
```bash
npm install -g codecartographer
```

### "engram not installed"
```bash
brew tap gentleman-programming/tap
brew install engram
```

## MCP Connection Issues

### "brain-router not found"

Ensure `~/.local/bin` is in your PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Or add to your shell profile:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

### "Unknown tool: brain_query"

The MCP client isn't wired to brain-router. Check your agent's MCP config:
- Claude Code: `~/.claude.json`
- Codex: `~/.codex/config.toml`
- Kimi: `~/.kimi/config.toml`
- OpenCode: `~/.opencode/settings.json`

Verify the `mcpServers` block from `config/mcp-servers.json` is present.

### MCP server starts but agent can't see tools

Some agents cache the tool list. Restart the agent or reload MCP config.

## Store Issues

### "engram DB not found"

Run project init:
```bash
./scripts/brain-init.sh /path/to/project
```

Or create manually:
```bash
mkdir -p ~/.engram
engram save "test" "test" --db ~/.engram/my-project.db
```

### "CGC indexing failed"

Check cgc is installed:
```bash
which cgc
cgc --version
```

Try manual index:
```bash
cgc add_code_to_graph /path/to/project --is-dependency=false
```

If it hangs on large repos, exclude directories with `.unified-brainignore`:
```
node_modules/
dist/
build/
```

### "CodeCartographer diagram failed"

Check codecartographer is installed:
```bash
which codecartographer
codecartographer --version
```

Try manual generation:
```bash
codecartographer diagram /path/to/project --backend memory
```

Common causes:
- Missing `dist/` directory → run `npm run build` in the codecartographer repo
- TypeScript compilation errors → check `tsconfig.json`

### "CodeCartographer timed out"

Large repos (>100K LOC) may timeout. Increase timeout in `brain_router.py`:
```python
_cc_run(["diagram", path], timeout=300)  # 5 minutes
```

Or run manually and save the report:
```bash
codecartographer diagram . --backend memory
```

## Validation Issues

### "Observation rejected: Missing Compiled Truth"

Your observation needs `## Compiled Truth` with `**What**` / `**Why**` / `**Where**` fields:

```markdown
## Compiled Truth
**What**: Fixed the auth loop
**Why**: Token refresh race condition
**Where**: src/auth/refresh.ts
```

### "Observation rejected: Missing Auto-Links"

For code-relevant types (bugfix, decision, architecture, etc.), add:
```markdown
## Auto-Links
- src/auth/refresh.ts
- TokenRefreshQueue
```

Or let brain_save auto-extract them by mentioning files/symbols in the content.

## Session Issues

### "No session state found"

Session state is in `~/.unified-brain/session_state.json`. If it's missing:
- The session-start hook didn't run
- Or `brain_session_start` wasn't called

Manually init:
```bash
# Via MCP
tools/call brain_session_start {"project": "myapp"}
```

### "Checkpoint suggestions not appearing"

Checkpoints are injected as `_checkpoint_suggestion` in tool responses. Your agent must:
1. Parse the JSON response
2. Check for the `_checkpoint_suggestion` field
3. Call `brain_checkpoint` when found

Some agents may not surface this field. In that case, manually call `brain_checkpoint` every 10 tool calls or 15 minutes.

## Performance Issues

### brain_query is slow (>500ms)

Possible causes:
- Large engram DB (1000+ observations) → normal, FTS5 is still fast
- DB on network drive → move to local SSD
- SQLite without FTS5 → rebuild: `engram rebuild`

### brain_codebase_index takes too long

Break it into steps:
```bash
# 1. CGC index only
cgc add_code_to_graph . --is-dependency=false

# 2. Diagram only (after index)
codecartographer diagram . --backend memory
```

### Multiple agents competing for engram DB

SQLite supports concurrent reads but not concurrent writes. If multiple agents write simultaneously:
- One will get "database is locked"
- Retry after a short delay

For heavy multi-agent use, consider running engram as a separate server process.

## Data Recovery

### Accidentally deleted observation

Engram doesn't have soft delete. Check if you have a backup:
```bash
ls ~/.engram/*.db.backup* 2>/dev/null
```

Or check git-synced chunks:
```bash
engram sync --dry-run
```

### Corrupted engram DB

SQLite has built-in recovery:
```bash
sqlite3 ~/.engram/my-project.db ".recover" > recovered.sql
sqlite3 ~/.engram/my-project.db.new < recovered.sql
mv ~/.engram/my-project.db.new ~/.engram/my-project.db
```

## Getting Help

1. Run `./scripts/brain-status.sh` for a full health check
2. Check `~/.unified-brain/config.yaml` for config issues
3. Review the handoff documents: `_handoff_*.md`
4. File an issue with the output of `brain-status.sh`
