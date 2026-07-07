"""Command-line runner for processing many seed URLs."""

from __future__ import annotations

import argparse
import json

from .harness.seed_batch import SeedBatchRunner, read_seed_urls


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m omni_scraper.run_seeds")
    parser.add_argument("seeds", nargs="*", help="Seed URLs.")
    parser.add_argument("--input", "-i", help="Text file containing one seed URL per line.")
    parser.add_argument("--output-dir", "-o", default="runs/seed_batch")
    parser.add_argument("--run-id", default="seed-batch")
    parser.add_argument("--max-router-pages", type=int, default=3, help="Maximum pages inspected per seed site.")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay between seed sites in seconds.")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop after the first failed seed.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    seeds = read_seed_urls(seeds=args.seeds, input_path=args.input)
    if not seeds:
        parser.error("provide seed URLs directly or with --input")

    result = SeedBatchRunner().run(
        seed_urls=seeds,
        output_dir=args.output_dir,
        run_id=args.run_id,
        max_router_pages=args.max_router_pages,
        delay_seconds=args.delay,
        continue_on_error=not args.stop_on_error,
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
