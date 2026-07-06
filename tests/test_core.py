from omni_scraper.core import PageRecord, ScrapeConfig, Scraper


def test_invalid_url_returns_error_record():
    record = Scraper(ScrapeConfig(respect_robots=False)).scrape("not-a-url")

    assert isinstance(record, PageRecord)
    assert record.ok is False
    assert record.status is None
    assert "invalid" in record.error.lower()


def test_page_record_serializes_to_dict():
    record = PageRecord(
        url="https://example.com",
        final_url="https://example.com",
        status=200,
        ok=True,
        title="Example",
    )

    data = record.to_dict()

    assert data["url"] == "https://example.com"
    assert data["ok"] is True
    assert data["title"] == "Example"
