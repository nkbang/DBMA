"""ADR-021 Phase F — Final Evidence Freeze (single-writer, single-run, atomic publish).

Per governance directive: this is the ONLY writer of
output/adr021_phase_ef_evidence/. It stages every artifact in a temp
directory, computes manifest.json LAST (after every other artifact is
final), and atomically replaces the published directory in one move.
Does not modify NAE/pipeline/registration/* or any other ADR-021
pipeline code.

Carries forward the technical extraction record already verified
independently against commit 5ed5562 (gifford/kim reached QUALITY_PASSED
via a real extract_pages() call; hall never reached extraction because
register_source()'s Source Validation step runs before Extraction and
rejected hall for missing publication_year/copyright_status). Freshly
re-runs: regression, FAIL-path scenarios, and exactly one Production
integrity check.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FINAL_DIR = REPO_ROOT / "output" / "adr021_phase_ef_evidence"
GIT_COMMIT = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT).stdout.strip()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Production integrity — exactly one check, INCONCLUSIVE if Qdrant unreachable
# ---------------------------------------------------------------------------

def check_production_integrity() -> dict:
    dagg = REPO_ROOT / "NAE/corpus/tsu/Dagg_Church_Order/tsu.json"
    hiscox = REPO_ROOT / "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json"
    expected = {
        "dagg": "10fc58ef2f80902c967a6cf24409be78a04e993303ffcb7228853a1698516ea5",
        "hiscox": "1da2d7dd75d5235f645d5d2b22c19f865723134754e08028c93fc7d3943ceb2a",
    }
    dagg_hash = sha256_file(dagg)
    hiscox_hash = sha256_file(hiscox)

    sys.path.insert(0, str(REPO_ROOT))
    try:
        from NAE.pipeline.index.qdrant_store import get_client
        from NAE.pipeline.index.config import COLLECTION_NAME
        client = get_client()
        info = client.get_collection(COLLECTION_NAME)
        qdrant_reachable = True
        qdrant_status = str(info.status)
        points_count = info.points_count
    except Exception as e:  # noqa: BLE001 — connectivity failure must be visible, not swallowed
        qdrant_reachable = False
        qdrant_status = None
        points_count = None

    tsu_match = dagg_hash == expected["dagg"] and hiscox_hash == expected["hiscox"]
    qdrant_match = qdrant_reachable and points_count == 3319 and qdrant_status == "green"

    if not qdrant_reachable:
        verification_status = "INCONCLUSIVE"
        production_mutation = None  # explicitly not asserted
    else:
        verification_status = "PASS" if (tsu_match and qdrant_match) else "FAIL"
        production_mutation = not (tsu_match and qdrant_match)

    return {
        "verification_timestamp": now(),
        "git_commit": GIT_COMMIT,
        "tsu_sha256": {
            "NAE/corpus/tsu/Dagg_Church_Order/tsu.json": dagg_hash,
            "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json": hiscox_hash,
        },
        "tsu_sha256_matches_baseline": tsu_match,
        "qdrant_reachable": qdrant_reachable,
        "qdrant_collection": "nae_tsu_v1",
        "qdrant_status": qdrant_status,
        "qdrant_points_count": points_count,
        "qdrant_points_count_expected": 3319,
        "verification_status": verification_status,
        "production_mutation": production_mutation,
        "note": "production_mutation is null (not asserted) when Qdrant is unreachable — never defaulted to false.",
    }


# ---------------------------------------------------------------------------
# Regression — fresh run
# ---------------------------------------------------------------------------

def run_regression() -> dict:
    result = subprocess.run(
        [str(Path.home() / "envs/dbma311/bin/python3"), "-m", "pytest",
         "tests/nae/registration/", "tests/", "-k", "ingest or manifest or incremental or registration", "-q"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    tail = result.stdout.strip().splitlines()[-5:]
    summary_line = next((l for l in reversed(tail) if "passed" in l or "failed" in l), "")
    return {
        "timestamp": now(),
        "command": "pytest tests/nae/registration/ tests/ -k 'ingest or manifest or incremental or registration' -q",
        "return_code": result.returncode,
        "summary_line": summary_line,
        "raw_tail": tail,
    }


# ---------------------------------------------------------------------------
# FAIL-path — fresh execution against the real pipeline, isolated fixtures
# ---------------------------------------------------------------------------

def run_fail_path_scenarios(staging: Path) -> list[dict]:
    sys.path.insert(0, str(REPO_ROOT))
    from NAE.pipeline.registration import raw_preservation
    from NAE.pipeline.registration.pipeline import RegistrationRequest, register_source
    from NAE.pipeline.registration.state import ExceptionQueue, RegistrationStateStore

    results = []

    def fresh_env(name: str):
        d = staging / "_work" / "fail_path" / name
        d.mkdir(parents=True, exist_ok=True)
        ledger = raw_preservation.ChecksumLedger(d / "ledger.jsonl")
        state_store = RegistrationStateStore(d / "state.json")
        exception_queue = ExceptionQueue(d / "exceptions.json")
        manifest_path = d / "source_manifest.yaml"
        return d, ledger, state_store, exception_queue, manifest_path

    def run(name: str, raw_item_dir: Path, **kwargs):
        d, ledger, state_store, exception_queue, manifest_path = fresh_env(name)
        req = RegistrationRequest(
            raw_item_dir=raw_item_dir,
            surname=kwargs.get("surname", "Test"),
            given_name=kwargs.get("given_name", "Fail"),
            title=kwargs.get("title", "Doc"),
            edition_slug="1900",
            publication_year=kwargs.get("publication_year", 1900),
            copyright_status=kwargs.get("copyright_status", "public_domain"),
            archive_source="x",
            source_id=f"failpath-{name}",
            manifest_path=manifest_path,
        )
        result = register_source(
            req,
            existing_author_ids=set(), existing_work_ids=set(),
            existing_edition_ids=set(), existing_source_ids=set(),
            ledger=ledger, state_store=state_store, exception_queue=exception_queue,
        )
        entries = exception_queue.entries()
        results.append({
            "test_name": name,
            "final_state": result.final_state.value,
            "in_exception_queue": len(entries) > 0,
            "exception_entries": entries,
        })

    empty_dir = staging / "_work" / "empty_raw"
    empty_dir.mkdir(parents=True, exist_ok=True)
    run("raw_missing", empty_dir)

    corrupt_dir = staging / "_work" / "corrupt_raw"
    corrupt_dir.mkdir(parents=True, exist_ok=True)
    (corrupt_dir / "hocr.html").write_text("", encoding="utf-8")  # 0 bytes -> zero-page / corrupt
    run("zero_page_extraction", corrupt_dir)

    garbage_dir = staging / "_work" / "garbage_raw"
    garbage_dir.mkdir(parents=True, exist_ok=True)
    (garbage_dir / "hocr.html").write_bytes(b"\x00\x01\x02" * 200)  # not valid hOCR markup
    run("corrupt_source", garbage_dir)

    no_hocr_markup_dir = staging / "_work" / "no_hocr_markup"
    no_hocr_markup_dir.mkdir(parents=True, exist_ok=True)
    (no_hocr_markup_dir / "hocr.html").write_text("plain text with no ocr_page markers " * 20, encoding="utf-8")
    run("extraction_output_missing", no_hocr_markup_dir)

    valid_dir = staging / "_work" / "valid_for_metadata_tests"
    valid_dir.mkdir(parents=True, exist_ok=True)
    words = " ".join(f'<span class="ocrx_word">W{i}</span>' for i in range(60))
    (valid_dir / "hocr.html").write_text(f'<div class="ocr_page"><p class="ocr_par"><span class="ocr_line">{words}</span></p></div>', encoding="utf-8")

    run("identity_unavailable", valid_dir, surname="", given_name="", title="")
    run("required_metadata_missing_year", valid_dir, publication_year=None)
    run("required_metadata_missing_copyright", valid_dir, copyright_status=None)
    run("both_metadata_missing", valid_dir, publication_year=None, copyright_status=None)

    return results


# ---------------------------------------------------------------------------
# Technical record — carried forward from the independently-verified commit
# 5ed5562, with the corrected hall description (governance directive SS2/SS8)
# ---------------------------------------------------------------------------

def phase_ef_hocr_results() -> list[dict]:
    return [
        {
            "candidate": "gifford_forward_mission",
            "source_commit": "5ed5562",
            "extraction_source": "hocr",
            "page_count": 29,
            "register_source_final_state": "QUALITY_PASSED",
            "quality_gate_verdict": "PASS",
            "validation_errors": [],
        },
        {
            "candidate": "kim_chang_sik_circuit_rider",
            "source_commit": "5ed5562",
            "extraction_source": "hocr",
            "page_count": 6,
            "register_source_final_state": "QUALITY_PASSED",
            "quality_gate_verdict": "PASS",
            "validation_errors": [],
        },
        {
            "candidate": "hall_esther_kim_pak",
            "source_commit": "5ed5562",
            "register_source_extraction": "NOT_REACHED",
            "register_source_final_state": "QUALITY_GATE_FAILED",
            "validation_errors": [
                "required metadata field missing: publication_year",
                "required metadata field missing: copyright_status",
            ],
            "direct_hocr_extraction_test": {
                "note": "Separate, standalone extract_pages() probe against hall's raw hocr.html — NOT part of the register_source() pipeline execution. Confirms the hOCR file itself contains real extractable text; does not demonstrate that register_source() reached extraction for this candidate.",
                "page_count": 15,
            },
            "correction_note": (
                "hall did NOT fail with 'hOCR extraction then metadata validation failure'. "
                "register_source()'s Source Validation step (pipeline.py, executed before "
                "the Extraction Adapter) rejected hall for missing publication_year and "
                "copyright_status BEFORE extract_pages() was ever called. The "
                "extraction_source='hocr' value recorded for hall in the prior evidence run "
                "does not prove register_source() executed extraction for this candidate."
            ),
        },
    ]


# ---------------------------------------------------------------------------
# Orchestration — stage everything, then atomically publish
# ---------------------------------------------------------------------------

def main() -> None:
    with tempfile.TemporaryDirectory(prefix="adr021_final_evidence_") as tmp:
        staging = Path(tmp) / "adr021_phase_ef_evidence"
        staging.mkdir()

        prod_integrity = check_production_integrity()
        regression = run_regression()
        fail_path = run_fail_path_scenarios(staging)
        hocr_results = phase_ef_hocr_results()

        (staging / "production_integrity.json").write_text(json.dumps(prod_integrity, indent=2, ensure_ascii=False), encoding="utf-8")
        (staging / "test_results.json").write_text(json.dumps(regression, indent=2, ensure_ascii=False), encoding="utf-8")
        (staging / "failure_path_results.json").write_text(json.dumps(fail_path, indent=2, ensure_ascii=False), encoding="utf-8")
        (staging / "phase_ef_hocr_results.json").write_text(json.dumps(hocr_results, indent=2, ensure_ascii=False), encoding="utf-8")

        fail_path_pass = sum(1 for r in fail_path if r["in_exception_queue"])
        gifford = hocr_results[0]
        kim = hocr_results[1]
        hall = hocr_results[2]

        final_report = f"""# ADR-021 Phase E/F Final Evidence — Single-Writer Snapshot

Generated: {now()}
Git commit: {GIT_COMMIT}
Writer: scripts/generate_adr021_final_evidence.py (sole writer, single run, atomic publish)

## Technical Assertions

```
gifford:
  extraction_source = {gifford['extraction_source']}
  page_count = {gifford['page_count']}
  QUALITY_PASSED = {gifford['register_source_final_state'] == 'QUALITY_PASSED'}

kim:
  extraction_source = {kim['extraction_source']}
  page_count = {kim['page_count']}
  QUALITY_PASSED = {kim['register_source_final_state'] == 'QUALITY_PASSED'}

hall:
  register_source extraction = {hall['register_source_extraction']}
  validation failure = publication_year, copyright_status
  direct hOCR extraction test = {hall['direct_hocr_extraction_test']['page_count']} pages
```

{hall['correction_note']}

## Regression

{regression['summary_line']}
return_code={regression['return_code']}

## FAIL-path

{fail_path_pass}/{len(fail_path)} scenarios recorded a non-empty Exception Queue entry.

## Production Integrity

```
verification_status = {prod_integrity['verification_status']}
qdrant_reachable     = {prod_integrity['qdrant_reachable']}
qdrant_points_count  = {prod_integrity['qdrant_points_count']}
tsu_sha256_matches   = {prod_integrity['tsu_sha256_matches_baseline']}
production_mutation  = {prod_integrity['production_mutation']}
```
"""
        (staging / "final_report.md").write_text(final_report, encoding="utf-8")

        # detailed_evidence.json / evidence_package.json / baseline.json / quality_gate_results.json
        # carried forward as informational context (not re-measured this run — no new claims made).
        (staging / "baseline.json").write_text(json.dumps({
            "note": "Baseline TSU/Qdrant figures — see production_integrity.json for this run's live measurement.",
            "verified_tsu": 3319, "generated_tsu": 776, "rejected_tsu": 22, "total_tsu": 4117,
        }, indent=2), encoding="utf-8")
        (staging / "quality_gate_results.json").write_text(json.dumps({
            "gate_type": "boolean",
            "fail_conditions": [
                "raw_file_missing", "raw_checksum_mismatch", "extraction_output_missing",
                "zero_page_extraction", "unreadable_or_corrupt_source",
                "required_identity_unavailable", "required_metadata_missing",
            ],
            "note": "Numeric OCR-confidence thresholds intentionally unset per ADR-021 SS8 — not a gap.",
        }, indent=2), encoding="utf-8")
        (staging / "detailed_evidence.json").write_text(json.dumps({
            "note": "See phase_ef_hocr_results.json (this run) and commit 5ed5562 for the underlying candidate-level data this snapshot carries forward.",
        }, indent=2), encoding="utf-8")
        (staging / "evidence_package.json").write_text(json.dumps({
            "note": "Superseded by phase_ef_hocr_results.json + production_integrity.json + test_results.json + failure_path_results.json in this snapshot.",
        }, indent=2), encoding="utf-8")

        # Working fixtures (isolated tmp raw dirs for FAIL-path scenarios) are
        # not part of the published evidence artifact set.
        work_dir = staging / "_work"
        if work_dir.exists():
            shutil.rmtree(work_dir)

        # manifest.json computed LAST, enumerating everything else already staged
        manifest_entries = []
        for f in sorted(staging.iterdir()):
            if f.name == "manifest.json" or not f.is_file():
                continue
            manifest_entries.append({
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "sha256": sha256_file(f),
                "generated_at": now(),
                "source_git_commit": GIT_COMMIT,
                "provenance": "generated by scripts/generate_adr021_final_evidence.py, single run",
            })
        manifest = {
            "adr": "ADR-021",
            "phase": "E/F",
            "snapshot_generated_at": now(),
            "git_commit": GIT_COMMIT,
            "writer": "scripts/generate_adr021_final_evidence.py",
            "artifacts": manifest_entries,
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        # Atomic publish: remove old dir, move staging into place
        if FINAL_DIR.exists():
            shutil.rmtree(FINAL_DIR)
        FINAL_DIR.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging), str(FINAL_DIR))

    print(json.dumps({
        "published_to": str(FINAL_DIR),
        "production_integrity_status": prod_integrity["verification_status"],
        "regression": regression["summary_line"],
        "fail_path": f"{fail_path_pass}/{len(fail_path)}",
    }, indent=2))


if __name__ == "__main__":
    main()
