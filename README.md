# persistent-brain

> **One memory brain. Every agent. Never lost.**

A portable, local-first, hybrid memory system for AI coding agents. Works across Claude Code, Codex, Qwen Code, Kimi K2 (via Cline/OpenCode), Cursor, Gemini CLI, and anything else speaking MCP.

**The problem.** Every session, your agent forgets. Swap tools (Claude → Qwen) and you lose even more. Claude-only memory systems (e.g., Claude plugins, Supermemory) die the moment you change frontends.

**The fix.** A unified brain-router that sits on top of two specialized stores:

- **[engram](https://github.com/Gentleman-Programming/engram)** — structured decisions, preferences, fixes (SQLite + FTS5, one tiny Go binary, git-syncable).
- **[MemPalace](https://github.com/MemPalace/mempalace)** — verbatim conversation recall (ChromaDB, 96.6% R@5 on LongMemEval, zero API calls).
- **brain-router** — unified MCP server that auto-routes queries across both stores, detects conflicts, and exposes 5 high-level tools.

Neither tool is agent-specific. Any MCP client sees the same brain with the same data.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Agent (Claude Code / Codex / Qwen / Kimi K2 / Cursor / …)  │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP stdio
                 ┌───────▼────────┐
                 │  brain-router  │  ← unified query/save interface
                 │  (Python, 0    │
                 │   dependencies)│
                 └──┬──────────┬──┘
                    │          │
            ┌───────▼────┐ ┌──▼──────────┐
            │  engram    │ │ mempalace   │
            │ (struct.)  │ │ (verbatim)  │
            └──────┬─────┘ └──────┬──────┘
            ┌──────▼─────┐ ┌──────▼──────┐
            │ SQLite+FTS5│ │ ChromaDB    │
            │ ~/.engram/ │ │ ~/.mempalace│
            └────────────┘ └─────────────┘
```

**The agent calls `brain_query` for everything.** The router decides which store to hit:
1. Search engram first (fast, structured, <50ms)
2. Fall back to mempalace only when engram has no answer or verbatim recall is requested

**No more routing errors.** The LLM doesn't have to guess which store has the answer.

### Tools

| Tool | Purpose |
|---|---|
| `brain_query` | Search all memories (auto-routes to the right store) |
| `brain_save` | Save a structured fact with conflict detection |
| `brain_context` | Load session-start context (project + global) |
| `brain_correct` | Fix a wrong memory (auto-supersedes old entry) |
| `brain_forget` | Delete a memory across both stores |

### Session Lifecycle

```
session-start.sh          session-end.sh
      │                         │
      ▼                         ▼
  engram.session-start     1. mempalace.latest → engram.capture-passive
  brain_context               (auto-distill up to 5 key facts)
  (load memories)          2. engram.session-end
                           3. mempalace.compress
                           4. engram.sync
```

**Session-end auto-distillation** catches anything the agent forgot to save. No more lost facts from crashed or rushed sessions.

---

## Quickstart

```bash
git clone https://github.com/nhouseholder/persistent-brain ~/persistent-brain
cd ~/persistent-brain
./install.sh
```

Installs `engram` (Homebrew tap), `mempalace` (pipx), `brain-router` (zero-dep Python), hooks (session-start + session-end + pre-compact), and initialises your global brain.

Then, per project:

```bash
./scripts/brain-init.sh ~/ProjectsHQ/my-app
```

Creates a project-scoped engram DB + mempalace palace, and drops a `.mcp.json` + `AGENTS.md` into the project so the agent auto-loads brain-router with the right scope.

### Inspect what the agent knows

```bash
./scripts/brain-inspect.sh my-app
```

Shows session context, memory type distribution, recent saves, mempalace status, disk usage, and a map of all project brains.

---

## Supported agents

Config snippets in [examples/](examples/):

| Agent | Setup |
|---|---|
| Claude Code | [claude-code-setup.md](examples/claude-code-setup.md) |
| Codex | [codex-setup.md](examples/codex-setup.md) |
| Qwen Code | [qwen-setup.md](examples/qwen-setup.md) |
| Kimi K2 (via Cline/OpenCode) | [kimi-k2-setup.md](examples/kimi-k2-setup.md) |
| Cursor | [cursor-setup.md](examples/cursor-setup.md) |

Any MCP-capable client works. If yours isn't listed, drop the block from [config/mcp-servers.json](config/mcp-servers.json) into its MCP config.

---

## Routing rules

The brain-router handles routing automatically. Full explanation: [docs/routing-rules.md](docs/routing-rules.md). Agent instructions: [config/AGENTS.md](config/AGENTS.md).

## Sync across machines

- **engram** — git-sync compressed chunks. See [docs/sync-strategy.md](docs/sync-strategy.md).
- **mempalace** — vector DB is too large for git; use rsync/SCP. The `brain-sync.sh` script has an `--rsync <host>` flag.

## Status + troubleshooting

```bash
./scripts/brain-status.sh     # health check both stores
./scripts/brain-inspect.sh    # see what the agent knows
```

Common issues: [docs/troubleshooting.md](docs/troubleshooting.md).

---

## Design Principles

1. **One query, both stores.** The agent never picks the wrong store — the router handles dispatch.
2. **Auto-distill on session end.** Every session's key facts are automatically extracted — no manual `mem_save` required.
3. **Conflict detection on write.** Contradictions are caught when saving, not discovered during retrieval.
4. **Zero external dependencies.** The router is pure Python 3.10+ stdlib. No pip install, no venv.
5. **Agent-agnostic.** MCP is the only interface. Any client that speaks MCP gets the full brain.

## License

MIT. See [LICENSE](LICENSE).
