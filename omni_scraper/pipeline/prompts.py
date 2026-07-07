"""Prompt builders for the three-stage contact pipeline."""

from __future__ import annotations

import json
from typing import Any

from omni_scraper.harness.text import trim_middle

SCOUT_SYSTEM_PROMPT = """You are the OmniScraper Scout stage. Do not extract final contact data. Find likely contact/company pages and discard obvious noise. Return JSON only."""

ROUTER_SYSTEM_PROMPT = """You are the OmniScraper Router stage. Keep pages likely to contain contact details, company identity, team/staff, offices, locations, or contact-form information. Discard generic pages. Return JSON only."""

EXTRACTOR_SYSTEM_PROMPT = """You are the OmniScraper Contact Extractor stage. Extract only facts visible in the finalized Markdown. Missing data is expected. For every non-missing value, provide exact_quote and context_50_each_side copied from the Markdown. Return JSON only."""


def scout_prompt(page: Any, *, max_chars: int = 12_000) -> str:
    packet = {
        "source_url": page.source_url,
        "final_url": page.final_url,
        "title": page.title,
        "description": page.description,
        "signals": page.signals,
        "link_clusters": page.link_clusters,
        "markdown": trim_middle(page.markdown, max_chars),
    }
    return "Review this reduced page packet. Prioritize likely contact/company destinations and discard patterns.\n\n" + json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)


def router_prompt(root_url: str, pages: list[Any], scout_output: dict[str, Any] | None = None, *, max_chars: int = 6_000) -> str:
    payload = {
        "root_url": root_url,
        "scout_output": scout_output or {},
        "pages": [
            {
                "source_url": page.source_url,
                "final_url": page.final_url,
                "page_id": page.page_id,
                "title": page.title,
                "signals": page.signals,
                "markdown_excerpt": trim_middle(page.markdown, max_chars),
            }
            for page in pages
        ],
    }
    return "Prioritize URLs for the extractor. Keep only useful contact/company pages.\n\n" + json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def extractor_prompt(bundle_markdown: str, *, root_url: str, bundle_id: str) -> str:
    return f"""Root URL: {root_url}
Bundle ID: {bundle_id}

Rules:
- Extract only facts visibly present below.
- Missing data is expected; do not guess.
- Every non-missing value must include exact_quote and context_50_each_side.
- The validator will reject fields whose evidence does not exactly match the Markdown.

Finalized Markdown:

{bundle_markdown}
"""
