"""scripts/nae_corpus_reconcile.py — NAE Corpus Reconciliation Tool (skeleton).

read-only. --apply 없음.

대상 관계: M2 ↔ incremental_state.json ↔ tsu.json::review_status ↔ Qdrant count
(ADR §9.3.4 / M-4).

Qdrant 미기동 → "unreachable" 명시적 출력, 나머지 3자 대조만 수행.

사용례:
    python scripts/nae_corpus_reconcile.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml

# ── Paths ────────────────────────────────────────────────────────────────────

M2_PATH = PROJECT_ROOT / "NAE" / "pipeline" / "registration" / "state" / "source_manifest.yaml"
INCREMENTAL_STATE = PROJECT_ROOT / "NAE" / "pipeline" / "ingest" / "state" / "incremental_state.json"
TSU_DIR = PROJECT_ROOT / "NAE" / "corpus" / "tsu"

# Qdrant (unreachable in current environment)
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "nae_tsu_v1"


class ReconciliationResult:
    def __init__(self) -> None:
        self.m2_count: int = 0
        self.incremental_count: int = 0
        self.tsu_count: int = 0
        self.qdrant_status: str = "unreachable"
        self.qdrant_count: int = 0
        self.discrepancies: list[str] = []

    def print_report(self) -> None:
        print("=" * 70)
        print("NAE Corpus Reconciliation Report (skeleton — read-only)")
        print("=" * 70)
        print(f"  M2 (source_manifest.yaml):    {self.m2_count} sources")
        print(f"  Incremental state:             {self.incremental_count} entries")
        print(f"  TSU (tsu.json review_status):  {self.tsu_count} records")
        print(f"  Qdrant ({QDRANT_COLLECTION}):     {self.qdrant_status}")
        if self.qdrant_status != "unreachable":
            print(f"    points_count:                {self.qdrant_count}")
        print("-" * 70)
        if self.discrepancies:
            print("\n[DISCREPANCIES]")
            for d in self.discrepancies:
                print(f"  ! {d}")
        else:
            print("\nNo discrepancies detected.")
        print("=" * 70)


def count_m2_sources() -> int:
    if not M2_PATH.exists():
        return 0
    data = yaml.safe_load(M2_PATH.read_text(encoding="utf-8"))
    return len(data.get("sources", []))


def count_incremental_state() -> int:
    if not INCREMENTAL_STATE.exists():
        return 0
    with open(INCREMENTAL_STATE) as f:
        data = json.load(f)
    if isinstance(data, dict):
        return len(data)
    elif isinstance(data, list):
        return len(data)
    return 0


def count_tsu_records() -> int:
    """Count TSU records across all canonical subdirectories."""
    total = 0
    if not TSU_DIR.exists():
        return 0
    for tsu_subdir in TSU_DIR.iterdir():
        if not tsu_subdir.is_dir() or tsu_subdir.name.startswith("_"):
            continue
        tsu_json = tsu_subdir / "tsu.json"
        if tsu_json.exists():
            with open(tsu_json) as f:
                data = json.load(f)
            # tsu.json is a list of records, not {"records": [...]}
            if isinstance(data, list):
                total += len(data)
            elif isinstance(data, dict):
                total += len(data.get("records", []))
    return total


def probe_qdrant() -> tuple[str, int]:
    """Probe Qdrant. Returns (status, count)."""
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        info = client.get_collection(QDRANT_COLLECTION)
        return ("reachable", info.points_count)
    except Exception:
        return ("unreachable", 0)


def reconcile() -> ReconciliationResult:
    result = ReconciliationResult()

    # Count sources
    result.m2_count = count_m2_sources()
    result.incremental_count = count_incremental_state()
    result.tsu_count = count_tsu_records()

    # Probe Qdrant
    result.qdrant_status, result.qdrant_count = probe_qdrant()

    # Check discrepancies (3-way comparison)
    if result.m2_count != result.incremental_count:
        result.discrepancies.append(
            f"M2 ({result.m2_count}) != incremental_state ({result.incremental_count})"
        )
    if result.m2_count != result.tsu_count:
        result.discrepancies.append(
            f"M2 ({result.m2_count}) != TSU records ({result.tsu_count})"
        )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    args = parser.parse_args()
    result = reconcile()
    result.print_report()
    return 1 if result.discrepancies else 0


if __name__ == "__main__":
    raise SystemExit(main())
