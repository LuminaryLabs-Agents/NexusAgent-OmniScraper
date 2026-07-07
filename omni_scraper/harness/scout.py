"""Scout stage."""

from __future__ import annotations

import json
import os
from typing import Any

from omni_scraper.models.lm_studio import LMStudioClient
from omni_scraper.reduce.html_to_markdown import ReducedPage
from omni_scraper.schemas.scout import SCOUT_JSON_SCHEMA

from .text import trim_middle

SCOUT_SYSTEM_PROMPT = """You are the OmniScraper Scout stage. Review compact reduced Markdown packets and return strict JSON about likely useful pages and discard patterns. Do not extract final contact data."""


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class ScoutAgent:
    def __init__(self, client: LMStudioClient | None = None, model: str | None = None) -> None:
        self.client = client or LMStudioClient()
        self.model = model or self.client.config.scout_model

    def run(self, page: ReducedPage) -> dict[str, Any]:
        return self.client.chat_json(
            model=self.model,
            system_prompt=SCOUT_SYSTEM_PROMPT,
            user_prompt=build_scout_prompt(page),
            response_schema=SCOUT_JSON_SCHEMA,
            schema_name="scout_response",
            max_tokens=self.client.config.scout_max_tokens,
            timeout_seconds=self.client.config.scout_timeout_seconds,
        )


def build_scout_prompt(page: ReducedPage, *, max_markdown_chars: int | None = None) -> str:
    max_chars = _env_int("OMNI_SCOUT_MARKDOWN_CHARS", 3000) if max_markdown_chars is None else max_markdown_chars
    packet = {
        "source_url": page.source_url,
        "final_url": page.final_url,
        "title": page.title[:160],
        "description": page.description[:300],
        "signals": compact_signals(page.signals),
        "link_clusters": compact_link_clusters(page.link_clusters, limit_per_cluster=8),
        "markdown_excerpt": trim_middle(page.markdown, max_chars),
    }
    return "Review this compact reduced page packet and produce the required JSON.\n\n" + json.dumps(packet, ensure_ascii=False, separators=(",", ":"))


def compact_signals(signals: dict[str, Any]) -> dict[str, Any]:
    keep = {
        "emails": 10,
        "phones": 10,
        "urls": 20,
        "contact_keywords": 20,
        "company_keywords": 20,
        "generic_discard_keywords": 20,
    }
    compact: dict[str, Any] = {}
    for key, value in signals.items():
        if key in keep and isinstance(value, list):
            compact[key] = value[: keep[key]]
        elif key.endswith("_count") or key.endswith("_score") or isinstance(value, (int, float, str, bool)):
            compact[key] = value
    return compact


def compact_link_clusters(clusters: dict[str, Any], *, limit_per_cluster: int) -> dict[str, list[dict[str, Any]]]:
    compact: dict[str, list[dict[str, Any]]] = {}
    for cluster_name, links in clusters.items():
        if not isinstance(links, list):
            continue
        compact[cluster_name] = []
        for link in links[:limit_per_cluster]:
            if isinstance(link, dict):
                compact[cluster_name].append(
                    {
                        "url": str(link.get("url", ""))[:500],
                        "label": str(link.get("label", ""))[:120],
                        "priority": link.get("priority", 0),
                        "reason": str(link.get("reason", ""))[:160],
                    }
                )
    return compact
