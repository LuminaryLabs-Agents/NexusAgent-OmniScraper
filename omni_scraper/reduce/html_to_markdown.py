"""Deterministic HTML-to-Markdown reduction."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from html import unescape
from html.parser import HTMLParser
import json
import re
from typing import Any
from urllib.parse import urljoin

from .link_cluster import cluster_links
from .signals import collect_signals

SPACE_RE = re.compile(r"\s+")
NOISY_ATTR_RE = re.compile(r"(cookie|consent|modal|popup|newsletter|subscribe|advert|promo|breadcrumb)", re.IGNORECASE)
SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "iframe"}
BLOCK_TAGS = {"p", "div", "section", "article", "main", "aside", "footer", "header", "li", "address", "td", "th"}
HEADING_TAGS = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}


@dataclass(slots=True)
class ReducedPage:
    source_url: str
    final_url: str
    page_id: str
    title: str
    description: str
    markdown: str
    accessibility_markdown: str = ""
    links: list[dict[str, str]] = field(default_factory=list)
    link_clusters: dict[str, list[dict[str, object]]] = field(default_factory=dict)
    signals: dict[str, Any] = field(default_factory=dict)
    reducer_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


class MarkdownReducer(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ""
        self.description = ""
        self.links: list[dict[str, str]] = []
        self._parts: list[str] = []
        self._skip_depth = 0
        self._capture_tag: str | None = None
        self._capture_buffer: list[str] = []
        self._current_href: str | None = None
        self._current_link_text: list[str] = []
        self._seen_link_urls: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        attr_text = " ".join([attrs_dict.get("id", ""), attrs_dict.get("class", ""), attrs_dict.get("aria-label", "")])

        if tag in SKIP_TAGS or NOISY_ATTR_RE.search(attr_text):
            self._skip_depth += 1
            return

        if tag in HEADING_TAGS or tag in {"title", "address"}:
            self._capture_tag = tag
            self._capture_buffer = []
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            if name == "description" or prop == "og:description":
                value = clean_text(attrs_dict.get("content", ""))
                if value and not self.description:
                    self.description = value
        elif tag == "a":
            href = attrs_dict.get("href", "")
            if href:
                absolute = urljoin(self.base_url, href)
                if absolute.startswith(("http://", "https://", "mailto:", "tel:")):
                    self._current_href = absolute
                    self._current_link_text = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._skip_depth:
            self._skip_depth = max(0, self._skip_depth - 1)
            return

        if tag == "a" and self._current_href:
            label = clean_text(" ".join(self._current_link_text)) or self._current_href
            self._add_link(label, self._current_href)
            self._parts.append(f"[{label}]({self._current_href})")
            self._current_href = None
            self._current_link_text = []
        elif self._capture_tag and tag == self._capture_tag:
            text = clean_text(" ".join(self._capture_buffer))
            if text:
                if tag == "title" and not self.title:
                    self.title = text
                elif tag == "address":
                    self._parts.append(f"Address: {text}")
                elif tag in HEADING_TAGS:
                    self._parts.append(f"{HEADING_TAGS[tag]} {text}")
            self._capture_tag = None
            self._capture_buffer = []
        elif tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = clean_text(data)
        if not text:
            return
        if self._capture_tag:
            self._capture_buffer.append(text)
        if self._current_href:
            self._current_link_text.append(text)
        elif not self._capture_tag or self._capture_tag == "address":
            self._parts.append(text)

    def _add_link(self, label: str, url: str) -> None:
        if url in self._seen_link_urls:
            return
        self._seen_link_urls.add(url)
        self.links.append({"label": label[:160], "url": url})

    @property
    def markdown(self) -> str:
        chunks: list[str] = []
        previous_blank = False
        for part in self._parts:
            cleaned = clean_text(part)
            if not cleaned:
                if not previous_blank:
                    chunks.append("")
                previous_blank = True
                continue
            chunks.append(cleaned)
            previous_blank = False
        body = "\n\n".join(chunk for chunk in chunks if chunk)
        header_parts: list[str] = []
        if self.title:
            header_parts.append(f"# {self.title}")
        if self.description:
            header_parts.append(f"> {self.description}")
        if header_parts:
            return "\n\n".join(header_parts + [body]).strip()
        return body.strip()


def clean_text(value: str) -> str:
    return SPACE_RE.sub(" ", unescape(value)).strip()


def page_id_from_url(url: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", url).strip("-").lower()
    return safe[-80:] or "page"


def reduce_html(
    html: str,
    *,
    source_url: str,
    final_url: str | None = None,
    accessibility_markdown: str = "",
) -> ReducedPage:
    reducer = MarkdownReducer(final_url or source_url)
    reducer.feed(html)
    markdown = reducer.markdown
    if accessibility_markdown:
        markdown = f"{markdown}\n\n---\n\n## Accessibility Tree Summary\n\n{accessibility_markdown}".strip()
    clusters = cluster_links(reducer.links)
    signals = collect_signals(markdown, reducer.links)
    return ReducedPage(
        source_url=source_url,
        final_url=final_url or source_url,
        page_id=page_id_from_url(final_url or source_url),
        title=reducer.title,
        description=reducer.description,
        markdown=markdown,
        accessibility_markdown=accessibility_markdown,
        links=reducer.links,
        link_clusters=clusters,
        signals=signals,
        reducer_warnings=[],
    )
