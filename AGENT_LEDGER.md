# Agent Ledger

## Repository target

- GitHub repository: `LuminaryLabs-Agents/NexusAgent-OmniScraper`
- Default branch: `main`
- Initial chat target: build and push an OmniScraper starter directly to the repository.

## Current implementation

- Python package: `omni_scraper`
- CLI command: `omni-scraper`
- Core module: `omni_scraper/core.py`
- Robots helper: `omni_scraper/robots.py`
- Tests: `tests/test_core.py`

## Build direction

Keep the scraper modular so future agent passes can add:

- Source-specific collectors.
- Browser-backed rendering.
- Queue and crawl frontier management.
- Deduplication and content fingerprints.
- Export formats beyond JSONL.
- Evidence/source ledgers for collected public data.
