# Agent Ledger

## Repository target

- GitHub repository: `LuminaryLabs-Agents/NexusAgent-OmniScraper`
- Default branch: `main`

## Current implementation

The repo now includes an LM Studio-ready contact harness built around deterministic reduction, cheap scout/router passes, a strict extractor schema, and deterministic validation.

Implemented areas:

```text
omni_scraper/reduce/
  fetch.py
  html_to_markdown.py
  link_cluster.py
  signals.py
  accessibility.py

omni_scraper/models/
  lm_studio.py

omni_scraper/harness/
  scout.py
  router.py
  extractor.py
  bundle.py
  runner.py
  ledger.py

omni_scraper/schemas/
  scout.py
  router.py
  extraction.py

omni_scraper/validate/
  regexes.py
  evidence.py
```

## Safety rails

- Raw HTML is reduced to Markdown before model stages.
- Scout and Router operate on reduced packets, not raw HTML.
- Missing data is expected in extractor output.
- Extracted fields require exact source quotes and exact context windows.
- Deterministic validation rejects unsupported contact fields before export.
