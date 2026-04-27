# Handoff — 2026-04-26 (Phase 6: Documentation + Polish)

## What
Rewrote all documentation for unified-brain v0.5.0.

### README.md (rewritten)
- Updated architecture diagram to three-layer (engram + CGC + CodeCartographer)
- Added all 15 MCP tools with descriptions
- Updated install instructions for single-command install
- Added session lifecycle diagram
- Added observation format example
- Added supported agents matrix
- Updated design principles (added session automation + validation)

### docs/getting-started.md (new)
- Step-by-step from prerequisites to first project
- Per-agent wiring instructions
- Verification commands

### docs/architecture.md (new)
- Three-store deep-dive
- brain-router design (zero dependencies, modular structure)
- Session automation internals
- Observation validation pipeline
- Data flow diagrams (session start / normal operation / session end)
- Performance table
- Security notes

### docs/agent-setup.md (new)
- Claude Code: ~/.claude.json + hooks
- Codex: ~/.codex/config.toml
- Kimi CLI: ~/.kimi/config.toml + skills
- Cursor: .cursor/rules/unified-brain.mdc
- OpenCode: ~/.opencode/settings.json + hooks
- Qwen Code / Aider: planned
- Per-project configuration via brain-init.sh
- Troubleshooting agent connection table

### docs/api-reference.md (new)
- All 15 tools with input/output JSON examples
- Temporal memory tools (engram)
- Structural memory tools (CGC)
- Enriched memory tools (CodeCartographer)
- Session management tools
- Checkpoint suggestion format

### docs/troubleshooting.md (rewritten)
- Installation issues (Node.js, uv, codecartographer, engram)
- MCP connection issues (PATH, config, caching)
- Store issues (engram DB, CGC indexing, CodeCartographer timeouts)
- Validation issues (Compiled Truth, Auto-Links examples)
- Session issues (state file, checkpoint suggestions)
- Performance issues (query speed, concurrent access)
- Data recovery (deleted observations, corrupted DB)

## Why
Approved product architecture plan requires A+ documentation for external users. The old README was v1.0 (two-layer, mentions mempalace). New docs reflect the unified three-layer architecture.

## What's Left
- Phase 7: Testing + Packaging (pytest suite, Makefile, CI pipeline)

## Checklist
- [x] Version bumped (0.5.0)
- [x] Handoff document written
- [ ] GitHub pushed (origin/main) — pending user approval
- [ ] Manual deploy triggered — N/A (backend MCP server)
