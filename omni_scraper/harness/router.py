"""Router stage."""

from __future__ import annotations

import json
from typing import Any

from omni_scraper.models.lm_studio import LMStudioClient
from omni_scraper.reduce.html_to_markdown import ReducedPage
from omni_scraper.schemas.router import ROUTER_JSON_SCHEMA

from .text import trim_middle

ROUTER_SYSTEM_PROMPT = """You are the OmniScraper Router stage. Rank reduced pages for downstream extraction and return strict JSON."""


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
        )


def build_router_prompt(
    *,
    root_url: str,
    pages: list[ReducedPage],
    scout_output: dict[str, Any] | None = None,
    max_page_chars: int = 6_000,
) -> str:
    page_packets = []
    for page in pages:
        page_packets.append(
            {
                "source_url": page.source_url,
                "final_url": page.final_url,
                "page_id": page.page_id,
                "title": page.title,
                "signals": page.signals,
                "link_clusters": page.link_clusters,
                "markdown_excerpt": trim_middle(page.markdown, max_page_chars),
            }
        )
    packet = {"root_url": root_url, "scout_output": scout_output or {}, "pages": page_packets}
    return "Prioritize reduced pages for the extractor and produce the required JSON.\n\n" + json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)
