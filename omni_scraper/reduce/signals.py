"""Deterministic contact and company signal detection."""

from __future__ import annotations

import re
from typing import Any

EMAIL_RE = re.compile(r"(?<![\w.+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![\w.+-])", re.IGNORECASE)
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?:\s*(?:x|ext\.?|extension)\s*\d{1,6})?(?!\w)",
    re.IGNORECASE,
)
URL_RE = re.compile(r"https?://[^\s)\]>\"']+", re.IGNORECASE)

CONTACT_KEYWORDS = {
    "contact",
    "email",
    "phone",
    "call",
    "address",
    "location",
    "office",
    "support",
    "sales",
    "inquiries",
    "reach us",
    "get in touch",
    "contact us",
}

COMPANY_KEYWORDS = {
    "about",
    "team",
    "leadership",
    "staff",
    "company",
    "mission",
    "who we are",
    "our story",
    "locations",
}

GENERIC_DISCARD_KEYWORDS = {
    "blog",
    "news",
    "privacy",
    "terms",
    "cookie",
    "login",
    "cart",
    "tag",
    "category",
    "archive",
    "press release",
}

SOCIAL_HOST_HINTS = {
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "tiktok.com",
}


def collect_signals(markdown: str, links: list[dict[str, str]] | None = None) -> dict[str, Any]:
    text_lower = markdown.lower()
    emails = sorted(set(EMAIL_RE.findall(markdown)))
    phones = sorted(set(match.group(0) for match in PHONE_RE.finditer(markdown)))
    urls = sorted(set(URL_RE.findall(markdown)))
    contact_hits = sorted(keyword for keyword in CONTACT_KEYWORDS if keyword in text_lower)
    company_hits = sorted(keyword for keyword in COMPANY_KEYWORDS if keyword in text_lower)
    discard_hits = sorted(keyword for keyword in GENERIC_DISCARD_KEYWORDS if keyword in text_lower)

    link_values = links or []
    contact_link_count = 0
    company_link_count = 0
    social_link_count = 0
    for link in link_values:
        combined = f"{link.get('label', '')} {link.get('url', '')}".lower()
        if any(keyword in combined for keyword in CONTACT_KEYWORDS):
            contact_link_count += 1
        if any(keyword in combined for keyword in COMPANY_KEYWORDS):
            company_link_count += 1
        if any(host in combined for host in SOCIAL_HOST_HINTS):
            social_link_count += 1

    score = min(
        100,
        len(emails) * 25
        + len(phones) * 20
        + len(contact_hits) * 8
        + len(company_hits) * 5
        + contact_link_count * 8
        + company_link_count * 5
        + social_link_count * 4
        - len(discard_hits) * 3,
    )

    return {
        "emails": emails[:25],
        "phones": phones[:25],
        "urls": urls[:100],
        "contact_keywords": contact_hits,
        "company_keywords": company_hits,
        "generic_discard_keywords": discard_hits,
        "contact_link_count": contact_link_count,
        "company_link_count": company_link_count,
        "social_link_count": social_link_count,
        "contact_signal_score": max(0, score),
    }
