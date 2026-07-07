"""Router stage."""

from __future__ import annotations

import json
import os
from typing import Any

from omni_scraper.models.lm_studio import LMStudioClient
from omni_scraper.reduce.html_to_markdown import ReducedPage
from omni_scraper.schemas.router import ROUTER_JSON_SCHEMA

from .scout import compact_link_clusters, compact_signals
from .text import trim_middle

ROUTER_SYSTEM_PROMPT = """You are the OmniScraper Router stage. Rank compact reduced pages for downstream extraction and return strict JSON. Keep only pages likely to contain contact, company, team, location, or support information."""


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class RouterAgent:
    def __init__(self, client: LMStudioClient | None = None, model: str | None = None) -> None:
        self.client = client or LMStudioClient()
        self.model = model or self.client.config.router_model

    def run(self, *, root_url: str, pages: list[ReducedPage], scout_output: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.client.chat_json(
            model=self.model,
            system_prompt=ROUTER_SYSTEM_PROMPT,
            user_prompt=build_router_prompt(root_url=root_url, pages=pages, scout_output=scout_output),
            response_schema=ROUTER_JSON_SCHEMA,
            schema_name="router_response",
            max_tokens=self.client.config.router_max_tokens,
            timeout_seconds=self.client.config.router_timeout_seconds,
        )


def build_router_prompt(
    *,
    root_url: str,
    pages: list[ReducedPage],
    scout_output: dict[str, Any] | None = None,
    max_page_chars: int | None = None,
) -> str:
    max_chars = _env_int("OMNI_ROUTER_PAGE_CHARS", 1200) if max_page_chars is None else max_page_chars
    max_pages = _env_int("OMNI_ROUTER_MAX_INPUT_PAGES", 5)
    page_packets = []
    for page in pages[:max_pages]:
        page_packets.append(
            {
                "source_url": page.source_url,
                "final_url": page.final_url,
                "page_id": page.page_id,
                "title": page.title[:160],
                "signals": compact_signals(page.signals),
                "link_clusters": compact_link_clusters(page.link_clusters, limit_per_cluster=5),
                "markdown_excerpt": trim_middle(page.markdown, max_chars),
            }
        )
    packet = {"root_url": root_url, "scout_output": compact_scout_output(scout_output or {}), "pages": page_packets}
    return "Prioritize compact reduced pages for the extractor and produce the required JSON.\n\n" + json.dumps(packet, ensure_ascii=False, separators=(",", ":"))


def compact_scout_output(scout_output: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_url": scout_output.get("source_url", ""),
        "site_type": scout_output.get("site_type", "unknown"),
        "likely_info_locations": _limit_dict_list(scout_output.get("likely_info_locations", []), 8),
        "discard_patterns": list(scout_output.get("discard_patterns", []) or [])[:10],
        "next_urls": _limit_dict_list(scout_output.get("next_urls", []), 12),
        "notes": str(scout_output.get("notes", ""))[:500],
    }


def _limit_dict_list(value: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    output: list[dict[str, Any]] = []
    for item in value[:limit]:
        if isinstance(item, dict):
            output.append({str(key): item[key] for key in list(item.keys())[:6]})
    return output
