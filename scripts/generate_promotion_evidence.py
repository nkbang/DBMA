"""Batch 24-36 Promotion Evidence Package 생성 (READ-ONLY).

C1의 독립 Forensic QA 결과를 전혀 참조하지 않고, CUE가 실제 수행한
Promotion 실행 기록(decisions/, backup 디렉터리, 현재 Production
파일, exception_queue.json, output/final_human_review_candidate.json
등)만을 근거로 evidence를 재계산한다. 이 스크립트는 어떤 파일도
쓰지 않는다(evidence 출력 2개 제외) — Production/decisions/
exception_queue/screening_state는 절대 건드리지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = REPO / "NAE/review/human/evidence"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    dagg = json.loads((REPO / "NAE/corpus/tsu/Dagg_Church_Order/tsu.json").read_text(encoding="utf-8"))
    hiscox = json.loads((REPO / "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json").read_text(encoding="utf-8"))
    dagg_by_id = {r["id"]: r for r in dagg}
    hiscox_by_id = {r["id"]: r for r in hiscox}
    dagg_status = Counter(r["review_status"] for r in dagg)
    hiscox_status = Counter(r["review_status"] for r in hiscox)

    # --- A. Batch accounting ---
    batches = []
    approved_ids: set[str] = set()
    for n in range(24, 37):
        f = REPO / f"NAE/review/human/decisions/batch_{n:04d}_decisions.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        ids = [it["tsu_id"] for it in d]
        approved_ids.update(ids)
        succeeded = sum(1 for t in ids if dagg_by_id.get(t, {}).get("review_status") == "verified")
        backups = sorted((REPO / "NAE/corpus/tsu").glob(f"_batch{n:04d}_promotion_backup_*"))
        before_verified = before_generated = None
        if backups:
            before_data = json.loads((backups[-1] / "Dagg_Church_Order_tsu.json").read_text(encoding="utf-8"))
            bstat = Counter(r["review_status"] for r in before_data)
            before_verified, before_generated = bstat.get("verified", 0), bstat.get("generated", 0)
        batches.append({
            "batch_id": f"batch_{n:04d}",
            "tsu_range": [ids[0], ids[-1]] if ids else None,
            "attempted": len(ids),
            "succeeded": succeeded,
            "failed": len(ids) - succeeded,
            "skipped": 0,
            "promoted_tsu_count": succeeded,
            "verified_before": before_verified,
            "generated_before": before_generated,
            "verified_after": (before_verified + succeeded) if before_verified is not None else None,
            "generated_after": (before_generated - succeeded) if before_generated is not None else None,
        })

    # --- B. Production accounting ---
    production_accounting = {
        "dagg_verified": dagg_status.get("verified", 0),
        "dagg_generated": dagg_status.get("generated", 0),
        "dagg_rejected": dagg_status.get("rejected", 0),
        "hiscox_verified": hiscox_status.get("verified", 0),
        "hiscox_generated": hiscox_status.get("generated", 0),
        "expected": {
            "dagg_verified": 2958, "dagg_generated": 397, "dagg_rejected": 22,
            "hiscox_verified": 361, "hiscox_generated": 379,
        },
    }
    production_accounting["matches_expected"] = all(
        production_accounting[k] == production_accounting["expected"][k]
        for k in production_accounting["expected"]
    )

    # --- C. Promotion set integrity ---
    promoted_ids = {t for t, r in dagg_by_id.items() if t in approved_ids and r["review_status"] == "verified"}

    hr = json.loads((REPO / "output/human_review_required.json").read_text(encoding="utf-8"))
    hr_ids = (
        set(hr["exact_duplicate_discrepancy"]["tsu_ids"])
        | set(hr["theological_review_required"]["tsu_ids"])
        | set(hr["pre_existing_unresolved_exception"]["tsu_ids"])
    )
    hiscox_pkg = json.loads((REPO / "output/hiscox_cue_forensic_package.json").read_text(encoding="utf-8"))
    hiscox_284_ids = {r["tsu_id"] for r in hiscox_pkg["records"]}

    eq = json.loads((REPO / "NAE/review/human/exception_queue.json").read_text(encoding="utf-8"))["entries"]
    unresolved_blocking_ids = {e["tsu_id"] for e in eq if e.get("status") not in ("RESOLVED", "QA_FLAG_NONBLOCKING")}

    set_integrity = {
        "approved_count": len(approved_ids),
        "promoted_count": len(promoted_ids),
        "approved_and_promoted": len(approved_ids & promoted_ids),
        "approved_minus_promoted": sorted(approved_ids - promoted_ids),
        "promoted_minus_approved": sorted(promoted_ids - approved_ids),
        "promoted_and_human_review_required": sorted(promoted_ids & hr_ids),
        "promoted_and_hiscox_284": sorted(promoted_ids & hiscox_284_ids),
        "promoted_and_unresolved_blocking_exception": sorted(promoted_ids & unresolved_blocking_ids),
    }
    set_integrity["PASS"] = (
        set_integrity["approved_and_promoted"] == 1271
        and not set_integrity["approved_minus_promoted"]
        and not set_integrity["promoted_minus_approved"]
        and not set_integrity["promoted_and_human_review_required"]
        and not set_integrity["promoted_and_hiscox_284"]
        and not set_integrity["promoted_and_unresolved_blocking_exception"]
    )

    # --- D. Protected-field integrity ---
    protected_fields = ["source_text", "claim", "doctrine", "id", "author_id", "work_id", "edition_id",
                         "book", "page", "paragraph", "sentence", "source_id", "source_identifier"]
    mutation_violations = []
    for n in range(24, 37):
        backups = sorted((REPO / "NAE/corpus/tsu").glob(f"_batch{n:04d}_promotion_backup_*"))
        if not backups:
            continue
        before = {r["id"]: r for r in json.loads((backups[-1] / "Dagg_Church_Order_tsu.json").read_text(encoding="utf-8"))}
        for tid, before_rec in before.items():
            after_rec = dagg_by_id.get(tid)
            if after_rec is None:
                mutation_violations.append({"tsu_id": tid, "issue": "MISSING_IN_CURRENT_PRODUCTION"})
                continue
            for field in protected_fields:
                if before_rec.get(field) != after_rec.get(field):
                    mutation_violations.append({"tsu_id": tid, "field": field, "batch": f"batch_{n:04d}"})
        break  # 첫 배치의 백업이 이미 이전 전체 상태를 담고 있으므로 1회만 비교하면 충분(아래 최신 백업으로 재확인)

    # 가장 이른 배치(batch_0024) 백업 = Promotion 시작 전 전체 스냅샷 — 이걸 기준으로 전 구간 재검증
    earliest_backup = sorted((REPO / "NAE/corpus/tsu").glob("_batch0024_promotion_backup_*"))[-1]
    before_all = {r["id"]: r for r in json.loads((earliest_backup / "Dagg_Church_Order_tsu.json").read_text(encoding="utf-8"))}
    protected_mutation_full = []
    for tid, before_rec in before_all.items():
        after_rec = dagg_by_id.get(tid)
        if after_rec is None:
            protected_mutation_full.append({"tsu_id": tid, "issue": "MISSING"})
            continue
        for field in protected_fields:
            if before_rec.get(field) != after_rec.get(field):
                protected_mutation_full.append({"tsu_id": tid, "field": field})

    protected_field_integrity = {
        "checked_records": len(before_all),
        "violations": protected_mutation_full[:50],
        "violation_count": len(protected_mutation_full),
        "PASS": len(protected_mutation_full) == 0,
    }

    # --- E. Boundary / leakage integrity ---
    earliest_hiscox_backup = earliest_backup / "Hiscox_Standard_Manual_tsu.json"
    hiscox_before_hash = sha256(earliest_hiscox_backup) if earliest_hiscox_backup.exists() else None
    hiscox_now_hash = sha256(REPO / "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json")

    boundary_integrity = {
        "hiscox_hash_before_batch24": hiscox_before_hash,
        "hiscox_hash_now": hiscox_now_hash,
        "hiscox_mutation": hiscox_before_hash != hiscox_now_hash if hiscox_before_hash else "UNKNOWN",
        "dagg_hiscox_boundary_violation": bool(set(dagg_by_id) & set(hiscox_by_id)),
    }
    boundary_integrity["PASS"] = (
        boundary_integrity["hiscox_mutation"] is False
        and not boundary_integrity["dagg_hiscox_boundary_violation"]
        and len(hr_ids & promoted_ids) == 0
    )

    # --- F. Indexing evidence ---
    sys.path.insert(0, str(REPO))
    from NAE.pipeline.index import indexer  # noqa: E402
    idx_summary = indexer.index_all(dry_run=True)
    identifiers_nonzero = [i for i in idx_summary["identifiers"] if i["indexed"] > 0]
    identifiers_all = [i["identifier"] for i in idx_summary["identifiers"]]
    corpus_identifiers = {"Dagg_Church_Order", "Hiscox_Standard_Manual"}
    backup_dirs_present = [i for i in identifiers_all if i.startswith("_")]

    indexing_evidence = {
        "final_indexed": idx_summary["indexed"],
        "identifiers_nonzero": identifiers_nonzero,
        "only_dagg_hiscox_nonzero": {i["identifier"] for i in identifiers_nonzero} == corpus_identifiers,
        "backup_snapshot_dirs_scanned_but_zero": len(backup_dirs_present),
        "PASS": idx_summary["indexed"] == 3319 and {i["identifier"] for i in identifiers_nonzero} == corpus_identifiers,
    }

    # --- G. Validation (실제 실행) ---
    def run(cmd: list[str]) -> tuple[bool, str]:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
        return r.returncode == 0, r.stdout[-3000:]

    targeted_files = [
        "tests/test_nae_batch_manager.py", "tests/test_c1_cue_reconciliation.py",
        "tests/test_c1_cue_final_disposition.py", "tests/test_indexer_review_gate_wiring.py",
        "tests/test_nae_pilot_human_review_intake.py",
    ]
    ok_tgt, tgt_out = run([sys.executable, "-m", "pytest", "-q", *targeted_files])
    ok_reg, reg_out = run([sys.executable, "-m", "pytest", "-q", "--ignore=output"])
    ok_src, src_out = run([sys.executable, "scripts/source_validator.py"])
    ok_auth, auth_out = run([sys.executable, "scripts/authority_validator.py"])

    def parse_pytest_tail(out: str) -> str:
        for line in reversed(out.strip().splitlines()):
            if "passed" in line or "failed" in line or "error" in line:
                return line.strip()
        return out.strip().splitlines()[-1] if out.strip() else ""

    validation = {
        "targeted_tests": {"PASS": ok_tgt, "summary": parse_pytest_tail(tgt_out)},
        "final_regression": {"PASS": ok_reg, "summary": parse_pytest_tail(reg_out)},
        "source_validator": {"PASS": ok_src, "summary": [l for l in src_out.splitlines() if "결과 요약" in l]},
        "authority_validator": {"PASS": ok_auth, "summary": [l for l in auth_out.splitlines() if "결과 요약" in l]},
        "DRIFT": 0 if (ok_src and ok_auth) else "NONZERO",
    }

    # --- H. Git evidence ---
    def gitcmd(*args: str) -> str:
        return subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO).stdout.strip()

    git_evidence = {
        "branch": gitcmd("rev-parse", "--abbrev-ref", "HEAD"),
        "head_commit": gitcmd("rev-parse", "HEAD"),
        "head_commit_short": gitcmd("rev-parse", "--short", "HEAD"),
        "commit_subject": gitcmd("log", "-1", "--format=%s"),
        "local_vs_remote": gitcmd("log", "origin/dev/dbma-engine..HEAD", "--oneline"),
        "uncommitted_production_diff": gitcmd(
            "diff", "--stat", "--",
            "NAE/corpus/tsu/Dagg_Church_Order/tsu.json",
            "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json",
            "NAE/review/human/exception_queue.json",
            "NAE/review/human/decisions",
        ),
    }
    git_evidence["push_status"] = "UP_TO_DATE" if not git_evidence["local_vs_remote"] else "AHEAD_OF_REMOTE"
    git_evidence["uncommitted_production_changes"] = bool(git_evidence["uncommitted_production_diff"])

    evidence = {
        "generated_at": now(),
        "generated_by": "CUE (independent — no C1 findings referenced)",
        "scope": "Batch 24-36, 1,271 candidates",
        "batch_accounting": batches,
        "production_accounting": production_accounting,
        "promotion_set_integrity": set_integrity,
        "protected_field_integrity": protected_field_integrity,
        "boundary_leakage_integrity": boundary_integrity,
        "indexing_evidence": indexing_evidence,
        "validation": validation,
        "git_evidence": git_evidence,
    }

    overall_gate = all([
        production_accounting["matches_expected"],
        set_integrity["PASS"],
        protected_field_integrity["PASS"],
        boundary_integrity["PASS"],
        indexing_evidence["PASS"],
        validation["targeted_tests"]["PASS"],
        validation["final_regression"]["PASS"],
        validation["source_validator"]["PASS"],
        validation["authority_validator"]["PASS"],
    ])
    evidence["overall_gate"] = "READ_ONLY_EVIDENCE_COMPLETE_PASS" if overall_gate else "READ_ONLY_EVIDENCE_COMPLETE_WITH_FAILURES"

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / "promotion_batch24_36_evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md = f"""# Promotion Evidence Package — Batch 24-36 (1,271건)

작성: CUE 독립 실행 기록 기반(C1 조사 결과 미참조). 생성 시각: {evidence['generated_at']}

## A. Batch Accounting

| Batch | 범위 | attempted | succeeded | failed | skipped | verified(전→후) |
|---|---|---|---|---|---|---|
""" + "\n".join(
        f"| {b['batch_id']} | {b['tsu_range'][0]}~{b['tsu_range'][1]} | {b['attempted']} | {b['succeeded']} | {b['failed']} | {b['skipped']} | {b['verified_before']}→{b['verified_after']} |"
        for b in batches
    ) + f"""

## B. Production Accounting

- Dagg verified: {production_accounting['dagg_verified']} (기대 2958)
- Dagg generated: {production_accounting['dagg_generated']} (기대 397)
- Dagg rejected: {production_accounting['dagg_rejected']} (기대 22)
- Hiscox verified/generated: {production_accounting['hiscox_verified']}/{production_accounting['hiscox_generated']} (기대 361/379)
- **일치 여부: {production_accounting['matches_expected']}**

## C. Promotion Set Integrity

- approved: {set_integrity['approved_count']}, promoted: {set_integrity['promoted_count']}
- approved ∩ promoted: {set_integrity['approved_and_promoted']}
- approved − promoted: {len(set_integrity['approved_minus_promoted'])}
- promoted − approved: {len(set_integrity['promoted_minus_approved'])}
- promoted ∩ HUMAN_REVIEW_REQUIRED(46): {len(set_integrity['promoted_and_human_review_required'])}
- promoted ∩ Hiscox(284): {len(set_integrity['promoted_and_hiscox_284'])}
- promoted ∩ unresolved blocking exception: {len(set_integrity['promoted_and_unresolved_blocking_exception'])}
- **PASS: {set_integrity['PASS']}**

## D. Protected-Field Integrity

- 검사 대상(Batch 24 시작 전 전체 스냅샷 기준): {protected_field_integrity['checked_records']}건
- 위반 건수: {protected_field_integrity['violation_count']}
- **PASS: {protected_field_integrity['PASS']}**

## E. Boundary / Leakage Integrity

- Hiscox mutation: {boundary_integrity['hiscox_mutation']}
- Dagg/Hiscox boundary violation: {boundary_integrity['dagg_hiscox_boundary_violation']}
- **PASS: {boundary_integrity['PASS']}**

## F. Indexing Evidence

- 최종 indexed: {indexing_evidence['final_indexed']} (기대 3319)
- non-zero identifiers: {[i['identifier'] for i in indexing_evidence['identifiers_nonzero']]}
- Dagg/Hiscox만 non-zero: {indexing_evidence['only_dagg_hiscox_nonzero']}
- backup/snapshot 디렉터리(0건으로 정상 스캔됨): {indexing_evidence['backup_snapshot_dirs_scanned_but_zero']}개
- **PASS: {indexing_evidence['PASS']}**

## G. Validation

- targeted tests: {validation['targeted_tests']['summary']} — PASS: {validation['targeted_tests']['PASS']}
- final regression: {validation['final_regression']['summary']} — PASS: {validation['final_regression']['PASS']}
- source_validator: {validation['source_validator']['summary']}
- authority_validator: {validation['authority_validator']['summary']}
- DRIFT: {validation['DRIFT']}

## H. Git Evidence

- branch: {git_evidence['branch']}
- HEAD: {git_evidence['head_commit_short']} ({git_evidence['commit_subject']})
- push status: {git_evidence['push_status']}
- Production/decisions/exception_queue uncommitted diff: {git_evidence['uncommitted_production_changes']}

## Overall Gate

**{evidence['overall_gate']}**
"""
    (EVIDENCE_DIR / "promotion_batch24_36_evidence.md").write_text(md, encoding="utf-8")

    print(json.dumps({
        "production_accounting_PASS": production_accounting["matches_expected"],
        "set_integrity_PASS": set_integrity["PASS"],
        "protected_field_PASS": protected_field_integrity["PASS"],
        "boundary_PASS": boundary_integrity["PASS"],
        "indexing_PASS": indexing_evidence["PASS"],
        "targeted_tests_PASS": validation["targeted_tests"]["PASS"],
        "regression_PASS": validation["final_regression"]["PASS"],
        "regression_summary": validation["final_regression"]["summary"],
        "overall_gate": evidence["overall_gate"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
