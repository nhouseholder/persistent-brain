# persistent-brain

> **One memory brain. Every agent. Never lost.**

A portable, local-first, hybrid memory system for AI coding agents. Works across Claude Code, Codex, Qwen Code, Kimi K2 (via Cline/OpenCode), Cursor, Gemini CLI, and anything else speaking MCP.

**The problem.** Every session, your agent forgets. Swap tools (Claude → Qwen) and you lose even more. Claude-only memory systems (e.g., Claude plugins, Supermemory) die the moment you change frontends.

**The fix.** Two MCP servers running side-by-side:

- **[engram](https://github.com/Gentleman-Programming/engram)** — structured decisions, preferences, fixes (SQLite + FTS5, one tiny Go binary, git-syncable).
- **[MemPalace](https://github.com/MemPalace/mempalace)** — verbatim conversation recall (ChromaDB, 96.6% R@5 on LongMemEval, zero API calls).

Neither tool is agent-specific. Any MCP client sees both stores with the same data.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Agent (Claude Code / Codex / Qwen / Kimi K2 / Cursor / …)  │
└────────────┬────────────────────────────────┬───────────────┘
             │ MCP stdio                      │ MCP stdio
     ┌───────▼────────┐              ┌────────▼─────────┐
     │  engram        │              │  mempalace       │
     │  (structured)  │              │  (verbatim)      │
     └───────┬────────┘              └────────┬─────────┘
             │                                │
     ┌───────▼────────┐              ┌────────▼─────────┐
     │ SQLite + FTS5  │              │ ChromaDB vector  │
     │ ~/.engram/     │              │ ~/.mempalace/    │
     └────────────────┘              └──────────────────┘
```

**Hybrid scope:** one global brain (prefs / role / cross-project facts) + one brain per project. Inside a project, the agent reads both.

**Routing:**
- Decisions, preferences, architecture, fix takeaways → `engram.mem_save` (hot, structured)
- "What did we discuss about X last week?" → `mempalace.search` (cold, verbatim)
- Session start → agent pulls `mem_context` from engram (project + global) before first reply

---

## Quickstart

```bash
git clone https://github.com/nhouseholder/persistent-brain ~/persistent-brain
cd ~/persistent-brain
./install.sh
```

Installs `engram` (via Homebrew tap) and `mempalace` (via pipx), writes MCP config snippets for every supported agent, installs a session-start hook, and initialises your global brain.

Then, per project:

```bash
./scripts/brain-init.sh ~/ProjectsHQ/my-app
```

Creates a project-scoped engram DB + mempalace palace, and drops a `.mcp.json` + `AGENTS.md` into the project so the agent auto-loads the right brain.

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

The glue between the two stores is a short, agent-agnostic ruleset in [config/AGENTS.md](config/AGENTS.md). `install.sh` drops it into the right file for each agent (`CLAUDE.md`, `AGENTS.md`, Cursor rules, etc.). Full explanation: [docs/routing-rules.md](docs/routing-rules.md).

## Sync across machines

- **engram** — git-sync compressed chunks. See [docs/sync-strategy.md](docs/sync-strategy.md).
- **mempalace** — vector DB is too large for git; use rsync/SCP. The `brain-sync.sh` script has an `--rsync <host>` flag.

## Status + troubleshooting

```bash
./scripts/brain-status.sh    # health check both stores
```

Common issues: [docs/troubleshooting.md](docs/troubleshooting.md).

---

## Non-goals

- No custom MCP bridge server (both stores stay independent).
- No team-shared brains (different problem; use Supermemory if that's what you need).
- No Windows native support (WSL only for now).
- No Obsidian / knowledge-graph export (use [graphify](https://github.com/safishamsi/graphify) separately if you want that).

## License

MIT. See [LICENSE](LICENSE).
