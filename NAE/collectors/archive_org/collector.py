"""NAE Corpus Builder - Phase 1: Internet Archive Collector.

Pipeline: Keyword -> Search -> License filter -> Metadata -> Download -> Integrity -> Catalog.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(iterable=None, **kwargs):
        return iterable if iterable is not None else []

from . import config, downloader, filters, metadata as meta_mod, search

logger = logging.getLogger("nae.collector")


def setup_logging(logs_root: Path = config.LOGS_ROOT) -> None:
    logs_root.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("nae.collector")
    root.setLevel(logging.INFO)
    root.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s")

    def add_handler(filename: str, level: int, name_filter: str | None = None) -> None:
        handler = logging.FileHandler(logs_root / filename)
        handler.setLevel(level)
        handler.setFormatter(fmt)
        if name_filter:
            handler.addFilter(lambda record: name_filter in record.name)
        root.addHandler(handler)

    add_handler("collector.log", logging.INFO)
    add_handler("download.log", logging.INFO, name_filter="download")
    add_handler("error.log", logging.ERROR)

    stream = logging.StreamHandler(sys.stdout)
    stream.setLevel(logging.INFO)
    stream.setFormatter(fmt)
    root.addHandler(stream)


def load_catalog(path: Path = config.CATALOG_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return {entry["identifier"]: entry for entry in data} if isinstance(data, list) else data
    except (json.JSONDecodeError, OSError):
        logger.warning("[catalog] failed to load %s, starting fresh", path)
        return {}


def save_catalog(catalog: dict[str, dict[str, Any]], path: Path = config.CATALOG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(list(catalog.values()), fh, ensure_ascii=False, indent=2)


def category_for(item: meta_mod.ItemMetadata) -> str:
    haystack = " ".join(item.subjects + [item.title]).lower()
    for category, keywords in config.CATEGORY_KEYWORDS.items():
        if any(kw in haystack for kw in keywords):
            return category
    return config.DEFAULT_CATEGORY


def known_checksums(catalog: dict[str, dict[str, Any]]) -> set[str]:
    return {e["checksum"] for e in catalog.values() if e.get("checksum")}


def find_item_dir(identifier: str, download_root: Path = config.DOWNLOAD_ROOT) -> Path | None:
    for category in list(config.CATEGORY_KEYWORDS.keys()) + [config.DEFAULT_CATEGORY]:
        candidate = download_root / category / identifier
        if candidate.exists():
            return candidate
    return None


def is_locally_intact(identifier: str, catalog_entry: dict[str, Any],
                       download_root: Path = config.DOWNLOAD_ROOT) -> bool:
    """Verify metadata.json, the original file, and its checksum actually exist on disk.

    A catalog entry with downloaded=True is not trusted on its own — the raw
    files may have been moved, deleted, or partially written since the last run.
    """
    item_dir = find_item_dir(identifier, download_root)
    if item_dir is None:
        return False
    if not (item_dir / "metadata.json").exists():
        return False
    originals = list(item_dir.glob("original.*"))
    if not originals:
        return False
    expected = catalog_entry.get("checksum", "")
    if not expected:
        return False
    return downloader.verify_checksum(originals[0], expected)


def write_manifest(item_dir: Path, *, identifier: str, entry: dict[str, Any]) -> None:
    manifest = {
        "identifier": identifier,
        "download_time": datetime.now(timezone.utc).isoformat(),
        "sha256": entry.get("checksum", ""),
        "files": sorted(p.name for p in item_dir.glob("*") if p.is_file() and p.name != "manifest.json"),
        "version": 1,
        "collector_version": config.COLLECTOR_VERSION,
    }
    config.MANIFESTS_ROOT.mkdir(parents=True, exist_ok=True)
    with open(item_dir / "manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    with open(config.MANIFESTS_ROOT / f"{identifier}.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)


def process_identifier(identifier: str, *, cfg: config.CollectorConfig,
                        catalog: dict[str, dict[str, Any]],
                        download_only: bool = False,
                        metadata_only: bool = False,
                        resume: bool = True) -> dict[str, Any]:
    """Process one identifier through metadata -> download -> integrity -> catalog entry."""
    if resume and not download_only and identifier in catalog:
        existing = catalog[identifier]
        if existing.get("downloaded") and is_locally_intact(identifier, existing, cfg.download_root):
            return {"identifier": identifier, "status": "skipped_duplicate"}
        if existing.get("downloaded"):
            logger.warning("[resume] catalog claims %s downloaded but local files missing/corrupt, re-downloading",
                            identifier)

    try:
        item = meta_mod.fetch_item_metadata(identifier, retry=cfg.retry, timeout=cfg.timeout)
    except Exception as exc:  # noqa: BLE001
        logger.error("[process] metadata fetch failed for %s: %s", identifier, exc)
        return {"identifier": identifier, "status": "failed", "reason": f"metadata_error:{exc}"}

    pd_ok, pd_reason = filters.is_public_domain(
        licenseurl=item.license, rights=item.rights,
        possible_copyright_status=item.possible_copyright_status, year=item.year,
    )
    if not pd_ok:
        return {"identifier": identifier, "status": "skipped_license", "reason": pd_reason}

    files = meta_mod.select_download_files(item)
    if not files:
        return {"identifier": identifier, "status": "failed", "reason": "no_downloadable_files"}

    category = category_for(item)
    item_dir = cfg.download_root / category / identifier
    downloaded_any = False
    checksum = ""
    download_url = ""

    if not metadata_only:
        for role, fentry in files.items():
            url = config.DOWNLOAD_URL_TEMPLATE.format(identifier=identifier, filename=fentry.name)
            dest_name = "original" + Path(fentry.name).suffix if role == "primary" else "ocr.txt"
            dest = item_dir / dest_name
            ok, result = downloader.download_file(url, dest, retry=cfg.retry, timeout=cfg.timeout)
            if role == "primary":
                download_url = url
                if ok:
                    checksum = result
                    downloaded_any = True
                else:
                    return {"identifier": identifier, "status": "failed", "reason": result}

        if checksum and checksum in known_checksums(catalog):
            return {"identifier": identifier, "status": "skipped_duplicate_checksum"}

    entry = meta_mod.build_metadata_dict(
        item, license_ok=pd_reason, download_url=download_url,
        checksum=checksum, downloaded=downloaded_any,
    )

    if not metadata_only:
        item_dir.mkdir(parents=True, exist_ok=True)
        with open(item_dir / "metadata.json", "w", encoding="utf-8") as fh:
            json.dump(entry, fh, ensure_ascii=False, indent=2)
        if downloaded_any:
            write_manifest(item_dir, identifier=identifier, entry=entry)

    catalog[identifier] = entry
    return {"identifier": identifier, "status": "downloaded" if downloaded_any else "metadata_only"}


def run_collector(keywords: list[str], *, cfg: config.CollectorConfig,
                   resume: bool = True, download_only: bool = False,
                   metadata_only: bool = False) -> dict[str, Any]:
    setup_logging()
    start_time = time.monotonic()
    catalog = load_catalog() if resume else {}

    all_results: list[search.SearchResult] = []
    for kw in keywords:
        all_results.extend(search.search_keyword(kw, rows=cfg.max_results, retry=cfg.retry, timeout=cfg.timeout))

    seen_ids: set[str] = set()
    deduped = []
    for r in all_results:
        if r.identifier not in seen_ids:
            seen_ids.add(r.identifier)
            deduped.append(r)

    accepted, exclusion_reasons = filters.filter_results(deduped)
    accepted = accepted[: cfg.max_download]

    summary = {
        "search_results": len(deduped),
        "downloaded": 0,
        "skipped_duplicate": 0,
        "skipped_license": sum(v for k, v in exclusion_reasons.items() if "license" in k),
        "failed": 0,
        "failures": [],
    }

    with ThreadPoolExecutor(max_workers=cfg.threads) as executor:
        futures = {
            executor.submit(process_identifier, r.identifier, cfg=cfg, catalog=catalog,
                             download_only=download_only, metadata_only=metadata_only,
                             resume=resume): r.identifier
            for r in accepted
        }
        for future in tqdm(as_completed(futures), total=len(futures), desc="collecting"):
            result = future.result()
            status = result["status"]
            if status == "downloaded" or status == "metadata_only":
                summary["downloaded"] += 1
            elif status.startswith("skipped_duplicate"):
                summary["skipped_duplicate"] += 1
            elif status == "skipped_license":
                summary["skipped_license"] += 1
            elif status == "failed":
                summary["failed"] += 1
                summary["failures"].append(result)

    save_catalog(catalog)
    summary["catalog_size"] = len(catalog)

    elapsed = time.monotonic() - start_time
    summary["elapsed_seconds"] = round(elapsed, 2)
    summary["average_per_sec"] = round(len(accepted) / elapsed, 3) if elapsed > 0 else 0.0
    write_report(summary, keywords)
    return summary


def write_report(summary: dict[str, Any], keywords: list[str]) -> Path:
    config.REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "collector_version": config.COLLECTOR_VERSION,
        "keywords": keywords,
        **summary,
    }
    report_path = config.REPORTS_ROOT / f"report_{int(time.time())}.json"
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    latest_path = config.REPORTS_ROOT / "latest.json"
    with open(latest_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    return report_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NAE Corpus Builder - Internet Archive Collector")
    parser.add_argument("--keyword", action="append", help="Keyword to search (repeatable)")
    parser.add_argument("--limit", type=int, default=config.MAX_DOWNLOAD, help="Max items to download")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--threads", type=int, default=config.THREADS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    keywords = args.keyword or (config.PRIORITY_A + config.PRIORITY_B + config.PRIORITY_C)

    cfg = config.CollectorConfig(max_download=args.limit, threads=args.threads)
    summary = run_collector(
        keywords, cfg=cfg, resume=args.resume,
        download_only=args.download_only, metadata_only=args.metadata_only,
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
