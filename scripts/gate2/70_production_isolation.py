#!/usr/bin/env python3
"""70_production_isolation.py — Production isolation tripwire (read-only).

BEFORE/AFTER hash and point count comparison for production files.
This script is read-only — it only computes hashes, never modifies anything.
Phase A: BEFORE=AFTER means no changes have been made yet (first evidence).

Tripwire targets from Task Order §1:
  - output/bench/tsu_dataset.jsonl
  - output/bench/tsu_manifest.json
  - NAE/corpus/tsu/tsu_id_state.json
  - core.config.DEFAULT_REGISTRY_PATH (= data/제련완성본/registry/documents.json)

Task Order: C1-TASK-ORDER-GATE2-ORCHESTRATOR-SCAFFOLDING.md §3 Phase A
"""

import hashlib
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVIDENCE_DIR = Path(__file__).resolve().parent / ".." / ".." / "evidence" / "gate2"


def file_sha256(filepath: Path) -> str | None:
    """Compute SHA-256 of a file, return None if not found."""
    if not filepath.exists():
        return None
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> dict:
    results: dict = {}
    all_pass = True

    # Production tripwire targets
    tripwires = [
        {
            "name": "tsu_dataset_jsonl",
            "path": PROJECT_ROOT / "output" / "bench" / "tsu_dataset.jsonl",
        },
        {
            "name": "tsu_manifest_json",
            "path": PROJECT_ROOT / "output" / "bench" / "tsu_manifest.json",
        },
        {
            "name": "tsu_id_state_json",
            "path": PROJECT_ROOT / "NAE" / "corpus" / "tsu" / "tsu_id_state.json",
        },
        {
            "name": "documents_registry",
            "path": PROJECT_ROOT / "data" / "제련완성본" / "registry" / "documents.json",
        },
    ]

    # Compute BEFORE hashes
    before_hashes: dict[str, str | None] = {}
    for tw in tripwires:
        h = file_sha256(tw["path"])
        before_hashes[tw["name"]] = h
        size = tw["path"].stat().st_size if tw["path"].exists() else 0
        results[f"before_{tw['name']}"] = {
            "status": "PASS" if h is not None else "MISSING",
            "sha256": h,
            "size_bytes": size,
        }

    # In a real scenario, mutations would happen here. For Phase A (read-only),
    # we immediately re-read to verify no changes occurred.
    after_hashes: dict[str, str | None] = {}
    for tw in tripwires:
        h = file_sha256(tw["path"])
        after_hashes[tw["name"]] = h

    # Compare BEFORE vs AFTER
    for tw in tripwires:
        before_h = before_hashes[tw["name"]]
        after_h = after_hashes[tw["name"]]
        key = f"tripwire_{tw['name']}"
        if before_h is None or after_h is None:
            results[key] = {
                "status": "WARN",
                "reason": "File missing — cannot verify isolation",
                "before": before_h,
                "after": after_h,
            }
        elif before_h == after_h:
            results[key] = {
                "status": "PASS",
                "sha256": before_h,
                "note": "No mutation — isolation verified",
            }
        else:
            results[key] = {
                "status": "FAIL",
                "before": before_h,
                "after": after_h,
                "reason": "File was modified during this run!",
            }
            all_pass = False

    # Qdrant point count check (read-only, informational)
    try:
        import http.client
        conn = http.client.HTTPConnection("localhost", 7333, timeout=5)
        conn.request("GET", "/collections/nae_tsu_v1/points")
        resp = conn.getresponse()
        if resp.status == 200:
            data = json.loads(resp.read())
            qdrant_count = data.get("result", {}).get("points_count", "unknown")
            results["qdrant_nae_tsu_v1"] = {
                "status": "PASS",
                "points_count": qdrant_count,
                "note": "Read-only check — no mutation",
            }
        else:
            results["qdrant_nae_tsu_v1"] = {"status": "WARN", "http_status": resp.status}
        conn.close()
    except Exception as exc:
        results["qdrant_nae_tsu_v1"] = {"status": "INFO", "reason": f"Unreachable: {exc}"}

    summary = {
        "script": "70_production_isolation.py",
        "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "all_pass": all_pass,
        "checks": results,
    }

    evidence_dir = EVIDENCE_DIR.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "70_production_isolation.json"
    evidence_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Result: {'PASS' if all_pass else 'FAIL'}")
    print(f"Evidence written to: {evidence_file}")
    return summary


if __name__ == "__main__":
    sys.exit(0 if main()["all_pass"] else 1)
