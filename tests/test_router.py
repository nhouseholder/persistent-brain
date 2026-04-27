#!/usr/bin/env python3
"""Tests for brain_router.py handler functions."""

import sys
import os
import json
import tempfile

# Mock engram DB path before importing router
os.environ["ENGRAM_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "router"))

# Patch engram functions to avoid real DB dependencies
import brain_router as br

# Create a fresh in-memory DB for tests
br.ENGRAM_DB = os.path.join(tempfile.mkdtemp(), "test.db")
br.PROJECT_NAME = "testproject"


class TestBrainQuery:
    def test_returns_structured_format(self):
        # We can't easily mock without refactoring, so test the response shape
        # when engram is unavailable
        result = br.handle_brain_query({"query": "test", "limit": 5})
        assert "query" in result
        assert "structured" in result
        assert "counts" in result


class TestBrainValidate:
    def test_valid_observation(self):
        content = "## Compiled Truth\n**What**: x\n**Why**: y\n\n---\n## Timeline\n- 2026-04-26: z\n\n## Auto-Links\n- src/main.py"
        result = br.handle_brain_validate({"content": content, "type": "bugfix"})
        assert result["valid"] is True
        assert result["enforce"] is False

    def test_rejects_missing_compiled_truth(self):
        result = br.handle_brain_validate({"content": "Just text", "type": "bugfix"})
        assert result["valid"] is False
        assert result["enforce"] is True
        assert "Compiled Truth" in result["reject_reason"]

    def test_auto_fixes_header(self):
        result = br.handle_brain_validate({"content": "**What**: Fixed bug in src/main.py\n**Why**: It was broken", "type": "bugfix"})
        assert result["valid"] is True
        assert any("Compiled Truth" in f for f in result["auto_fixes"])


class TestBrainSessionStart:
    def test_starts_session(self):
        result = br.handle_brain_session_start({"project": "myapp"})
        assert result["session_started"] is True
        assert result["project"] == "myapp"
        assert "session_id" in result


class TestBrainSessionStats:
    def test_returns_stats(self):
        br.handle_brain_session_start({"project": "myapp"})
        result = br.handle_brain_session_stats({})
        assert result["active"] is True
        assert result["project"] == "myapp"


class TestBrainSessionEnd:
    def test_ends_session(self):
        br.handle_brain_session_start({"project": "myapp"})
        result = br.handle_brain_session_end({})
        assert result["ended"] is True


class TestBrainCheckpoint:
    def test_saves_checkpoint(self):
        br.handle_brain_session_start({"project": "myapp"})
        result = br.handle_brain_checkpoint({
            "task": "Refactoring",
            "recent_actions": ["Extracted function"],
            "open_files": ["src/main.py"]
        })
        assert result["checkpoint_saved"] is True
        assert result["checkpoints"] >= 1


class TestStoreStatus:
    def test_returns_status_dict(self):
        status = br._store_status()
        assert "engram_available" in status
        assert isinstance(status["engram_available"], bool)


class TestMCPProtocol:
    def test_initialize_response(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = br.handle_request(req)
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        assert "result" in resp
        assert resp["result"]["serverInfo"]["name"] == "brain-router"
        assert resp["result"]["serverInfo"]["version"] == "0.5.0"

    def test_tools_list(self):
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = br.handle_request(req)
        assert "result" in resp
        tools = resp["result"]["tools"]
        assert len(tools) == 15
        tool_names = {t["name"] for t in tools}
        assert "brain_query" in tool_names
        assert "brain_save" in tool_names
        assert "brain_validate" in tool_names
        assert "brain_session_start" in tool_names
        assert "brain_codebase_index" in tool_names

    def test_unknown_tool(self):
        req = {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "nonexistent", "arguments": {}}}
        resp = br.handle_request(req)
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_ping(self):
        req = {"jsonrpc": "2.0", "id": 4, "method": "ping", "params": {}}
        resp = br.handle_request(req)
        assert resp["result"] == {}
