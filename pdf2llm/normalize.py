"""Markdown normalization helpers."""

from __future__ import annotations

import re

_HYPHENATED_BREAK_RE = re.compile(r"([A-Za-z])-\n([A-Za-z])")
_BLANK_LINE_RE = re.compile(r"\n{3,}")


def normalize_markdown(text: str) -> str:
    """Apply deterministic normalization for markdown text."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
    normalized = _HYPHENATED_BREAK_RE.sub(r"\1\2", normalized)
    normalized = _BLANK_LINE_RE.sub("\n\n", normalized)
    return normalized.strip() + "\n"
