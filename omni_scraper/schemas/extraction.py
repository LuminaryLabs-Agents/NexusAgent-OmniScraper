"""Strict contact extraction schema.

Missing data is expected: the extractor should set missing=true, value="",
and provide a missing_reason instead of guessing.
"""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "contact_extraction.v1"

EVIDENCE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "source_url": {"type": "string"},
        "page_id": {"type": "string"},
        "exact_quote": {"type": "string"},
        "context_50_each_side": {"type": "string"},
    },
    "required": ["source_url", "page_id", "exact_quote", "context_50_each_side"],
}

CONTACT_FIELD_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "value": {"type": "string"},
        "missing": {"type": "boolean"},
        "missing_reason": {"type": "string"},
        "evidence": EVIDENCE_JSON_SCHEMA,
    },
    "required": ["value", "missing", "missing_reason", "evidence"],
}

SITE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "root_url": {"type": "string"},
        "source_bundle_id": {"type": "string"},
        "company_name": CONTACT_FIELD_JSON_SCHEMA,
        "website": CONTACT_FIELD_JSON_SCHEMA,
        "company_description": CONTACT_FIELD_JSON_SCHEMA,
        "industry": CONTACT_FIELD_JSON_SCHEMA,
        "headquarters": CONTACT_FIELD_JSON_SCHEMA,
    },
    "required": ["root_url", "source_bundle_id", "company_name", "website", "company_description", "industry", "headquarters"],
}

CONTACT_RECORD_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "contact_id": {"type": "string"},
        "contact_type": {"type": "string", "enum": ["general", "person", "department", "location", "social", "form", "unknown"]},
        "source_priority": {"type": "integer", "minimum": 0, "maximum": 100},
        "person_name": CONTACT_FIELD_JSON_SCHEMA,
        "role": CONTACT_FIELD_JSON_SCHEMA,
        "department": CONTACT_FIELD_JSON_SCHEMA,
        "email": CONTACT_FIELD_JSON_SCHEMA,
        "phone": CONTACT_FIELD_JSON_SCHEMA,
        "address": CONTACT_FIELD_JSON_SCHEMA,
        "contact_form_url": CONTACT_FIELD_JSON_SCHEMA,
        "social_url": CONTACT_FIELD_JSON_SCHEMA,
    },
    "required": ["contact_id", "contact_type", "source_priority", "person_name", "role", "department", "email", "phone", "address", "contact_form_url", "social_url"],
}

CONTACT_EXTRACTION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "string", "enum": [SCHEMA_VERSION]},
        "site": SITE_JSON_SCHEMA,
        "contacts": {"type": "array", "items": CONTACT_RECORD_JSON_SCHEMA, "minItems": 0},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["schema_version", "site", "contacts", "warnings"],
}
