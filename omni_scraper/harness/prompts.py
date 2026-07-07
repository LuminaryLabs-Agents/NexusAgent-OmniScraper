"""Prompt loading helpers."""

from __future__ import annotations

from pathlib import Path

PROMPT_ROOT = Path(__file__).resolve().parents[2] / "prompts"


def load_prompt(relative_path: str) -> str:
    return (PROMPT_ROOT / relative_path).read_text(encoding="utf-8")
