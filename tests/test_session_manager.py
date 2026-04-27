#!/usr/bin/env python3
"""Tests for session_manager.py."""

import sys
import os
import json
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "router"))

import session_manager as sm


class TestInitSession:
    def setup_method(self):
        # Use a temp dir for state
        self.tmpdir = Path(tempfile.mkdtemp())
        sm.STATE_DIR = self.tmpdir
        sm.STATE_FILE = self.tmpdir / "session_state.json"

    def teardown_method(self):
        if sm.STATE_FILE.exists():
            sm.STATE_FILE.unlink()
        self.tmpdir.rmdir()

    def test_init_creates_state(self):
        state = sm.init_session("myapp")
        assert state["project"] == "myapp"
        assert "session_id" in state
        assert "started_at" in state
        assert state["tool_calls"] == 0
        assert state["checkpoints"] == 0

    def test_state_persisted_to_file(self):
        sm.init_session("myapp")
        assert sm.STATE_FILE.exists()
        with open(sm.STATE_FILE) as f:
            data = json.load(f)
        assert data["project"] == "myapp"


class TestRecordToolCall:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        sm.STATE_DIR = self.tmpdir
        sm.STATE_FILE = self.tmpdir / "session_state.json"
        sm.init_session("myapp")

    def teardown_method(self):
        if sm.STATE_FILE.exists():
            sm.STATE_FILE.unlink()
        self.tmpdir.rmdir()

    def test_increments_counter(self):
        sm.record_tool_call()
        sm.record_tool_call()
        state = sm.record_tool_call()
        assert state["tool_calls"] == 3

    def test_no_state_returns_empty(self):
        sm.STATE_FILE.unlink()
        state = sm.record_tool_call()
        assert state == {}


class TestCheckpointDue:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        sm.STATE_DIR = self.tmpdir
        sm.STATE_FILE = self.tmpdir / "session_state.json"
        sm.init_session("myapp")

    def teardown_method(self):
        if sm.STATE_FILE.exists():
            sm.STATE_FILE.unlink()
        self.tmpdir.rmdir()

    def test_not_due_initially(self):
        due, state = sm.is_checkpoint_due()
        assert due is False

    def test_due_after_10_calls(self):
        for _ in range(10):
            sm.record_tool_call()
        due, state = sm.is_checkpoint_due()
        assert due is True

    def test_due_after_time(self):
        # Manually set last_checkpoint_at to 20 minutes ago
        with open(sm.STATE_FILE) as f:
            data = json.load(f)
        from datetime import datetime, timezone, timedelta
        old = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
        data["last_checkpoint_at"] = old
        with open(sm.STATE_FILE, "w") as f:
            json.dump(data, f)
        due, state = sm.is_checkpoint_due()
        assert due is True

    def test_not_due_after_checkpoint_reset(self):
        for _ in range(10):
            sm.record_tool_call()
        sm.save_checkpoint("myapp", "test", ["a"], ["f.py"])
        due, state = sm.is_checkpoint_due()
        assert due is False


class TestSaveCheckpoint:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        sm.STATE_DIR = self.tmpdir
        sm.STATE_FILE = self.tmpdir / "session_state.json"
        sm.init_session("myapp")

    def teardown_method(self):
        if sm.STATE_FILE.exists():
            sm.STATE_FILE.unlink()
        self.tmpdir.rmdir()

    def test_increments_checkpoint_count(self):
        sm.save_checkpoint("myapp", "task1", ["a"], ["f.py"])
        state = sm.save_checkpoint("myapp", "task2", ["b"], ["g.py"])
        assert state["checkpoints"] == 2

    def test_resets_call_counter(self):
        for _ in range(5):
            sm.record_tool_call()
        sm.save_checkpoint("myapp", "task", ["a"], ["f.py"])
        due, state = sm.is_checkpoint_due()
        assert due is False


class TestSessionStats:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        sm.STATE_DIR = self.tmpdir
        sm.STATE_FILE = self.tmpdir / "session_state.json"

    def teardown_method(self):
        if sm.STATE_FILE.exists():
            sm.STATE_FILE.unlink()
        self.tmpdir.rmdir()

    def test_no_session(self):
        stats = sm.get_session_stats()
        assert stats["active"] is False

    def test_active_session(self):
        sm.init_session("myapp")
        sm.record_tool_call()
        stats = sm.get_session_stats()
        assert stats["active"] is True
        assert stats["project"] == "myapp"
        assert stats["tool_calls"] == 1
        assert stats["elapsed_minutes"] >= 0


class TestEndSession:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        sm.STATE_DIR = self.tmpdir
        sm.STATE_FILE = self.tmpdir / "session_state.json"

    def teardown_method(self):
        if sm.STATE_FILE.exists():
            sm.STATE_FILE.unlink()
        self.tmpdir.rmdir()

    def test_end_no_session(self):
        result = sm.end_session()
        assert result["ended"] is False

    def test_end_active_session(self):
        sm.init_session("myapp")
        sm.record_tool_call()
        result = sm.end_session()
        assert result["ended"] is True
        assert result["total_tool_calls"] == 1


class TestCheckpointSuggestion:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        sm.STATE_DIR = self.tmpdir
        sm.STATE_FILE = self.tmpdir / "session_state.json"
        sm.init_session("myapp")

    def teardown_method(self):
        if sm.STATE_FILE.exists():
            sm.STATE_FILE.unlink()
        self.tmpdir.rmdir()

    def test_no_suggestion_initially(self):
        suggestion = sm.get_checkpoint_suggestion()
        assert suggestion is None

    def test_suggestion_when_due(self):
        for _ in range(12):
            sm.record_tool_call()
        suggestion = sm.get_checkpoint_suggestion()
        assert suggestion is not None
        assert "CHECKPOINT DUE" in suggestion
