"""Contact extractor stage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omni_scraper.models.lm_studio import LMStudioClient
from omni_scraper.schemas.extraction import CONTACT_EXTRACTION_JSON_SCHEMA

EXTRACTOR_SYSTEM_PROMPT = """You are the OmniScraper Contact Extractor stage. Extract only facts present in the finalized Markdown bundle. Missing data is expected. Every non-missing value needs an exact quote and context_50_each_side. Return strict JSON only."""


class ExtractorAgent:
    def __init__(self, client: LMStudioClient | None = None, model: str | None = None) -> None:
        self.client = client or LMStudioClient()
        self.model = model or self.client.config.extractor_model

    def run(self, bundle_markdown: str, *, root_url: str, bundle_id: str) -> dict[str, Any]:
        return self.client.chat_json(
            model=self.model,
            system_prompt=EXTRACTOR_SYSTEM_PROMPT,
            user_prompt=build_extractor_prompt(bundle_markdown, root_url=root_url, bundle_id=bundle_id),
            response_schema=CONTACT_EXTRACTION_JSON_SCHEMA,
            schema_name="contact_extraction",
            temperature=0.0,
        )

    def run_file(self, bundle_path: str | Path, *, root_url: str, bundle_id: str) -> dict[str, Any]:
        return self.run(Path(bundle_path).read_text(encoding="utf-8"), root_url=root_url, bundle_id=bundle_id)


def build_extractor_prompt(bundle_markdown: str, *, root_url: str, bundle_id: str) -> str:
    return f"""Root URL: {root_url}
Bundle ID: {bundle_id}

Instructions:
- Extract only facts visibly present in the Markdown bundle below.
- Missing data is expected. Use missing=true with an empty value and a clear missing_reason.
- Do not infer emails, phone numbers, names, addresses, roles, or company descriptions.
- Every non-missing field must include an exact_quote copied from the bundle.
- Every non-missing field must include context_50_each_side copied from the bundle.
- The deterministic validator will reject fields whose quote/context/value do not exactly appear in the bundle.

Finalized Markdown bundle:

```markdown
{bundle_markdown}
```
"""
