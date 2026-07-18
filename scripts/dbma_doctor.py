#!/usr/bin/env python3
"""scripts/dbma_doctor.py — DBMA Engineering Health Check (SPRINT29-A).

Read-only diagnostic CLI: reports the current state of DBMA (git, config,
corpus, TSU, retrieval index, capacity, known issues) in a single view.
Reuses existing modules wherever a signal is already computable —
core/execution_context.py (TSU/pipeline status), core/identity_registry.py
(document counts), core/runtime_state.py (vector-index leftover check),
core/tsu_builder.py's sha256/git helpers (dataset integrity, build
provenance), scripts/check_environment.py (Python/PyYAML/config checks).
Does not touch core/retrieval.py, does not write to production data, does
not modify the TSU dataset or registry.

Usage:
    python scripts/dbma_doctor.py                # fast checks only (default)
    python scripts/dbma_doctor.py --tests         # also runs pytest (slower)
    python scripts/dbma_doctor.py --json          # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── Git ──────────────────────────────────────────────────────────

def _git(*args: str) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=5,
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip()
    except Exception:
        return None


def check_git() -> dict[str, Any]:
    branch = _git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    head = _git("rev-parse", "--short", "HEAD") or "unknown"
    status = _git("status", "--porcelain") or ""
    dirty_files = [ln for ln in status.splitlines() if ln.strip()]
    return {
        "branch": branch,
        "head": head,
        "dirty": len(dirty_files) > 0,
        "dirty_count": len(dirty_files),
    }


# ── Python / Config (reuses scripts/check_environment.py) ─────────

def check_python_and_config() -> dict[str, Any]:
    import io
    import contextlib
    import scripts.check_environment as env_check

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        python_ok = env_check.check_python_version()
        yaml_ok = env_check.check_pyyaml()
        config_ok = env_check.check_config_yaml_exists()
        output_dir_ok = env_check.check_output_dir()

    from core.config import (
        APP_VERSION, DEFAULT_EMBED_MODEL, DEFAULT_GEN_MODEL,
        DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP,
    )

    return {
        "python_version": f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}",
        "python_ok": python_ok,
        "pyyaml_ok": yaml_ok,
        "config_yaml_ok": config_ok,
        "output_dir_ok": output_dir_ok,
        "app_version": APP_VERSION,
        "embed_model": DEFAULT_EMBED_MODEL,
        "gen_model": DEFAULT_GEN_MODEL,
        "chunk_size": DEFAULT_CHUNK_SIZE,
        "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
    }


# ── Corpus / Registry (reuses core/identity_registry.py) ──────────

def check_corpus() -> dict[str, Any]:
    from core.config import DEFAULT_RAW_DIR, DEFAULT_REGISTRY_PATH, SUPPORTED_EXTENSIONS
    from core.identity_registry import load_identity_registry

    raw_dir = Path(DEFAULT_RAW_DIR)
    raw_files = []
    if raw_dir.exists():
        raw_files = [
            f for f in raw_dir.rglob("*")
            if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

    registry = load_identity_registry(DEFAULT_REGISTRY_PATH)
    documents = registry.get("documents", {})
    total_chunks = sum(d.get("chunk_count", 0) for d in documents.values())
    missing_metadata = sum(
        1 for d in documents.values()
        if not d.get("source_file") or d.get("chunk_count", 0) <= 0
    )

    return {
        "raw_file_count": len(raw_files),
        "registered_document_count": len(documents),
        "total_chunk_count": total_chunks,
        "documents_missing_metadata": missing_metadata,
    }


# ── TSU / Retrieval Index (reuses core/execution_context.py,
#    core/runtime_state.py, core/tsu_builder.py) ───────────────────

def check_tsu_and_index() -> dict[str, Any]:
    from core.execution_context import ExecutionContext
    from core.runtime_state import _check_vector_index
    from core.tsu_builder import _sha256_of_file
    from core.config import DEFAULT_TSU_DATASET_PATH, DEFAULT_TSU_MANIFEST_PATH, DEFAULT_OUTPUT_DIR

    tsu_status = ExecutionContext().get_tsu_status()

    dataset_path = Path(DEFAULT_TSU_DATASET_PATH)
    manifest_path = Path(DEFAULT_TSU_MANIFEST_PATH)
    dataset_exists = dataset_path.exists()
    dataset_size_mb = dataset_path.stat().st_size / 1e6 if dataset_exists else 0.0

    integrity_ok = None
    if dataset_exists and manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            stored_sha = manifest.get("dataset_sha256")
            if stored_sha:
                live_sha = _sha256_of_file(dataset_path)
                integrity_ok = (live_sha == stored_sha)
        except Exception:
            integrity_ok = None

    # [ADR-003] DBMA does not use a vector DB in production. A leftover
    # chroma_db/VectorDB directory indicates orphaned legacy state, not a
    # healthy component — flagged as a known issue, not a feature.
    stray_vector_db = _check_vector_index(Path(DEFAULT_OUTPUT_DIR))

    return {
        "manifest_exists": tsu_status.get("manifest_exists", False),
        "tsu_count": tsu_status.get("tsu_count", 0),
        "source_document_count": tsu_status.get("source_document_count", 0),
        "generated_at": tsu_status.get("generated_at"),
        "dataset_exists": dataset_exists,
        "dataset_size_mb": round(dataset_size_mb, 2),
        "dataset_integrity_ok": integrity_ok,
        "stray_vector_db_present": stray_vector_db,
    }


# ── Embedding backend reachability (Ollama) ────────────────────────

def check_embedding_backend(embed_model: str, gen_model: str) -> dict[str, Any]:
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        model_names = {m.get("name") for m in data.get("models", [])}
        return {
            "reachable": True,
            "embed_model_installed": embed_model in model_names,
            "gen_model_installed": gen_model in model_names,
        }
    except Exception:
        return {"reachable": False, "embed_model_installed": None, "gen_model_installed": None}


# ── Benchmark (reads existing output/bench/*.json, no new run) ────

def check_last_benchmark() -> Optional[dict[str, Any]]:
    from core.config import DEFAULT_BENCH_DIR

    bench_dir = Path(DEFAULT_BENCH_DIR)
    if not bench_dir.exists():
        return None
    candidates = sorted(
        bench_dir.glob("chapter_level_result_*.json"),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    if not candidates:
        return None
    try:
        data = json.loads(candidates[0].read_text(encoding="utf-8"))
    except Exception:
        return None
    metrics = data.get("metrics", {})
    return {
        "file": candidates[0].name,
        "queries_evaluated": data.get("queries_evaluated"),
        "precision_at_1": metrics.get("precision_at_1"),
        "mrr": metrics.get("mrr"),
        "ndcg_at_10": metrics.get("ndcg_at_10"),
        "avg_latency_ms": data.get("avg_latency_ms"),
    }


# ── Capacity (SPRINT28 Capacity Report + SPRINT28-C measured ratios) ─

# Measured (SPRINT28-C Preflight, isolated Beta corpus, 8002 TSU):
#   healthy path (TF-IDF unbuilt, common case since SPRINT28-C):  4.81 KB/TSU
#   fallback path (TF-IDF built, embedding backend down):        23.9 KB/TSU
_RAM_KB_PER_TSU_HEALTHY = 4.81
_RAM_KB_PER_TSU_FALLBACK = 23.9

_ZONE_GREEN_MAX = 300_000
_ZONE_YELLOW_MAX = 700_000


def check_capacity(tsu_count: int) -> dict[str, Any]:
    if tsu_count <= _ZONE_GREEN_MAX:
        zone = "GREEN"
    elif tsu_count <= _ZONE_YELLOW_MAX:
        zone = "YELLOW"
    else:
        zone = "RED"
    return {
        "tsu_count": tsu_count,
        "zone": zone,
        "estimated_ram_healthy_mb": round(tsu_count * _RAM_KB_PER_TSU_HEALTHY / 1024, 1),
        "estimated_ram_fallback_mb": round(tsu_count * _RAM_KB_PER_TSU_FALLBACK / 1024, 1),
        "green_ceiling": _ZONE_GREEN_MAX,
        "yellow_ceiling": _ZONE_YELLOW_MAX,
    }


# ── Optional: full test suite (opt-in, slow) ───────────────────────

def run_tests() -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=ROOT, capture_output=True, text=True, timeout=600,
    )
    elapsed = time.perf_counter() - t0
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    return {
        "ran": True,
        "passed": proc.returncode == 0,
        "summary_line": tail,
        "elapsed_sec": round(elapsed, 1),
    }


# ── Known Issues aggregation (Phase 5 auto-checks) ─────────────────

def collect_known_issues(git_info, cfg_info, corpus_info, tsu_info, embed_info, test_info) -> list[str]:
    issues: list[str] = []
    if git_info["dirty"]:
        issues.append(f"Working tree dirty ({git_info['dirty_count']} changed files)")
    if not cfg_info["pyyaml_ok"]:
        issues.append("PyYAML not installed — config.yaml silently ignored")
    if not cfg_info["python_ok"]:
        issues.append(f"Python version {cfg_info['python_version']} outside expected 3.11.x/3.12.x")
    if not tsu_info["manifest_exists"]:
        issues.append("TSU manifest missing — index status unknown")
    if tsu_info["dataset_integrity_ok"] is False:
        issues.append("TSU dataset sha256 mismatch vs manifest — dataset changed after last build")
    if tsu_info["stray_vector_db_present"]:
        issues.append("Legacy vector DB directory present (chroma_db/VectorDB) — ADR-003 says none should exist in production")
    if corpus_info["documents_missing_metadata"] > 0:
        issues.append(f"{corpus_info['documents_missing_metadata']} registered document(s) missing source_file or chunk_count")
    if not embed_info["reachable"]:
        issues.append("Embedding backend (Ollama) unreachable — retrieval will fall back to TF-IDF for all queries")
    elif embed_info["embed_model_installed"] is False:
        issues.append(f"Configured embed model not found in Ollama's installed model list")
    if test_info is not None and not test_info["passed"]:
        issues.append(f"pytest regression: {test_info['summary_line']}")
    return issues


# ── Report rendering ────────────────────────────────────────────────

def render_report(
    git_info, cfg_info, corpus_info, tsu_info, embed_info,
    bench_info, capacity_info, known_issues, test_info, elapsed_sec,
) -> str:
    lines: list[str] = []
    W = 60
    lines.append("=" * W)
    lines.append("DBMA HEALTH REPORT")
    lines.append("=" * W)
    lines.append("")
    lines.append(f"Branch          {git_info['branch']}")
    lines.append(f"HEAD            {git_info['head']}")
    lines.append(f"Working Tree    {'DIRTY (' + str(git_info['dirty_count']) + ' files)' if git_info['dirty'] else 'clean'}")
    lines.append(f"Python          {cfg_info['python_version']} ({'OK' if cfg_info['python_ok'] else 'UNEXPECTED'})")
    lines.append(f"DBMA Version    {cfg_info['app_version']}")
    lines.append("")
    lines.append(f"Embed Model     {cfg_info['embed_model']}")
    lines.append(f"Gen Model       {cfg_info['gen_model']}")
    lines.append(f"Chunk Size      {cfg_info['chunk_size']} / overlap {cfg_info['chunk_overlap']}")
    lines.append("")
    lines.append(f"Corpus          {corpus_info['raw_file_count']} raw files, {corpus_info['registered_document_count']} registered documents")
    lines.append(f"TSU             {tsu_info['tsu_count']:,} (from {tsu_info['source_document_count']} documents, generated {tsu_info['generated_at'] or 'N/A'})")
    integrity = "OK" if tsu_info["dataset_integrity_ok"] else ("MISMATCH" if tsu_info["dataset_integrity_ok"] is False else "N/A")
    lines.append(f"Retrieval Index {tsu_info['dataset_size_mb']}MB on disk, integrity={integrity} (BM25+TF-IDF, no vector DB — ADR-003)")
    lines.append("")
    if bench_info:
        lines.append(f"Last Benchmark  {bench_info['file']}: P@1={bench_info['precision_at_1']} MRR={bench_info['mrr']} nDCG@10={bench_info['ndcg_at_10']} ({bench_info['queries_evaluated']} queries)")
    else:
        lines.append("Last Benchmark  no result file found in output/bench/")
    if test_info is not None:
        lines.append(f"Regression      {test_info['summary_line']} ({test_info['elapsed_sec']}s)")
    else:
        lines.append("Regression      skipped (pass --tests to run pytest)")
    lines.append("")
    lines.append(f"Capacity        {capacity_info['tsu_count']:,} TSU -> {capacity_info['zone']} "
                  f"(healthy ~{capacity_info['estimated_ram_healthy_mb']}MB / fallback ~{capacity_info['estimated_ram_fallback_mb']}MB RAM, extrapolated)")
    lines.append("")
    lines.append("Known Issues")
    if known_issues:
        for issue in known_issues:
            lines.append(f"  - {issue}")
    else:
        lines.append("  none detected")
    lines.append("")
    lines.append("Recommendation")
    if capacity_info["zone"] == "RED":
        lines.append("  Corpus exceeds RED capacity boundary — see SPRINT28 Capacity Report / SPRINT28-C before growing further.")
    elif known_issues:
        lines.append("  Review Known Issues above before the next ingest/release.")
    else:
        lines.append("  No action needed.")
    lines.append("")
    lines.append(f"(checked in {elapsed_sec:.1f}s)")
    lines.append("=" * W)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="DBMA Engineering Health Check")
    parser.add_argument("--tests", action="store_true", help="also run the full pytest suite (slower)")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON instead of the text report")
    args = parser.parse_args()

    t0 = time.perf_counter()

    git_info = check_git()
    cfg_info = check_python_and_config()
    corpus_info = check_corpus()
    tsu_info = check_tsu_and_index()
    embed_info = check_embedding_backend(cfg_info["embed_model"], cfg_info["gen_model"])
    bench_info = check_last_benchmark()
    capacity_info = check_capacity(tsu_info["tsu_count"])
    test_info = run_tests() if args.tests else None
    known_issues = collect_known_issues(git_info, cfg_info, corpus_info, tsu_info, embed_info, test_info)

    elapsed = time.perf_counter() - t0

    if args.json:
        print(json.dumps({
            "git": git_info, "config": cfg_info, "corpus": corpus_info,
            "tsu": tsu_info, "embedding_backend": embed_info,
            "last_benchmark": bench_info, "capacity": capacity_info,
            "known_issues": known_issues, "test": test_info,
            "elapsed_sec": round(elapsed, 2),
        }, ensure_ascii=False, indent=2))
    else:
        print(render_report(
            git_info, cfg_info, corpus_info, tsu_info, embed_info,
            bench_info, capacity_info, known_issues, test_info, elapsed,
        ))

    return 1 if known_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
