"""NAE Benchmark Review CLI - human review 상태 관리 + promote.

TASK 4 (C1-TASK-ORDER-037):
- --summary: review.status별 개수 집계
- --approve / --reject / --needs-revision: review 상태 변경
- --promote: approved 중 필수 필드 재검증 후 gold dataset으로 승격

중요: promote 시 approved인데 필수 필드가 비어있는 레코드는 반드시 차단.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


# ------------------------------------------------------------------
# JSONL I/O
# ------------------------------------------------------------------

def load_jsonl(path: str) -> List[Dict[str, Any]]:
    """JSONL 파일을 로드하여 레코드 목록 반환."""
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"ERROR: JSON decode error on line {line_no} in {path}: {exc}", file=sys.stderr)
                sys.exit(1)
    return records


def save_jsonl(records: List[Dict[str, Any]], path: str) -> None:
    """레코드 목록을 JSONL 파일로 저장."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------
# --summary
# ------------------------------------------------------------------

def cmd_summary(dataset_path: str) -> int:
    """review.status별 개수 집계 출력."""
    records = load_jsonl(dataset_path)
    if not records:
        print(f"WARNING: {dataset_path} is empty", file=sys.stderr)
        return 0

    counts: Dict[str, int] = {}
    for rec in records:
        status = rec.get("review_status", "unknown")
        counts[status] = counts.get(status, 0) + 1

    print(f"Dataset: {dataset_path}")
    print(f"Total records: {len(records)}")
    print("Review status distribution:")
    for status in sorted(counts.keys()):
        print(f"  {status}: {counts[status]}")
    return 0


# ------------------------------------------------------------------
# --approve / --reject / --needs-revision
# ------------------------------------------------------------------

def _find_record_index(records: List[Dict[str, Any]], benchmark_id: str) -> int:
    """benchmark_id로 레코드 인덱스 찾기. 없으면 -1."""
    for i, rec in enumerate(records):
        if rec.get("benchmark_id") == benchmark_id:
            return i
    return -1


def cmd_approve(dataset_path: str, benchmark_id: str, reviewer: str) -> int:
    """레코드를 approved로 승인."""
    records = load_jsonl(dataset_path)
    idx = _find_record_index(records, benchmark_id)
    if idx == -1:
        print(f"ERROR: benchmark_id '{benchmark_id}' not found in {dataset_path}", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc).isoformat()
    records[idx]["review_status"] = "approved"
    records[idx]["review"] = {
        "status": "approved",
        "reviewer": reviewer,
        "reviewed_at": now,
    }
    save_jsonl(records, dataset_path)
    print(f"Approved: {benchmark_id} (reviewer={reviewer})")
    return 0


def cmd_reject(dataset_path: str, benchmark_id: str, notes: str) -> int:
    """레코드를 rejected으로 거부."""
    records = load_jsonl(dataset_path)
    idx = _find_record_index(records, benchmark_id)
    if idx == -1:
        print(f"ERROR: benchmark_id '{benchmark_id}' not found in {dataset_path}", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc).isoformat()
    records[idx]["review_status"] = "rejected"
    records[idx]["review"] = {
        "status": "rejected",
        "reviewer": "",
        "reviewed_at": now,
        "notes": notes,
    }
    save_jsonl(records, dataset_path)
    print(f"Rejected: {benchmark_id} (notes={notes})")
    return 0


def cmd_needs_revision(dataset_path: str, benchmark_id: str, notes: str) -> int:
    """레코드를 needs-revision으로 되돌림."""
    records = load_jsonl(dataset_path)
    idx = _find_record_index(records, benchmark_id)
    if idx == -1:
        print(f"ERROR: benchmark_id '{benchmark_id}' not found in {dataset_path}", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc).isoformat()
    records[idx]["review_status"] = "review"
    records[idx]["review"] = {
        "status": "needs-revision",
        "reviewer": "",
        "reviewed_at": now,
        "notes": notes,
    }
    save_jsonl(records, dataset_path)
    print(f"Needs revision: {benchmark_id} (notes={notes})")
    return 0


# ------------------------------------------------------------------
# --promote (재검증 로직 포함)
# ------------------------------------------------------------------

def cmd_promote(draft_path: str, output_path: str, manifest_path: str) -> int:
    """approved 레코드 중 필수 필드가 채워진 것만 gold dataset으로 promote.

    재검증 로직:
    1. review.status == "approved"인 레코드만 필터링
    2. question.text 가 비어있지 않은지 확인
    3. gold_tsu_ids 가 비어있지 않은지 확인
    4. 통과한 레코드만 output_path로 출력
    5. manifest_path 에 메타데이터 기록
    """
    records = load_jsonl(draft_path)

    # 1. approved 필터링
    approved_records = [
        rec for rec in records
        if rec.get("review_status") == "approved"
        and isinstance(rec.get("review"), dict)
        and rec["review"].get("status") == "approved"
    ]

    if not approved_records:
        print("WARNING: No approved records found in draft", file=sys.stderr)
        # 빈 gold 파일 생성
        save_jsonl([], output_path)
        manifest = {
            "dataset_version": "",
            "schema_version": "1",
            "question_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "promoted_from": draft_path,
            "doctrine_coverage": {},
        }
        Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=2)
        print(f"Promoted 0 records -> {output_path}")
        return 0

    # 2~3. 필수 필드 재검증
    valid_records: List[Dict[str, Any]] = []
    invalid_ids: List[tuple] = []

    for rec in approved_records:
        bid = rec.get("benchmark_id", "unknown")
        qtext = rec.get("question", {}).get("text", "")
        gold_ids = rec.get("gold_tsu_ids", rec.get("expected", {}).get("gold_tsu_ids", []))

        errors = []
        if not qtext or not qtext.strip():
            errors.append("question.text is empty")
        if not gold_ids:
            errors.append("gold_tsu_ids is empty")

        if errors:
            invalid_ids.append((bid, errors))
        else:
            valid_records.append(rec)

    # 실패한 레코드 출력
    if invalid_ids:
        print("ERROR: The following approved records have empty required fields and CANNOT be promoted:", file=sys.stderr)
        for bid, errs in invalid_ids:
            print(f"  {bid}: {', '.join(errs)}", file=sys.stderr)
        print(f"\nPromotion aborted. {len(valid_records)} records passed validation.", file=sys.stderr)
        return 1

    # 4. 통과한 레코드만 출력
    save_jsonl(valid_records, output_path)

    # 5. manifest 생성 - doctrine_coverage 집계
    doctrine_coverage: Dict[str, int] = {}
    for rec in valid_records:
        ta = rec.get("question", {}).get("theology_area", "")
        if ta:
            doctrine_coverage[ta] = doctrine_coverage.get(ta, 0) + 1

    manifest = {
        "dataset_version": "",
        "schema_version": "1",
        "question_count": len(valid_records),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "promoted_from": draft_path,
        "doctrine_coverage": doctrine_coverage,
    }

    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    print(f"Promoted {len(valid_records)} records -> {output_path}")
    print(f"Manifest -> {manifest_path}")
    if doctrine_coverage:
        print("Doctrine coverage:")
        for doctrine, count in sorted(doctrine_coverage.items()):
            print(f"  {doctrine}: {count}")
    return 0


# ------------------------------------------------------------------
# CLI Entry Point
# ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """CLI 파서 생성."""
    parser = argparse.ArgumentParser(
        prog="nae-benchmark-review",
        description="NAE Benchmark - human review 상태 관리 + promote",
    )
    parser.add_argument("--dataset", type=str, help="JSONL 데이터셋 경로")

    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # --summary
    subparsers.add_parser("summary", help="review.status별 개수 집계")

    # --approve
    p_approve = subparsers.add_parser("approve", help="레코드 승인")
    p_approve.add_argument("--id", type=str, required=True, help="benchmark_id")
    p_approve.add_argument("--reviewer", type=str, required=True, help="검토자 이름")

    # --reject
    p_reject = subparsers.add_parser("reject", help="레코드 거부")
    p_reject.add_argument("--id", type=str, required=True, help="benchmark_id")
    p_reject.add_argument("--notes", type=str, required=True, help="거부 사유")

    # --needs-revision
    p_revision = subparsers.add_parser("needs-revision", help="수정 요청")
    p_revision.add_argument("--id", type=str, required=True, help="benchmark_id")
    p_revision.add_argument("--notes", type=str, required=True, help="수정 요청 사유")

    # --promote
    p_promote = subparsers.add_parser("promote", help="approved 레코드를 gold dataset으로 승격")
    p_promote.add_argument("--draft", type=str, required=True, help="draft JSONL 경로")
    p_promote.add_argument("--output", type=str, required=True, help="출력 gold JSONL 경로")
    p_promote.add_argument("--manifest", type=str, required=True, help="출력 manifest JSON 경로")

    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI 메인 함수."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    dataset_path = getattr(args, "dataset", None)

    if args.command == "summary":
        if not dataset_path:
            print("ERROR: --dataset is required for summary", file=sys.stderr)
            return 1
        return cmd_summary(dataset_path)

    elif args.command == "approve":
        if not dataset_path:
            print("ERROR: --dataset is required for approve", file=sys.stderr)
            return 1
        return cmd_approve(dataset_path, args.id, args.reviewer)

    elif args.command == "reject":
        if not dataset_path:
            print("ERROR: --dataset is required for reject", file=sys.stderr)
            return 1
        return cmd_reject(dataset_path, args.id, args.notes)

    elif args.command == "needs-revision":
        if not dataset_path:
            print("ERROR: --dataset is required for needs-revision", file=sys.stderr)
            return 1
        return cmd_needs_revision(dataset_path, args.id, args.notes)

    elif args.command == "promote":
        return cmd_promote(args.draft, args.output, args.manifest)

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
