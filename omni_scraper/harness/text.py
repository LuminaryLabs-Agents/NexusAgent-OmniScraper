"""Text shaping helpers for agent packets."""

from __future__ import annotations


def trim_middle(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head
    return f"{text[:head]}\n\n...[trimmed {len(text) - max_chars} chars]...\n\n{text[-tail:]}"
