#!/usr/bin/env python3
"""Shared pytest fixtures for unified-brain tests."""

import sys
import os
import tempfile
from pathlib import Path

# Ensure router modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "router"))

# Use a temporary directory for all test state
TEST_TMPDIR = Path(tempfile.mkdtemp(prefix="unified-brain-test-"))

# Patch session manager state dir before any imports
import session_manager as sm
sm.STATE_DIR = TEST_TMPDIR / ".unified-brain"
sm.STATE_FILE = sm.STATE_DIR / "session_state.json"

# Patch engram DB path
os.environ["ENGRAM_DB"] = str(TEST_TMPDIR / "test.db")
