# Handoff — 2026-04-26 (Phase 4: Session Automation)

## What
Implemented session automation hooks and tool-call tracking:

### router/session_manager.py (new)
- Tracks session state in `~/.unified-brain/session_state.json`
- `init_session(project)` — creates session with ID, start time, counters
- `record_tool_call()` — increments counter on every tool call
- `is_checkpoint_due()` — triggers at 10 calls or 15 minutes
- `save_checkpoint()` — saves checkpoint observation to engram
- `get_session_stats()` — returns elapsed time, tool calls, checkpoints
- `end_session()` — marks session ended, returns final stats
- `get_checkpoint_suggestion()` — returns human-readable suggestion if due

### brain_router.py changes
- Imported session_manager with HAS_SESSION_MANAGER flag
- Auto-init session on MCP initialize (if BRAIN_PROJECT env set)
- Records tool call on every tools/call
- Injects `_checkpoint_suggestion` field into responses when checkpoint is due
- Added 4 new MCP tools:
  - `brain_session_start` — init session tracking
  - `brain_session_end` — close session
  - `brain_checkpoint` — save checkpoint observation
  - `brain_session_stats` — get session stats

### hooks/session-start.sh (rewritten)
- Writes session state JSON to `~/.unified-brain/session_state.json`
- Checks engram DB exists
- Checks GRAPH_REPORT.md freshness (>7 days = stale warning)
- Outputs agent instructions (brain_context, brain_codebase_index, brain_validate, checkpoint policy)

### hooks/session-end.sh (rewritten)
- Reads session stats from state file
- Closes open sessions in engram SQLite DB
- Outputs session stats (tool calls, checkpoints, elapsed time)
- Suggests brain_session_summary + brain_session_end if work was done
- Syncs engram in background
- Marks state file as ended

### hooks/pre-commit.sh (new)
- Checks for staged code changes (*.ts, *.tsx, *.js, etc.)
- Runs `cgc add_code_to_graph` if CGC installed
- Runs `codecartographer diagram` if CodeCartographer installed
- Auto-stages updated GRAPH_REPORT.md

### install.sh changes
- Added pre-commit.sh to hook installation list
- Updated hook registration instructions

## Why
Approved product architecture plan requires automated session lifecycle:
- Agent shouldn't need to manually track tool calls or remember to checkpoint
- Session start should auto-load context + check diagram freshness
- Session end should auto-close timeline + suggest summary
- Git commits should auto-refresh codebase index

## How
- Session state persisted in JSON file (survives MCP server restarts)
- Checkpoint suggestions injected as `_checkpoint_suggestion` field in MCP responses
- Hooks are shell scripts (agent-agnostic, work with OpenCode/Claude/Codex/Cursor)
- Non-destructive: stale warnings are suggestions, not forced actions

## What's Left
- Phase 5: Compiled Truth + Auto-Links Enforcement (validator wired into brain_save)
- Phase 6: Documentation + Polish (README.md, docs/getting-started.md, etc.)
- Phase 7: Testing + Packaging (pytest suite, Makefile, CI pipeline)

## Checklist
- [x] Version bumped (0.5.0)
- [x] Handoff document written
- [ ] GitHub pushed (origin/main) — pending user approval
- [ ] Manual deploy triggered — N/A (backend MCP server)
