"""Markdown packet helpers."""

from __future__ import annotations

from urllib.parse import urlparse


def site_slug(root_url: str) -> str:
    parsed = urlparse(root_url)
    host = parsed.netloc or parsed.path
    return host.replace(":", "-").replace(".", "-").strip("-") or "site"


def make_markdown_packet(root_url: str, pages: list[dict[str, str]], run_id: str = "manual") -> str:
    slug = site_slug(root_url)
    lines = [f"# Final Markdown Packet: {slug}", "", f"- Root URL: {root_url}", f"- Packet ID: {run_id}/{slug}", ""]
    for index, page in enumerate(pages, start=1):
        lines.extend([
            f"## Page {index}: {page.get('title') or page.get('final_url') or page.get('source_url')}",
            "",
            f"Page ID: {page.get('page_id', '')}",
            f"Source URL: {page.get('source_url', '')}",
            f"Final URL: {page.get('final_url', '')}",
            "",
            page.get("markdown", ""),
            "",
            "---",
            "",
        ])
    return "\n".join(lines).strip() + "\n"
