"""C1 <-> CUE Forensic Reconciliation (NAE Pilot 001 확장, 2026-08-11).

READ-ONLY. Production/decisions/exception_queue/screening_state 등 어떤
파일도 쓰지 않는다 — 오직 `output/c1_cue_reconciliation*.json`과
`output/c1_cue_reconciliation_report.md`만 생성한다. 새 Human Decision을
생성하지 않으며, Promotion을 실행하지 않는다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "output"


def _load(name: str) -> Any:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def build_c1_evidence() -> dict[str, dict[str, list[dict]]]:
    """tsu_id -> {category: [evidence dict, ...]}"""
    ev: dict[str, dict[str, list[dict]]] = {}

    def add(tid: str, category: str, detail: dict):
        ev.setdefault(tid, {}).setdefault(category, []).append(detail)

    # 1. CJK/foreign-language contamination — Dagg 전체, full coverage
    cjk = _load("c1_cjk_contamination.json")
    for e in cjk["detailed_entries"]:
        add(e["tsu_id"], "CJK_FOREIGN_CONTAMINATION", {
            "source": "c1_cjk_contamination.json", "status_at_audit": e.get("status"),
            "cjk_found": e.get("cjk_found"),
        })

    # 2. Duplicate claims — Dagg 전체, full coverage(exact) / semantic
    dup = _load("c1_duplicate_claims.json")
    for pair in dup["exact_duplicates"]["pairs"]:
        for tid in pair["tsu_ids"]:
            add(tid, "EXACT_DUPLICATE", {"source": "c1_duplicate_claims.json", "pair": pair["tsu_ids"], "claim": pair["claim"]})
    for pair in dup["semantic_duplicates"]["pairs"]:
        for tid in (pair["tsu_a"], pair["tsu_b"]):
            add(tid, "SEMANTIC_DUPLICATE", {"source": "c1_duplicate_claims.json", "pair": [pair["tsu_a"], pair["tsu_b"]], "similarity": pair.get("similarity")})

    # 3. Adjacent overlap — SAMPLE ONLY (30/44 entries persisted)
    adj = _load("c1_adjacent_overlap.json")
    for e in adj["detailed_entries"]:
        for tid in (e["tsu_a"], e["tsu_b"]):
            add(tid, "ADJACENT_CONTEXT_OVERLAP", {"source": "c1_adjacent_overlap.json (SAMPLE 30/44)", "pair": [e["tsu_a"], e["tsu_b"]], "overlap_ratio": e.get("overlap_ratio")})

    # 4. Hedge / theological distortion — scope: verified_tsus_audited only (1149건, generated pool과 대부분 비중첩)
    hedge = _load("c1_hedge_distortion.json")
    for e in hedge["detailed_entries"]:
        add(e["tsu_id"], "THEOLOGICAL_WEAKENING", {"source": "c1_hedge_distortion.json", "distortion_type": e.get("distortion_type"), "audited_scope": "verified_tsus_only(1149)"})

    # 5. OCR artifacts — SAMPLE ONLY (30/98 entries persisted)
    ocr = _load("c1_ocr_artifacts.json")
    for e in ocr["detailed_entries"]:
        add(e["tsu_id"], "OCR_ARTIFACT", {"source": "c1_ocr_artifacts.json (SAMPLE 30/98)", "artifacts_found": list(e.get("artifacts_found", {}).keys())})

    # 6. Boundary/segmentation — SAMPLE ONLY (10/291 truncated examples persisted)
    bnd = _load("c1_boundary_analysis.json")
    for e in bnd.get("truncated_examples", []):
        add(e["tsu_id"], "BOUNDARY_TRUNCATED", {"source": "c1_boundary_analysis.json (SAMPLE 10/291, informational — not auto-defect per instruction 4.6)", "ratio": e.get("ratio")})
    for e in bnd.get("expanded_examples", []):
        add(e["tsu_id"], "BOUNDARY_EXPANDED", {"source": "c1_boundary_analysis.json (SAMPLE)", "ratio": e.get("ratio")})

    # 7. Scripture metadata — SAMPLE ONLY (5 with_refs / partial sample without_refs)
    scr = _load("c1_scripture_metadata_audit.json")
    refs = scr.get("verified_tsu_implicit_refs", {})
    for e in refs.get("sample_with_refs", []):
        add(e["id"], "SCRIPTURE_METADATA_GAP_WITH_IMPLICIT_REF", {"source": "c1_scripture_metadata_audit.json (SAMPLE, informational — metadata 누락 자체는 claim 오류 아님)", "source_preview": e.get("source_preview")})

    return ev


def classify(tsu_id: str, cue_disposition: str, c1_ev: dict[str, list[dict]]) -> dict:
    c1_categories = set(c1_ev.keys())
    has_c1_blocking = bool(c1_categories & {
        "CJK_FOREIGN_CONTAMINATION", "EXACT_DUPLICATE", "SEMANTIC_DUPLICATE",
        "THEOLOGICAL_WEAKENING",
    })
    has_c1_informational = bool(c1_categories & {
        "ADJACENT_CONTEXT_OVERLAP", "OCR_ARTIFACT", "BOUNDARY_TRUNCATED",
        "BOUNDARY_EXPANDED", "SCRIPTURE_METADATA_GAP_WITH_IMPLICIT_REF",
    })

    cue_blocking = cue_disposition in ("CJK_FOREIGN_CONTAMINATION", "NEEDS_CLAIM_REVIEW")
    cue_qa = cue_disposition == "QA_FLAG_NONBLOCKING"
    cue_clear = cue_disposition == "SCREENING_CLEAR"

    discrepancy = False
    human_review_required = False
    status: str

    if "THEOLOGICAL_WEAKENING" in c1_categories:
        status = "HUMAN_THEOLOGICAL_REVIEW_REQUIRED"
        human_review_required = True
        if cue_clear:
            discrepancy = True
    elif "SEMANTIC_DUPLICATE" in c1_categories:
        status = "HUMAN_THEOLOGICAL_REVIEW_REQUIRED"
        human_review_required = True
        if cue_clear:
            discrepancy = True
    elif has_c1_blocking and cue_clear:
        # CJK/EXACT_DUPLICATE found by C1 but CUE said SCREENING_CLEAR -> CRITICAL discrepancy
        status = "C1_CUE_DISCREPANCY"
        discrepancy = True
        human_review_required = True
    elif has_c1_blocking and cue_blocking:
        status = "RECONCILED_EXCEPTION"
    elif cue_blocking:
        # CUE found a blocking issue C1 evidence doesn't cover (CUE_ONLY)
        status = "RECONCILED_EXCEPTION"
    elif cue_qa:
        status = "RECONCILED_QA"
    elif cue_clear and not has_c1_blocking:
        status = "RECONCILED_CLEAR"
    else:
        status = "RECONCILED_CLEAR"

    return {
        "reconciliation_status": status,
        "discrepancy": discrepancy,
        "human_review_required": human_review_required,
        "c1_evidence_categories": sorted(c1_categories),
        "c1_has_blocking_evidence": has_c1_blocking,
        "c1_has_informational_evidence": has_c1_informational,
    }


def run() -> dict:
    sweep_path = REPO_ROOT / "NAE" / "review" / "human" / "screening_sweep_report.json"
    sweep = json.loads(sweep_path.read_text(encoding="utf-8"))
    eq_path = REPO_ROOT / "NAE" / "review" / "human" / "exception_queue.json"
    eq = json.loads(eq_path.read_text(encoding="utf-8"))

    sweep_entries = [e for e in eq["entries"] if e.get("disposition_basis", "").startswith("automated_screening_sweep")]

    dagg = json.loads((REPO_ROOT / "NAE/corpus/tsu/Dagg_Church_Order/tsu.json").read_text(encoding="utf-8"))
    hiscox = json.loads((REPO_ROOT / "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json").read_text(encoding="utf-8"))
    dagg_ids = {r["id"] for r in dagg}
    hiscox_ids = {r["id"] for r in hiscox}

    # CUE per-TSU disposition across the full 2,047-TSU screening sweep
    cue_disposition: dict[str, str] = {}
    for tid in sweep["approval_candidates"]:
        cue_disposition[tid] = "SCREENING_CLEAR"
    from collections import defaultdict
    by_tsu_statuses: dict[str, set[str]] = defaultdict(set)
    for e in sweep_entries:
        by_tsu_statuses[e["tsu_id"]].add(e["status"])
    for tid, statuses in by_tsu_statuses.items():
        if statuses == {"QA_FLAG_NONBLOCKING"}:
            cue_disposition[tid] = "QA_FLAG_NONBLOCKING"
        elif "CJK_FOREIGN_CONTAMINATION" in statuses:
            cue_disposition[tid] = "CJK_FOREIGN_CONTAMINATION"
        elif "NEEDS_CLAIM_REVIEW" in statuses:
            cue_disposition[tid] = "NEEDS_CLAIM_REVIEW"
        else:
            cue_disposition[tid] = next(iter(statuses))

    c1_evidence = build_c1_evidence()

    records = []
    c1_only_ids = []
    cue_only_ids = []
    both_ids = []
    neither_ids = []
    discrepancies = []
    human_review_required = []

    for tid, cue_disp in cue_disposition.items():
        corpus = "Dagg_Church_Order" if tid in dagg_ids else ("Hiscox_Standard_Manual" if tid in hiscox_ids else "UNKNOWN")
        c1_ev = c1_evidence.get(tid, {})
        c1_has_any = bool(c1_ev)
        cue_has_finding = cue_disp != "SCREENING_CLEAR"

        if c1_has_any and cue_has_finding:
            both_ids.append(tid)
        elif c1_has_any and not cue_has_finding:
            c1_only_ids.append(tid)
        elif not c1_has_any and cue_has_finding:
            cue_only_ids.append(tid)
        else:
            neither_ids.append(tid)

        cls = classify(tid, cue_disp, c1_ev)
        rec = {
            "tsu_id": tid,
            "corpus": corpus,
            "c1_audited_corpus": corpus == "Dagg_Church_Order",
            "cue_disposition": cue_disp,
            "c1_disposition": sorted(c1_ev.keys()) if c1_ev else [],
            "reconciliation_status": cls["reconciliation_status"],
            "c1_evidence": [{"category": k, "items": v} for k, v in c1_ev.items()],
            "cue_evidence": [s for s in by_tsu_statuses.get(tid, [])] or (["SCREENING_CLEAR"] if cue_disp == "SCREENING_CLEAR" else []),
            "discrepancy": cls["discrepancy"],
            "human_review_required": cls["human_review_required"],
        }
        records.append(rec)
        if cls["discrepancy"]:
            discrepancies.append(rec)
        if cls["human_review_required"]:
            human_review_required.append(rec)

    critical_missed = [r for r in records if r["reconciliation_status"] == "C1_CUE_DISCREPANCY"]

    status_counts: dict[str, int] = defaultdict(int)
    for r in records:
        status_counts[r["reconciliation_status"]] += 1

    hiscox_not_audited = [r for r in records if r["corpus"] == "Hiscox_Standard_Manual"]

    summary = {
        "total_reconciled": len(records),
        "c1_only": len(c1_only_ids),
        "cue_only": len(cue_only_ids),
        "both": len(both_ids),
        "neither": len(neither_ids),
        "discrepancies": len(discrepancies),
        "human_theological_review_required": len(human_review_required),
        "reconciliation_status_counts": dict(status_counts),
        "hiscox_not_audited_by_c1_count": len(hiscox_not_audited),
        "critical_c1_found_cue_clear_missed": [r["tsu_id"] for r in critical_missed],
        "sample_coverage_caveats": [
            "c1_adjacent_overlap.json: 44건 중 30건만 detailed_entries에 persist(SAMPLE)",
            "c1_ocr_artifacts.json: 98건 중 30건만 persist(SAMPLE)",
            "c1_boundary_analysis.json: truncated 291건 중 10건만 persist(SAMPLE)",
            "c1_scripture_metadata_audit.json: implicit-ref sample 5건만 persist(SAMPLE, informational)",
            "c1_hedge_distortion.json: verified_tsus_audited=1149(이미 Promotion된 TSU) 대상 — 이번 2,047건 generated pool과 대부분 비중첩, 참고용",
            "모든 C1 audit는 corpus=Dagg_Church_Order로 명시됨 — Hiscox_Standard_Manual은 C1 evidence 파일에 전혀 등장하지 않음(scope gap)",
        ],
    }

    return {
        "records": records,
        "summary": summary,
        "discrepancies": discrepancies,
        "human_review_required": human_review_required,
    }


def main() -> None:
    result = run()
    OUT.mkdir(exist_ok=True)

    (OUT / "c1_cue_reconciliation.json").write_text(
        json.dumps({"summary": result["summary"], "records": result["records"]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "c1_cue_discrepancies.json").write_text(
        json.dumps(result["discrepancies"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "c1_cue_human_review_required.json").write_text(
        json.dumps(result["human_review_required"], ensure_ascii=False, indent=2), encoding="utf-8"
    )

    s = result["summary"]
    clear = s["reconciliation_status_counts"].get("RECONCILED_CLEAR", 0)
    qa = s["reconciliation_status_counts"].get("RECONCILED_QA", 0)
    exc = s["reconciliation_status_counts"].get("RECONCILED_EXCEPTION", 0)
    md = f"""# C1 <-> CUE Reconciliation Report (2026-08-11, READ-ONLY)

## Summary

- Total reconciled: {s['total_reconciled']}
- C1/CUE agreement (BOTH have a finding): {s['both']}
- C1_ONLY (C1 flagged, CUE silent): {s['c1_only']}
- CUE_ONLY (CUE flagged, no C1 evidence): {s['cue_only']}
- NEITHER (both clear): {s['neither']}
- Discrepancies (C1_CUE_DISCREPANCY): {s['discrepancies']}
- Human theological review required: {s['human_theological_review_required']}

## Reconciliation status breakdown

- RECONCILED_CLEAR: {clear}
- RECONCILED_QA: {qa}
- RECONCILED_EXCEPTION: {exc}
- C1_CUE_DISCREPANCY: {s['reconciliation_status_counts'].get('C1_CUE_DISCREPANCY', 0)}
- HUMAN_THEOLOGICAL_REVIEW_REQUIRED: {s['reconciliation_status_counts'].get('HUMAN_THEOLOGICAL_REVIEW_REQUIRED', 0)}

## CRITICAL — C1 found, CUE missed (SCREENING_CLEAR despite C1 blocking evidence)

Count: {len(s['critical_c1_found_cue_clear_missed'])}

```
{s['critical_c1_found_cue_clear_missed']}
```

## Scope caveats

{chr(10).join('- ' + c for c in s['sample_coverage_caveats'])}

## Hiscox scope gap

{s['hiscox_not_audited_by_c1_count']}건이 Hiscox_Standard_Manual 소속이며, C1 evidence 10개
파일 전부 corpus=Dagg_Church_Order로 한정되어 있어 Hiscox TSU에 대한 C1
독립 검증이 전혀 없다. 이 건들은 C1/CUE agreement로 볼 수 없으며, 최종
승인 패키지에서 별도 표기 필요.
"""
    (OUT / "c1_cue_reconciliation_report.md").write_text(md, encoding="utf-8")
    print(json.dumps(s, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
