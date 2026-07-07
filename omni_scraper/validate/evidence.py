"""Deterministic validation for extractor outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Iterable

from .regexes import validate_regex

FIELD_NAMES_BY_SCOPE = {
    "site": ["company_name", "website", "company_description", "industry", "headquarters"],
    "contact": ["person_name", "role", "department", "email", "phone", "address", "contact_form_url", "social_url"],
}


@dataclass(slots=True)
class FieldValidation:
    path: str
    kind: str
    value: str
    accepted: bool
    reason: str
    source_url: str = ""
    page_id: str = ""


@dataclass(slots=True)
class ValidationResult:
    accepted_fields: list[FieldValidation] = field(default_factory=list)
    rejected_fields: list[FieldValidation] = field(default_factory=list)
    missing_fields: list[FieldValidation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_fields": [asdict(item) for item in self.accepted_fields],
            "rejected_fields": [asdict(item) for item in self.rejected_fields],
            "missing_fields": [asdict(item) for item in self.missing_fields],
            "warnings": self.warnings,
            "stats": {"accepted": len(self.accepted_fields), "rejected": len(self.rejected_fields), "missing": len(self.missing_fields)},
        }


def validate_extraction(bundle_markdown: str, extraction: dict[str, Any], *, bundle_metadata: dict[str, Any] | None = None) -> ValidationResult:
    result = ValidationResult()
    allowed_urls = _allowed_urls(bundle_metadata)

    for path, kind, field_data in iter_contact_fields(extraction):
        validation = validate_field(path, kind, field_data, bundle_markdown, allowed_urls=allowed_urls)
        if field_data.get("missing") is True:
            result.missing_fields.append(validation)
        elif validation.accepted:
            result.accepted_fields.append(validation)
        else:
            result.rejected_fields.append(validation)

    if result.rejected_fields:
        result.warnings.append("One or more extracted fields failed deterministic validation and should not be exported.")
    return result


def validate_extraction_files(
    *,
    bundle_path: str | Path,
    extraction_path: str | Path,
    metadata_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> ValidationResult:
    bundle_text = Path(bundle_path).read_text(encoding="utf-8")
    extraction = json.loads(Path(extraction_path).read_text(encoding="utf-8"))
    metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8")) if metadata_path else None
    result = validate_extraction(bundle_text, extraction, bundle_metadata=metadata)
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return result


def iter_contact_fields(extraction: dict[str, Any]) -> Iterable[tuple[str, str, dict[str, Any]]]:
    site = extraction.get("site", {})
    if isinstance(site, dict):
        for kind in FIELD_NAMES_BY_SCOPE["site"]:
            field_data = site.get(kind)
            if isinstance(field_data, dict):
                yield f"site.{kind}", kind, field_data

    contacts = extraction.get("contacts", [])
    if isinstance(contacts, list):
        for index, contact in enumerate(contacts):
            if not isinstance(contact, dict):
                continue
            for kind in FIELD_NAMES_BY_SCOPE["contact"]:
                field_data = contact.get(kind)
                if isinstance(field_data, dict):
                    yield f"contacts[{index}].{kind}", kind, field_data


def validate_field(path: str, kind: str, field_data: dict[str, Any], bundle_markdown: str, *, allowed_urls: set[str] | None = None) -> FieldValidation:
    value = str(field_data.get("value", "")).strip()
    missing = field_data.get("missing") is True
    missing_reason = str(field_data.get("missing_reason", "")).strip()
    evidence = field_data.get("evidence", {}) if isinstance(field_data.get("evidence"), dict) else {}
    source_url = str(evidence.get("source_url", "")).strip()
    page_id = str(evidence.get("page_id", "")).strip()
    exact_quote = str(evidence.get("exact_quote", ""))
    context = str(evidence.get("context_50_each_side", ""))

    if missing:
        if value:
            return FieldValidation(path, kind, value, False, "Field marked missing but value is not empty.", source_url, page_id)
        if not missing_reason:
            return FieldValidation(path, kind, value, False, "Missing field lacks missing_reason.", source_url, page_id)
        return FieldValidation(path, kind, value, True, missing_reason, source_url, page_id)

    if not value:
        return FieldValidation(path, kind, value, False, "Non-missing field has empty value.", source_url, page_id)
    if allowed_urls is not None and source_url and source_url not in allowed_urls:
        return FieldValidation(path, kind, value, False, "Source URL is not present in bundle metadata.", source_url, page_id)
    if not source_url:
        return FieldValidation(path, kind, value, False, "Evidence source_url is required.", source_url, page_id)
    if not page_id:
        return FieldValidation(path, kind, value, False, "Evidence page_id is required.", source_url, page_id)
    if not exact_quote:
        return FieldValidation(path, kind, value, False, "Exact quote is required.", source_url, page_id)
    if exact_quote not in bundle_markdown:
        return FieldValidation(path, kind, value, False, "Exact quote was not found in finalized Markdown.", source_url, page_id)
    if value not in exact_quote:
        return FieldValidation(path, kind, value, False, "Value does not appear inside exact_quote.", source_url, page_id)
    if not context:
        return FieldValidation(path, kind, value, False, "context_50_each_side is required.", source_url, page_id)
    if context not in bundle_markdown:
        return FieldValidation(path, kind, value, False, "context_50_each_side was not found in finalized Markdown.", source_url, page_id)
    if value not in context:
        return FieldValidation(path, kind, value, False, "Value does not appear inside context_50_each_side.", source_url, page_id)

    expected_context = expected_context_from_quote(bundle_markdown, exact_quote, value)
    if expected_context != context:
        return FieldValidation(path, kind, value, False, "context_50_each_side does not match the deterministic 50-character window.", source_url, page_id)

    regex_ok, regex_reason = validate_regex(kind, value)
    if not regex_ok:
        return FieldValidation(path, kind, value, False, regex_reason, source_url, page_id)

    return FieldValidation(path, kind, value, True, "Accepted.", source_url, page_id)


def expected_context_from_quote(bundle_markdown: str, exact_quote: str, value: str) -> str:
    quote_start = bundle_markdown.index(exact_quote)
    value_offset = exact_quote.index(value)
    value_start = quote_start + value_offset
    value_end = value_start + len(value)
    return bundle_markdown[max(0, value_start - 50) : min(len(bundle_markdown), value_end + 50)]


def _allowed_urls(bundle_metadata: dict[str, Any] | None) -> set[str] | None:
    if not bundle_metadata:
        return None
    urls: set[str] = set()
    for page in bundle_metadata.get("pages", []) or []:
        if isinstance(page, dict):
            if page.get("source_url"):
                urls.add(str(page["source_url"]))
            if page.get("final_url"):
                urls.add(str(page["final_url"]))
    return urls
