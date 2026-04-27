# unified-brain

> **One brain. Three layers. Every agent. Never lost.**

A unified, local-first persistent memory system for AI coding agents. Works across Claude Code, Codex, Kimi, Cursor, Qwen, Aider, and anything else speaking MCP.

**The problem.** Every session, your agent forgets. Swap tools (Claude → Kimi) and you lose even more. Frontend-specific memory systems die the moment you change agents.

**The fix.** A unified `brain-router` MCP server that combines three complementary memory stores through one interface:
- **engram** — temporal memory (what we DID): decisions, bugfixes, preferences, session history
- **CGC** — structural memory (what the code IS): call graphs, complexity, dead code
- **CodeCartographer** — enriched structural memory: GRAPH_REPORT.md, hybrid search, typed relationships

**One query, one interface.** The agent never picks the wrong store — the router handles dispatch automatically.

---

## Architecture (v0.6.0 — Three-Layer Memory + Reasoning)

```
┌─────────────────────────────────────────────────────────┐
│  Agent (Claude / Codex / Kimi / Cursor / Qwen / …)      │
└────────────────────────┬────────────────────────────────┘
                         │ MCP stdio
                 ┌───────▼────────┐
                 │  brain-router  │  ← UNIFIED MCP SERVER
                 │  (Python, 0    │     18 tools, 0 dependencies
                 │   dependencies)│
                 └───────┬────────┘
                         │
      ┌──────────────────┼──────────────────┐
      ▼                  ▼                  ▼
┌──────────┐    ┌──────────────┐    ┌──────────────┐
│  engram  │    │      CGC     │    │CodeCartographer│
│(temporal)│    │ (structural) │    │ (enrichment)   │
│SQLite+   │    │ FalkorDB     │    │ GRAPH_REPORT.md│
│FTS5      │    │ Graph        │    │ Hybrid search  │
│Compiled  │    │ Callers      │    │ Typed edges    │
│Truth+    │    │ Complexity   │    │                │
│Timeline  │    │ Dead code    │    │                │
└──────────┘    └──────────────┘    └──────────────┘
```

**Three-layer memory:**
- **engram** = temporal memory — what we DID, decisions, bugfixes, preferences, session history
- **CGC** = structural memory — what the code IS, call graphs, complexity, dead code
- **CodeCartographer** = enriched structural memory — GRAPH_REPORT.md generation, hybrid semantic search (BM25 + embeddings + RRF), typed relationships (TESTS/EXPORTS/EXTENDS/IMPLEMENTS)

---

## Install

```bash
git clone https://github.com/nhouseholder/unified-brain ~/unified-brain
cd ~/unified-brain
./install.sh
```

Installs:
- `engram` (Homebrew tap) — temporal memory
- `cgc` (uv/pipx) — structural graph
- `codecartographer` (npm) — enriched diagrams + hybrid search
- `brain-router` (zero-dep Python) — unified MCP server
- Hooks — session start/end, pre-commit reindex

**Prerequisites:** macOS or Linux, Homebrew, Python 3.10+, Node.js 18+

---

## Quickstart

```bash
# Per-project init (indexes codebase + generates GRAPH_REPORT.md)
./scripts/brain-init.sh ~/ProjectsHQ/my-app

# Health check
./scripts/brain-status.sh

# Inspect memories
./scripts/brain-inspect.sh my-app
```

Then launch your agent from the project directory. The `.mcp.json` file auto-wires brain-router.

---

## 18 MCP Tools

| Tool | Store | Purpose |
|---|---|---|
| `brain_query` | engram | Search temporal memory (FTS5) |
| `brain_save` | engram | Save observation with auto-validation |
| `brain_context` | engram | Load session-start context |
| `brain_correct` | engram | Fix/update observation |
| `brain_forget` | engram | Delete observation |
| `brain_validate` | engram | Validate Compiled Truth + Auto-Links before saving |
| `brain_diagram` | CGC | Get codebase stats, complexity, dead code |
| `brain_callers` | CGC | Find who calls a function |
| `brain_structure` | CGC | Get repo structural stats |
| `brain_codebase_index` | CGC + CodeCartographer | Index project + generate GRAPH_REPORT.md |
| `brain_codebase_search` | CodeCartographer | Hybrid semantic search across code |
| `brain_session_start` | engram | Start tracked session |
| `brain_session_end` | engram | End tracked session |
| `brain_checkpoint` | engram | Save checkpoint observation |
| `brain_session_stats` | engram | Get live session statistics |
| `brain_reason` | — | Declare reasoning mode + get budget |
| `brain_calibrate` | engram | Save calibration data after SLOW tasks |
| `brain_calibration_stats` | engram | View calibration aggregates |

Full API reference: [docs/api-reference.md](docs/api-reference.md)

---

## Session Lifecycle (Automated)

```
Agent starts session
    ↓
Hook auto-calls:
  1. brain_context (load recent memories)
  2. brain_codebase_index --check (load/generate GRAPH_REPORT.md)
  3. brain_reason (declare FAST/DELIBERATE/SLOW mode + budget)
    ↓
Agent works, calls brain_save after significant work
  - Router auto-counts evidence pulls against budget
  - Budget breach triggers escalation warning
  - Auto-validates Compiled Truth format
  - Auto-extracts Auto-Links
  - Checkpoint suggested every 10 calls / 15 min
    ↓
Agent says "done"
    ↓
Hook auto-calls:
  1. Checkpoint save (if due)
  2. brain_session_summary (mandatory)
  3. brain_session_end (mandatory)
```

---

## Observation Format

All observations use **Compiled Truth + Timeline + Auto-Links**:

```markdown
## Compiled Truth
**What**: [concise description]
**Why**: [reasoning or problem]
**Where**: [files/paths affected]
**Learned**: [gotchas or edge cases]

---
## Timeline
- 2026-04-26T17:00:00: Initial implementation
- 2026-04-26T18:00:00: Discovered edge case, fixed

## Auto-Links
- src/auth/refresh.ts
- TokenRefreshQueue
- myproject
```

`brain_save` auto-fixes missing sections and rejects unfixable observations.

---

## Supported Agents

| Agent | Setup | Status |
|---|---|---|
| Claude Code | `~/.claude.json` mcpServers block | ✅ Tested |
| Codex | `~/.codex/config.toml` | ✅ Tested |
| Kimi (Kimi CLI) | `~/.kimi/config.toml` | ✅ Tested |
| Cursor | `.cursor/rules/unified-brain.mdc` | ✅ Tested |
| OpenCode | `~/.opencode/settings.json` | ✅ Tested |
| Qwen Code | See docs/agent-setup.md | 🔄 Planned |
| Aider | See docs/agent-setup.md | 🔄 Planned |

Any MCP-capable client works. Config snippets in [config/mcp-servers.json](config/mcp-servers.json).

---

## Documentation

| Doc | Purpose |
|---|---|
| [docs/getting-started.md](docs/getting-started.md) | Step-by-step for new users |
| [docs/architecture.md](docs/architecture.md) | Technical deep-dive |
| [docs/agent-setup.md](docs/agent-setup.md) | Per-agent configuration |
| [docs/api-reference.md](docs/api-reference.md) | Full tool reference |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common issues |
| [config/AGENTS.md](config/AGENTS.md) | Agent instruction protocol |

---

## Design Principles

1. **One query, one interface.** The agent never picks the wrong store — the router handles dispatch.
2. **Explicit saves with validation.** Agents must save structured facts manually — but `brain_save` auto-validates and auto-fixes format.
3. **Conflict detection on write.** Contradictions are caught when saving, not discovered during retrieval.
4. **Zero external dependencies for the router.** Pure Python 3.10+ stdlib. Stores have their own installers.
5. **Agent-agnostic.** MCP is the only interface. Any client that speaks MCP gets the full brain.
6. **Session automation.** Start/end hooks + checkpoint tracking reduce manual bookkeeping.

---

## License

MIT. See [LICENSE](LICENSE).
