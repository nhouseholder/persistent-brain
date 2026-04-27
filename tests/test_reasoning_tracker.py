#!/usr/bin/env python3
"""Tests for reasoning_tracker.py."""

import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "router"))

import reasoning_tracker as rt


class TestStartTask:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        rt.STATE_DIR = self.tmpdir
        rt.STATE_FILE = self.tmpdir / "reasoning_state.json"

    def teardown_method(self):
        if rt.STATE_FILE.exists():
            rt.STATE_FILE.unlink()
        self.tmpdir.rmdir()

    def test_fast_task(self):
        task = rt.start_task("fast", "rename variable")
        assert task["mode"] == "fast"
        assert task["budget_pulls"] == 0
        assert task["budget_tokens"] == 200
        assert task["pulls_used"] == 0

    def test_deliberate_task(self):
        task = rt.start_task("deliberate", "check auth pattern")
        assert task["mode"] == "deliberate"
        assert task["budget_pulls"] == 1
        assert task["budget_tokens"] == 1500

    def test_slow_task(self):
        task = rt.start_task("slow", "design auth architecture")
        assert task["mode"] == "slow"
        assert task["budget_pulls"] == 3
        assert task["budget_tokens"] is None


class TestRecordPull:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        rt.STATE_DIR = self.tmpdir
        rt.STATE_FILE = self.tmpdir / "reasoning_state.json"
        rt.start_task("deliberate", "test task")

    def teardown_method(self):
        if rt.STATE_FILE.exists():
            rt.STATE_FILE.unlink()
        self.tmpdir.rmdir()

    def test_counts_research_tool(self):
        rt.record_pull("brain_query")
        task = rt.get_task_stats()
        assert task["pulls_used"] == 1

    def test_ignores_non_research(self):
        rt.record_pull("web_search")
        task = rt.get_task_stats()
        assert task["pulls_used"] == 0

    def test_breach_detection(self):
        rt.record_pull("brain_query")
        rt.record_pull("brain_diagram")
        breached, task = rt.is_budget_breached()
        assert breached is True


class TestBudgetBreach:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        rt.STATE_DIR = self.tmpdir
        rt.STATE_FILE = self.tmpdir / "reasoning_state.json"

    def teardown_method(self):
        if rt.STATE_FILE.exists():
            rt.STATE_FILE.unlink()
        self.tmpdir.rmdir()

    def test_fast_breaches_on_any_pull(self):
        rt.start_task("fast", "test")
        rt.record_pull("brain_query")
        breached, _ = rt.is_budget_breached()
        assert breached is True

    def test_no_breach_within_budget(self):
        rt.start_task("deliberate", "test")
        rt.record_pull("brain_query")
        breached, _ = rt.is_budget_breached()
        assert breached is False

    def test_warning_when_breached(self):
        rt.start_task("fast", "test")
        rt.record_pull("brain_query")
        warning = rt.get_budget_warning()
        assert warning is not None
        assert "BUDGET BREACH" in warning

    def test_near_limit_warning(self):
        rt.start_task("deliberate", "test")
        rt.record_pull("brain_query")
        warning = rt.get_budget_warning()
        assert warning is not None
        assert "WARNING" in warning


class TestEndTask:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        rt.STATE_DIR = self.tmpdir
        rt.STATE_FILE = self.tmpdir / "reasoning_state.json"
        rt.start_task("slow", "test")
        rt.record_pull("brain_query")

    def teardown_method(self):
        if rt.STATE_FILE.exists():
            rt.STATE_FILE.unlink()
        self.tmpdir.rmdir()

    def test_archives_task(self):
        rt.end_task("success")
        stats = rt.get_calibration_stats()
        assert stats["total_tasks"] == 1


class TestCalibrationStats:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        rt.STATE_DIR = self.tmpdir
        rt.STATE_FILE = self.tmpdir / "reasoning_state.json"

    def teardown_method(self):
        if rt.STATE_FILE.exists():
            rt.STATE_FILE.unlink()
        self.tmpdir.rmdir()

    def test_empty_stats(self):
        stats = rt.get_calibration_stats()
        assert stats["total_tasks"] == 0

    def test_stats_aggregation(self):
        rt.start_task("fast", "rename")
        rt.end_task("success")

        rt.start_task("slow", "architecture")
        rt.record_pull("brain_query")
        rt.record_pull("brain_diagram")
        rt.end_task("success")

        stats = rt.get_calibration_stats()
        assert stats["total_tasks"] == 2
        assert stats["fast_count"] == 1
        assert stats["slow_count"] == 1
