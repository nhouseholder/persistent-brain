#!/usr/bin/env python3
"""Session manager for brain-router.

Tracks tool-call count and elapsed time per session.
Auto-suggests checkpoints at 10 calls or 15 minutes.
Saves checkpoint observations to engram when triggered.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

STATE_DIR = Path.home() / ".unified-brain"
STATE_FILE = STATE_DIR / "session_state.json"

# Thresholds
CHECKPOINT_CALLS = 10
CHECKPOINT_MINUTES = 15
SESSION_SUMMARY_AFTER_MINUTES = 30


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_state(state: Dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def init_session(project: str) -> Dict[str, Any]:
    """Initialize a new session state."""
    state = {
        "session_id": f"session-{project}-{int(time.time())}",
        "project": project,
        "started_at": _now_iso(),
        "tool_calls": 0,
        "last_checkpoint_at": _now_iso(),
        "last_checkpoint_calls": 0,
        "checkpoints": 0,
    }
    _save_state(state)
    return state


def record_tool_call() -> Dict[str, Any]:
    """Increment tool call counter and return updated state."""
    state = _load_state()
    if not state:
        return state
    state["tool_calls"] = state.get("tool_calls", 0) + 1
    _save_state(state)
    return state


def is_checkpoint_due() -> tuple[bool, Dict[str, Any]]:
    """Check if checkpoint is due (10 calls or 15 min since last)."""
    state = _load_state()
    if not state:
        return False, state

    calls_since = state.get("tool_calls", 0) - state.get("last_checkpoint_calls", 0)
    if calls_since >= CHECKPOINT_CALLS:
        return True, state

    last_cp = state.get("last_checkpoint_at")
    if last_cp:
        try:
            last_dt = datetime.fromisoformat(last_cp.replace("Z", "+00:00"))
            elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds() / 60
            if elapsed >= CHECKPOINT_MINUTES:
                return True, state
        except ValueError:
            pass

    return False, state


def save_checkpoint(project: str, task: str, recent_actions: list, open_files: list) -> Dict[str, Any]:
    """Save a checkpoint observation and reset counters."""
    state = _load_state()
    if not state:
        state = init_session(project)

    checkpoint_data = {
        "task": task,
        "time": _now_iso(),
        "tool_calls_since_last": state.get("tool_calls", 0) - state.get("last_checkpoint_calls", 0),
        "recent_actions": recent_actions,
        "open_files": open_files,
    }

    # Write to engram via direct SQLite (same pattern as brain_router.py)
    # We import here to avoid circular dependency at module load time
    from brain_router import engram_save

    engram_save(
        title=f"Checkpoint: {task}",
        content=f"## Session Checkpoint\n**Task**: {task}\n**Time**: {checkpoint_data['time']}\n**Tool calls since last checkpoint**: {checkpoint_data['tool_calls_since_last']}\n**Recent Actions**:\n" + "\n".join(f"- {a}" for a in recent_actions) + f"\n**Open Files**: {', '.join(open_files)}",
        type_tag="checkpoint",
        topic_key=f"checkpoint/{state.get('session_id', 'unknown')}",
    )

    state["last_checkpoint_at"] = _now_iso()
    state["last_checkpoint_calls"] = state.get("tool_calls", 0)
    state["checkpoints"] = state.get("checkpoints", 0) + 1
    _save_state(state)
    return state


def get_session_stats() -> Dict[str, Any]:
    """Return current session statistics."""
    state = _load_state()
    if not state:
        return {"active": False}

    started = state.get("started_at")
    elapsed_min = 0
    if started:
        try:
            start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            elapsed_min = (datetime.now(timezone.utc) - start_dt).total_seconds() / 60
        except ValueError:
            pass

    return {
        "active": True,
        "session_id": state.get("session_id"),
        "project": state.get("project"),
        "started_at": started,
        "elapsed_minutes": round(elapsed_min, 1),
        "tool_calls": state.get("tool_calls", 0),
        "checkpoints": state.get("checkpoints", 0),
    }


def end_session() -> Dict[str, Any]:
    """Mark session as ended and clean up state."""
    state = _load_state()
    if not state:
        return {"ended": False, "reason": "no active session"}

    state["ended_at"] = _now_iso()
    _save_state(state)

    # Keep the file for a bit but mark ended — next init_session will overwrite
    return {
        "ended": True,
        "session_id": state.get("session_id"),
        "started_at": state.get("started_at"),
        "ended_at": state.get("ended_at"),
        "total_tool_calls": state.get("tool_calls", 0),
        "total_checkpoints": state.get("checkpoints", 0),
    }


def get_checkpoint_suggestion() -> Optional[str]:
    """Return a human-readable checkpoint suggestion if due."""
    due, state = is_checkpoint_due()
    if not due:
        return None

    calls_since = state.get("tool_calls", 0) - state.get("last_checkpoint_calls", 0)
    return (
        f"⚠️ CHECKPOINT DUE: {calls_since} tool calls since last checkpoint. "
        f"Consider calling brain_save with a checkpoint observation."
    )
