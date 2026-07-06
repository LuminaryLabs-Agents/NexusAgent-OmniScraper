"""Command-line entry point for NexusAgent OmniScraper."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import ScrapeConfig, Scraper


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

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
