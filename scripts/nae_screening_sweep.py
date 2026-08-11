"""NAE/review/human 자동 forensic screening sweep (screening_cursor 기반).

Batch 24부터 generated pool이 소진될 때까지, `batch_manager.get_screening_batch()`
(Promotion과 독립적인 screening_cursor)를 이용해 100건씩 순차 screening한다.

이 스크립트는 다음을 절대 하지 않는다:
- Human Decision(Q1-Q3/FINAL) 생성
- Promotion(review_status 변경)
- Production TSU/claim/schema 수정
- exception_queue.json 외 파일 쓰기(batch_state.json, requests/ 파일 생성 없음)

CJK/외국어 오염, claim 인접-중복, doctrine 공백만 기계적으로 탐지해
`exception_queue.json`에 신규 항목으로 누적하고, 문제 없는 TSU는
approval-candidates 목록에 쌓는다. 최종 결과는 JSON 리포트로 저장된다.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from NAE.review.human import batch_manager as bm

REPO_ROOT = Path(__file__).resolve().parent.parent
EXCEPTION_QUEUE_PATH = REPO_ROOT / "NAE" / "review" / "human" / "exception_queue.json"
REPORT_PATH = REPO_ROOT / "NAE" / "review" / "human" / "screening_sweep_report.json"

CONTAM_RE = re.compile(r"[一-鿿぀-ヿЀ-ӿ]")
VIET_RE = re.compile(r"[ăâđêôơư]", re.IGNORECASE)

CHUNK_SIZE = 100


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def screen_record(rec: dict, prev_claim: str | None) -> list[dict]:
    """단일 TSU에 대한 기계적 forensic 검사. 문제가 있으면 예외 dict
    리스트를 반환(없으면 빈 리스트)."""
    issues = []
    claim = (rec.get("claim") or "")
    doctrine = (rec.get("doctrine") or "").strip()

    if CONTAM_RE.search(claim):
        issues.append({"type": "CJK_FOREIGN_CONTAMINATION", "detail": "claim에 CJK/한글 외 비-라틴 문자 감지"})
    if VIET_RE.search(claim):
        issues.append({"type": "CJK_FOREIGN_CONTAMINATION", "detail": "claim에 베트남어 발음부호 감지"})
    if not doctrine:
        issues.append({"type": "QA_FLAG_NONBLOCKING", "detail": "doctrine 필드 공백"})
    if prev_claim is not None and claim.strip() and claim.strip() == prev_claim.strip():
        issues.append({"type": "NEEDS_CLAIM_REVIEW", "detail": "인접 TSU와 claim 완전 동일(중복 의심)"})

    return issues


def load_exception_queue() -> dict:
    return json.loads(EXCEPTION_QUEUE_PATH.read_text(encoding="utf-8"))


def save_exception_queue(data: dict) -> None:
    EXCEPTION_QUEUE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run_sweep(start_batch_number: int = 24) -> dict:
    eq_data = load_exception_queue()
    existing_ids = {e["tsu_id"] for e in eq_data["entries"]}

    approval_candidates: list[str] = []
    new_exceptions: list[dict] = []
    chunk_summaries: list[dict] = []

    batch_number = start_batch_number
    while True:
        batch = bm.get_screening_batch(batch_size=CHUNK_SIZE)
        if not batch:
            break

        batch_id = f"batch_{batch_number:04d}"
        prev_claim = None
        clear_count = 0
        exc_count = 0
        for rec in batch:
            issues = screen_record(rec, prev_claim)
            prev_claim = rec.get("claim")
            if issues:
                exc_count += 1
                for issue in issues:
                    entry = {
                        "tsu_id": rec["id"],
                        "batch_id": batch_id,
                        "status": issue["type"],
                        "current_review_status": rec.get("review_status"),
                        "human_decision": None,
                        "reason": issue["detail"],
                        "action": "PENDING_HUMAN_REVIEW",
                        "flagged_at": _now(),
                        "resolved_at": None,
                        "resolution": None,
                        "downstream_eligibility": "BLOCKED_PENDING_REVIEW" if issue["type"] != "QA_FLAG_NONBLOCKING" else "ELIGIBLE_WITH_FLAG",
                        "disposition_basis": "automated_screening_sweep(screening_cursor, 2026-08-11)",
                    }
                    if rec["id"] not in existing_ids:
                        new_exceptions.append(entry)
            else:
                clear_count += 1
                approval_candidates.append(rec["id"])

        chunk_summaries.append({
            "batch_id": batch_id,
            "count": len(batch),
            "first_tsu_id": batch[0]["id"],
            "last_tsu_id": batch[-1]["id"],
            "screening_clear": clear_count,
            "exceptions": exc_count,
        })
        batch_number += 1

    eq_data["entries"].extend(new_exceptions)
    save_exception_queue(eq_data)

    report = {
        "run_at": _now(),
        "start_batch_number": start_batch_number,
        "chunks_processed": len(chunk_summaries),
        "total_screened": sum(c["count"] for c in chunk_summaries),
        "approval_candidates_count": len(approval_candidates),
        "new_exceptions_count": len(new_exceptions),
        "chunk_summaries": chunk_summaries,
        "approval_candidates": approval_candidates,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run_sweep()
    print(json.dumps({k: v for k, v in result.items() if k not in ("approval_candidates", "chunk_summaries")}, ensure_ascii=False, indent=2))
