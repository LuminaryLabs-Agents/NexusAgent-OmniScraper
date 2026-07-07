"""Scout response schema."""

SCOUT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "source_url": {"type": "string"},
        "site_type": {"type": "string"},
        "likely_info_locations": {"type": "array"},
        "discard_patterns": {"type": "array"},
        "next_urls": {"type": "array"},
        "notes": {"type": "string"},
    },
    "required": ["source_url", "site_type", "likely_info_locations", "discard_patterns", "next_urls", "notes"],
}
