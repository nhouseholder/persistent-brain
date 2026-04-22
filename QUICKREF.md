# Quick Reference — persistent-brain

## What This Is
A local-first, permanent memory system for AI agents. Works across **OpenCode, Claude Code, Codex, VS Code/Copilot Chat, Cursor, Antigravity**. Every agent shares the same brain.

## Architecture
- **engram** = structured facts (SQLite + FTS5, <50ms search)
- **brain-router** = unified MCP server that routes queries to engram

## Setup (one-time)
```bash
git clone https://github.com/nhouseholder/persistent-brain ~/persistent-brain
cd ~/persistent-brain && ./install.sh
```

## Per-Project (run once per repo)
```bash
~/persistent-brain/scripts/brain-init.sh /path/to/project
```
This creates a project-scoped engram DB and drops `.mcp.json` + `AGENTS.md` into the project.

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
| `brain_query` | Search all memory — routes to engram (fast structured search) |
| `brain_save` | Save a structured fact with conflict detection |
| `brain_context` | Load session-start context (project + global) |
| `brain_correct` | Fix a wrong memory (auto-supersedes old entry) |
| `brain_forget` | Soft-delete a memory |

## Saving Facts (Structured Format)

Use this format for high-quality, retrievable memories:

```json
{
  "title": "Fixed auth loop on token refresh",
  "content": "**What**: Replaced synchronous token refresh with async queue\n**Why**: Multiple concurrent requests triggered overlapping refreshes\n**Where**: src/auth/refresh.ts, src/middleware/auth.ts\n**Learned**: Always debounce token refresh; never rely on client-side clock",
  "type": "bugfix",
  "topic_key": "project/myapp/bugfix/auth-refresh-race"
}
```

### Validation Rules
- **Valid types**: `decision`, `architecture`, `bugfix`, `pattern`, `config`, `learning`, `manual`
- **topic_key required** for: `decision`, `architecture`, `bugfix`, `pattern`, `config`
- **topic_key format**: lowercase, hyphens, slashes only (e.g., `project/mmalogic/bugfix/auth-loop`)
- **Content warning** if no `**` markers (structured format recommended)

## Session Lifecycle (automatic)
```
Session Start → brain_context loads 20 project + 5 global memories
Session End   → closes session timeline + syncs engram
```

## Health Check
```bash
~/persistent-brain/scripts/brain-status.sh
~/persistent-brain/scripts/brain-inspect.sh <project-name>
```

## Cross-Project Memory
Global memories (scope=personal) are shared across all projects. Project-scoped memories are only loaded when working in that project's directory.

## Project Name Mapping
Worktree names are automatically mapped to canonical project names via `~/.engram/project-map.json`. This prevents the same project from appearing under multiple names.

## Troubleshooting
| Symptom | Fix |
|---|---|
| "engram store unavailable" | `brew install engram` |
| No memories found | Run `brain-init.sh` for the project |
| Wrong project memories | Check `BRAIN_PROJECT` env in MCP config |
| "topic_key required" | Add topic_key for structured types (decision, architecture, bugfix, pattern, config) |
