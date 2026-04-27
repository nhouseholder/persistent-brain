#!/usr/bin/env python3
"""Reasoning tracker for per-task evidence budget and mode enforcement.

Tracks tool calls + reasoning tokens per task. Integrates with session_manager
for checkpoint-level tracking. Auto-saves calibration data after tasks.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

STATE_DIR = Path.home() / ".unified-brain"
STATE_FILE = STATE_DIR / "reasoning_state.json"

# Research tools that count as evidence pulls
RESEARCH_TOOLS = {
    "brain_query", "brain_codebase_search", "brain_diagram",
    "brain_callers", "brain_structure", "brain_codebase_index",
    "engram_mem_search", "engram_mem_context", "engram_mem_timeline",
    "grep", "glob", "read", "fetch", "webfetch",
}

# Budget definitions
BUDGETS = {
    "fast": {"pulls": 0, "tokens": 200},
    "deliberate": {"pulls": 1, "tokens": 1500},
    "slow": {"pulls": 3, "tokens": None},  # unlimited
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"tasks": [], "current_task": None}


def _save_state(state: Dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def start_task(mode: str, task_description: str = "") -> Dict[str, Any]:
    """Initialize a new task with reasoning budget."""
    budget = BUDGETS.get(mode, BUDGETS["fast"])
    task = {
        "task_id": f"task-{int(time.time())}",
        "mode": mode,
        "description": task_description,
        "started_at": _now_iso(),
        "budget_pulls": budget["pulls"],
        "budget_tokens": budget["tokens"],
        "pulls_used": 0,
        "tokens_used": 0,
        "tools_called": [],
        "breached": False,
        "ended_at": None,
    }
    state = _load_state()
    # Archive previous task if exists
    if state.get("current_task"):
        state["tasks"].append(state["current_task"])
        # Keep only last 100 tasks
        state["tasks"] = state["tasks"][-100:]
    state["current_task"] = task
    _save_state(state)
    return task


def record_pull(tool_name: str, token_estimate: int = 0) -> Dict[str, Any]:
    """Record an evidence pull. Returns updated task with breach status."""
    state = _load_state()
    task = state.get("current_task")
    if not task:
        return {"error": "No active task. Call start_task() first."}

    # Count pull
    is_research = tool_name in RESEARCH_TOOLS or tool_name.startswith("brain_")
    if is_research:
        task["pulls_used"] = task.get("pulls_used", 0) + 1

    task["tools_called"].append(tool_name)

    # Estimate tokens if provided
    if token_estimate > 0:
        task["tokens_used"] = task.get("tokens_used", 0) + token_estimate

    # Check breach
    budget_pulls = task.get("budget_pulls", 0)
    budget_tokens = task.get("budget_tokens")

    pull_breach = budget_pulls is not None and task["pulls_used"] > budget_pulls
    token_breach = budget_tokens is not None and task["tokens_used"] > budget_tokens

    if pull_breach or token_breach:
        task["breached"] = True

    _save_state(state)
    return task


def record_tokens(token_count: int) -> Dict[str, Any]:
    """Record reasoning tokens used."""
    state = _load_state()
    task = state.get("current_task")
    if not task:
        return {"error": "No active task."}

    task["tokens_used"] = task.get("tokens_used", 0) + token_count
    budget_tokens = task.get("budget_tokens")

    if budget_tokens is not None and task["tokens_used"] > budget_tokens:
        task["breached"] = True

    _save_state(state)
    return task


def is_budget_breached() -> tuple[bool, Dict[str, Any]]:
    """Check if current task has breached its budget."""
    state = _load_state()
    task = state.get("current_task")
    if not task:
        return False, {}
    return task.get("breached", False), task


def end_task(outcome: str = "unknown") -> Dict[str, Any]:
    """End current task and archive it."""
    state = _load_state()
    task = state.get("current_task")
    if not task:
        return {"error": "No active task."}

    task["ended_at"] = _now_iso()
    task["outcome"] = outcome
    state["tasks"].append(task)
    state["tasks"] = state["tasks"][-100:]
    state["current_task"] = None
    _save_state(state)
    return task


def get_task_stats() -> Dict[str, Any]:
    """Get current task statistics."""
    state = _load_state()
    task = state.get("current_task")
    if not task:
        return {"active": False}

    budget_pulls = task.get("budget_pulls", 0)
    budget_tokens = task.get("budget_tokens")
    pulls_remaining = budget_pulls - task.get("pulls_used", 0) if budget_pulls is not None else None
    tokens_remaining = budget_tokens - task.get("tokens_used", 0) if budget_tokens is not None else None

    return {
        "active": True,
        "task_id": task.get("task_id"),
        "mode": task.get("mode"),
        "description": task.get("description"),
        "pulls_used": task.get("pulls_used", 0),
        "pulls_remaining": pulls_remaining,
        "tokens_used": task.get("tokens_used", 0),
        "tokens_remaining": tokens_remaining,
        "breached": task.get("breached", False),
        "tools_called": task.get("tools_called", []),
    }


def get_calibration_data(limit: int = 100) -> List[Dict[str, Any]]:
    """Get historical task data for calibration analysis."""
    state = _load_state()
    tasks = state.get("tasks", [])

    calibration = []
    for task in tasks:
        if task.get("mode") in ("deliberate", "slow"):
            calibration.append({
                "mode": task.get("mode"),
                "description": task.get("description", "")[:100],
                "pulls_used": task.get("pulls_used", 0),
                "tokens_used": task.get("tokens_used", 0),
                "outcome": task.get("outcome", "unknown"),
                "breached": task.get("breached", False),
            })

    return calibration[-limit:]


def get_calibration_stats() -> Dict[str, Any]:
    """Aggregate calibration statistics."""
    tasks = _load_state().get("tasks", [])
    if not tasks:
        return {"total_tasks": 0}

    total = len(tasks)
    fast_tasks = [t for t in tasks if t.get("mode") == "fast"]
    slow_tasks = [t for t in tasks if t.get("mode") == "slow"]
    deliberate_tasks = [t for t in tasks if t.get("mode") == "deliberate"]
    breached = [t for t in tasks if t.get("breached")]

    # Estimate fast sufficiency: tasks that were slow/deliberate but used <1 pull
    potentially_fast = [t for t in slow_tasks + deliberate_tasks if t.get("pulls_used", 0) <= 1]

    return {
        "total_tasks": total,
        "fast_count": len(fast_tasks),
        "deliberate_count": len(deliberate_tasks),
        "slow_count": len(slow_tasks),
        "breached_count": len(breached),
        "breach_rate": round(len(breached) / total * 100, 1) if total else 0,
        "fast_sufficiency_estimate": round(len(potentially_fast) / len(slow_tasks + deliberate_tasks) * 100, 1) if (slow_tasks + deliberate_tasks) else 0,
        "avg_pulls_slow": round(sum(t.get("pulls_used", 0) for t in slow_tasks) / len(slow_tasks), 1) if slow_tasks else 0,
        "avg_tokens_slow": round(sum(t.get("tokens_used", 0) for t in slow_tasks) / len(slow_tasks), 1) if slow_tasks else 0,
    }


def get_budget_warning() -> Optional[str]:
    """Return a human-readable budget warning if breached or near limit."""
    breached, task = is_budget_breached()
    if not task:
        return None

    if breached:
        mode = task.get("mode", "unknown")
        pulls = task.get("pulls_used", 0)
        budget_pulls = task.get("budget_pulls", 0)
        tokens = task.get("tokens_used", 0)
        budget_tokens = task.get("budget_tokens")

        msg = f"⚠️ BUDGET BREACH: {mode} mode exceeded limits. "
        if pulls > budget_pulls:
            msg += f"Pulls: {pulls}/{budget_pulls}. "
        if budget_tokens and tokens > budget_tokens:
            msg += f"Tokens: {tokens}/{budget_tokens}. "
        msg += "Declare terminal state or escalate."
        return msg

    # Near-limit warning (80% of budget)
    mode = task.get("mode", "unknown")
    budget_pulls = task.get("budget_pulls", 0)
    pulls_used = task.get("pulls_used", 0)
    if budget_pulls > 0 and pulls_used / budget_pulls >= 0.8:
        return f"⚠️ BUDGET WARNING: {mode} mode at {pulls_used}/{budget_pulls} pulls. Consider terminal state."

    return None
