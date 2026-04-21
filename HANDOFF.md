# Handoff: Memory Sync + Delegation Gate Fix (v1.7.0)

## Two Issues Addressed

### Issue 1: Orchestrator Bypassed Delegation to @generalist

**What happened**: During karpathy-llm-wiki-k2.6 repo build, the orchestrator created 32 implementation files directly instead of delegating to @generalist. Rationalized with "tight coupling" despite ARCHITECTURE.md being the single source of truth.

**Root cause**: The decision tree was a suggestion, not a circuit breaker. No mandatory gate fired before implementation work.

**Fix applied**:
- Added `MANDATORY DELEGATION GATE` section to `agents/orchestrator.md` — fires BEFORE the decision tree
- File count rules: 1 trivial → orchestrator, 1 non-trivial → @generalist, 2+ → @generalist parallel, 10+ → split batches
- Banned specific rationalizations (tight coupling, overhead, context, speed, "files already written")
- Added `Delegation Escalation` section to `agents/generalist.md` — feedback loop when orchestrator sends too many files
- Version bump: 1.6.0 → 1.7.0

### Issue 2: brain-router_brain_save Reports Success But Content Not Searchable

**What happened**: `brain-router_brain_save` returned success but the saved content was not findable via `brain-router_brain_query` or `mempalace_mempalace_search`.

**Root cause**: The brain-router MCP writes to `~/.mempalace/global/transcripts/` for "periodic mining" — but the mining process doesn't run in real-time. Content sits on disk but never gets indexed into the HNSW vector embedding store.

**Fix applied**:
- Use `engram_mem_save` for structured, searchable observations (✅ working)
- Use `mempalace_mempalace_add_drawer` for direct embedding index writes (✅ working)
- Skip `brain-router_brain_save` wrapper — it's a write-to-disk-only operation with no real-time indexing

## Memory Sync (This Session)

### Engram Export
- Exported 9 observations from `10-agent-team` project to `persistent-brain/engram-chunks/engram-10-agent-team.json`
- Includes: session summaries, bugfixes, architecture decisions, and the delegation gate decision
- Total: 176 observations across all projects, 9 filtered to 10-agent-team

### Mempalace Export
- Exported global decisions drawer to `persistent-brain/mempalace-export/global-decisions.json`
- Contains the delegation rule decision with full structured content

### Files Changed

#### 8-Agent Team Repo (`~/.config/opencode/`)
| File | Change |
|---|---|
| `agents/orchestrator.md` | Added Mandatory Delegation Gate section (~25 lines) |
| `agents/generalist.md` | Added Delegation Escalation section (~8 lines) |
| `README.md` | Version bump 1.6.0 → 1.7.0 |
| `HANDOFF.md` | This document |

#### Persistent Brain Repo (`~/.mempalace/persistent-brain/`)
| File | Change |
|---|---|
| `engram-chunks/engram-10-agent-team.json` | 9 observations exported |
| `mempalace-export/global-decisions.json` | 1 global decision exported |

## Verification

- ✅ Engram search: `engram_mem_search(query="delegation generalist routing")` → returns #175
- ✅ Mempalace search: `mempalace_mempalace_search(query="delegation generalist routing")` → returns delegation rule (similarity 0.446)
- ✅ Orchestrator gate: present in `agents/orchestrator.md` before decision tree
- ✅ Generalist escalation: present in `agents/generalist.md`
- ✅ Git: committed and pushed to `feat/routing-generalist-execution` branch

## Next Steps

1. Merge PR #1 to main in 8-agent-team repo
2. Monitor next multi-file task to verify delegation gate fires correctly
3. Consider adding validation script that checks agent prompts for required sections
4. Fix brain-router MCP to trigger real-time indexing after transcript writes (separate issue)
