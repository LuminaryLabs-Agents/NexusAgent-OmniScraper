"""Batch seed URL runner for mass contact scraping."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import time
from typing import Any

from .runner import ContactHarnessRunner


@dataclass(slots=True)
class SeedRunResult:
    seed_url: str
    ok: bool
    manifest: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass(slots=True)
class SeedBatchResult:
    run_id: str
    output_dir: str
    total: int
    succeeded: int
    failed: int
    results: list[SeedRunResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "output_dir": self.output_dir,
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "results": [asdict(result) for result in self.results],
        }


def read_seed_urls(*, seeds: list[str] | None = None, input_path: str | Path | None = None) -> list[str]:
    values: list[str] = []
    if input_path:
        values.extend(Path(input_path).read_text(encoding="utf-8").splitlines())
    if seeds:
        values.extend(seeds)

    output: list[str] = []
    seen: set[str] = set()
    for raw in values:
        url = raw.strip()
        if not url or url.startswith("#"):
            continue
        if url not in seen:
            output.append(url)
            seen.add(url)
    return output


class SeedBatchRunner:
    def __init__(self, runner: ContactHarnessRunner | None = None) -> None:
        self.runner = runner or ContactHarnessRunner()

    def run(
        self,
        *,
        seed_urls: list[str],
        output_dir: str | Path,
        run_id: str,
        max_router_pages: int = 3,
        delay_seconds: float = 0.0,
        continue_on_error: bool = True,
    ) -> SeedBatchResult:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        results: list[SeedRunResult] = []

        for index, seed_url in enumerate(seed_urls, start=1):
            if delay_seconds > 0 and index > 1:
                time.sleep(delay_seconds)
            try:
                manifest = self.runner.run(
                    seed_url,
                    output_dir=output,
                    run_id=run_id,
                    max_router_pages=max_router_pages,
                )
                results.append(SeedRunResult(seed_url=seed_url, ok=True, manifest=manifest))
            except Exception as exc:
                result = SeedRunResult(seed_url=seed_url, ok=False, error=str(exc))
                results.append(result)
                if not continue_on_error:
                    break
            write_batch_manifest(output / "seed-batch-manifest.json", run_id=run_id, output_dir=output, results=results)

        succeeded = sum(1 for result in results if result.ok)
        failed = len(results) - succeeded
        batch = SeedBatchResult(
            run_id=run_id,
            output_dir=str(output),
            total=len(results),
            succeeded=succeeded,
            failed=failed,
            results=results,
        )
        write_batch_manifest(output / "seed-batch-manifest.json", run_id=run_id, output_dir=output, results=results)
        write_seed_status_jsonl(output / "seed-status.jsonl", results)
        return batch


def write_batch_manifest(path: str | Path, *, run_id: str, output_dir: Path, results: list[SeedRunResult]) -> None:
    succeeded = sum(1 for result in results if result.ok)
    failed = len(results) - succeeded
    payload = {
        "run_id": run_id,
        "output_dir": str(output_dir),
        "total": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "results": [asdict(result) for result in results],
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def write_seed_status_jsonl(path: str | Path, results: list[SeedRunResult]) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
