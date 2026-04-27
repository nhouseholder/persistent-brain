# Handoff — 2026-04-26 (Phase 2: Installer Integration + Phase 3: Agent-Agnostic Protocol)

## What
Updated install.sh, brain-init.sh, brain-status.sh, and config/AGENTS.md for unified-brain architecture:

### install.sh changes:
- Added Node.js prereq check (18+)
- Added uv check (preferred for CGC) with pipx fallback
- Added cgc installation via `uv tool install codegraphcontext`
- Added codecartographer installation (local repo link or npm)
- Added migration detection for legacy persistent-brain installs
- Added unified config creation at `~/.unified-brain/config.yaml`
- Renamed hooks from `persistent-brain-*` to `unified-brain-*`
- Updated final messages to reference unified-brain

### brain-init.sh changes:
- Added CGC `add_code_to_graph` indexing step
- Added CodeCartographer `diagram` generation step
- Updated AGENTS.md template with new tools (brain_codebase_index, brain_codebase_search, brain_validate)
- Added `.unified-brainignore` file creation
- Updated session start protocol in template

### brain-status.sh changes:
- Added cgc binary check
- Added codecartographer binary check
- Added CGC indexed repositories list
- Added GRAPH_REPORT.md coverage check
- Added brain-router MCP smoke test
- Added unified config check

### config/AGENTS.md changes:
- Updated from "two-layer" to "three-layer" memory system
- Added CodeCartographer as third store
- Added new tools: brain_validate, brain_codebase_index, brain_codebase_search
- Added Compiled Truth + Timeline format specification
- Added Auto-Links requirement
- Added Session End Protocol
- Added brain_validate to Save Rules
- Updated Codebase Diagram Protocol to use brain_codebase_index

## Why
Approved product architecture plan requires single-command install (`./install.sh`) that sets up all three stores (engram, CGC, CodeCartographer) and agent-agnostic protocol that works across all agents.

## How
- Subprocess-based installation (uv for CGC, npm for CodeCartographer)
- Local repo detection for CodeCartographer (`~/ProjectsHQ/codecartographer`)
- Non-destructive updates (won't overwrite existing configs)
- Agent-agnostic AGENTS.md uses only brain-router tools

## What's Left
- Phase 4: Session Automation (hooks for start/end with brain_codebase_index --check)
- Phase 5: Compiled Truth + Auto-Links Enforcement (validator wired into brain_save)
- Phase 6: Documentation + Polish (README.md, docs/getting-started.md, etc.)
- Phase 7: Testing + Packaging (pytest suite, Makefile, CI pipeline)

## Checklist
- [x] Version bumped (0.5.0 in brain_router.py, install.sh, config.yaml)
- [x] Handoff document written
- [ ] GitHub pushed (origin/main) — pending user approval
- [ ] Manual deploy triggered — N/A (backend MCP server)
