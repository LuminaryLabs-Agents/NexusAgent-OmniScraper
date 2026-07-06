# NexusAgent OmniScraper

A small, dependency-light scraping starter for collecting public web pages into normalized JSON records.

## Current scope

- Fetch public HTTP/HTTPS pages.
- Extract title, meta description, headings, links, and cleaned text.
- Respect basic robots.txt disallow rules for the configured user agent.
- Save results as JSON Lines.
- Run as a CLI or import as a Python library.

## Install for local development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## CLI usage

Scrape one or more URLs:

```bash
omni-scraper scrape https://example.com --output data/pages.jsonl
```

Scrape URLs from a text file:

```bash
omni-scraper scrape --input urls.txt --output data/pages.jsonl
```

Validate package tests:

```bash
python -m unittest discover
```

## Design notes

This repo starts intentionally small. The scraper core is separated from the CLI so future agents can add domain-specific collectors, browser automation, deduplication, queues, rate limits, source ledgers, and export formats without rewriting the base flow.
