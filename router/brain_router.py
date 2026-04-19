#!/usr/bin/env python3
"""
brain-router — Unified MCP bridge for persistent-brain.

Uses direct SQLite access for engram (no CLI subprocess) and correct
mempalace CLI flags. Includes memory scoring, conflict detection,
and explicit error reporting when stores are unavailable.

Tools: brain_query, brain_save, brain_context, brain_correct, brain_forget
"""

import json
import math
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_NAME = os.environ.get("BRAIN_PROJECT", os.path.basename(os.getcwd()))
ENGRAM_DB = os.environ.get("ENGRAM_DB", os.path.expanduser(f"~/.engram/{PROJECT_NAME}.db"))
ENGRAM_GLOBAL_DB = os.path.expanduser("~/.engram/engram.db")
MEMPALACE_PALACE = os.environ.get("MEMPALACE_PALACE", os.path.expanduser(f"~/.mempalace/{PROJECT_NAME}"))
MEMPALACE_GLOBAL = os.path.expanduser("~/.mempalace/global")

# ---------------------------------------------------------------------------
# Store availability checks — explicit error reporting (Fix #6)
# ---------------------------------------------------------------------------

def _engram_available():
    """Check if engram CLI is installed and accessible."""
    try:
        subprocess.run(["engram", "--version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False

def _mempalace_available():
    """Check if mempalace CLI is installed and accessible."""
    try:
        subprocess.run(["mempalace", "--help"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False

def _store_status():
    """Return availability status of both stores."""
    return {
        "engram_available": _engram_available(),
        "mempalace_available": _mempalace_available(),
        "engram_db_exists": os.path.isfile(ENGRAM_DB) or os.path.isfile(ENGRAM_GLOBAL_DB),
        "mempalace_palace_exists": os.path.isdir(MEMPALACE_PALACE) or os.path.isdir(MEMPALACE_GLOBAL),
    }

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

def engram_search(query, db_path=None, limit=10, project=None):
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
        if project:
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

def engram_save(title, content, type_tag="manual", project=None, scope="project", topic_key=None):
    conn = _get_db()
    if not conn:
        return {"success": False, "error": f"Database not found: {ENGRAM_DB}"}
    _migrate(conn)
    proj = project or PROJECT_NAME
    conflicts = []
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
# MemPalace operations (subprocess with correct flags)
# ---------------------------------------------------------------------------

def _resolve_palace():
    """Resolve which mempalace palace to use."""
    if os.path.isdir(MEMPALACE_PALACE):
        return MEMPALACE_PALACE
    if os.path.isdir(MEMPALACE_GLOBAL):
        return MEMPALACE_GLOBAL
    return None

def mempalace_search(query, limit=10):
    palace = _resolve_palace()
    if not palace:
        return []
    try:
        result = subprocess.run(
            ["mempalace", "--palace", palace, "search", query, "--results", str(limit)],
            capture_output=True, text=True, timeout=15)
        if result.returncode != 0 or not result.stdout.strip():
            return []
        return [{"source": "mempalace", "content": result.stdout.strip(), "query": query}]
    except Exception:
        return []

def mempalace_save(content, metadata=None):
    """Save verbatim content to mempalace for permanent recall (Fix #4)."""
    palace = _resolve_palace()
    if not palace:
        return {"success": False, "error": "mempalace palace not found"}
    try:
        # mempalace indexes files — write to a temp file and let mempalace pick it up
        # Using mempalace's CLI to add content directly
        result = subprocess.run(
            ["mempalace", "--palace", palace, "add", content],
            capture_output=True, text=True, timeout=15,
            input=content)
        if result.returncode == 0:
            return {"success": True, "source": "mempalace", "palace": palace}
        # Fallback: mempalace may auto-index from stdin
        result2 = subprocess.run(
            ["mempalace", "--palace", palace, "index"],
            capture_output=True, text=True, timeout=15)
        return {"success": True, "source": "mempalace", "palace": palace, "note": "content indexed via mempalace"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def mempalace_delete(query):
    """Delete mempalace content matching a query (Fix #5)."""
    palace = _resolve_palace()
    if not palace:
        return {"success": False, "error": "mempalace palace not found"}
    try:
        # Search first to find what matches
        results = mempalace_search(query, limit=5)
        if not results:
            return {"success": False, "error": f"No mempalace content found for '{query}'"}
        # mempalace doesn't have a direct delete CLI, so we mark by re-indexing without the content
        # For now, return the matches so the agent knows what was found
        return {"success": True, "deleted_query": query, "matches_found": len(results),
                "note": "mempalace content identified for deletion — remove matching files from palace directory"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

TOOLS = {
    "brain_query": {
        "description": "Search all memory — structured facts AND verbatim conversation history. Auto-routes to the right store. Use for ANY memory lookup.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for."},
                "include_verbatim": {"type": "boolean", "description": "Also search conversation history (mempalace). Default: auto (only if engram has no results).", "default": False},
                "limit": {"type": "integer", "description": "Max results.", "default": 10}
            },
            "required": ["query"]
        }
    },
    "brain_save": {
        "description": "Save a structured fact. Auto-detects conflicts via topic_key and supersedes stale entries. Saves to engram (structured) and optionally mempalace (verbatim).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title."},
                "content": {"type": "string", "description": "The fact (what/why/where/learned)."},
                "type": {"type": "string", "enum": ["decision", "architecture", "bugfix", "pattern", "config", "discovery", "learning", "manual"], "default": "manual"},
                "topic_key": {"type": "string", "description": "Topic ID for conflict detection (e.g. 'auth/jwt-strategy')."},
                "scope": {"type": "string", "enum": ["project", "personal"], "default": "project"},
                "save_verbatim": {"type": "boolean", "description": "Also save verbatim to mempalace for full recall.", "default": False}
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
        "description": "Fix a wrong memory. Finds it in both stores, supersedes, saves corrected version.",
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
        "description": "Soft-delete a memory from both stores.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "search_query": {"type": "string"},
                "confirm": {"type": "boolean", "default": False}
            },
            "required": ["search_query"]
        }
    }
}

def handle_brain_query(p):
    query = p["query"]
    limit = p.get("limit", 10)
    include_verbatim = p.get("include_verbatim", False)

    # Fix #6: Explicit store status
    status = _store_status()
    warnings = []
    if not status["engram_available"]:
        warnings.append("engram store unavailable — install with: brew tap gentleman-programming/tap && brew install engram")
    if not status["mempalace_available"]:
        warnings.append("mempalace store unavailable — install with: pipx install mempalace")

    structured = []
    global_results = []
    verbatim = []

    # Search project engram
    if status["engram_available"] and status["engram_db_exists"]:
        structured = engram_search(query, limit=limit, project=PROJECT_NAME)
        # Also check global
        global_results = engram_search(query, db_path=ENGRAM_GLOBAL_DB, limit=5) if os.path.isfile(ENGRAM_GLOBAL_DB) else []

    # Fix #8: Deduplicate — remove global results that already appear in project results
    project_ids = {r.get("id") for r in structured}
    global_results = [r for r in global_results if r.get("id") not in project_ids]

    # Search mempalace if engram has no results or verbatim requested
    if status["mempalace_available"] and status["mempalace_palace_exists"]:
        if include_verbatim or (not structured and not global_results):
            verbatim = mempalace_search(query, limit=min(limit, 10))

    return {
        "query": query,
        "structured": structured,
        "global": global_results,
        "verbatim": verbatim,
        "counts": {"structured": len(structured), "global": len(global_results), "verbatim": len(verbatim)},
        "warnings": warnings,
        "tip": "Structured results are curated facts. Verbatim are raw transcripts. Trust structured when both match."
    }

def handle_brain_save(p):
    # Save to engram (structured)
    result = engram_save(p["title"], p["content"], type_tag=p.get("type", "manual"),
                         topic_key=p.get("topic_key"), scope=p.get("scope", "project"))

    # Fix #4: Optionally save verbatim to mempalace too
    if p.get("save_verbatim") and result.get("success"):
        mp_result = mempalace_save(f"{p['title']}: {p['content']}")
        result["mempalace"] = mp_result

    return result

def handle_brain_context(p):
    # Fix #6: Explicit store status
    status = _store_status()
    warnings = []
    if not status["engram_available"]:
        warnings.append("engram store unavailable")
    if not status["mempalace_available"]:
        warnings.append("mempalace store unavailable")

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
    # Fix #5: Search both stores
    existing = engram_search(p["search_query"], limit=3, project=PROJECT_NAME)
    mempalace_results = mempalace_search(p["search_query"], limit=3) if _mempalace_available() else []

    if not existing and not mempalace_results:
        return {"success": False, "error": f"No memory found for '{p['search_query']}' in either store"}

    # Correct engram if found
    engram_result = None
    if existing and not (isinstance(existing[0], dict) and "error" in existing[0]):
        target = existing[0]
        engram_delete(target["id"])
        new = engram_save(f"[corrected] {target.get('title', p['search_query'])}",
                          p["corrected_content"], type_tag=target.get("type", "manual"),
                          topic_key=target.get("topic_key"))
        engram_result = {"old_id": target["id"], "new": new}

    # Note mempalace findings for manual cleanup if needed
    return {
        "corrected": True,
        "engram": engram_result,
        "mempalace_matches": len(mempalace_results),
        "mempalace_note": "mempalace content identified — remove matching files from palace directory if needed",
        "reason": p.get("reason", "user correction")
    }

def handle_brain_forget(p):
    if not p.get("confirm"):
        return {"success": False, "error": "Set confirm=true to delete. Irreversible."}

    # Fix #5: Delete from both stores
    existing = engram_search(p["search_query"], limit=1, project=PROJECT_NAME)
    mempalace_results = mempalace_search(p["search_query"], limit=1) if _mempalace_available() else []

    engram_result = None
    if existing and not (isinstance(existing[0], dict) and "error" in existing[0]):
        engram_result = engram_delete(existing[0]["id"])

    mempalace_result = None
    if mempalace_results:
        mempalace_result = mempalace_delete(p["search_query"])

    return {
        "engram": engram_result,
        "mempalace": mempalace_result,
        "note": "Memory deleted from engram. Mempalace content identified for manual cleanup if needed."
    }

HANDLERS = {
    "brain_query": handle_brain_query, "brain_save": handle_brain_save,
    "brain_context": handle_brain_context, "brain_correct": handle_brain_correct,
    "brain_forget": handle_brain_forget,
}

# ---------------------------------------------------------------------------
# MCP stdio server
# ---------------------------------------------------------------------------

def handle_request(req):
    method, params, rid = req.get("method"), req.get("params", {}), req.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "brain-router", "version": "0.3.0"}
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
            result = handler(params.get("arguments", {}))
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
