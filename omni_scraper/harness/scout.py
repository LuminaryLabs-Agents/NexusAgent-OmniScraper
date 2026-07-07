"""Scout stage."""

from __future__ import annotations

import json
from typing import Any

from omni_scraper.models.lm_studio import LMStudioClient
from omni_scraper.reduce.html_to_markdown import ReducedPage
from omni_scraper.schemas.scout import SCOUT_JSON_SCHEMA

from .text import trim_middle

SCOUT_SYSTEM_PROMPT = """You are the OmniScraper Scout stage. Review reduced Markdown packets and return strict JSON about likely useful pages and discard patterns."""


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


def build_scout_prompt(page: ReducedPage, *, max_markdown_chars: int = 12_000) -> str:
    packet = {
        "source_url": page.source_url,
        "final_url": page.final_url,
        "title": page.title,
        "description": page.description,
        "signals": page.signals,
        "link_clusters": page.link_clusters,
        "markdown": trim_middle(page.markdown, max_markdown_chars),
    }
    return "Review this reduced page packet and produce the required JSON.\n\n" + json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)
