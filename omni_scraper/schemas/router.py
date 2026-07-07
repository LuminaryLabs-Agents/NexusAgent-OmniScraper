"""Router agent response schema."""

from __future__ import annotations

from typing import Any

ROUTER_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "site_root": {"type": "string"},
        "kept_urls": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "url": {"type": "string"},
                    "priority": {"type": "integer", "minimum": 0, "maximum": 100},
                    "reason": {"type": "string"},
                    "extractor_task": {"type": "string"},
                },
                "required": ["url", "priority", "reason", "extractor_task"],
            },
        },
        "discarded_urls": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"url": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["url", "reason"],
            },
        },
        "needs_more_fetch": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"url": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["url", "reason"],
            },
        },
        "notes": {"type": "string"},
    },
    "required": ["site_root", "kept_urls", "discarded_urls", "needs_more_fetch", "notes"],
}
