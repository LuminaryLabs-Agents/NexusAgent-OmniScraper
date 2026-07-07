"""Classify links before they reach agent stages."""

from __future__ import annotations

from urllib.parse import urlparse

CONTACT_TERMS = ("contact", "connect", "inquiry", "inquiries", "support", "sales", "location", "office", "directory")
COMPANY_TERMS = ("about", "team", "staff", "leadership", "company", "mission", "people", "who-we-are", "our-story")
LEGAL_TERMS = ("privacy", "terms", "cookie", "accessibility", "legal")
GENERIC_TERMS = ("blog", "news", "tag", "category", "archive", "login", "cart", "account", "search")
SOCIAL_HOSTS = ("linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com", "youtube.com", "tiktok.com")


def classify_link(label: str, url: str) -> tuple[str, int, str]:
    text = f"{label} {url}".lower()
    host = urlparse(url).netloc.lower()
    if any(host.endswith(social_host) for social_host in SOCIAL_HOSTS):
        return "social", 65, "Social profile host."
    if any(term in text for term in CONTACT_TERMS):
        return "contact_likely", 95, "Contact/location/support term in label or URL."
    if any(term in text for term in COMPANY_TERMS):
        return "company_likely", 80, "About/team/company term in label or URL."
    if any(term in text for term in LEGAL_TERMS):
        return "legal_discard", 5, "Legal/compliance page usually not useful for contact extraction."
    if any(term in text for term in GENERIC_TERMS):
        return "generic_discard", 10, "Generic archive/account/search page."
    return "other", 35, "No strong deterministic route signal."


def cluster_links(links: list[dict[str, str]], *, limit_per_cluster: int = 40) -> dict[str, list[dict[str, object]]]:
    clusters: dict[str, list[dict[str, object]]] = {
        "contact_likely": [],
        "company_likely": [],
        "social": [],
        "legal_discard": [],
        "generic_discard": [],
        "other": [],
    }
    seen: set[str] = set()
    for link in links:
        url = link.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        cluster, priority, reason = classify_link(link.get("label", ""), url)
        if len(clusters[cluster]) >= limit_per_cluster:
            continue
        clusters[cluster].append({
            "url": url,
            "label": link.get("label", ""),
            "priority": priority,
            "reason": reason,
        })
    for values in clusters.values():
        values.sort(key=lambda item: int(item["priority"]), reverse=True)
    return clusters
