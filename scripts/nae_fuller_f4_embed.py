"""scripts/nae_fuller_f4_embed.py — F4 Fuller embedding, additive/dry-run-first.

ADR-030 Amendment A §3 F4 gate: "review_status == verified TSU only, verified
건수 = 임베딩 건수, bge-m3:latest, 차원 1024". Amendment A is currently
PROPOSED (not Approved) — §8: "F4/F5/F6는 본 Amendment가 Approved 된 후에만
착수". This script is prepared code only; it must not be run with --apply
until the Amendment is promoted (see docs/NAE_F4_F5_F6_PREPARATION_DESIGN_v1.md).

Scope: Fuller_Complete_Works_Vol01-08 TSU records only, `review_status ==
"verified"`. As of writing, F3 (human review) has not disposed any Fuller
record, so every volume is 100% `generated` and the verified-count is 0 —
running this script (even with --apply) is currently a no-op that touches
nothing. The gate exists for when that changes.

What this script does NOT do:
  - No Qdrant writes (that's F5, scripts/nae_fuller_f5_upsert.py).
  - No mutation of tsu.json, decisions, or exception_queue files.
  - No embedding calls at all unless --apply is passed (dry-run is a pure
    cache-hit/miss count, zero Ollama traffic — relevant during the GPU
    full-load window, [memory: GPU Full Load Window]).

Usage:
    python scripts/nae_fuller_f4_embed.py            # dry-run (default)
    python scripts/nae_fuller_f4_embed.py --apply     # actually embed cache misses
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from NAE.pipeline.embed import client as embed_client
from NAE.pipeline.embed import hashing
from NAE.pipeline.tsu.config import TSU_SCHEMA_VERSION

FULLER_VOLUMES = [f"Fuller_Complete_Works_Vol{n:02d}" for n in range(1, 9)]
DEFAULT_TSU_DIR = PROJECT_ROOT / "NAE" / "corpus" / "tsu"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "output" / "nae_fuller_f4_embed_report.json"


def _load_verified_records(tsu_dir: Path = DEFAULT_TSU_DIR) -> list[dict]:
    """Fuller volumes only, `review_status == "verified"` only. Skips volumes
    whose tsu.json doesn't exist yet (F2 may still be generating later
    volumes in the background — see [memory: GPU Full Load Window])."""
    records: list[dict] = []
    for vol in FULLER_VOLUMES:
        path = tsu_dir / vol / "tsu.json"
        if not path.exists():
            continue
        recs = json.loads(path.read_text(encoding="utf-8"))
        records.extend(r for r in recs if r.get("review_status") == "verified")
    return records


def _content_hash(record: dict) -> str:
    return hashing.tsu_hash(
        schema_version=record.get("tsu_schema_version", TSU_SCHEMA_VERSION),
        claim=record.get("claim") or "",
        book=record.get("book") or "",
        page=record.get("page", ""),
        scriptures=record.get("scriptures", []),
    )


def run(*, apply: bool, tsu_dir: Path = DEFAULT_TSU_DIR, report_path: Path = DEFAULT_REPORT_PATH) -> dict:
    verified = _load_verified_records(tsu_dir)

    already_cached = 0
    newly_embedded = 0
    would_embed = 0
    embed_errors: list[tuple[str, str]] = []

    for record in verified:
        content_hash = _content_hash(record)
        cached = embed_client.get_cached(content_hash)
        if cached is not None:
            already_cached += 1
            continue

        if not apply:
            would_embed += 1
            continue

        claim_text = record.get("claim")
        if not claim_text:
            embed_errors.append((record.get("id", "?"), "EMPTY_CLAIM"))
            continue
        vector = embed_client.embed_text(claim_text, content_hash=content_hash)
        if vector is None:
            embed_errors.append((record.get("id", "?"), "EMBED_FAILED"))
            continue
        newly_embedded += 1

    report = {
        "mode": "apply" if apply else "dry-run",
        "verified_total": len(verified),
        "already_cached": already_cached,
        "would_embed": would_embed,
        "newly_embedded": newly_embedded,
        "errors": embed_errors,
        "error_count": len(embed_errors),
        "note": (
            "dry-run: zero Ollama calls made — counts are cache hit/miss only"
            if not apply
            else "apply: cache misses were embedded via Ollama (bge-m3:latest)"
        ),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually call Ollama to embed cache misses. Default is dry-run (report only, no embedding calls).",
    )
    args = parser.parse_args()

    report = run(apply=args.apply)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
