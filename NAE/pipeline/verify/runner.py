"""Phase 3.5 - Knowledge Verification Layer orchestrator.

Default pass: duplicate detection + citation consistency + evidence format
check + score decomposition. Contradiction detection (contradiction.py) is
NOT run here by default - it is opt-in, expensive, and imprecise; call
NAE.pipeline.verify.contradiction.find_contradictions() explicitly if needed.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from NAE.pipeline.tsu import config as tsu_config

from . import config, duplicate, score

logger = logging.getLogger("nae.verify.runner")


def load_tsu_records(identifier: str, tsu_root: Path = tsu_config.TSU_ROOT) -> list[dict]:
    path = tsu_root / identifier / "tsu.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def verify_identifier(identifier: str, *, tsu_root: Path = tsu_config.TSU_ROOT) -> dict[str, Any]:
    records = load_tsu_records(identifier, tsu_root)
    if not records:
        return {"identifier": identifier, "records": [], "report": {
            "identifier": identifier, "status": "no_records",
            "verify_version": config.VERIFY_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }}

    duplicates = duplicate.find_duplicates(records)

    verified_records = []
    for record in records:
        scores = score.compute_scores(record)
        enriched = {
            **record,
            **scores,
            "duplicate_of": duplicates.get(record["id"]),
        }
        verified_records.append(enriched)

    out_dir = tsu_root / identifier
    with open(out_dir / "tsu_verified.json", "w", encoding="utf-8") as fh:
        json.dump(verified_records, fh, ensure_ascii=False, indent=2)

    overall_scores = [r["overall_score"] for r in verified_records if r["overall_score"] is not None]
    report = {
        "identifier": identifier,
        "status": "ok",
        "verify_version": config.VERIFY_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records_verified": len(verified_records),
        "duplicates_found": len(duplicates),
        "average_overall_score": round(sum(overall_scores) / len(overall_scores), 3) if overall_scores else None,
        "note": "contradiction detection is opt-in and not included in this pass "
                "(see NAE.pipeline.verify.contradiction)",
    }
    with open(out_dir / "verify_report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    return {"identifier": identifier, "records": verified_records, "report": report}


def verify_all(*, tsu_root: Path = tsu_config.TSU_ROOT) -> dict[str, Any]:
    if not tsu_root.exists():
        return {"processed": 0, "identifiers": []}
    identifiers = [d.name for d in tsu_root.iterdir() if d.is_dir()]
    summary = {"processed": 0, "identifiers": []}
    for identifier in identifiers:
        result = verify_identifier(identifier, tsu_root=tsu_root)
        summary["processed"] += 1
        summary["identifiers"].append({"identifier": identifier, "status": result["report"]["status"]})
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NAE Knowledge Verification Layer")
    parser.add_argument("--identifier", help="Verify a single identifier only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.identifier:
        result = verify_identifier(args.identifier)
        print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    else:
        print(json.dumps(verify_all(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
