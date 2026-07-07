"""LM Studio local model configuration and JSON parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from typing import Any


class ModelCallError(RuntimeError):
    """Raised when a local model call fails or returns invalid JSON."""


@dataclass(slots=True)
class LMStudioConfig:
    base_url: str = "http://localhost:1234/v1"
    scout_model: str = "qwen3.5-4b"
    router_model: str = "qwen3.5-4b"
    extractor_model: str = "agents-a1"
    timeout_seconds: float = 120.0
    temperature: float = 0.0
    max_tokens: int = 4096

    @classmethod
    def from_env(cls) -> "LMStudioConfig":
        qwen_default = os.getenv("OMNI_QWEN_MODEL", "qwen3.5-4b")
        return cls(
            base_url=os.getenv("OMNI_LMSTUDIO_BASE_URL", "http://localhost:1234/v1").rstrip("/"),
            scout_model=os.getenv("OMNI_SCOUT_MODEL", qwen_default),
            router_model=os.getenv("OMNI_ROUTER_MODEL", qwen_default),
            extractor_model=os.getenv("OMNI_EXTRACTOR_MODEL", "agents-a1"),
            timeout_seconds=float(os.getenv("OMNI_LMSTUDIO_TIMEOUT", "120")),
            temperature=float(os.getenv("OMNI_LMSTUDIO_TEMPERATURE", "0")),
            max_tokens=int(os.getenv("OMNI_LMSTUDIO_MAX_TOKENS", "4096")),
        )


def parse_json_content(content: str) -> dict[str, Any]:
    """Parse JSON from a model content string, tolerating fenced JSON blocks."""
    text = content.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ModelCallError(f"Model returned invalid JSON: {content[:1000]}") from exc
    if not isinstance(parsed, dict):
        raise ModelCallError(f"Model returned JSON that was not an object: {parsed!r}")
    return parsed
