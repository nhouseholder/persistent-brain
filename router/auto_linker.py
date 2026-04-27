#!/usr/bin/env python3
"""Auto-link extraction for observation content.

Extracts file paths, symbol names, and project references from text
to create bidirectional bridges between temporal memory and code graph."""

import re

# File extensions we care about
FILE_RE = re.compile(r"[\w\-/.]+\.(ts|tsx|js|jsx|py|go|rs|java|md|json|yml|yaml)")
# Backtick-wrapped symbols: `calculateBuffettScore`
SYMBOL_RE = re.compile(r"`([A-Za-z_]\w*)")
# Project names from ProjectsHQ references
PROJECT_RE = re.compile(r"(?:ProjectsHQ|project)[\s/:]+([\w-]+)", re.IGNORECASE)


def extract_links(text: str) -> list[str]:
    """Extract all linkable entities from observation content."""
    links = set()

    for m in FILE_RE.finditer(text):
        links.add(m.group(0))

    for m in SYMBOL_RE.finditer(text):
        links.add(m.group(1))

    for m in PROJECT_RE.finditer(text):
        links.add(m.group(1))

    return sorted(links)


def append_auto_links(content: str) -> str:
    """Append ## Auto-Links section if links are found and section doesn't exist."""
    if "## Auto-Links" in content:
        return content

    links = extract_links(content)
    if not links:
        return content

    section = "\n\n## Auto-Links\n" + "\n".join(f"- {link}" for link in links)
    return content.rstrip() + section
