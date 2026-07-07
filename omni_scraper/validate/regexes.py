"""Regex validators for extracted contact fields."""

from __future__ import annotations

import re
from urllib.parse import urlparse

EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)
PHONE_RE = re.compile(r"^(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?:\s*(?:x|ext\.?|extension)\s*\d{1,6})?$", re.IGNORECASE)
ADDRESS_HINT_RE = re.compile(r"\b\d{1,8}\b.+\b(st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|suite|ste|floor|fl|way|parkway|pkwy|court|ct)\b", re.IGNORECASE)
PERSON_NAME_RE = re.compile(r"^[A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+){0,4}$")
ROLE_HINT_RE = re.compile(r"\b(ceo|founder|president|director|manager|lead|head|chief|officer|principal|partner|sales|support|contact|coordinator|administrator)\b", re.IGNORECASE)
SOCIAL_DOMAINS = ("linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com", "youtube.com", "tiktok.com")


def validate_regex(kind: str, value: str) -> tuple[bool, str]:
    value = value.strip()
    if not value:
        return False, "Empty value."
    if kind == "email":
        return (True, "") if EMAIL_RE.fullmatch(value) else (False, "Email failed regex.")
    if kind == "phone":
        return (True, "") if PHONE_RE.fullmatch(value) else (False, "Phone failed regex.")
    if kind in {"website", "contact_form_url", "social_url"}:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False, "URL must be absolute HTTP/HTTPS."
        if kind == "social_url" and not any(parsed.netloc.lower().endswith(domain) for domain in SOCIAL_DOMAINS):
            return False, "Social URL host is not an allowed social domain."
        return True, ""
    if kind in {"address", "headquarters"}:
        return (True, "") if ADDRESS_HINT_RE.search(value) else (False, "Address did not contain address-like tokens.")
    if kind == "person_name":
        if "@" in value or "http" in value.lower():
            return False, "Person name cannot be an email or URL."
        return (True, "") if PERSON_NAME_RE.fullmatch(value) else (False, "Person name failed conservative name regex.")
    if kind == "role":
        return (True, "") if ROLE_HINT_RE.search(value) or len(value.split()) <= 8 else (False, "Role is too long and lacks role-like tokens.")
    return True, ""
