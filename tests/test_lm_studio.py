import unittest

from omni_scraper.models.lm_studio import extract_first_json_object, parse_json_content


class LMStudioTests(unittest.TestCase):
    def test_parse_json_content_tolerates_fence(self):
        parsed = parse_json_content('```json\n{"ok": true}\n```')

        self.assertEqual(parsed, {"ok": True})

    def test_parse_json_content_extracts_object_from_prose(self):
        parsed = parse_json_content('Here is the result: {"ok": true, "count": 2}')

        self.assertEqual(parsed, {"ok": True, "count": 2})

    def test_parse_json_content_ignores_thinking_block(self):
        parsed = parse_json_content('<think>draft</think>\n{"ok": true}')

        self.assertEqual(parsed, {"ok": True})

    def test_extract_first_json_object_handles_nested_objects(self):
        extracted = extract_first_json_object('prefix {"outer": {"inner": true}} suffix')

        self.assertEqual(extracted, '{"outer": {"inner": true}}')


if __name__ == "__main__":
    unittest.main()
