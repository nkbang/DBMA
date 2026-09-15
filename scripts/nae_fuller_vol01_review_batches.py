#!/usr/bin/env python3
"""scripts/nae_fuller_vol01_review_batches.py — Fuller Vol.01 TSU Human Review Batch Generator (Phase 2 P1-first).

Reads NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu.json (read-only),
classifies into P1/P2 tiers, sorts P1(id) + P2(id), splits into batches of <=100,
and writes HumanReviewRequest files via NAE.review.human.decision_gate.

Phase 2: P1-first ordering (P1=176 -> batch_0001(100)+batch_0002(76), P2=batch_0003..0037)
Total: 37 batches, 3,643 TSU.

batch_id prefix: fuller_v01_batch_NNNN (0001-0037)
Default: --dry-run (plan only, no writes). Use --apply to write files.
--force: delete existing fuller_v01_batch_* before regenerating.

Each request is enriched (post-process, no decision_gate.py change):
  - source_id / work_id / edition_id filled from M2 (authoritative source_manifest)
  - evidence = canonical.txt context window (+/- 600 chars) around the TSU sentence

Prohibited:
  - Modifying decision_gate.py / batch_manager.py / schema.py / batch_state.json
  - Touching existing requests/batch_00*_requests.json or decisions/
  - Modifying tsu.json, embedding, Qdrant, promote, --apply(ingest)
  - Vol.02-08, baseline 3319 contact
"""
from __future__ import annotations

import argparse
import dataclasses
import glob as glob_mod
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo-root on sys.path (scripts/nae_reference_ingest.py 선례와 동일)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

TSU_PATH = Path("NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu.json")
CANONICAL_TXT = Path("NAE/corpus/canonical/Fuller_Complete_Works_Vol01/canonical.txt")
M2_PATH = Path("NAE/pipeline/registration/state/source_manifest.yaml")
REQUESTS_DIR = Path("NAE/review/human/requests")
MAX_BATCH_SIZE = 100  # MAX_PENDING_REVIEW from schema.py
FULLER_SOURCE_ID = "BAP-MISS-FULLER-VOL01"
CONTEXT_CHARS = 600

# P1 doctrine set
P1_DOCTRINES = {"Baptism", "Confession", "Ecclesiology"}


def load_fuller_identity() -> dict[str, str]:
    """source_id / work_id / edition_id for Fuller Vol.01 from M2 (authoritative)."""
    import yaml

    data = yaml.safe_load(M2_PATH.read_text(encoding="utf-8"))
    for s in data.get("sources", []):
        if s.get("source_id") == FULLER_SOURCE_ID:
            return {
                "source_id": s["source_id"],
                "work_id": s.get("work_id", "") or "",
                "edition_id": s.get("edition_id", "") or "",
            }
    raise SystemExit(f"STOP: {FULLER_SOURCE_ID} not found in M2 {M2_PATH}")


def context_window(source_text: str, canon: str, span: int = CONTEXT_CHARS) -> str:
    """Locate source_text in canonical.txt and return +/- span chars of surrounding
    prose (whitespace-snapped, newlines collapsed). '' if not locatable."""
    st = (source_text or "").strip()
    if not st:
        return ""
    idx = canon.find(st)
    if idx < 0:
        idx = canon.find(st[:40])
    if idx < 0:
        probe = st[len(st) // 3 : len(st) // 3 + 40]
        idx = canon.find(probe) if probe else -1
    if idx < 0:
        return ""
    start = max(0, idx - span)
    end = min(len(canon), idx + len(st) + span)
    while start > 0 and not canon[start].isspace():
        start -= 1
    while end < len(canon) and not canon[end].isspace():
        end += 1
    return " ".join(canon[start:end].split())


def load_and_filter_tsu() -> list[dict]:
    """Load tsu.json, filter review_status='generated', sort by id ascending."""
    data = json.loads(TSU_PATH.read_text(encoding="utf-8"))
    generated = [r for r in data if r.get("review_status") == "generated"]
    generated.sort(key=lambda r: r["id"])
    return generated


def is_p1(record: dict) -> bool:
    """P1 판정: doctrine in {Baptism,Confession,Ecclesiology} OR len(claim)<20."""
    doc = record.get("doctrine") or ""
    claim_len = len(record.get("claim", ""))
    return doc in P1_DOCTRINES or claim_len < 20


def check_name_conflict(batch_id: str) -> bool:
    """Check if a batch file name would conflict with existing files."""
    candidate = REQUESTS_DIR / f"{batch_id}_requests.json"
    return candidate.exists()


def remove_existing_fuller_batches() -> None:
    """Remove existing fuller_v01_batch_*_requests.json files (untracked)."""
    pattern = str(REQUESTS_DIR / "fuller_v01_batch_*_requests.json")
    existing = glob_mod.glob(pattern)
    for fpath in existing:
        Path(fpath).unlink()
        print(f"  Removed: {fpath}")


def write_manifest(tiers_info: dict, cit_ids: list[str]) -> None:
    """Write fuller_v01_MANIFEST.json."""
    manifest = {
        "source": "Fuller_Complete_Works_Vol01",
        "total_tsu": tiers_info["total"],
        "tiers": {
            "P1": {
                "count": tiers_info["p1_count"],
                "batches": tiers_info["p1_batches"],
                "criteria": "doctrine in {Baptism,Confession,Ecclesiology} OR len(claim)<20",
            },
            "P2": {
                "count": tiers_info["p2_count"],
                "batches": tiers_info["p2_batches"],
                "criteria": "default (all remaining)",
            },
        },
        "cit_check_tsu_ids": cit_ids,
        "generated_at": "2026-09-08T00:00:00Z",
        "generator": "scripts/nae_fuller_vol01_review_batches.py --force --apply",
    }
    manifest_path = REQUESTS_DIR / "fuller_v01_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Written: {manifest_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fuller Vol.01 Human Review Batch Generator (Phase 2 P1-first)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write batch files to disk (default: dry-run, plan only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicit no-op alias for default behavior (plan only, no writes)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing fuller_v01_batch_* before regenerating",
    )
    args = parser.parse_args()

    # Load and filter
    records = load_and_filter_tsu()
    total = len(records)
    print(f"=== Fuller Vol.01 TSU Batch Generator (Phase 2 P1-first) ===")
    print(f"Total generated records: {total}")

    if total != 3643:
        print(f"STOP: Expected 3643 generated records, got {total}")
        sys.exit(1)

    # Classify P1/P2
    p1_records = [r for r in records if is_p1(r)]
    p2_records = [r for r in records if not is_p1(r)]
    p1_count = len(p1_records)
    p2_count = len(p2_records)
    print(f"P1 candidates: {p1_count}")
    print(f"P2 candidates: {p2_count}")

    if p1_count != 176:
        print(f"STOP: Expected P1=176, got {p1_count}")
        sys.exit(1)
    if p2_count != 3467:
        print(f"STOP: Expected P2=3467, got {p2_count}")
        sys.exit(1)

    # Sort: P1(id asc) + P2(id asc) -- already sorted by id from load_and_filter_tsu
    ordered = p1_records + p2_records

    # Split into batches (Selection A: P1 pure separation)
    # batch_0001 = P1[:100], batch_0002 = P1[100:] (76), batch_0003.. = P2
    p1_batches = []
    for i in range(0, p1_count, MAX_BATCH_SIZE):
        p1_batches.append(p1_records[i : i + MAX_BATCH_SIZE])

    p2_batches = []
    for i in range(0, p2_count, MAX_BATCH_SIZE):
        p2_batches.append(p2_records[i : i + MAX_BATCH_SIZE])

    # Total batches: len(p1_batches) + len(p2_batches)
    num_batches = len(p1_batches) + len(p2_batches)
    print(f"Batch size limit: {MAX_BATCH_SIZE}")
    print(f"P1 batches: {len(p1_batches)} ({sum(len(b) for b in p1_batches)} TSU)")
    print(f"P2 batches: {len(p2_batches)} ({sum(len(b) for b in p2_batches)} TSU)")
    print(f"Total batches: {num_batches}")

    # Collect all batches with tier info
    all_batches = []
    for batch in p1_batches:
        all_batches.append(("P1", batch))
    for batch in p2_batches:
        all_batches.append(("P2", batch))

    # Check conflicts and plan
    print(f"\n=== Batch Plan ===")
    all_conflicts = False
    for idx, (tier, batch) in enumerate(all_batches, 1):
        batch_id = f"fuller_v01_batch_{idx:04d}"
        first_id = batch[0]["id"]
        last_id = batch[-1]["id"]
        conflict = check_name_conflict(batch_id)
        status = "CONFLICT" if conflict else "OK"
        print(f"  {batch_id} [{tier}]: {len(batch)} TSU [{first_id} .. {last_id}] -> {status}")
        if conflict:
            all_conflicts = True

    if all_conflicts and not args.force:
        print("\nSTOP: Name conflicts detected. Use --force to overwrite.")
        sys.exit(1)

    # Apply or dry-run
    if args.apply:
        from NAE.review.human.decision_gate import build_requests_from_records, write_batch_requests

        # Remove existing fuller batches if --force
        if args.force:
            print(f"\n=== Force: Removing existing fuller_v01_batch_* files ===")
            remove_existing_fuller_batches()

        # Enrichment inputs (M2 provenance + canonical context) — no decision_gate.py change
        identity = load_fuller_identity()
        canon = CANONICAL_TXT.read_text(encoding="utf-8")
        print(f"\nFuller identity: source_id={identity['source_id']} "
              f"work_id={identity['work_id'][:48]}...")
        enrich_hits = 0
        enrich_total = 0

        print(f"\n=== Applying: Writing {num_batches} batch files ===")
        for idx, (tier, batch) in enumerate(all_batches, 1):
            batch_id = f"fuller_v01_batch_{idx:04d}"
            # inject provenance fields so build_requests_from_records() picks them up
            enriched = [
                {**rec, "source_id": identity["source_id"],
                 "work_id": identity["work_id"], "edition_id": identity["edition_id"]}
                for rec in batch
            ]
            reqs = build_requests_from_records(enriched)
            # attach canonical context window as evidence
            out_reqs = []
            for rq, rec in zip(reqs, batch):
                ev = context_window(rec.get("source_text", ""), canon)
                enrich_total += 1
                enrich_hits += 1 if ev else 0
                out_reqs.append(dataclasses.replace(rq, evidence=ev))
            path = write_batch_requests(out_reqs, batch_id)
            print(f"  Written: {path} ({len(out_reqs)} requests) [{tier}]")

        print(f"\nEnrichment: provenance filled for all {enrich_total}; "
              f"canonical context attached to {enrich_hits}/{enrich_total}")

        # Collect citation TSU IDs for manifest
        cit_ids = sorted(
            r["id"]
            for r in records
            if r.get("citations") and len(r.get("citations", [])) > 0
        )

        # Write manifest
        tiers_info = {
            "total": total,
            "p1_count": p1_count,
            "p2_count": p2_count,
            "p1_batches": [f"fuller_v01_batch_{i:04d}" for i in range(1, len(p1_batches) + 1)],
            "p2_batches": [f"fuller_v01_batch_{i:04d}" for i in range(len(p1_batches) + 1, num_batches + 1)],
        }
        print(f"\n=== Writing MANIFEST ===")
        write_manifest(tiers_info, cit_ids)

        # Verify
        import subprocess

        result = subprocess.run(
            ["git", "status", "--porcelain", "NAE/review/human/requests/"],
            capture_output=True, text=True,
        )
        new_files = [l for l in result.stdout.strip().split("\n") if l and l.startswith("??")]
        print(f"\n=== Verification ===")
        print(f"New files in requests/: {len(new_files)}")
        for f in new_files:
            print(f"  {f}")

        # Verify no existing files modified
        result2 = subprocess.run(
            ["git", "diff", "--stat", "NAE/review/human/requests/batch_00*_requests.json"],
            capture_output=True, text=True,
        )
        if result2.stdout.strip():
            print(f"\nWARNING: Existing batch files modified:")
            print(result2.stdout)
        else:
            print("Existing batch_00*_requests.json: no modification")

        # Verify pilot_* unchanged
        result2b = subprocess.run(
            ["git", "diff", "--stat", "NAE/review/human/pilot_*"],
            capture_output=True, text=True,
        )
        if result2b.stdout.strip():
            print(f"\nWARNING: pilot_* files modified:")
            print(result2b.stdout)
        else:
            print("pilot_*: no modification")

        # Verify decisions/ unchanged
        result2c = subprocess.run(
            ["git", "diff", "--stat", "NAE/review/human/decisions/"],
            capture_output=True, text=True,
        )
        if result2c.stdout.strip():
            print(f"\nWARNING: decisions/ files modified:")
            print(result2c.stdout)
        else:
            print("decisions/: no modification")

        # Verify tsu.json unchanged
        result3 = subprocess.run(
            ["git", "diff", "--stat", "NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu.json"],
            capture_output=True, text=True,
        )
        if result3.stdout.strip():
            print(f"\nWARNING: tsu.json modified!")
            print(result3.stdout)
        else:
            print("tsu.json: no modification (read-only confirmed)")

        # Verify unique TSU IDs across all batches
        all_tsu_ids = set()
        for idx, (tier, batch) in enumerate(all_batches, 1):
            for r in batch:
                all_tsu_ids.add(r["id"])
        print(f"Unique TSU IDs across all batches: {len(all_tsu_ids)}")
        if len(all_tsu_ids) != total:
            print(f"STOP: Unique TSU count mismatch! Expected {total}, got {len(all_tsu_ids)}")
            sys.exit(1)

        # Verify batch_0001-0002 are all P1
        p1_check_ok = True
        for idx in [1, 2]:
            tier, batch = all_batches[idx - 1]
            if tier != "P1":
                print(f"STOP: batch_000{idx} is not P1!")
                sys.exit(1)
            for r in batch:
                if not is_p1(r):
                    print(f"STOP: batch_000{idx} contains non-P1 record {r['id']}!")
                    p1_check_ok = False
                    sys.exit(1)
        if p1_check_ok:
            print("batch_0001-0002: all P1 records confirmed")

        print("\nApply complete.")
    else:
        print(f"\n=== Dry-run: No files written. ===")
        print(f"Use --apply to write {num_batches} batch files.")


if __name__ == "__main__":
    main()
