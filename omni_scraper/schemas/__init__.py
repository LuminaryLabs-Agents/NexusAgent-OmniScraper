"""JSON schemas for OmniScraper pipeline stages."""

from .extraction import CONTACT_EXTRACTION_JSON_SCHEMA, SCHEMA_VERSION
from .scout import SCOUT_JSON_SCHEMA

__all__ = ["CONTACT_EXTRACTION_JSON_SCHEMA", "SCHEMA_VERSION", "SCOUT_JSON_SCHEMA"]
