"""Build extractor-ready Markdown bundles from router decisions."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from omni_scraper.reduce.html_to_markdown import ReducedPage


@dataclass(slots=True)
class ExtractorBundle:
    bundle_id: str
    root_url: str
    markdown: str
    metadata: dict[str, Any]

    def write(self, output_dir: str | Path) -> tuple[Path, Path]:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        md_path = path / "site-bundle.md"
        json_path = path / "site-bundle.json"
        md_path.write_text(self.markdown, encoding="utf-8")
        json_path.write_text(json.dumps(self.metadata, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return md_path, json_path


def site_slug(root_url: str) -> str:
    parsed = urlparse(root_url)
    host = parsed.netloc or parsed.path
    return host.replace(":", "-").replace(".", "-").strip("-") or "site"


def build_extractor_bundle(
    *,
    root_url: str,
    reduced_pages: list[ReducedPage],
    router_output: dict[str, Any],
    scout_output: dict[str, Any] | None = None,
    run_id: str = "manual",
) -> ExtractorBundle:
    slug = site_slug(root_url)
    bundle_id = f"{run_id}/{slug}"
    kept_by_url = {item.get("url", ""): item for item in router_output.get("kept_urls", []) if isinstance(item, dict)}
    ordered_pages = sorted(
        reduced_pages,
        key=lambda page: int(kept_by_url.get(page.final_url, kept_by_url.get(page.source_url, {})).get("priority", 0)),
        reverse=True,
    )

    lines: list[str] = [
        f"# Extractor Bundle: {slug}",
        "",
        "## Source Summary",
        "",
        f"- Root URL: {root_url}",
        f"- Bundle ID: {bundle_id}",
        f"- Scout site type: {(scout_output or {}).get('site_type', 'unknown')}",
        "- Instruction: extract only facts visible in this bundle; missing data is expected.",
        "",
        "---",
        "",
    ]

    page_metadata: list[dict[str, Any]] = []
    for index, page in enumerate(ordered_pages, start=1):
        route = kept_by_url.get(page.final_url) or kept_by_url.get(page.source_url) or {}
        page_id = page.page_id or f"page-{index:02d}"
        page_metadata.append({
            "page_id": page_id,
            "source_url": page.source_url,
            "final_url": page.final_url,
            "priority": route.get("priority", 0),
            "reason": route.get("reason", "Included in finalized bundle."),
        })
        lines.extend(
            [
                f"## Page {index}: {page.title or page.final_url}",
                "",
                f"Page ID: {page_id}",
                f"Source URL: {page.source_url}",
                f"Final URL: {page.final_url}",
                f"Router Priority: {route.get('priority', 0)}",
                f"Router Reason: {route.get('reason', 'Included in finalized bundle.')}",
                "",
                "### Reduced Markdown",
                "",
                page.markdown.strip(),
                "",
                "---",
                "",
            ]
        )

    metadata = {
        "bundle_id": bundle_id,
        "root_url": root_url,
        "pages": page_metadata,
        "router_output": router_output,
        "scout_output": scout_output or {},
    }
    return ExtractorBundle(bundle_id=bundle_id, root_url=root_url, markdown="\n".join(lines).strip() + "\n", metadata=metadata)
