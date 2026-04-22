# Handoff — persistent-brain LTM System

**Date:** 2026-04-22
**Version:** v0.4.0
**Status:** Production-ready, engram-only, auto-distill disabled

## What This Is

Portable, local-first memory system for AI coding agents. Unified brain-router on top of engram (SQLite + FTS5). Works across Claude Code, Codex, Qwen, Kimi K2, Cursor, anything MCP-capable.

## Architecture

- **brain-router** — unified query/save interface (Python, zero deps)
- **engram** — structured facts, decisions, bugfixes, patterns (SQLite+FTS5)
- **mempalace** — READ-ONLY semantic search (stripped from write path)
- **Session lifecycle** — session-start.sh → brain_context → session-end.sh → engram.sync

## Current State

- **Auto-distill:** DISABLED (was producing 55.9% noise)
- **109 auto-distill entries:** soft-deleted
- **Topic key enforcement:** active (brain-router validates format)
- **Project consolidation:** 15 canonical mappings in ~/.engram/project-map.json
- **Data quality:** 23.7% actionable (up from pre-cleanup baseline)

## Key Files

| File | Purpose |
|---|---|
| router/brain_router.py | v0.4.0 — unified router with validation |
| hooks/session-start.sh | Loads brain_context at session start |
| hooks/session-end.sh | Closes session, runs engram.sync |
| hooks/pre-compact.sh | Pre-compaction checkpoint trigger |
| scripts/brain-init.sh | Initialize project-scoped brain |
| scripts/brain-inspect.sh | Inspect what agent knows |
| scripts/brain-status.sh | Health check |
| scripts/brain-cleanup.sh | Soft-delete auto-distill noise |
| scripts/brain-backfill-topickeys.sh | Backfill missing topic_keys |
| config/AGENTS.md | Agent instructions |
| config/mcp-servers.json | MCP server config template |

## Design Principles

1. One query, one store — router handles dispatch
2. Explicit saves — agents save structured facts manually
3. Conflict detection on write — contradictions caught at save time
4. Zero external dependencies — pure Python 3.10+ stdlib
5. Agent-agnostic — MCP is the only interface

## Known Gotchas

- Auto-distill is OFF — agents must manually save via brain_save
- topic_key is mandatory for decision/architecture/bugfix/pattern/config types
- No "discovery" type — reserved, use "manual" or "learning" instead
- Mempalace is read-only — do not write to it during normal save rhythm
- Project map must be kept in sync with actual worktree names

## Next Steps

1. Monitor data quality after auto-distill disable
2. Add more project mappings as new repos are created
3. Consider re-enabling auto-distill with quality gate (future)
4. Build calibration data for which tasks need which mode

## Repo

https://github.com/nhouseholder/persistent-brain
