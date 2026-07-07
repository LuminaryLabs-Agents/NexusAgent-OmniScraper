# NexusAgent OmniScraper

NexusAgent OmniScraper is a local-model scraping harness for collecting contact and company information from public websites without sending raw HTML into model stages.

The current flow is:

```text
URL seed
→ deterministic fetch
→ HTML to Markdown reduction
→ Scout stage
→ Router stage
→ finalized Markdown bundle
→ Extractor stage
→ deterministic quote/context/regex validation
```

## Install

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

## Local model configuration

Set model names to match your local LM Studio server:

```bash
export OMNI_LMSTUDIO_BASE_URL="http://localhost:1234/v1"
export OMNI_QWEN_MODEL="qwen3.5-4b"
export OMNI_SCOUT_MODEL="$OMNI_QWEN_MODEL"
export OMNI_ROUTER_MODEL="$OMNI_QWEN_MODEL"
export OMNI_EXTRACTOR_MODEL="agents-a1"
```

Check config:

```bash
omni-scraper show-config
```

## Commands

Reduce one URL into Markdown and JSON:

```bash
omni-scraper reduce-url https://example.com/contact --output-dir runs/dev/reduced
```

Build a finalized Markdown bundle from reduced page JSON files:

```bash
omni-scraper bundle-pages --root-url https://example.com --run-id example --output runs/example/site-bundle.md runs/dev/reduced/page.json
```

Run the full contact harness:

```bash
omni-scraper run-contact-harness https://example.com --output-dir runs/example --run-id example
```

Run extraction only from an existing bundle:

```bash
omni-scraper extract-contact --bundle runs/example/site-bundle.md --root-url https://example.com --bundle-id example/example-com --output runs/example/extractor-output.json
```

Validate extraction output:

```bash
omni-scraper validate-extraction --bundle runs/example/site-bundle.md --metadata runs/example/site-bundle.json --extraction runs/example/extractor-output.json --output runs/example/validation-result.json
```

## Validation rules

Extractor output is accepted only when deterministic validation confirms:

- the exact quote exists in the finalized Markdown bundle
- the extracted value is inside the quote
- the context window exists in the bundle
- the context window matches the deterministic 50-character window around the value
- field regex/type checks pass
- missing fields have an empty value and a missing reason

## Tests

```bash
python -m unittest discover
```
