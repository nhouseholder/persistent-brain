#!/usr/bin/env python3
"""Observation format validation for Compiled Truth + Timeline + Auto-Links.

Enforcement policy:
- Compiled Truth: REQUIRED. Auto-fix if **What**/**Why** fields exist but header is missing.
  Otherwise REJECT with helpful error.
- Timeline: RECOMMENDED. Auto-fix by adding separator + timestamp.
- Auto-Links: REQUIRED for code-relevant types. Auto-fix by extracting from content.
  If no links found, warn but don't reject.
"""

import re
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


CODE_RELEVANT_TYPES = {"bugfix", "decision", "architecture", "discovery", "pattern", "config", "manual"}


def validate_compiled_truth(content: str) -> tuple[bool, str, bool]:
    """Check Compiled Truth section.
    Returns (is_valid, message, can_auto_fix).
    """
    if "## Compiled Truth" in content:
        return True, "OK", False

    # Can auto-fix if What/Why fields exist but header is missing
    if "**What**" in content and "**Why**" in content:
        return False, "Has What/Why fields but missing '## Compiled Truth' header", True

    return False, "Missing '## Compiled Truth' section with **What** / **Why** / **Where** / **Learned**", False


def validate_timeline(content: str) -> tuple[bool, str, bool]:
    """Check Timeline section. Returns (is_valid, message, can_auto_fix)."""
    if "## Timeline" in content:
        return True, "OK", False
    return False, "Missing '## Timeline' section", True


def validate_auto_links(content: str, obs_type: str) -> tuple[bool, str, bool]:
    """Check Auto-Links for code-relevant types.
    Returns (is_valid, message, can_auto_fix).
    """
    if obs_type not in CODE_RELEVANT_TYPES:
        return True, "OK (non-code type)", False

    if "## Auto-Links" in content:
        return True, "OK", False

    # Can auto-fix if there are extractable links in content
    from auto_linker import extract_links
    links = extract_links(content)
    if links:
        return False, f"Code-relevant type '{obs_type}' missing Auto-Links ({len(links)} potential links found)", True

    return False, f"Code-relevant type '{obs_type}' should have '## Auto-Links' section", False


def auto_fix(content: str, obs_type: str) -> tuple[str, list[str]]:
    """Attempt to auto-fix missing sections.
    Returns (updated_content, list_of_fixes_applied).
    """
    fixes = []

    # Fix 1: Add Compiled Truth header if What/Why exist but header is missing
    if "## Compiled Truth" not in content and "**What**" in content:
        content = "## Compiled Truth\n\n" + content.lstrip()
        fixes.append("Added '## Compiled Truth' header")

    # Fix 2: Add Timeline separator if missing
    if "## Timeline" not in content:
        content = content.rstrip() + f"\n\n---\n## Timeline\n- {_now_iso()}: Initial observation"
        fixes.append("Added '## Timeline' section")

    # Fix 3: Add Auto-Links if code-relevant and missing
    if obs_type in CODE_RELEVANT_TYPES and "## Auto-Links" not in content:
        from auto_linker import append_auto_links
        new_content = append_auto_links(content)
        if new_content != content:
            content = new_content
            fixes.append("Added '## Auto-Links' section")

    return content, fixes


def validate(content: str, obs_type: str) -> dict:
    """Full validation with enforcement decision.
    Returns dict with:
    - valid: bool (after auto-fix attempts)
    - enforce: bool (True = must pass, False = warning only)
    - reject_reason: str | None (why it was rejected)
    - auto_fixes: list[str] (what was auto-fixed)
    - checks: detailed per-section results
    """
    ct_ok, ct_msg, ct_fixable = validate_compiled_truth(content)
    tl_ok, tl_msg, tl_fixable = validate_timeline(content)
    al_ok, al_msg, al_fixable = validate_auto_links(content, obs_type)

    auto_fixes = []

    # Try auto-fix if anything is fixable
    if (not ct_ok and ct_fixable) or (not tl_ok and tl_fixable) or (not al_ok and al_fixable):
        content, auto_fixes = auto_fix(content, obs_type)
        # Re-validate after auto-fix
        ct_ok, ct_msg, _ = validate_compiled_truth(content)
        tl_ok, tl_msg, _ = validate_timeline(content)
        al_ok, al_msg, _ = validate_auto_links(content, obs_type)

    all_ok = ct_ok and tl_ok and al_ok

    # Determine if we should reject (enforce = True)
    # Compiled Truth is always enforced
    # Auto-Links is enforced for code-relevant types ONLY if there are extractable links
    #   (if no code references exist, Auto-Links is not required)
    # Timeline is recommendation only (never enforced)
    reject_reason = None
    if not ct_ok:
        reject_reason = ct_msg
    elif not al_ok and obs_type in CODE_RELEVANT_TYPES:
        # Only reject if auto-fixable links were found but not applied
        # If no links exist, it's a non-code observation → warn only
        from auto_linker import extract_links
        if extract_links(content):
            reject_reason = al_msg

    return {
        "valid": all_ok,
        "enforce": reject_reason is not None,
        "reject_reason": reject_reason,
        "auto_fixes": auto_fixes,
        "checks": {
            "compiled_truth": {"ok": ct_ok, "message": ct_msg, "required": True},
            "timeline": {"ok": tl_ok, "message": tl_msg, "required": False},
            "auto_links": {"ok": al_ok, "message": al_msg, "required": obs_type in CODE_RELEVANT_TYPES},
        },
        "content": content,  # Return potentially fixed content
    }
