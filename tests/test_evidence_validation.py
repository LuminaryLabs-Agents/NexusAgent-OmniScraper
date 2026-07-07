import unittest

from omni_scraper.validate.evidence import expected_context_from_quote, validate_extraction


def field(value, quote, context, source_url="https://example.com/contact", page_id="example-contact"):
    return {
        "value": value,
        "missing": False,
        "missing_reason": "",
        "evidence": {
            "source_url": source_url,
            "page_id": page_id,
            "exact_quote": quote,
            "context_50_each_side": context,
        },
    }


class EvidenceValidationTests(unittest.TestCase):
    def test_accepts_email_with_exact_quote_context_and_regex(self):
        bundle = "# Bundle\n\nPage ID: example-contact\nSource URL: https://example.com/contact\n\nEmail us at info@example.com for support.\n"
        quote = "Email us at info@example.com for support."
        context = expected_context_from_quote(bundle, quote, "info@example.com")
        extraction = {"contacts": [{"email": field("info@example.com", quote, context)}]}

        result = validate_extraction(bundle, extraction)

        self.assertEqual(len(result.accepted_fields), 1)
        self.assertEqual(len(result.rejected_fields), 0)

    def test_rejects_email_when_context_is_not_exact_window(self):
        bundle = "# Bundle\n\nPage ID: example-contact\nSource URL: https://example.com/contact\n\nEmail us at info@example.com for support.\n"
        quote = "Email us at info@example.com for support."
        extraction = {"contacts": [{"email": field("info@example.com", quote, "Email us at info@example.com")}]} 

        result = validate_extraction(bundle, extraction)

        self.assertEqual(len(result.accepted_fields), 0)
        self.assertEqual(len(result.rejected_fields), 1)
        self.assertIn("50-character", result.rejected_fields[0].reason)

    def test_missing_field_is_allowed_with_reason(self):
        extraction = {"contacts": [{"phone": {"value": "", "missing": True, "missing_reason": "No phone present.", "evidence": {"source_url": "", "page_id": "", "exact_quote": "", "context_50_each_side": ""}}}]}

        result = validate_extraction("# Bundle", extraction)

        self.assertEqual(len(result.missing_fields), 1)
        self.assertTrue(result.missing_fields[0].accepted)


if __name__ == "__main__":
    unittest.main()
