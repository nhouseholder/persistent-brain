#!/usr/bin/env python3
"""Tests for observation_validator.py."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "router"))

from observation_validator import (
    validate_compiled_truth,
    validate_timeline,
    validate_auto_links,
    auto_fix,
    validate,
    CODE_RELEVANT_TYPES,
)


class TestValidateCompiledTruth:
    def test_valid_with_header(self):
        ok, msg, fixable = validate_compiled_truth("## Compiled Truth\n**What**: x")
        assert ok is True
        assert fixable is False

    def test_missing_header_but_has_fields(self):
        ok, msg, fixable = validate_compiled_truth("**What**: x\n**Why**: y")
        assert ok is False
        assert fixable is True
        assert "missing" in msg.lower()

    def test_missing_everything(self):
        ok, msg, fixable = validate_compiled_truth("Just some text")
        assert ok is False
        assert fixable is False
        assert "Missing" in msg


class TestValidateTimeline:
    def test_valid_with_timeline(self):
        ok, msg, fixable = validate_timeline("## Timeline\n- 2026-04-26: x")
        assert ok is True
        assert fixable is False

    def test_missing_timeline(self):
        ok, msg, fixable = validate_timeline("No timeline here")
        assert ok is False
        assert fixable is True


class TestValidateAutoLinks:
    def test_code_type_with_links(self):
        ok, msg, fixable = validate_auto_links("## Compiled Truth\n**What**: Fixed src/main.py\n**Why**: bug", "bugfix")
        assert ok is False  # missing Auto-Links section
        assert fixable is True  # but links are extractable

    def test_code_type_without_links(self):
        ok, msg, fixable = validate_auto_links("Just text no code refs", "bugfix")
        assert ok is False
        assert fixable is False  # nothing to extract

    def test_non_code_type(self):
        ok, msg, fixable = validate_auto_links("Whatever", "learning")
        assert ok is True
        assert "non-code" in msg.lower()

    def test_already_has_auto_links(self):
        ok, msg, fixable = validate_auto_links("## Auto-Links\n- src/main.py", "bugfix")
        assert ok is True
        assert fixable is False


class TestAutoFix:
    def test_adds_compiled_truth_header(self):
        content, fixes = auto_fix("**What**: x\n**Why**: y", "bugfix")
        assert "## Compiled Truth" in content
        assert any("Compiled Truth" in f for f in fixes)

    def test_adds_timeline(self):
        content, fixes = auto_fix("## Compiled Truth\n**What**: x", "manual")
        assert "## Timeline" in content
        assert any("Timeline" in f for f in fixes)

    def test_adds_auto_links_for_code_type(self):
        content, fixes = auto_fix("**What**: Fixed src/auth.ts\n**Why**: bug", "bugfix")
        assert "## Auto-Links" in content
        assert any("Auto-Links" in f for f in fixes)

    def test_no_auto_links_for_non_code_type(self):
        content, fixes = auto_fix("**What**: Note\n**Why**: Reason", "learning")
        assert "## Auto-Links" not in content


class TestValidate:
    def test_valid_observation(self):
        content = "## Compiled Truth\n**What**: x\n**Why**: y\n\n---\n## Timeline\n- 2026-04-26: z\n\n## Auto-Links\n- src/main.py"
        result = validate(content, "bugfix")
        assert result["valid"] is True
        assert result["enforce"] is False
        assert result["reject_reason"] is None
        assert result["auto_fixes"] == []

    def test_rejects_missing_compiled_truth(self):
        result = validate("Just text", "bugfix")
        assert result["valid"] is False
        assert result["enforce"] is True
        assert "Compiled Truth" in result["reject_reason"]

    def test_auto_fixes_header(self):
        result = validate("**What**: x\n**Why**: y\n**Where**: src/main.py", "bugfix")
        assert result["valid"] is True
        assert result["enforce"] is False
        assert any("Compiled Truth" in f for f in result["auto_fixes"])

    def test_manual_no_code_refs_warns_only(self):
        result = validate("## Compiled Truth\n**What**: Note\n**Why**: Reason", "manual")
        # manual IS in CODE_RELEVANT_TYPES, but no extractable links
        assert result["valid"] is False  # timeline is missing
        assert result["enforce"] is False  # but not enforced (no code refs)

    def test_code_type_with_extractable_links_auto_fixes(self):
        result = validate("## Compiled Truth\n**What**: Fixed src/auth.ts\n**Why**: bug", "bugfix")
        assert result["valid"] is True
        assert any("Auto-Links" in f for f in result["auto_fixes"])

    def test_returns_fixed_content(self):
        result = validate("**What**: x\n**Why**: y", "bugfix")
        assert "## Compiled Truth" in result["content"]
        assert "## Timeline" in result["content"]

    def test_all_code_relevant_types(self):
        for t in CODE_RELEVANT_TYPES:
            result = validate("Just text no code refs", t)
            # Should not enforce Auto-Links if no links exist
            if not result["valid"] and result["enforce"]:
                assert "Compiled Truth" in result["reject_reason"]  # not Auto-Links
