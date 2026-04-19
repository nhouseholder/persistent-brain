# Quick Reference — persistent-brain

## What This Is
A local-first, permanent memory system for AI agents. Works across **OpenCode, Claude Code, Codex, VS Code/Copilot Chat, Cursor, Antigravity**. Every agent shares the same brain.

## Architecture
- **engram** = structured facts (SQLite + FTS5, <50ms search)
- **mempalace** = verbatim conversation recall (ChromaDB vector search)
- **brain-router** = unified MCP server that auto-routes between both

## Setup (one-time)
```bash
git clone https://github.com/nhouseholder/persistent-brain ~/persistent-brain
cd ~/persistent-brain && ./install.sh
```

## Per-Project (run once per repo)
```bash
~/persistent-brain/scripts/brain-init.sh /path/to/project
```
This creates a project-scoped engram DB + mempalace palace and drops `.mcp.json` + `AGENTS.md` into the project.

## 33 Projects Initialized
All repos in `~/ProjectsHQ/` are wired. Global brain at `~/.engram/engram.db` + `~/.mempalace/global`.

## Agent Wiring
| Agent | Config File | Status |
|---|---|---|
| **OpenCode** | `~/.config/opencode/opencode.json` | ✅ |
| **Claude Code** | `~/.claude.json` + `~/.claude/settings.json` | ✅ |
| **Codex** | `~/.codex/config.toml` | ✅ |
| **VS Code / Copilot Chat** | `~/Library/Application Support/Code/User/settings.json` | ✅ |
| **Cursor** | `~/.cursor/mcp.json` | ✅ |
| **Antigravity** | `~/Library/Application Support/Antigravity/User/settings.json` | ✅ |
| **GitHub Copilot (JetBrains)** | `~/.config/github-copilot/intellij/mcp.json` | ✅ |

## MCP Tools
| Tool | What it does |
|---|---|
| `brain_query` | Search all memory — auto-routes to engram (fast) or mempalace (fuzzy) |
| `brain_save` | Save a structured fact with conflict detection |
| `brain_context` | Load session-start context (project + global) |
| `brain_correct` | Fix a wrong memory (auto-supersedes old entry) |
| `brain_forget` | Soft-delete a memory from both stores |

## Session Lifecycle (automatic)
```
Session Start → brain_context loads 20 project + 5 global memories
Session End   → auto-distills recent context into engram
Pre-Compact   → compresses mempalace index
```

## Health Check
```bash
~/persistent-brain/scripts/brain-status.sh
~/persistent-brain/scripts/brain-inspect.sh <project-name>
```

## Cross-Project Memory
Global memories (scope=personal) are shared across all projects. Project-scoped memories are only loaded when working in that project's directory.

## Troubleshooting
| Symptom | Fix |
|---|---|
| "engram store unavailable" | `brew install engram` |
| "mempalace store unavailable" | `pipx install mempalace` |
| No memories found | Run `brain-init.sh` for the project |
| Wrong project memories | Check `BRAIN_PROJECT` env in MCP config |
