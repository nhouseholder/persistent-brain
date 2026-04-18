# Troubleshooting

## `engram: command not found` after install

Homebrew's bin dir isn't on PATH. Add to your shell rc:

```bash
export PATH="/opt/homebrew/bin:$PATH"       # Apple Silicon
export PATH="/usr/local/bin:$PATH"          # Intel Mac
```

## `mempalace: command not found` after install

pipx installs to `~/.local/bin`, which isn't always on PATH. Run:

```bash
pipx ensurepath
exec $SHELL -l   # reload shell
```

## `/mcp` in Claude Code shows no engram/mempalace

1. Check MCP config is in the right file: `~/.claude.json` (not `~/.claude/settings.json`).
2. Restart Claude Code fully (quit + reopen — hot reload doesn't reliably pick up new MCP servers).
3. Check `/mcp` output for errors — a non-zero exit from either server will show the stderr.

## Mempalace errors on startup: "no palace at ..."

The palace directory doesn't exist or was deleted. Recreate:

```bash
mempalace --palace ~/.mempalace/global init
```

For project palaces, rerun `./scripts/brain-init.sh <project-path>`.

## Engram says "database is locked"

SQLite concurrency — two agents writing to the same DB at the same instant. Engram retries automatically; if it keeps failing, check that you don't have a stale `engram mcp` process hanging:

```bash
ps aux | grep '[e]ngram mcp'
# kill any stale ones
```

## Mempalace search returns nothing despite recent conversations

Mempalace needs the auto-save hook to populate. Check:

1. `mempalace --palace ~/.mempalace/<project> status` — does it show non-zero sessions?
2. If zero: the PostToolUse hook isn't firing. Re-register it per your agent's hook config.
3. If non-zero but search is empty: try `mempalace --palace <path> mine` to re-index.

## Per-project brain not loading (loads global instead)

The agent is reading the global MCP config, not the project `.mcp.json`. Fix:

1. Confirm `<project>/.mcp.json` exists (`brain-init.sh` creates it).
2. Launch the agent from the project directory — most agents pick up project MCP configs automatically only when `cwd` matches.
3. For Claude Code specifically: the project `.mcp.json` is picked up on session start when you open Claude Code inside the project folder.

## "I ran install.sh and the hook didn't register"

`install.sh` copies the hook file but does **not** edit your `~/.claude/settings.json` — we don't touch hook registrations automatically. Add the `SessionStart` entry manually per `examples/claude-code-setup.md`.

## Disk usage creeping up

- Engram: tiny (SQLite, FTS5). Not the problem.
- Mempalace: Chroma can grow fast. Periodic cleanup:
  ```bash
  mempalace --palace ~/.mempalace/global compress
  ```
  This deduplicates and reindexes.

If a project palace is huge and you want to archive it:

```bash
tar czf ~/archives/mempalace-<project>-$(date +%Y%m%d).tgz ~/.mempalace/<project>
rm -rf ~/.mempalace/<project>
```
