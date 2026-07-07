"""Command-line entry point for NexusAgent OmniScraper."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import ScrapeConfig, Scraper
from .harness.extractor import ExtractorAgent
from .harness.runner import ContactHarnessRunner
from .models.lm_studio import LMStudioClient, LMStudioConfig
from .pipeline.packets import make_markdown_packet, site_slug
from .reduce.fetch import fetch_html
from .reduce.html_to_markdown import reduce_html
from .validate.evidence import validate_extraction_files


def _read_urls(args: argparse.Namespace) -> list[str]:
    urls: list[str] = []
    if args.input:
        input_path = Path(args.input)
        urls.extend(line.strip() for line in input_path.read_text(encoding="utf-8").splitlines())
    urls.extend(args.urls or [])
    return [url for url in urls if url and not url.startswith("#")]


def _write_records(records: list[object], output: str) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True))
            stream.write("\n")


def _write_json(path: str | Path, data: object) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="omni-scraper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape = subparsers.add_parser("scrape", help="Scrape public pages into JSONL records.")
    scrape.add_argument("urls", nargs="*", help="One or more HTTP/HTTPS URLs to scrape.")
    scrape.add_argument("--input", "-i", help="Text file containing one URL per line.")
    scrape.add_argument("--output", "-o", default="data/pages.jsonl", help="Output JSONL path.")
    scrape.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds.")
    scrape.add_argument("--delay", type=float, default=0.0, help="Delay between requests in seconds.")
    scrape.add_argument("--max-bytes", type=int, default=2_000_000, help="Maximum response bytes per page.")
    scrape.add_argument("--ignore-robots", action="store_true", help="Do not check robots.txt before fetching.")
    scrape.add_argument("--user-agent", default=ScrapeConfig.user_agent, help="User-Agent header.")

    reduce_url = subparsers.add_parser("reduce-url", help="Fetch a URL and write deterministic reduced Markdown/JSON.")
    reduce_url.add_argument("url")
    reduce_url.add_argument("--output-dir", "-o", default="runs/manual/reduced", help="Directory for page.md and page.json.")
    reduce_url.add_argument("--timeout", type=float, default=20.0)
    reduce_url.add_argument("--max-bytes", type=int, default=3_000_000)

    bundle = subparsers.add_parser("bundle-pages", help="Create a finalized Markdown packet from reduced page JSON files.")
    bundle.add_argument("--root-url", required=True)
    bundle.add_argument("--run-id", default="manual")
    bundle.add_argument("--output", default="runs/manual/site-bundle.md")
    bundle.add_argument("pages", nargs="+", help="Reduced page JSON files created by reduce-url.")

    extract = subparsers.add_parser("extract-contact", help="Run the extractor stage on a finalized Markdown bundle.")
    extract.add_argument("--bundle", required=True, help="Path to finalized site-bundle.md.")
    extract.add_argument("--root-url", required=True)
    extract.add_argument("--bundle-id", default="manual/site")
    extract.add_argument("--output", "-o", default="runs/manual/extractor-output.json")
    extract.add_argument("--model", help="Override OMNI_EXTRACTOR_MODEL for this call.")

    validate = subparsers.add_parser("validate-extraction", help="Run deterministic validation on extractor JSON.")
    validate.add_argument("--bundle", required=True, help="Path to finalized site-bundle.md.")
    validate.add_argument("--extraction", required=True, help="Path to extractor-output.json.")
    validate.add_argument("--metadata", help="Optional path to site-bundle.json for source URL validation.")
    validate.add_argument("--output", "-o", default="runs/manual/validation-result.json")

    run = subparsers.add_parser("run-contact-harness", help="Run scout -> router -> extractor -> validator for one seed URL.")
    run.add_argument("seed_url")
    run.add_argument("--output-dir", "-o", default="runs/manual")
    run.add_argument("--run-id", default="manual")
    run.add_argument("--max-router-pages", type=int, default=8)

    config = subparsers.add_parser("show-config", help="Show LM Studio configuration resolved from environment variables.")
    config.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scrape":
        urls = _read_urls(args)
        if not urls:
            parser.error("provide URLs directly or with --input")

        config = ScrapeConfig(
            user_agent=args.user_agent,
            timeout_seconds=args.timeout,
            delay_seconds=args.delay,
            max_bytes=args.max_bytes,
            respect_robots=not args.ignore_robots,
        )
        records = Scraper(config).scrape_many(urls)
        _write_records(records, args.output)

        ok_count = sum(1 for record in records if record.ok)
        print(f"wrote {len(records)} records to {args.output} ({ok_count} ok)")
        return 0 if ok_count == len(records) else 1

    if args.command == "reduce-url":
        fetched = fetch_html(args.url, timeout_seconds=args.timeout, max_bytes=args.max_bytes)
        if not fetched.ok:
            print(f"fetch failed: {fetched.error}", file=sys.stderr)
            return 1
        page = reduce_html(fetched.html, source_url=args.url, final_url=fetched.final_url)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "page.md").write_text(page.markdown, encoding="utf-8")
        (output_dir / "page.json").write_text(page.to_json(), encoding="utf-8")
        print(f"wrote reduced page to {output_dir}")
        return 0

    if args.command == "bundle-pages":
        pages = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.pages]
        markdown = make_markdown_packet(args.root_url, pages, run_id=args.run_id)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8")
        metadata = {"bundle_id": f"{args.run_id}/{site_slug(args.root_url)}", "root_url": args.root_url, "pages": pages}
        output.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(f"wrote finalized Markdown packet to {output}")
        return 0

    if args.command == "extract-contact":
        client = LMStudioClient()
        model = args.model or client.config.extractor_model
        agent = ExtractorAgent(client=client, model=model)
        bundle_text = Path(args.bundle).read_text(encoding="utf-8")
        extraction = agent.run(bundle_text, root_url=args.root_url, bundle_id=args.bundle_id)
        output = _write_json(args.output, extraction)
        print(f"wrote extractor output to {output}")
        return 0

    if args.command == "validate-extraction":
        result = validate_extraction_files(
            bundle_path=args.bundle,
            extraction_path=args.extraction,
            metadata_path=args.metadata,
            output_path=args.output,
        )
        print(f"validated extraction: {json.dumps(result.to_dict()['stats'], sort_keys=True)}")
        return 1 if result.rejected_fields else 0

    if args.command == "run-contact-harness":
        manifest = ContactHarnessRunner().run(
            args.seed_url,
            output_dir=args.output_dir,
            run_id=args.run_id,
            max_router_pages=args.max_router_pages,
        )
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0

    if args.command == "show-config":
        cfg = LMStudioConfig.from_env()
        data = {
            "base_url": cfg.base_url,
            "scout_model": cfg.scout_model,
            "router_model": cfg.router_model,
            "extractor_model": cfg.extractor_model,
            "timeout_seconds": cfg.timeout_seconds,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
        }
        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            for key, value in data.items():
                print(f"{key}: {value}")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
