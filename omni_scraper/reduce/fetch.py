"""HTTP fetch helpers for deterministic reduction."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_USER_AGENT = "NexusAgent-OmniScraper/0.2 (+https://github.com/LuminaryLabs-Agents/NexusAgent-OmniScraper)"


@dataclass(slots=True)
class FetchResult:
    url: str
    final_url: str
    status: int | None
    content_type: str
    html: str
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error and bool(self.status is None or 200 <= int(self.status) < 400)


def fetch_html(
    url: str,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout_seconds: float = 20.0,
    max_bytes: int = 3_000_000,
) -> FetchResult:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return FetchResult(url=url, final_url=url, status=None, content_type="", html="", error="Invalid HTTP/HTTPS URL")

    request = Request(url, headers={"User-Agent": user_agent})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", None)
            final_url = response.geturl()
            content_type = response.headers.get("content-type", "")
            raw = response.read(max_bytes + 1)
    except HTTPError as exc:
        return FetchResult(url=url, final_url=exc.geturl(), status=exc.code, content_type="", html="", error=f"HTTP {exc.code}")
    except URLError as exc:
        return FetchResult(url=url, final_url=url, status=None, content_type="", html="", error=str(exc.reason))
    except TimeoutError:
        return FetchResult(url=url, final_url=url, status=None, content_type="", html="", error="Request timed out")

    if len(raw) > max_bytes:
        return FetchResult(url=url, final_url=final_url, status=status, content_type=content_type, html="", error="Response exceeded max_bytes")
    if "html" not in content_type.lower():
        return FetchResult(url=url, final_url=final_url, status=status, content_type=content_type, html="", error=f"Unsupported content type: {content_type}")
    return FetchResult(url=url, final_url=final_url, status=status, content_type=content_type, html=raw.decode("utf-8", errors="replace"))
