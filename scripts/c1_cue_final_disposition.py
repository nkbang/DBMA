"""1,601 승인 후보에서 (1) C1 exact-duplicate discrepancy 9건, (2) C1
theological-review 대상 32건, (3) C1 evidence가 전혀 없는 Hiscox 284건을
제외해 실질 FINAL_HUMAN_REVIEW_CANDIDATE를 재계산한다.

READ-ONLY. Production/decisions/exception_queue 등 어떤 파일도 쓰지
않는다 — output/ 산출물만 생성한다. Human Decision을 생성하지 않고
Promotion을 실행하지 않는다.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "output"


def load_1601_candidates() -> tuple[set[str], set[str]]:
    """(clear_ids, qa_only_ids) — 항상 분리 보존(지시 5절)."""
    sweep = json.loads((REPO_ROOT / "NAE/review/human/screening_sweep_report.json").read_text(encoding="utf-8"))
    clear_ids = set(sweep["approval_candidates"])

    eq = json.loads((REPO_ROOT / "NAE/review/human/exception_queue.json").read_text(encoding="utf-8"))["entries"]
    sweep_entries = [e for e in eq if e.get("disposition_basis", "").startswith("automated_screening_sweep")]
    by_tsu: dict[str, set[str]] = defaultdict(set)
    for e in sweep_entries:
        by_tsu[e["tsu_id"]].add(e["status"])
    qa_only_ids = {t for t, s in by_tsu.items() if s == {"QA_FLAG_NONBLOCKING"}}
    return clear_ids, qa_only_ids


def main() -> None:
    clear_ids, qa_only_ids = load_1601_candidates()
    candidates_1601 = clear_ids | qa_only_ids
    assert len(candidates_1601) == 1601, f"expected 1601, got {len(candidates_1601)}"

    dagg = json.loads((REPO_ROOT / "NAE/corpus/tsu/Dagg_Church_Order/tsu.json").read_text(encoding="utf-8"))
    hiscox = json.loads((REPO_ROOT / "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json").read_text(encoding="utf-8"))
    dagg_ids = {r["id"] for r in dagg}
    hiscox_ids = {r["id"] for r in hiscox}
    dagg_by_id = {r["id"]: r for r in dagg}
    hiscox_by_id = {r["id"]: r for r in hiscox}

    recon = json.loads((OUT / "c1_cue_reconciliation.json").read_text(encoding="utf-8"))
    recs = {r["tsu_id"]: r for r in recon["records"]}

    dup9 = {tid for tid, r in recs.items() if r["reconciliation_status"] == "C1_CUE_DISCREPANCY"}
    theo32 = {tid for tid, r in recs.items() if r["reconciliation_status"] == "HUMAN_THEOLOGICAL_REVIEW_REQUIRED"}

    hiscox_candidates = candidates_1601 & hiscox_ids
    dagg_candidates = candidates_1601 & dagg_ids

    # 1. exact-duplicate 9건 영구 제외
    excluded_duplicates = dup9 & candidates_1601
    # 2. theological-review 대상(dagg_candidates 안에 있는 것만 — 정의상 전부 Dagg)
    excluded_theological = theo32 & candidates_1601
    # 3. Hiscox 전체(C1 evidence 없음)
    excluded_hiscox = hiscox_candidates

    excluded_union = excluded_duplicates | excluded_theological | excluded_hiscox
    final_candidates = candidates_1601 - excluded_union

    # QA/CLEAR 구분 보존
    final_clear = final_candidates & clear_ids
    final_qa = final_candidates & qa_only_ids
    assert final_clear | final_qa == final_candidates
    assert final_clear & final_qa == set()

    human_review_required_ids = excluded_duplicates | excluded_theological

    def rec_summary(tid: str) -> dict:
        r = recs.get(tid, {})
        return {
            "tsu_id": tid,
            "corpus": "Dagg_Church_Order" if tid in dagg_ids else "Hiscox_Standard_Manual",
            "was_candidate_type": "SCREENING_CLEAR" if tid in clear_ids else "QA_FLAG_NONBLOCKING",
            "exclusion_reason": r.get("reconciliation_status", "N/A"),
            "c1_evidence_categories": r.get("c1_disposition", []),
        }

    final_human_review_required = {
        "generated_at": "2026-08-11",
        "total": len(human_review_required_ids),
        "exact_duplicate_discrepancy": {
            "count": len(excluded_duplicates),
            "tsu_ids": sorted(excluded_duplicates),
            "reason": "C1 corpus-wide exact-match scan found non-adjacent duplicate claims that CUE's adjacent-pair-only screening missed",
        },
        "theological_review_required": {
            "count": len(excluded_theological),
            "tsu_ids": sorted(excluded_theological),
            "reason": "SEMANTIC_DUPLICATE(31, within 1,601 candidate scope) per C1 evidence — never auto-approvable per instruction 6. Note: TSU-0001756(THEOLOGICAL_WEAKENING) is separately already Promoted(verified) prior to this sweep and outside the 2,047-TSU generated-pool scope; not part of this 40-item queue.",
        },
        "records": [rec_summary(t) for t in sorted(human_review_required_ids)],
    }

    final_candidate_package = {
        "generated_at": "2026-08-11",
        "total": len(final_candidates),
        "screening_clear": {"count": len(final_clear), "tsu_ids": sorted(final_clear)},
        "qa_flag_nonblocking": {"count": len(final_qa), "tsu_ids": sorted(final_qa)},
        "scope": "Dagg_Church_Order only — C1-verified, no discrepancy, no theological-review flag",
        "excluded_from_1601": {
            "exact_duplicate_discrepancy": len(excluded_duplicates),
            "theological_review_required": len(excluded_theological),
            "hiscox_pending_independent_verification": len(excluded_hiscox),
            "total_excluded": len(excluded_union),
        },
    }

    # Hiscox 282(clear) + 2(QA) 별도 forensic package — CUE 자체 evidence만 (C1 없음)
    def hiscox_cue_evidence(tid: str) -> dict:
        rec = hiscox_by_id[tid]
        r = recs.get(tid, {})
        return {
            "tsu_id": tid,
            "candidate_type": "SCREENING_CLEAR" if tid in clear_ids else "QA_FLAG_NONBLOCKING",
            "review_status": rec.get("review_status"),
            "doctrine": rec.get("doctrine"),
            "cue_disposition": r.get("cue_disposition", "SCREENING_CLEAR"),
            "cue_evidence": r.get("cue_evidence", []),
            "c1_independent_verification": "NOT_PERFORMED — Hiscox_Standard_Manual is outside all 10 C1 audit files' scope (corpus=Dagg_Church_Order only)",
        }

    hiscox_package = {
        "generated_at": "2026-08-11",
        "corpus": "Hiscox_Standard_Manual",
        "total": len(hiscox_candidates),
        "screening_clear_count": len(hiscox_candidates & clear_ids),
        "qa_flag_nonblocking_count": len(hiscox_candidates & qa_only_ids),
        "status": "NOT APPROVED — excluded from FINAL_HUMAN_REVIEW_CANDIDATE pending independent (C1 or equivalent) verification of Hiscox corpus",
        "records": [hiscox_cue_evidence(t) for t in sorted(hiscox_candidates)],
    }

    (OUT / "final_human_review_candidate.json").write_text(
        json.dumps(final_candidate_package, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "human_review_required.json").write_text(
        json.dumps(final_human_review_required, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "hiscox_cue_forensic_package.json").write_text(
        json.dumps(hiscox_package, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps({
        "input_1601": len(candidates_1601),
        "excluded_duplicates_9": len(excluded_duplicates),
        "excluded_theological_32": len(excluded_theological),
        "excluded_hiscox": len(excluded_hiscox),
        "excluded_total_union": len(excluded_union),
        "FINAL_HUMAN_REVIEW_CANDIDATE": len(final_candidates),
        "  screening_clear": len(final_clear),
        "  qa_flag_nonblocking": len(final_qa),
        "HUMAN_REVIEW_REQUIRED": len(human_review_required_ids),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
