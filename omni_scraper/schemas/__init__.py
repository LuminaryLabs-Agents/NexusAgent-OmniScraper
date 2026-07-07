"""JSON schemas for OmniScraper agent harness stages."""

from .extraction import CONTACT_EXTRACTION_JSON_SCHEMA, SCHEMA_VERSION
from .router import ROUTER_JSON_SCHEMA
from .scout import SCOUT_JSON_SCHEMA

__all__ = ["CONTACT_EXTRACTION_JSON_SCHEMA", "ROUTER_JSON_SCHEMA", "SCHEMA_VERSION", "SCOUT_JSON_SCHEMA"]
