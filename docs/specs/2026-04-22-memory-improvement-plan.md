# Memory System Improvement Plan

**Date:** 2026-04-22
**Status:** In Progress

## Problem Statement

The current memory system has three critical issues:
1. **Auto-distill creates noise** — 109 "Session summary (auto-distilled)" observations with low signal-to-noise ratio
2. **No structured format enforcement** — agents save observations without topic_key, with inconsistent formatting
3. **Project name drift** — same project appears under multiple worktree names (e.g., "vigorous-kirch-204b5b" and "mmalogic")

## Solution: 5-Phase Implementation

### Phase 1: Disable Auto-distill (30 min)
- Comment out auto-distill block in `session-end.sh`
- Add validation to reject `type="discovery"` from `engram_save()`
- Keep session-end SQLite UPDATE and engram sync

### Phase 2: Structured Format Enforcement (1-2 hours)
- Add validation constants in `brain_router.py`:
  - `VALID_TYPES = {"decision", "architecture", "bugfix", "pattern", "config", "learning", "manual"}`
  - `STRUCTURED_TYPES = {"decision", "architecture", "bugfix", "pattern", "config"}`
- Require `topic_key` for structured types
- Validate `topic_key` format: `^[a-z0-9_-]+(/[a-z0-9_-]+)*$`
- Warn if `content` doesn't contain `**` (structured format indicator)
- Update `AGENTS.md` with Memory Quality Checklist

### Phase 3: Project Consolidation (2-3 hours)
- Create `~/.engram/project-map.json` with canonical mappings
- Update `brain_router.py` to load and use project map
- Update `session-start.sh` to emit canonical name
- Update `brain-inspect.sh` to group by canonical name

### Phase 4: Backfill + Cleanup (2 hours)
- Create `brain-cleanup.sh` to soft-delete auto-distilled observations
- Create `brain-backfill-topickeys.sh` to generate topic_keys for existing observations
- Run both scripts with `--execute`

### Phase 5: Docs + Sync (1 hour)
- Update `README.md` — remove mempalace references, update architecture
- Update `QUICKREF.md` — new save format examples
- Update `8-agent-team/_shared/memory-systems.md`
- Regenerate prompts and commit both repos

## Constraints
- No DB schema migrations
- All deletes are soft-deletes (deleted_at column)
- Commit after each phase
