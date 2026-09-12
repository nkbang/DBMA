"""scripts/nae_fuller_f5_upsert.py — F5 Fuller additive upsert into `nae_tsu_v1`.

ADR-030 Amendment A §3 F5 gate: "nae_tsu_v1 additive upsert. 3,319 baseline
point 무접촉, work_id/source_id 격리, upsert 후 count = 3,319 + Fuller
verified." Amendment A is currently PROPOSED — §8: "F4/F5/F6는 본 Amendment가
Approved 된 후에만 착수". This script is prepared code only; --apply must
not be run until the Amendment is promoted (see
docs/NAE_F4_F5_F6_PREPARATION_DESIGN_v1.md).

Safety model:
  - Default is dry-run: reads Qdrant (scroll, read-only) to report what
    *would* be upserted; never calls client.upsert.
  - --apply is required for any write, and even then the script refuses
    (BaselineDriftError) unless the pre-upsert scroll shows exactly the
    expected 3,319 baseline points — this is the "baseline point 무접촉"
    guard as actual code, not a comment.
  - A Fuller TSU id colliding with an existing baseline point id would mean
    the additive upsert could silently overwrite a baseline point; this is
    also refused (BaselineDriftError) rather than proceeding.
  - Only reads embeddings already cached by F4
    (scripts/nae_fuller_f4_embed.py) — this script does not call Ollama. A
    Fuller record with no cached embedding is reported as an error and
    skipped, not embedded on the fly (keeps F4/F5 phase separation clean).
  - After a successful --apply, runs scripts/nae_corpus_reconcile.py and
    includes its drift verdict in the report (Amendment A §3 F5 gate
    requires drift 0).

Usage:
    python scripts/nae_fuller_f5_upsert.py            # dry-run (default)
    python scripts/nae_fuller_f5_upsert.py --apply     # actually upsert (baseline-guarded)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from NAE.pipeline.embed import client as embed_client
from NAE.pipeline.embed import hashing
from NAE.pipeline.index import config, qdrant_store
from NAE.pipeline.tsu.config import TSU_SCHEMA_VERSION

FULLER_VOLUMES = [f"Fuller_Complete_Works_Vol{n:02d}" for n in range(1, 9)]
DEFAULT_TSU_DIR = PROJECT_ROOT / "NAE" / "corpus" / "tsu"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "output" / "nae_fuller_f5_upsert_report.json"

# Dagg_Church_Order (2,958) + Hiscox_Standard_Manual (361) — ADR-030 §14 /
# Amendment A header "CLEAN baseline (변경 금지)". Not re-derived at runtime
# on purpose: the guard must fail loudly if the live collection ever drifts
# from this fixed expectation, rather than silently re-baselining itself.
EXPECTED_BASELINE_COUNT = 3319


class BaselineDriftError(RuntimeError):
    """Raised when the pre-upsert Qdrant state doesn't match the frozen
    3,319 baseline — refuse to write rather than risk touching it."""


def _load_verified_records(tsu_dir: Path = DEFAULT_TSU_DIR) -> list[dict]:
    records: list[dict] = []
    for vol in FULLER_VOLUMES:
        path = tsu_dir / vol / "tsu.json"
        if not path.exists():
            continue
        recs = json.loads(path.read_text(encoding="utf-8"))
        records.extend(r for r in recs if r.get("review_status") == "verified")
    return records


def _scroll_all_ids(client) -> set[str]:
    ids: set[str] = set()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=config.COLLECTION_NAME, limit=500, offset=offset,
            with_payload=True, with_vectors=False,
        )
        ids.update(p.payload["tsu_id"] for p in points)
        if offset is None:
            break
    return ids


def _embed_for_upsert(record: dict) -> list[float] | None:
    """Cache-only lookup — never calls Ollama. F4 is responsible for
    populating the cache; F5 only consumes it."""
    content_hash = hashing.tsu_hash(
        schema_version=record.get("tsu_schema_version", TSU_SCHEMA_VERSION),
        claim=record.get("claim") or "",
        book=record.get("book") or "",
        page=record.get("page", ""),
        scriptures=record.get("scriptures", []),
    )
    return embed_client.get_cached(content_hash)


def run(*, apply: bool, tsu_dir: Path = DEFAULT_TSU_DIR, report_path: Path = DEFAULT_REPORT_PATH) -> dict:
    fuller_verified = _load_verified_records(tsu_dir)
    fuller_ids = {r["id"] for r in fuller_verified}

    client = qdrant_store.get_client()
    existing_ids = _scroll_all_ids(client)

    if apply and len(existing_ids) != EXPECTED_BASELINE_COUNT:
        raise BaselineDriftError(
            f"pre-upsert scroll shows {len(existing_ids)} points, expected "
            f"exactly {EXPECTED_BASELINE_COUNT} baseline — refusing to write."
        )

    colliding_ids = fuller_ids & existing_ids
    if apply and colliding_ids:
        raise BaselineDriftError(
            f"{len(colliding_ids)} Fuller tsu_id(s) collide with existing "
            f"baseline point ids — refusing to write: {sorted(colliding_ids)[:5]}"
        )

    to_upsert_records = [r for r in fuller_verified if r["id"] not in existing_ids]

    not_embedded: list[str] = []
    points = []
    for record in to_upsert_records:
        vector = _embed_for_upsert(record)
        if vector is None:
            not_embedded.append(record["id"])
            continue
        if apply:
            points.append(qdrant_store.build_point(record, vector))

    reconcile_result = None
    if apply:
        if points:
            qdrant_store.upsert_points(client, points)
        post_ids = _scroll_all_ids(client)
        expected_final = len(existing_ids) + (len(to_upsert_records) - len(not_embedded))
        assert existing_ids <= post_ids, "baseline points missing after upsert — additive-only invariant broken"
        assert len(post_ids) == expected_final, (
            f"post-upsert count {len(post_ids)} != expected {expected_final} "
            f"(baseline {len(existing_ids)} + newly upserted {len(to_upsert_records) - len(not_embedded)})"
        )
        reconcile_result = _run_reconcile()

    report = {
        "mode": "apply" if apply else "dry-run",
        "baseline_count": len(existing_ids),
        "fuller_verified_total": len(fuller_verified),
        "already_in_qdrant": len(fuller_verified) - len(to_upsert_records),
        "to_upsert": len(to_upsert_records),
        "not_embedded_yet": not_embedded,
        "upserted": len(points) if apply else 0,
        "post_upsert_count": len(existing_ids) + len(points) if apply else None,
        "reconcile": reconcile_result,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _run_reconcile() -> dict:
    """Amendment A §3 F5 gate requires drift 0 — run the existing read-only
    reconciler and fold its verdict into this script's report."""
    proc = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "nae_corpus_reconcile.py"), "--json"],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        parsed = {"raw_stdout": proc.stdout[-2000:]}
    return {"exit_code": proc.returncode, "drift_clean": proc.returncode == 0, **parsed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually upsert into nae_tsu_v1. Refuses (BaselineDriftError) unless the pre-upsert baseline is exactly 3,319 points.",
    )
    args = parser.parse_args()

    report = run(apply=args.apply)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
