"""Core scraping primitives for OmniScraper.

The first implementation intentionally uses only Python standard-library modules.
That keeps the repo easy to run in agent environments before browser automation,
queues, and richer parsers are added.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
import re
import time
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .robots import RobotsPolicy

_TEXT_SPACE_RE = re.compile(r"\s+")


@dataclass(slots=True)
class ScrapeConfig:
    """Runtime options for a scrape pass."""

    user_agent: str = "NexusAgent-OmniScraper/0.1 (+https://github.com/LuminaryLabs-Agents/NexusAgent-OmniScraper)"
    timeout_seconds: float = 20.0
    delay_seconds: float = 0.0
    max_bytes: int = 2_000_000
    respect_robots: bool = True


@dataclass(slots=True)
class PageRecord:
    """Normalized page result emitted by the scraper."""

    url: str
    final_url: str
    status: int | None
    ok: bool
    title: str = ""
    description: str = ""
    headings: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    text: str = ""
    error: str = ""
    fetched_at_epoch: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class _PageHTMLParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ""
        self.description = ""
        self.headings: list[str] = []
        self.links: list[str] = []
        self._text_parts: list[str] = []
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()

        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return

        if tag == "title":
            self._start_capture("title")
        elif tag in {"h1", "h2", "h3"}:
            self._start_capture("heading")
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            if name == "description" or prop == "og:description":
                value = attrs_dict.get("content", "")
                if value and not self.description:
                    self.description = _clean_text(value)
        elif tag == "a":
            href = attrs_dict.get("href", "")
            if href:
                absolute = urljoin(self.base_url, href)
                if absolute.startswith(("http://", "https://")):
                    self.links.append(absolute)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._capture and tag in {"title", "h1", "h2", "h3"}:
            text = _clean_text(" ".join(self._buffer))
            if self._capture == "title" and text and not self.title:
                self.title = text
            elif self._capture == "heading" and text:
                self.headings.append(text)
            self._capture = None
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._capture:
            self._buffer.append(data)
        cleaned = _clean_text(data)
        if cleaned:
            self._text_parts.append(cleaned)

    def _start_capture(self, name: str) -> None:
        self._capture = name
        self._buffer = []

    @property
    def text(self) -> str:
        return _clean_text(" ".join(self._text_parts))


def _clean_text(value: str) -> str:
    return _TEXT_SPACE_RE.sub(" ", value).strip()


def _is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class Scraper:
    """Fetch and normalize public pages."""

    def __init__(self, config: ScrapeConfig | None = None) -> None:
        self.config = config or ScrapeConfig()
        self._robots = RobotsPolicy(self.config.user_agent, self.config.timeout_seconds)

    def scrape_many(self, urls: Iterable[str]) -> list[PageRecord]:
        records: list[PageRecord] = []
        for index, url in enumerate(urls):
            if index and self.config.delay_seconds > 0:
                time.sleep(self.config.delay_seconds)
            records.append(self.scrape(url))
        return records

    def scrape(self, url: str) -> PageRecord:
        url = url.strip()
        if not _is_http_url(url):
            return PageRecord(url=url, final_url=url, status=None, ok=False, error="Unsupported or invalid URL")

        if self.config.respect_robots and not self._robots.allowed(url):
            return PageRecord(url=url, final_url=url, status=None, ok=False, error="Blocked by robots.txt policy")

        request = Request(url, headers={"User-Agent": self.config.user_agent})
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                status = getattr(response, "status", None)
                final_url = response.geturl()
                content_type = response.headers.get("content-type", "")
                raw = response.read(self.config.max_bytes + 1)
        except HTTPError as exc:
            return PageRecord(url=url, final_url=exc.geturl(), status=exc.code, ok=False, error=f"HTTP {exc.code}")
        except URLError as exc:
            return PageRecord(url=url, final_url=url, status=None, ok=False, error=str(exc.reason))
        except TimeoutError:
            return PageRecord(url=url, final_url=url, status=None, ok=False, error="Request timed out")

        if len(raw) > self.config.max_bytes:
            return PageRecord(url=url, final_url=final_url, status=status, ok=False, error="Response exceeded max_bytes")

        if "html" not in content_type.lower():
            return PageRecord(url=url, final_url=final_url, status=status, ok=False, error=f"Unsupported content type: {content_type}")

        encoding = "utf-8"
        decoded = raw.decode(encoding, errors="replace")
        parser = _PageHTMLParser(final_url)
        parser.feed(decoded)

        return PageRecord(
            url=url,
            final_url=final_url,
            status=status,
            ok=bool(status is None or 200 <= int(status) < 400),
            title=parser.title,
            description=parser.description,
            headings=parser.headings[:25],
            links=sorted(set(parser.links))[:250],
            text=parser.text[:20_000],
        )
