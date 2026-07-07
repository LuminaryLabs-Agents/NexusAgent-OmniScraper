"""LM Studio local chat client.

This module uses LM Studio's OpenAI-compatible endpoint directly through the
standard library. No OpenAI SDK dependency is required.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import time
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
    response_format: str = "json_schema"
    debug_dir: str = ""

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
            response_format=os.getenv("OMNI_LMSTUDIO_RESPONSE_FORMAT", "json_schema"),
            debug_dir=os.getenv("OMNI_LMSTUDIO_DEBUG_DIR", ""),
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
        """Call LM Studio and parse a JSON object, retrying weaker format modes.

        Some local models/LM Studio builds do not reliably honor strict
        json_schema output. We try json_schema first, then json_object, then a
        plain prompt with the schema embedded. This keeps the harness usable
        while still validating downstream outputs deterministically.
        """
        modes = _fallback_modes(self.config.response_format)
        last_error = "No LM Studio attempt was made."
        last_raw: dict[str, Any] | None = None

        for mode in modes:
            prompt = user_prompt
            if mode == "none":
                prompt = _append_schema_instruction(user_prompt, response_schema)

            payload = self._build_payload(
                model=model,
                system_prompt=system_prompt,
                user_prompt=prompt,
                response_schema=response_schema,
                schema_name=schema_name,
                response_format=mode,
                temperature=self.config.temperature if temperature is None else temperature,
                max_tokens=self.config.max_tokens if max_tokens is None else max_tokens,
            )
            raw = self._post_json("/chat/completions", payload)
            last_raw = raw
            self._debug_write(schema_name=schema_name, mode=mode, payload=payload, raw=raw)
            content = extract_message_text(raw)
            if not content.strip():
                last_error = f"LM Studio returned empty message content using response_format={mode}; {_finish_reason(raw)}"
                continue
            try:
                return parse_json_content(content)
            except ModelCallError as exc:
                last_error = f"{exc} using response_format={mode}; {_finish_reason(raw)}"
                continue

        preview = json.dumps(last_raw, ensure_ascii=False)[:2000] if last_raw else ""
        raise ModelCallError(f"{last_error}. Raw response preview: {preview}")

    def _build_payload(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        schema_name: str,
        response_format: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if response_format == "json_schema":
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": response_schema},
            }
        elif response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}
        return payload

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

    def _debug_write(self, *, schema_name: str, mode: str, payload: dict[str, Any], raw: dict[str, Any]) -> None:
        if not self.config.debug_dir:
            return
        debug_dir = Path(self.config.debug_dir)
        debug_dir.mkdir(parents=True, exist_ok=True)
        safe_schema = re.sub(r"[^a-zA-Z0-9_.-]+", "-", schema_name).strip("-") or "call"
        path = debug_dir / f"{int(time.time() * 1000)}-{safe_schema}-{mode}.json"
        path.write_text(
            json.dumps({"payload": payload, "raw": raw}, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def _fallback_modes(primary: str) -> list[str]:
    normalized = primary.strip().lower().replace("-", "_") or "json_schema"
    if normalized not in {"json_schema", "json_object", "none"}:
        normalized = "json_schema"
    modes: list[str] = []
    for mode in [normalized, "json_object", "none"]:
        if mode not in modes:
            modes.append(mode)
    return modes


def _append_schema_instruction(user_prompt: str, response_schema: dict[str, Any]) -> str:
    schema_text = json.dumps(response_schema, ensure_ascii=False, sort_keys=True)
    return (
        f"{user_prompt}\n\n"
        "Return exactly one JSON object and no prose. The JSON object must match this schema:\n"
        f"{schema_text}"
    )


def _finish_reason(raw: dict[str, Any]) -> str:
    try:
        reason = raw["choices"][0].get("finish_reason")
    except (KeyError, IndexError, TypeError, AttributeError):
        reason = None
    return f"finish_reason={reason!r}"


def extract_message_text(raw: dict[str, Any]) -> str:
    """Extract useful text from common OpenAI-compatible response shapes."""
    try:
        message = raw["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ModelCallError(f"Unexpected LM Studio response shape: {raw!r}") from exc
    if not isinstance(message, dict):
        raise ModelCallError(f"Unexpected LM Studio message shape: {message!r}")

    candidates: list[Any] = [
        message.get("content"),
        message.get("reasoning_content"),
        message.get("reasoning"),
        message.get("thinking"),
    ]
    for candidate in candidates:
        text = _content_to_text(candidate)
        if text.strip():
            return text
    return ""


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces: list[str] = []
        for item in content:
            if isinstance(item, dict):
                pieces.append(str(item.get("text") or item.get("content") or ""))
            else:
                pieces.append(str(item))
        return "\n".join(piece for piece in pieces if piece)
    return str(content)


def parse_json_content(content: str) -> dict[str, Any]:
    """Parse JSON from a model content string, tolerating fences/prose."""
    text = _strip_thinking_blocks(content.strip())
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        extracted = extract_first_json_object(text)
        if not extracted:
            raise ModelCallError(f"Model returned invalid JSON: {content[:1000]}")
        try:
            parsed = json.loads(extracted)
        except json.JSONDecodeError as exc:
            raise ModelCallError(f"Model returned invalid JSON object: {extracted[:1000]}") from exc
    if not isinstance(parsed, dict):
        raise ModelCallError(f"Model returned JSON that was not an object: {parsed!r}")
    return parsed


def _strip_thinking_blocks(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    return text


def extract_first_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        return ""
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return ""
