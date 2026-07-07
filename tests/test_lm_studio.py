import unittest

from omni_scraper.models.lm_studio import parse_json_content


class LMStudioTests(unittest.TestCase):
    def test_parse_json_content_tolerates_fence(self):
        parsed = parse_json_content('```json\n{"ok": true}\n```')

        self.assertEqual(parsed, {"ok": True})


if __name__ == "__main__":
    unittest.main()
