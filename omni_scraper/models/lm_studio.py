"""LM Studio local chat client.

This module uses LM Studio's OpenAI-compatible endpoint directly through the
standard library. No OpenAI SDK dependency is required.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ModelCallError(RuntimeError):
    """Raised when a local model call fails or returns invalid JSON."""


@dataclass(slots=True)
class LMStudioConfig:
    base_url: str = "http://localhost:1234/v1"
    api_key: str = "lm-studio"
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
            api_key=os.getenv("OMNI_LMSTUDIO_API_KEY", "lm-studio"),
            scout_model=os.getenv("OMNI_SCOUT_MODEL", qwen_default),
            router_model=os.getenv("OMNI_ROUTER_MODEL", qwen_default),
            extractor_model=os.getenv("OMNI_EXTRACTOR_MODEL", "agents-a1"),
            timeout_seconds=float(os.getenv("OMNI_LMSTUDIO_TIMEOUT", "120")),
            temperature=float(os.getenv("OMNI_LMSTUDIO_TEMPERATURE", "0")),
            max_tokens=int(os.getenv("OMNI_LMSTUDIO_MAX_TOKENS", "4096")),
        )


class LMStudioClient:
    def __init__(self, config: LMStudioConfig | None = None) -> None:
        self.config = config or LMStudioConfig.from_env()

    def chat_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        schema_name: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.config.temperature if temperature is None else temperature,
            "max_tokens": self.config.max_tokens if max_tokens is None else max_tokens,
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": response_schema,
                },
            },
        }
        raw = self._post_json("/chat/completions", payload)
        try:
            content = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelCallError(f"Unexpected LM Studio response shape: {raw!r}") from exc
        return parse_json_content(content)

    def _post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.config.base_url}{endpoint}"
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ModelCallError(f"LM Studio HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise ModelCallError(f"Could not reach LM Studio at {url}: {exc.reason}") from exc
        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ModelCallError(f"LM Studio returned non-JSON body: {body[:500]}") from exc
        if not isinstance(decoded, dict):
            raise ModelCallError(f"LM Studio returned non-object JSON: {decoded!r}")
        return decoded


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
