#!/usr/bin/env python3
"""
brain-router — Unified MCP bridge for persistent-brain.

Uses direct SQLite access for engram (no CLI subprocess).
Includes memory scoring, conflict detection, and explicit error
reporting when stores are unavailable.

Tools: brain_query, brain_save, brain_context, brain_correct, brain_forget
"""

import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone

# Local modules for observation quality and codebase integration
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import auto_linker
    import observation_validator
    HAS_VALIDATION = True
except Exception:
    HAS_VALIDATION = False

try:
    import session_manager
    HAS_SESSION_MANAGER = True
except Exception:
    HAS_SESSION_MANAGER = False

try:
    import reasoning_tracker
    HAS_REASONING_TRACKER = True
except Exception:
    HAS_REASONING_TRACKER = False

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_NAME = os.environ.get("BRAIN_PROJECT", os.path.basename(os.getcwd()))
ENGRAM_DB = os.environ.get("ENGRAM_DB", os.path.expanduser(f"~/.engram/{PROJECT_NAME}.db"))
ENGRAM_GLOBAL_DB = os.path.expanduser("~/.engram/engram.db")
PROJECT_MAP_PATH = os.path.expanduser("~/.engram/project-map.json")

_project_map_cache = None

def _load_project_map():
    """Load canonical project name mapping from project-map.json. Cached."""
    global _project_map_cache
    if _project_map_cache is not None:
        return _project_map_cache
    if not os.path.isfile(PROJECT_MAP_PATH):
        _project_map_cache = {}
        return _project_map_cache
    try:
        with open(PROJECT_MAP_PATH, "r") as f:
            _project_map_cache = json.load(f)
        return _project_map_cache
    except Exception:
        _project_map_cache = {}
        return _project_map_cache

def _canonical_project(name):
    """Return canonical project name from map, or original if not mapped."""
    mapping = _load_project_map()
    return mapping.get(name, name)


# ---------------------------------------------------------------------------
# Store availability checks — explicit error reporting (Fix #6)
# Cached to avoid subprocess overhead on every query
# ---------------------------------------------------------------------------

_store_cache = None

def _store_status():
    """Return availability status of engram store. Cached for 60s."""
    global _store_cache
    if _store_cache is not None:
        return _store_cache
    
    status = {
        "engram_available": False,
        "engram_db_exists": os.path.isfile(ENGRAM_DB) or os.path.isfile(ENGRAM_GLOBAL_DB),
    }
    
    try:
        subprocess.run(["engram", "--version"], capture_output=True, timeout=3)
        status["engram_available"] = True
    except Exception:
        pass
    
    _store_cache = status
    return status

# ---------------------------------------------------------------------------
# SQLite helpers (engram direct access)
# ---------------------------------------------------------------------------

# Expected schema — always create/verify against this (Fix #3)
ENGRAM_SCHEMA = """
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        project TEXT NOT NULL,
        directory TEXT NOT NULL,
        started_at TEXT NOT NULL DEFAULT (datetime('now')),
        ended_at TEXT,
        summary TEXT
    );
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sync_id TEXT,
        session_id TEXT NOT NULL,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        tool_name TEXT,
        project TEXT,
        scope TEXT NOT NULL DEFAULT 'project',
        topic_key TEXT,
        normalized_hash TEXT,
        revision_count INTEGER NOT NULL DEFAULT 1,
        duplicate_count INTEGER NOT NULL DEFAULT 1,
        last_seen_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        deleted_at TEXT,
        access_count INTEGER NOT NULL DEFAULT 0
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
        title, content, tool_name, type, project, topic_key,
        content='observations', content_rowid='id'
    );
    CREATE TRIGGER IF NOT EXISTS obs_fts_insert AFTER INSERT ON observations BEGIN
        INSERT OR IGNORE INTO observations_fts(rowid, title, content, tool_name, type, project, topic_key)
        VALUES (new.id, new.title, new.content, new.tool_name, new.type, new.project, new.topic_key);
    END;
"""

def _get_db(db_path=None):
    """Get SQLite connection, creating schema if needed. Always verifies schema."""
    path = db_path or ENGRAM_DB
    needs_schema = not os.path.isfile(path)

    try:
        conn = sqlite3.connect(path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")

        if needs_schema:
            conn.executescript(ENGRAM_SCHEMA)
            conn.commit()
        else:
            # Fix #3: Verify schema on every connection — migrate if columns missing
            _migrate(conn)

        return conn
    except Exception:
        return None

def _migrate(conn):
    """Add missing columns if schema is older than expected."""
    # Add access_count column if missing
    try:
        conn.execute("SELECT access_count FROM observations LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE observations ADD COLUMN access_count INTEGER NOT NULL DEFAULT 0")
        conn.commit()

    # Add last_seen_at column if missing
    try:
        conn.execute("SELECT last_seen_at FROM observations LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE observations ADD COLUMN last_seen_at TEXT")
        conn.commit()

    # Add normalized_hash column if missing
    try:
        conn.execute("SELECT normalized_hash FROM observations LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE observations ADD COLUMN normalized_hash TEXT")
        conn.commit()

    # Ensure FTS table exists
    try:
        conn.execute("SELECT rowid FROM observations_fts LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
                title, content, tool_name, type, project, topic_key,
                content='observations', content_rowid='id'
            )
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS obs_fts_insert AFTER INSERT ON observations BEGIN
                INSERT OR IGNORE INTO observations_fts(rowid, title, content, tool_name, type, project, topic_key)
                VALUES (new.id, new.title, new.content, new.tool_name, new.type, new.project, new.topic_key);
            END
        """)
        conn.commit()

def _score_row(row):
    """Compute relevance score for an observation (accepts dict or Row)."""
    now = datetime.now(timezone.utc)
    try:
        raw = row.get("updated_at") if isinstance(row, dict) else row["updated_at"]
        updated = datetime.fromisoformat(str(raw).replace("Z", "").replace("+00:00", ""))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
    except Exception:
        updated = now
    days = max(0, (now - updated).total_seconds() / 86400)
    recency = 1.0 / (1.0 + days / 30.0)
    access = row.get("access_count", 0) if isinstance(row, dict) else (row["access_count"] if "access_count" in row.keys() else 0)
    frequency = min(2.0, 1.0 + math.log(max(1, access or 0)))
    confidence = 0.5 ** (days / 90.0)
    return confidence * recency * frequency

def _row_to_dict(row):
    return {k: row[k] for k in row.keys()}

def _track_access(conn, obs_ids):
    """Update access_count and last_seen_at for retrieved observations."""
    if not obs_ids:
        return
    now = datetime.now(timezone.utc).isoformat()
    for oid in obs_ids:
        try:
            conn.execute(
                "UPDATE observations SET access_count = access_count + 1, last_seen_at = ? WHERE id = ?",
                (now, oid))
        except Exception:
            pass
    conn.commit()

# ---------------------------------------------------------------------------
# Engram operations (direct SQLite)
# ---------------------------------------------------------------------------

def engram_search(query, db_path=None, limit=10, project=None, canonical_project=None):
    conn = _get_db(db_path)
    if not conn:
        return []
    _migrate(conn)
    try:
        sql = """
            SELECT o.id, o.type, o.title, o.content, o.topic_key, o.project,
                   o.scope, o.created_at, o.updated_at, o.access_count,
                   rank
            FROM observations_fts fts
            JOIN observations o ON o.id = fts.rowid
            WHERE observations_fts MATCH ? AND o.deleted_at IS NULL
        """
        params = [query]
        if canonical_project:
            # Resolve all worktree names mapped to this canonical project
            mapping = _load_project_map()
            worktree_names = [k for k, v in mapping.items() if v == canonical_project]
            worktree_names.append(canonical_project)  # include canonical name itself
            placeholders = ",".join("?" * len(worktree_names))
            sql += f" AND o.project IN ({placeholders})"
            params.extend(worktree_names)
        elif project:
            sql += " AND o.project = ?"
            params.append(project)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        results = [_row_to_dict(r) for r in rows]
        # Score and sort
        for r in results:
            r["_score"] = round(_score_row(r), 4)
        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        _track_access(conn, [r["id"] for r in results])
        return results
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        conn.close()

def engram_context(db_path=None, limit=20, project=None, scope=None):
    conn = _get_db(db_path)
    if not conn:
        return []
    _migrate(conn)
    try:
        sql = "SELECT * FROM observations WHERE deleted_at IS NULL"
        params = []
        if project:
            sql += " AND project = ?"
            params.append(project)
        if scope:
            sql += " AND scope = ?"
            params.append(scope)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit * 3)  # fetch extra for scoring
        rows = conn.execute(sql, params).fetchall()
        results = [_row_to_dict(r) for r in rows]
        for r in results:
            r["_score"] = round(_score_row(r), 4)
        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        results = results[:limit]
        _track_access(conn, [r["id"] for r in results])
        return results
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        conn.close()

VALID_TYPES = {"decision", "architecture", "bugfix", "pattern", "config", "learning", "manual"}
STRUCTURED_TYPES = {"decision", "architecture", "bugfix", "pattern", "config"}
TOPIC_KEY_PATTERN = re.compile(r"^[a-z0-9_-]+(/[a-z0-9_-]+)*$")

def engram_save(title, content, type_tag="manual", project=None, scope="project", topic_key=None):
    if type_tag == "discovery":
        return {"success": False, "error": "discovery type is reserved for auto-distill; use 'manual' or 'learning' instead"}
    if type_tag not in VALID_TYPES:
        return {"success": False, "error": f"Invalid type '{type_tag}'. Valid types: {', '.join(sorted(VALID_TYPES))}"}
    if type_tag in STRUCTURED_TYPES and topic_key is None:
        return {"success": False, "error": f"topic_key is required for type '{type_tag}'. Use format: project/<name>/{type_tag}/<topic>"}
    if topic_key is not None and not TOPIC_KEY_PATTERN.match(topic_key):
        return {"success": False, "error": f"Invalid topic_key format '{topic_key}'. Must match: ^[a-z0-9_-]+(/[a-z0-9_-]+)*$"}

    conn = _get_db()
    if not conn:
        return {"success": False, "error": f"Database not found: {ENGRAM_DB}"}
    _migrate(conn)
    proj = project or PROJECT_NAME
    conflicts = []
    warnings = []
    if "**" not in content:
        warnings.append("Content does not use structured format (**What**/**Why**/**Where**/**Learned**). Consider adding structure for better retrieval.")
    try:
        # Conflict detection via topic_key
        if topic_key:
            rows = conn.execute(
                """SELECT id, title, content, topic_key, updated_at FROM observations
                   WHERE topic_key = ? AND project = ? AND scope = ? AND deleted_at IS NULL
                   ORDER BY updated_at DESC LIMIT 5""",
                (topic_key, proj, scope)).fetchall()
            for r in rows:
                conflicts.append(_row_to_dict(r))
                # Soft-delete the old entry
                conn.execute(
                    "UPDATE observations SET deleted_at = datetime('now') WHERE id = ?",
                    (r["id"],))

        # Ensure a session exists
        session_id = f"brain-router-{proj}"
        conn.execute(
            "INSERT OR IGNORE INTO sessions (id, project, directory, started_at) VALUES (?, ?, ?, datetime('now'))",
            (session_id, proj, os.getcwd()))

        conn.execute(
            """INSERT INTO observations (session_id, type, title, content, project, scope, topic_key, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
            (session_id, type_tag, title, content, proj, scope, topic_key))
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        result = {"success": True, "id": new_id, "project": proj}
        if conflicts:
            result["superseded"] = [c["id"] for c in conflicts]
            result["superseded_count"] = len(conflicts)
            result["note"] = f"Superseded {len(conflicts)} older entries with topic_key '{topic_key}'"
        if warnings:
            result["warnings"] = warnings
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

def engram_update(obs_id, **kwargs):
    conn = _get_db()
    if not conn:
        return {"success": False, "error": "DB not found"}
    try:
        sets, params = [], []
        for k in ("title", "content", "type", "scope", "topic_key"):
            if k in kwargs and kwargs[k] is not None:
                sets.append(f"{k} = ?")
                params.append(kwargs[k])
        if not sets:
            return {"success": False, "error": "Nothing to update"}
        sets.append("updated_at = datetime('now')")
        sets.append("revision_count = revision_count + 1")
        params.append(obs_id)
        conn.execute(f"UPDATE observations SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
        return {"success": True, "id": obs_id}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

def engram_delete(obs_id):
    conn = _get_db()
    if not conn:
        return {"success": False, "error": "DB not found"}
    try:
        conn.execute("UPDATE observations SET deleted_at = datetime('now') WHERE id = ?", (obs_id,))
        conn.commit()
        return {"success": True, "id": obs_id}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()



# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# CGC integration — structural memory layer
# ---------------------------------------------------------------------------

def _cgc_available():
    """Check if CodeGraphContext CLI is installed."""
    try:
        subprocess.run(["cgc", "--version"], capture_output=True, timeout=3)
        return True
    except Exception:
        return False

def _cgc_run(args):
    """Run a cgc command and return parsed JSON output."""
    try:
        result = subprocess.run(
            ["cgc"] + args,
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return {"error": result.stderr or "cgc command failed"}
        # Try to parse JSON, fallback to raw text
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"output": result.stdout}
    except subprocess.TimeoutExpired:
        return {"error": "cgc command timed out (>30s)"}
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = {
    "brain_query": {
        "description": "Search all memory. Auto-routes to the right store. Use for ANY memory lookup.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for."},
                "limit": {"type": "integer", "description": "Max results.", "default": 10}
            },
            "required": ["query"]
        }
    },
    "brain_save": {
        "description": "Save a structured fact. Auto-detects conflicts via topic_key and supersedes stale entries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title."},
                "content": {"type": "string", "description": "The fact (what/why/where/learned)."},
                "type": {"type": "string", "enum": ["decision", "architecture", "bugfix", "pattern", "config", "learning", "manual"], "default": "manual"},
                "topic_key": {"type": "string", "description": "Topic ID for conflict detection (e.g. 'auth/jwt-strategy'). Required for structured types (decision, architecture, bugfix, pattern, config)."},
                "scope": {"type": "string", "enum": ["project", "personal"], "default": "project"}
            },
            "required": ["title", "content"]
        }
    },
    "brain_context": {
        "description": "Load session-start context. Call before your first reply every session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_limit": {"type": "integer", "default": 20},
                "global_limit": {"type": "integer", "default": 5}
            }
        }
    },
    "brain_correct": {
        "description": "Fix a wrong memory. Finds it in engram, supersedes, saves corrected version.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "search_query": {"type": "string"},
                "corrected_content": {"type": "string"},
                "reason": {"type": "string", "default": "user correction"}
            },
            "required": ["search_query", "corrected_content"]
        }
    },
    "brain_forget": {
        "description": "Soft-delete a memory from engram.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "search_query": {"type": "string"},
                "confirm": {"type": "boolean", "default": False}
            },
            "required": ["search_query"]
        }
    },
    "brain_diagram": {
        "description": "Generate or load codebase architecture diagram via CodeGraphContext. Returns file counts, complexity hotspots, dead code, and structure.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project path (default: cwd)", "default": "."},
                "force_regenerate": {"type": "boolean", "description": "Force full reindex even if graph exists", "default": False}
            }
        }
    },
    "brain_callers": {
        "description": "Find who calls a function or uses a symbol. Structural query via CodeGraphContext.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Function name or symbol to find callers for"},
                "context": {"type": "string", "description": "File path for disambiguation", "default": ""}
            },
            "required": ["target"]
        }
    },
    "brain_structure": {
        "description": "Get repository stats from CodeGraphContext: files, functions, classes, modules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": "."}
            }
        }
    },
    "brain_codebase_index": {
        "description": "Index a project into the structural code graph (CodeGraphContext). Run once per project or after major refactors.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project root path", "default": "."},
                "force": {"type": "boolean", "description": "Force reindex even if already indexed", "default": False}
            }
        }
    },
    "brain_codebase_search": {
        "description": "Hybrid semantic search over codebase symbols (CodeCartographer BM25 + embeddings). Natural language queries like 'function that handles portfolio grading'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "path": {"type": "string", "description": "Project root path", "default": "."},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    },
    "brain_validate": {
        "description": "Validate an observation before saving. Checks Compiled Truth, Timeline, and Auto-Links format.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Observation content to validate"},
                "type": {"type": "string", "description": "Observation type", "default": "manual"}
            },
            "required": ["content"]
        }
    },
    "brain_session_start": {
        "description": "Start a tracked session. Initializes session state for checkpoint monitoring.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project name", "default": "global"}
            }
        }
    },
    "brain_session_end": {
        "description": "End the current tracked session. Returns session stats.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    "brain_checkpoint": {
        "description": "Save a checkpoint observation. Captures current task, recent actions, and open files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Current task description"},
                "recent_actions": {"type": "array", "items": {"type": "string"}, "description": "List of recent actions"},
                "open_files": {"type": "array", "items": {"type": "string"}, "description": "List of open files"}
            },
            "required": ["task"]
        }
    },
    "brain_session_stats": {
        "description": "Get current session statistics (elapsed time, tool calls, checkpoints).",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    "brain_reason": {
        "description": "Reasoning gate. Declare mode and get approved budget. Call at start of every non-trivial task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "proposed_mode": {"type": "string", "enum": ["fast", "deliberate", "slow"], "description": "Proposed reasoning mode"},
                "justification": {"type": "string", "description": "Why this mode?"},
                "task_description": {"type": "string", "description": "What are we doing?"}
            },
            "required": ["proposed_mode", "justification"]
        }
    },
    "brain_calibrate": {
        "description": "Auto-save calibration data after DELIBERATE/SLOW tasks. Records mode, pulls, tokens, outcome.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode_declared": {"type": "string", "description": "Mode that was used"},
                "pulls_actual": {"type": "integer", "description": "Actual pulls used"},
                "tokens_actual": {"type": "integer", "description": "Actual reasoning tokens used (estimate)"},
                "outcome": {"type": "string", "enum": ["success", "partial", "failure"], "description": "Task outcome"},
                "would_fast_have_sufficed": {"type": "string", "enum": ["yes", "no", "uncertain"], "description": "Could FAST mode have handled this?"}
            },
            "required": ["mode_declared", "outcome"]
        }
    },
    "brain_calibration_stats": {
        "description": "Get aggregate calibration statistics. Shows fast sufficiency rate, breach rate, slow overuse.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
}

def handle_brain_query(p):
    query = p["query"]
    limit = p.get("limit", 10)

    # Fix #6: Explicit store status
    status = _store_status()
    warnings = []
    if not status["engram_available"]:
        warnings.append("engram store unavailable — install with: brew tap gentleman-programming/tap && brew install engram")

    structured = []
    global_results = []

    # Search project engram
    if status["engram_available"] and status["engram_db_exists"]:
        structured = engram_search(query, limit=limit, project=PROJECT_NAME)
        # Also check global
        global_results = engram_search(query, db_path=ENGRAM_GLOBAL_DB, limit=5) if os.path.isfile(ENGRAM_GLOBAL_DB) else []

    # Fix #8: Deduplicate — remove global results that already appear in project results
    project_ids = {r.get("id") for r in structured}
    global_results = [r for r in global_results if r.get("id") not in project_ids]

    return {
        "query": query,
        "structured": structured,
        "global": global_results,
        "counts": {"structured": len(structured), "global": len(global_results)},
        "warnings": warnings
    }

def _codecartographer_available():
    """Check if CodeCartographer CLI is installed."""
    try:
        subprocess.run(["codecartographer", "--version"], capture_output=True, timeout=3)
        return True
    except Exception:
        return False


def _codecartographer_run(args, cwd=None, timeout=60):
    """Run a codecartographer command and return parsed output."""
    try:
        result = subprocess.run(
            ["codecartographer"] + args,
            capture_output=True, text=True, timeout=timeout, cwd=cwd
        )
        if result.returncode != 0:
            return {"error": result.stderr or "codecartographer command failed"}
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"output": result.stdout}
    except subprocess.TimeoutExpired:
        return {"error": f"codecartographer timed out (>{timeout}s)"}
    except Exception as e:
        return {"error": str(e)}


def handle_brain_save(p):
    title = p["title"]
    content = p["content"]
    type_tag = p.get("type", "manual")
    topic_key = p.get("topic_key")
    scope = p.get("scope", "project")

    validation = None
    if HAS_VALIDATION:
        # Full validation with auto-fix and enforcement
        validation = observation_validator.validate(content, type_tag)
        content = validation["content"]  # Use potentially auto-fixed content

        # Reject if unfixable and enforced
        if validation["enforce"] and not validation["valid"]:
            return {
                "saved": False,
                "error": f"Observation rejected: {validation['reject_reason']}",
                "format_validation": validation,
                "suggestion": "Fix the content and call brain_validate first, or use brain_save with type='manual' (not recommended for code-relevant facts)."
            }

    result = engram_save(title, content, type_tag=type_tag,
                         topic_key=topic_key, scope=scope)
    result["saved"] = True
    if validation:
        result["format_validation"] = validation
    return result

def handle_brain_context(p):
    # Fix #6: Explicit store status
    status = _store_status()
    warnings = []
    if not status["engram_available"]:
        warnings.append("engram store unavailable")

    # Fix #7: Load ALL global memories, not just scope="personal"
    project_ctx = engram_context(limit=p.get("project_limit", 20), project=PROJECT_NAME) if status["engram_available"] else []
    global_ctx = engram_context(db_path=ENGRAM_GLOBAL_DB, limit=p.get("global_limit", 5)) if (status["engram_available"] and os.path.isfile(ENGRAM_GLOBAL_DB)) else []

    return {
        "project": PROJECT_NAME,
        "project_memories": project_ctx, "project_count": len(project_ctx),
        "global_memories": global_ctx, "global_count": len(global_ctx),
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "warnings": warnings,
        "tip": "Do NOT ask the user to repeat anything listed here. These are authoritative memories."
    }

def handle_brain_correct(p):
    existing = engram_search(p["search_query"], limit=3, project=PROJECT_NAME)

    if not existing:
        return {"success": False, "error": f"No memory found for '{p['search_query']}'"}

    target = existing[0]
    if isinstance(target, dict) and "error" in target:
        return {"success": False, "error": target["error"]}

    engram_delete(target["id"])
    new = engram_save(f"[corrected] {target.get('title', p['search_query'])}",
                      p["corrected_content"], type_tag=target.get("type", "manual"),
                      topic_key=target.get("topic_key"))

    return {
        "corrected": True,
        "engram": {"old_id": target["id"], "new": new},
        "reason": p.get("reason", "user correction")
    }

def handle_brain_forget(p):
    if not p.get("confirm"):
        return {"success": False, "error": "Set confirm=true to delete. Irreversible."}

    existing = engram_search(p["search_query"], limit=1, project=PROJECT_NAME)

    if not existing or (isinstance(existing[0], dict) and "error" in existing[0]):
        return {"success": False, "error": f"No memory found for '{p['search_query']}'"}

    return engram_delete(existing[0]["id"])

def handle_brain_diagram(p):
    path = p.get("path", ".")
    force = p.get("force_regenerate", False)
    
    if not _cgc_available():
        return {
            "error": "CodeGraphContext not installed. Install: uv tool install codegraphcontext",
            "diagram": None,
            "engram_fallback": "Search engram for topic_key='codebase/diagram/{PROJECT_NAME}' instead"
        }
    
    # Check if graph exists
    contexts = _cgc_run(["list"])
    has_graph = not ("error" in contexts and "No projects" in str(contexts.get("error", "")))
    
    if force or not has_graph:
        # Force reindex
        _cgc_run(["add_code_to_graph", path, "--is-dependency=false"])
    
    # Get stats
    stats = _cgc_run(["stats", path])
    
    # Get complexity
    complexity = _cgc_run(["analyze", "complexity", "--limit", "10"])
    
    # Get dead code
    dead_code = _cgc_run(["analyze", "dead-code"])
    
    return {
        "source": "codegraphcontext",
        "path": path,
        "stats": stats,
        "complexity_hotspots": complexity,
        "dead_code_candidates": dead_code,
        "tip": "For historical context about this codebase, search engram with mem_search"
    }

def handle_brain_callers(p):
    target = p["target"]
    context = p.get("context", "")
    
    if not _cgc_available():
        return {"error": "CodeGraphContext not installed"}
    
    # Use CGC's find_code for simple lookup
    result = _cgc_run(["find_code", target])
    return {
        "target": target,
        "context": context,
        "results": result,
        "tip": f"For call chain analysis, use CGC directly: cgc analyze call-chain --target {target}"
    }

def handle_brain_structure(p):
    path = p.get("path", ".")
    
    if not _cgc_available():
        return {"error": "CodeGraphContext not installed"}
    
    return _cgc_run(["stats", path])


# ---------------------------------------------------------------------------
# Phase 2: CodeCartographer integration (subprocess with timeout)
# ---------------------------------------------------------------------------

def _cc_available():
    try:
        subprocess.run(["which", "codecartographer"], capture_output=True, text=True, check=True, timeout=5)
        return True
    except Exception:
        return False

def _cc_run(args: List[str], cwd: str = None, timeout: int = 60):
    cmd = ["codecartographer"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        if result.returncode != 0:
            return {"error": f"CodeCartographer failed: {result.stderr.strip() or result.stdout.strip()}", "command": " ".join(cmd)}
        return json.loads(result.stdout) if result.stdout.strip() else {"success": True}
    except subprocess.TimeoutExpired:
        return {"error": f"CodeCartographer timed out after {timeout}s", "command": " ".join(cmd)}
    except json.JSONDecodeError:
        return {"raw_output": result.stdout.strip(), "command": " ".join(cmd)}
    except Exception as e:
        return {"error": str(e), "command": " ".join(cmd)}

def handle_brain_codebase_index(p):
    """Index a codebase with CGC and generate GRAPH_REPORT.md with CodeCartographer."""
    path = p.get("path", ".")
    force = p.get("force_reindex", False)
    backend = p.get("backend", "memory")

    if not _cgc_available():
        return {"error": "CodeGraphContext not installed. Install: uv tool install codegraphcontext"}
    if not _cc_available():
        return {"error": "CodeCartographer not installed. Install: npm i -g codecartographer"}

    # Step 1: CGC index
    if force:
        # Delete old context if exists
        contexts = _cgc_run(["list"])
        # CGC doesn't have a direct delete; we re-add which overwrites
    cgc_result = _cgc_run(["add_code_to_graph", path, "--is-dependency=false"])

    # Step 2: CodeCartographer diagram
    cc_result = _cc_run(["diagram", path, "--backend", backend], timeout=120)

    return {
        "source": "codebase_index_pipeline",
        "path": path,
        "backend": backend,
        "cgc_index": cgc_result,
        "codecartographer_diagram": cc_result,
        "next_steps": [
            f"Graph report: {os.path.join(path, '.codecartographer', 'GRAPH_REPORT.md')}",
            "Use brain_query to search indexed code",
            "Use brain_diagram to get structural stats"
        ]
    }

def handle_brain_codebase_search(p):
    """Hybrid search across indexed code (BM25 + embeddings + RRF)."""
    query = p["search_query"]
    path = p.get("path", ".")
    limit = p.get("limit", 10)

    if not _cc_available():
        return {"error": "CodeCartographer not installed"}

    result = _cc_run(["search", query, "--path", path, "--limit", str(limit), "--hybrid"], timeout=60)
    return {
        "source": "codecartographer_hybrid_search",
        "query": query,
        "path": path,
        "results": result,
        "tip": "For temporal context about these symbols, search engram with brain_query"
    }

def handle_brain_validate(p):
    """Validate an observation before saving (Compiled Truth + Auto-Links)."""
    content = p.get("content", "")
    type_tag = p.get("type", "manual")
    
    if HAS_VALIDATION:
        result = observation_validator.validate(content, type_tag)
        # Strip the full content from the response to keep it concise
        result.pop("content", None)
        return result
    
    # Fallback if validator not available
    errors = []
    warnings = []
    if "## Compiled Truth" not in content:
        errors.append("Missing '## Compiled Truth' section. Required for all observations.")
    if "## Timeline" not in content:
        warnings.append("Missing '## Timeline' section. Recommended for tracking history.")
    
    potential_files = re.findall(r'[\w\-./]+\.(?:ts|tsx|js|jsx|py|go|rs|java|md)', content)
    potential_symbols = re.findall(r'`([^`]{3,})`', content)
    
    return {
        "valid": len(errors) == 0,
        "enforce": len(errors) > 0,
        "reject_reason": errors[0] if errors else None,
        "auto_fixes": [],
        "checks": {
            "compiled_truth": {"ok": "## Compiled Truth" in content, "message": errors[0] if errors else "OK", "required": True},
            "timeline": {"ok": "## Timeline" in content, "message": "OK" if "## Timeline" in content else "Missing", "required": False},
            "auto_links": {"ok": True, "message": "Validator module not available", "required": False},
        }
    }

# ---------------------------------------------------------------------------
# Session management handlers
# ---------------------------------------------------------------------------

def handle_brain_session_start(p):
    """Initialize a tracked session for checkpoint monitoring."""
    if not HAS_SESSION_MANAGER:
        return {"error": "session_manager module not available"}
    project = p.get("project", PROJECT_NAME or "global")
    state = session_manager.init_session(project)
    return {
        "session_started": True,
        "session_id": state.get("session_id"),
        "project": project,
        "started_at": state.get("started_at"),
        "checkpoint_thresholds": {
            "calls": session_manager.CHECKPOINT_CALLS,
            "minutes": session_manager.CHECKPOINT_MINUTES
        }
    }

def handle_brain_session_end(p):
    """End the current tracked session."""
    if not HAS_SESSION_MANAGER:
        return {"error": "session_manager module not available"}
    result = session_manager.end_session()
    return result

def handle_brain_checkpoint(p):
    """Save a checkpoint observation."""
    if not HAS_SESSION_MANAGER:
        return {"error": "session_manager module not available"}
    project = p.get("project", PROJECT_NAME or "global")
    task = p.get("task", "unknown task")
    recent_actions = p.get("recent_actions", [])
    open_files = p.get("open_files", [])
    state = session_manager.save_checkpoint(project, task, recent_actions, open_files)
    return {
        "checkpoint_saved": True,
        "session_id": state.get("session_id"),
        "tool_calls": state.get("tool_calls"),
        "checkpoints": state.get("checkpoints"),
        "last_checkpoint_at": state.get("last_checkpoint_at")
    }

def handle_brain_session_stats(p):
    """Get current session statistics."""
    if not HAS_SESSION_MANAGER:
        return {"error": "session_manager module not available"}
    return session_manager.get_session_stats()

# ---------------------------------------------------------------------------
# Reasoning management handlers (Kahneman v3.0)
# ---------------------------------------------------------------------------

def handle_brain_reason(p):
    """Reasoning gate — approve mode and return budget."""
    if not HAS_REASONING_TRACKER:
        return {"error": "reasoning_tracker module not available"}
    proposed = p.get("proposed_mode", "fast")
    justification = p.get("justification", "")
    task_desc = p.get("task_description", "")

    # Auto-override: if no justification for slow, downgrade to deliberate
    if proposed == "slow" and len(justification) < 10:
        return {
            "approved_mode": "deliberate",
            "reasoning_budget_tokens": 1500,
            "evidence_budget_pulls": 1,
            "native_reasoning": "on",
            "note": "SLOW mode requires substantive justification. Approved DELIBERATE instead. Escalate to SLOW if fatal flaw found.",
            "escalation_triggers": ["fatal flaw after pull", "3+ approaches emerge", "security implication discovered"]
        }

    budget = reasoning_tracker.BUDGETS.get(proposed, reasoning_tracker.BUDGETS["fast"])
    reasoning_tracker.start_task(proposed, task_desc)

    return {
        "approved_mode": proposed,
        "reasoning_budget_tokens": budget["tokens"] if budget["tokens"] else "unlimited",
        "evidence_budget_pulls": budget["pulls"],
        "native_reasoning": "off" if proposed == "fast" else "on",
        "justification_accepted": True,
        "escalation_triggers": [
            "3+ viable approaches" if proposed == "fast" else None,
            "high-stakes architectural impact" if proposed in ("fast", "deliberate") else None,
            "fatal flaw after pull" if proposed == "deliberate" else None,
        ]
    }

def handle_brain_calibrate(p):
    """Save calibration data after DELIBERATE/SLOW tasks."""
    if not HAS_REASONING_TRACKER:
        return {"error": "reasoning_tracker module not available"}

    mode = p.get("mode_declared", "unknown")
    pulls = p.get("pulls_actual", 0)
    tokens = p.get("tokens_actual", 0)
    outcome = p.get("outcome", "unknown")
    fast_sufficed = p.get("would_fast_have_sufficed", "uncertain")

    # End the task in reasoning tracker
    task = reasoning_tracker.end_task(outcome)

    # Save to engram
    content = f"## Compiled Truth\n**What**: Calibration data for {mode} task\n**Why**: Track mode accuracy for future optimization\n**Where**: reasoning_tracker.py\n**Learned**: {fast_sufficed} — FAST mode would have sufficed"
    if HAS_VALIDATION:
        content = observation_validator.auto_fix(content, "pattern")[0]
        content = auto_linker.append_auto_links(content)

    result = engram_save(
        title=f"Calibration: {mode} task ({outcome})",
        content=content,
        type_tag="pattern",
        topic_key="reasoning/calibration"
    )

    return {
        "calibrated": True,
        "task_id": task.get("task_id"),
        "mode": mode,
        "pulls": pulls,
        "tokens": tokens,
        "outcome": outcome,
        "would_fast_have_sufficed": fast_sufficed,
        "engram_id": result.get("id")
    }

def handle_brain_calibration_stats(p):
    """Get aggregate calibration statistics."""
    if not HAS_REASONING_TRACKER:
        return {"error": "reasoning_tracker module not available"}
    return reasoning_tracker.get_calibration_stats()

HANDLERS = {
    "brain_query": handle_brain_query, "brain_save": handle_brain_save,
    "brain_context": handle_brain_context, "brain_correct": handle_brain_correct,
    "brain_forget": handle_brain_forget,
    "brain_diagram": handle_brain_diagram,
    "brain_callers": handle_brain_callers,
    "brain_structure": handle_brain_structure,
    "brain_codebase_index": handle_brain_codebase_index,
    "brain_codebase_search": handle_brain_codebase_search,
    "brain_validate": handle_brain_validate,
    "brain_session_start": handle_brain_session_start,
    "brain_session_end": handle_brain_session_end,
    "brain_checkpoint": handle_brain_checkpoint,
    "brain_session_stats": handle_brain_session_stats,
    "brain_reason": handle_brain_reason,
    "brain_calibrate": handle_brain_calibrate,
    "brain_calibration_stats": handle_brain_calibration_stats,
}

# ---------------------------------------------------------------------------
# MCP stdio server
# ---------------------------------------------------------------------------

def handle_request(req):
    method, params, rid = req.get("method"), req.get("params", {}), req.get("id")
    if method == "initialize":
        # Auto-init session if project is known
        if HAS_SESSION_MANAGER and PROJECT_NAME:
            session_manager.init_session(PROJECT_NAME)
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "brain-router", "version": "0.6.0"}
        }}
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": [
            {"name": n, "description": t["description"], "inputSchema": t["inputSchema"]}
            for n, t in TOOLS.items()
        ]}}
    if method == "tools/call":
        handler = HANDLERS.get(params.get("name"))
        if not handler:
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Unknown tool: {params.get('name')}"}}
        try:
            tool_name = params.get("name")
            result = handler(params.get("arguments", {}))
            # Token estimation heuristic: response JSON size / 4 ≈ token count
            # (1 token ≈ 4 chars for English text; conservative estimate)
            estimated_tokens = len(json.dumps(result, default=str)) // 4
            # Track tool calls and inject checkpoint suggestion if due
            if HAS_SESSION_MANAGER:
                session_manager.record_tool_call()
                suggestion = session_manager.get_checkpoint_suggestion()
                if suggestion:
                    result["_checkpoint_suggestion"] = suggestion
            # Track reasoning pulls and inject budget warning if breached
            if HAS_REASONING_TRACKER:
                reasoning_tracker.record_pull(tool_name, estimated_tokens)
                budget_warning = reasoning_tracker.get_budget_warning()
                if budget_warning:
                    result["_budget_warning"] = budget_warning
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]
            }}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "isError": True
            }}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Unknown: {method}"}}

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle_request(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
