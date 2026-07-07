"""End-to-end contact harness runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from omni_scraper.models.lm_studio import LMStudioClient
from omni_scraper.reduce.fetch import fetch_html
from omni_scraper.reduce.html_to_markdown import ReducedPage, reduce_html
from omni_scraper.validate.evidence import validate_extraction

from .bundle import build_extractor_bundle, site_slug
from .extractor import ExtractorAgent
from .ledger import RunLedger
from .router import RouterAgent
from .scout import ScoutAgent


class ContactHarnessRunner:
    """Scout -> Router -> Extractor -> Validator harness for one seed site."""

    def __init__(self, client: LMStudioClient | None = None) -> None:
        self.client = client or LMStudioClient()
        self.scout = ScoutAgent(self.client)
        self.router = RouterAgent(self.client)
        self.extractor = ExtractorAgent(self.client)

    def run(
        self,
        seed_url: str,
        *,
        output_dir: str | Path,
        run_id: str = "manual",
        max_router_pages: int = 8,
    ) -> dict[str, Any]:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        ledger = RunLedger(output)
        root_url = root_from_url(seed_url)
        slug = site_slug(root_url)
        site_dir = output / "sites" / slug
        reduced_dir = site_dir / "01-reduced-pages"
        stage_dir = site_dir / "02-router"
        bundle_dir = site_dir / "03-extractor-input"
        extraction_dir = site_dir / "04-extraction"
        for directory in [reduced_dir, stage_dir, bundle_dir, extraction_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        ledger.append("fetch", "Fetching seed URL.", url=seed_url)
        seed_page = self._fetch_reduce(seed_url)
        self._write_reduced(seed_page, reduced_dir, "seed")

        ledger.append("scout", "Calling Scout Agent.", model=self.client.config.scout_model)
        scout_output = self.scout.run(seed_page)
        (stage_dir / "scout-output.json").write_text(json.dumps(scout_output, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

        urls = prioritized_urls_from_scout(scout_output, root_url=root_url, limit=max_router_pages - 1)
        reduced_pages = [seed_page]
        for index, url in enumerate(urls, start=1):
            ledger.append("fetch", "Fetching Scout-prioritized URL.", url=url)
            page = self._fetch_reduce(url)
            reduced_pages.append(page)
            self._write_reduced(page, reduced_dir, f"page-{index:02d}")

        ledger.append("router", "Calling Router Agent.", model=self.client.config.router_model, pages=len(reduced_pages))
        router_output = self.router.run(root_url=root_url, pages=reduced_pages, scout_output=scout_output)
        (stage_dir / "router-output.json").write_text(json.dumps(router_output, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

        kept_urls = {item.get("url", "") for item in router_output.get("kept_urls", []) if isinstance(item, dict)}
        kept_pages = [page for page in reduced_pages if page.final_url in kept_urls or page.source_url in kept_urls]
        if not kept_pages:
            kept_pages = [seed_page]
            ledger.append("router", "Router kept no pages; seed page retained as fallback.")

        bundle = build_extractor_bundle(
            root_url=root_url,
            reduced_pages=kept_pages,
            router_output=router_output,
            scout_output=scout_output,
            run_id=run_id,
        )
        bundle_md, bundle_json = bundle.write(bundle_dir)
        ledger.append("bundle", "Wrote finalized extractor bundle.", bundle=str(bundle_md))

        ledger.append("extractor", "Calling Extractor Agent.", model=self.client.config.extractor_model)
        extraction = self.extractor.run(bundle.markdown, root_url=root_url, bundle_id=bundle.bundle_id)
        extraction_path = extraction_dir / "extractor-output.json"
        extraction_path.write_text(json.dumps(extraction, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

        validation = validate_extraction(bundle.markdown, extraction, bundle_metadata=bundle.metadata)
        validation_path = extraction_dir / "validation-result.json"
        validation_path.write_text(json.dumps(validation.to_dict(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        ledger.append("validation", "Completed deterministic validation.", **validation.to_dict()["stats"])

        manifest = {
            "root_url": root_url,
            "site_dir": str(site_dir),
            "scout_output": str(stage_dir / "scout-output.json"),
            "router_output": str(stage_dir / "router-output.json"),
            "bundle_markdown": str(bundle_md),
            "bundle_metadata": str(bundle_json),
            "extraction_output": str(extraction_path),
            "validation_result": str(validation_path),
        }
        (site_dir / "00-site-ledger.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return manifest

    def _fetch_reduce(self, url: str) -> ReducedPage:
        fetched = fetch_html(url)
        if not fetched.ok:
            return ReducedPage(
                source_url=url,
                final_url=fetched.final_url,
                page_id="fetch-error",
                title="",
                description="",
                markdown=f"# Fetch Error\n\nURL: {url}\n\nError: {fetched.error}",
                reducer_warnings=[fetched.error],
            )
        return reduce_html(fetched.html, source_url=url, final_url=fetched.final_url)

    @staticmethod
    def _write_reduced(page: ReducedPage, output_dir: Path, name: str) -> None:
        (output_dir / f"{name}.md").write_text(page.markdown, encoding="utf-8")
        (output_dir / f"{name}.json").write_text(page.to_json(), encoding="utf-8")


def root_from_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def same_site(url: str, root_url: str) -> bool:
    return urlparse(url).netloc.lower() == urlparse(root_url).netloc.lower()


def prioritized_urls_from_scout(scout_output: dict[str, Any], *, root_url: str, limit: int) -> list[str]:
    candidates = scout_output.get("next_urls", [])
    urls: list[tuple[int, str]] = []
    if isinstance(candidates, list):
        for item in candidates:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", ""))
            if url and same_site(url, root_url):
                urls.append((int(item.get("priority", 0)), url))
    ordered: list[str] = []
    seen: set[str] = set()
    for _priority, url in sorted(urls, reverse=True):
        if url not in seen:
            ordered.append(url)
            seen.add(url)
        if len(ordered) >= limit:
            break
    return ordered
