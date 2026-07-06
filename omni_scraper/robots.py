"""Small robots.txt policy helper.

This is deliberately conservative and simple. It supports common Disallow rules
for `*` and the configured user-agent. It does not try to implement every
robots.txt extension.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(slots=True)
class _Rules:
    disallow: list[str] = field(default_factory=list)


class RobotsPolicy:
    def __init__(self, user_agent: str, timeout_seconds: float) -> None:
        self.user_agent = user_agent.lower()
        self.timeout_seconds = timeout_seconds
        self._cache: dict[str, _Rules] = {}

    def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        rules = self._cache.get(origin)
        if rules is None:
            rules = self._fetch_rules(origin)
            self._cache[origin] = rules

        path = parsed.path or "/"
        for rule in rules.disallow:
            if rule == "/" or path.startswith(rule):
                return False
        return True

    def _fetch_rules(self, origin: str) -> _Rules:
        request = Request(f"{origin}/robots.txt", headers={"User-Agent": self.user_agent})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                content = response.read(256_000).decode("utf-8", errors="replace")
        except Exception:
            return _Rules()

        active = False
        selected = _Rules()
        for raw_line in content.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, value = [part.strip() for part in line.split(":", 1)]
            key = key.lower()
            value_lower = value.lower()

            if key == "user-agent":
                active = value_lower == "*" or value_lower in self.user_agent
            elif active and key == "disallow" and value:
                selected.disallow.append(value)

        return selected
