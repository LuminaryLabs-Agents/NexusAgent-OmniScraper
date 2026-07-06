import unittest

from omni_scraper.core import PageRecord, ScrapeConfig, Scraper


class CoreTests(unittest.TestCase):
    def test_invalid_url_returns_error_record(self):
        record = Scraper(ScrapeConfig(respect_robots=False)).scrape("not-a-url")

        self.assertIsInstance(record, PageRecord)
        self.assertFalse(record.ok)
        self.assertIsNone(record.status)
        self.assertIn("invalid", record.error.lower())

    def test_page_record_serializes_to_dict(self):
        record = PageRecord(
            url="https://example.com",
            final_url="https://example.com",
            status=200,
            ok=True,
            title="Example",
        )

        data = record.to_dict()

        self.assertEqual(data["url"], "https://example.com")
        self.assertTrue(data["ok"])
        self.assertEqual(data["title"], "Example")


if __name__ == "__main__":
    unittest.main()
