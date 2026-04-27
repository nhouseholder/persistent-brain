#!/usr/bin/env python3
"""Auto-calibrate pending DELIBERATE/SLOW tasks at session end.

Called by hooks/session-end.sh. Checks reasoning_state.json for any
active task with mode 'deliberate' or 'slow', ends it, and saves
calibration data to engram.
"""

import json
import os
import sys
from pathlib import Path

# Add router to path
ROUTER_DIR = Path(__file__).parent.parent / "router"
sys.path.insert(0, str(ROUTER_DIR))

import reasoning_tracker


def main():
    state = reasoning_tracker._load_state()
    task = state.get("current_task")
    if not task:
        print("[unified-brain] No active reasoning task to calibrate.")
        return 0

    mode = task.get("mode", "fast")
    outcome = task.get("outcome", "completed")

    # End the task
    ended = reasoning_tracker.end_task(outcome)

    if mode not in ("deliberate", "slow"):
        print(f"[unified-brain] Task ended ({mode}). FAST mode — no calibration needed.")
        return 0

    # Auto-calibrate for deliberate/slow tasks
    pulls = ended.get("pulls_used", 0)
    tokens = ended.get("tokens_used", 0)
    budget_pulls = ended.get("budget_pulls", 0)
    budget_tokens = ended.get("budget_tokens")

    # Infer whether FAST would have sufficed
    fast_sufficed = "uncertain"
    if pulls <= 1:
        fast_sufficed = "likely yes"
    elif pulls > budget_pulls:
        fast_sufficed = "likely no"

    # Try to save via brain_router if available
    try:
        import brain_router
        result = brain_router.handle_brain_calibrate({
            "mode_declared": mode,
            "pulls_actual": pulls,
            "tokens_actual": tokens,
            "outcome": outcome,
            "would_fast_have_sufficed": fast_sufficed,
        })
        if result.get("calibrated"):
            print(f"[unified-brain] ✓ Auto-calibrated {mode} task: {pulls} pulls, {tokens} tokens ({fast_sufficed})")
        else:
            print(f"[unified-brain] Calibration returned: {result}")
    except Exception as e:
        print(f"[unified-brain] ⚠ Calibration save failed: {e}")
        # Fallback: just log locally
        print(f"[unified-brain]   Task: {mode}, pulls: {pulls}, tokens: {tokens}, sufficed: {fast_sufficed}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
