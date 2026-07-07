"""Optional accessibility-tree helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AccessibilitySnapshot:
    available: bool
    markdown: str = ""
    error: str = ""


def tree_to_markdown(tree: dict[str, Any] | None, *, max_nodes: int = 250) -> str:
    if not tree:
        return ""
    lines: list[str] = []
    count = 0

    def walk(node: dict[str, Any], depth: int) -> None:
        nonlocal count
        if count >= max_nodes:
            return
        role = str(node.get("role", "")).strip()
        name = str(node.get("name", "")).strip()
        value = str(node.get("value", "")).strip()
        interesting = " ".join(part for part in [role, name, value] if part)
        if interesting:
            lines.append(f"{'  ' * depth}- {interesting}")
            count += 1
        for child in node.get("children", []) or []:
            if isinstance(child, dict):
                walk(child, depth + 1)

    walk(tree, 0)
    return "\n".join(lines)


def unavailable_snapshot(reason: str) -> AccessibilitySnapshot:
    return AccessibilitySnapshot(available=False, error=reason)
