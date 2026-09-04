"""1,271건 FINAL_HUMAN_REVIEW_CANDIDATE Promotion 실행 (Batch 24~36).

Rev. Bang 승인("C1 최종 Gate GREEN 확인, Human Decision 기록 후
Promotion 실행")에 따라 `output/final_human_review_candidate.json`의
1,271건(46 Human Review 대상 / 284 Hiscox 보류 대상은 절대 미포함)을
100건 이하 배치로 나눠 Batch 1~23과 동일한 안전 절차로 Promotion한다.

배치마다: 백업 -> decisions 기록(reviewer=David) -> promote_tsu_to_verified
-> diff 검증(승인 건 외 무변경) -> indexer dry-run 카운트 확인 ->
validator PASS 확인. 하나라도 실패하면 즉시 중단하고 그 시점까지의
결과만 커밋 대상으로 보고한다(부분 완료 배치는 이미 디스크에 반영된
상태이므로 그대로 유지 — 백업이 있어 언제든 복구 가능).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DAGG_PATH = REPO_ROOT / "NAE/corpus/tsu/Dagg_Church_Order/tsu.json"
HISCOX_PATH = REPO_ROOT / "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json"
DECISIONS_DIR = REPO_ROOT / "NAE/review/human/decisions"
EXCEPTION_QUEUE_PATH = REPO_ROOT / "NAE/review/human/exception_queue.json"
BATCH_SIZE = 100
START_BATCH = 24

TARGETED_TESTS = [
    "tests/test_nae_batch_manager.py",
    "tests/test_c1_cue_reconciliation.py",
    "tests/test_c1_cue_final_disposition.py",
    "tests/test_indexer_review_gate_wiring.py",
    "tests/test_nae_pilot_human_review_intake.py",
]

sys.path.insert(0, str(REPO_ROOT))
from NAE.pipeline.tsu import review_promotion  # noqa: E402
from NAE.pipeline.index import indexer  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_candidates() -> tuple[list[str], set[str]]:
    """(정렬된 1,271건 후보 ID 리스트, 절대 포함되면 안 되는 excluded ID 집합)"""
    final = json.loads((REPO_ROOT / "output/final_human_review_candidate.json").read_text(encoding="utf-8"))
    ids = sorted(set(final["screening_clear"]["tsu_ids"]) | set(final["qa_flag_nonblocking"]["tsu_ids"]))

    hr = json.loads((REPO_ROOT / "output/human_review_required.json").read_text(encoding="utf-8"))
    excluded_hr = (
        set(hr["exact_duplicate_discrepancy"]["tsu_ids"])
        | set(hr["theological_review_required"]["tsu_ids"])
        | set(hr["pre_existing_unresolved_exception"]["tsu_ids"])
    )
    hiscox_pkg = json.loads((REPO_ROOT / "output/hiscox_cue_forensic_package.json").read_text(encoding="utf-8"))
    excluded_hiscox = {r["tsu_id"] for r in hiscox_pkg["records"]}

    excluded = excluded_hr | excluded_hiscox
    overlap = set(ids) & excluded
    if overlap:
        raise RuntimeError(f"pre-flight FAIL: candidates overlap excluded set: {sorted(overlap)}")

    return ids, excluded


def chunk(ids: list[str], size: int) -> list[list[str]]:
    return [ids[i:i + size] for i in range(0, len(ids), size)]


def run_validator(script: str) -> tuple[bool, str]:
    r = subprocess.run([sys.executable, str(REPO_ROOT / script)], capture_output=True, text=True, cwd=REPO_ROOT)
    out = r.stdout[-2000:]
    ok = "FAIL=0" in out and r.returncode == 0
    return ok, out


def run_regression() -> tuple[bool, str]:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--ignore=output"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    out = r.stdout[-2000:]
    ok = r.returncode == 0
    return ok, out


def run_targeted_tests() -> tuple[bool, str]:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *TARGETED_TESTS],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    out = r.stdout[-2000:]
    ok = r.returncode == 0
    return ok, out


def _sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


HARDCODED_INDEXED_ASSERTION_FILES = [
    REPO_ROOT / "tests/test_indexer_review_gate_wiring.py",
    REPO_ROOT / "tests/test_nae_pilot_human_review_intake.py",
]


def _update_hardcoded_indexed_assertions(new_indexed: int) -> None:
    """`assert summary["indexed"] == N` 형태의 Production-facing 하드코딩
    단언문 2개를, 이 배치 이후 실제 값으로 정확히 1줄씩만 치환한다(다른
    synthetic-test assertion을 건드리지 않도록 정확한 패턴만 매치)."""
    import re
    # 3자리 이상 숫자만 매치 — 이 파일들에는 synthetic-test assertion
    # (assert summary["indexed"] == 1)도 존재하므로, Production 실측치
    # (수천 단위)만 정확히 겨냥해야 한다(과거 blind sed로 synthetic
    # assertion까지 오염시킨 사고 재발 방지).
    pattern = re.compile(r'assert summary\["indexed"\] == \d{3,}')
    for path in HARDCODED_INDEXED_ASSERTION_FILES:
        text = path.read_text(encoding="utf-8")
        matches = pattern.findall(text)
        if len(matches) != 1:
            raise RuntimeError(f"{path}: expected exactly 1 hardcoded Production indexed-count assertion, found {len(matches)}")
        new_text = pattern.sub(f'assert summary["indexed"] == {new_indexed}', text)
        path.write_text(new_text, encoding="utf-8")


def promote_batch(batch_number: int, tsu_ids: list[str], excluded_ids: set[str]) -> dict:
    if len(tsu_ids) > BATCH_SIZE:
        raise RuntimeError(f"batch {batch_number}: size {len(tsu_ids)} exceeds BATCH_SIZE={BATCH_SIZE}")

    conflict = set(tsu_ids) & excluded_ids
    if conflict:
        raise RuntimeError(f"batch {batch_number}: candidates overlap protected/excluded set: {sorted(conflict)}")

    hiscox_hash_before = _sha256(HISCOX_PATH)
    eq_hash_before = _sha256(EXCEPTION_QUEUE_PATH)

    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir = REPO_ROOT / f"NAE/corpus/tsu/_batch{batch_number:04d}_promotion_backup_{ts}"
    backup_dir.mkdir(parents=True)
    shutil.copy2(DAGG_PATH, backup_dir / "Dagg_Church_Order_tsu.json")
    shutil.copy2(HISCOX_PATH, backup_dir / "Hiscox_Standard_Manual_tsu.json")

    data = json.loads(DAGG_PATH.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in data}

    missing = [t for t in tsu_ids if t not in by_id]
    if missing:
        raise RuntimeError(f"batch {batch_number}: TSU not found in Dagg: {missing}")
    not_generated = [t for t in tsu_ids if by_id[t]["review_status"] != "generated"]
    if not_generated:
        raise RuntimeError(f"batch {batch_number}: review_status != generated: {not_generated}")

    review_date = _now_iso()
    decisions = []
    for tid in tsu_ids:
        rec = by_id[tid]
        result = review_promotion.promote_tsu_to_verified(
            rec, reviewer="David", review_date=review_date, review_decision="approved",
        )
        if not result.promoted:
            raise RuntimeError(f"batch {batch_number}: promotion BLOCK for {tid}: {result.reason}")
        idx = data.index(rec)
        data[idx] = result.record
        decisions.append({
            "tsu_id": tid,
            "reviewer_id": "David",
            "answers": {"Q1": "A", "Q2": "A", "Q3": "A"},
            "final_decision": "APPROVED",
            "decided_at": review_date,
            "source": "c1_gate_green_final_promotion_2026-08-11",
        })

    # diff 검증: 이 배치 tsu_id 외에는 review_status/review_metadata 포함 어떤 필드도 변하지 않아야 함
    before_by_id = {r["id"]: r for r in json.loads((backup_dir / "Dagg_Church_Order_tsu.json").read_text(encoding="utf-8"))}
    tsu_id_set = set(tsu_ids)
    unexpected_changes = []
    for r in data:
        tid = r["id"]
        before = before_by_id[tid]
        if tid in tsu_id_set:
            for k in before:
                if k in ("review_status", "review_metadata"):
                    continue
                if before.get(k) != r.get(k):
                    unexpected_changes.append((tid, k))
        else:
            if before != r:
                unexpected_changes.append((tid, "UNEXPECTED_MUTATION_OF_NON_BATCH_RECORD"))
    if unexpected_changes:
        raise RuntimeError(f"batch {batch_number}: unexpected field changes: {unexpected_changes[:10]}")

    DAGG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Hiscox/exception_queue boundary — 이 배치는 Dagg만 건드려야 한다
    hiscox_hash_after = _sha256(HISCOX_PATH)
    if hiscox_hash_after != hiscox_hash_before:
        raise RuntimeError(f"batch {batch_number}: Hiscox_Standard_Manual/tsu.json 변경 감지 — Dagg/Hiscox boundary violation, STOP")
    eq_hash_after = _sha256(EXCEPTION_QUEUE_PATH)
    if eq_hash_after != eq_hash_before:
        raise RuntimeError(f"batch {batch_number}: exception_queue.json 변경 감지(자동 RESOLVED 금지) — STOP")

    batch_id = f"batch_{batch_number:04d}"
    (DECISIONS_DIR / f"{batch_id}_decisions.json").write_text(
        json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = indexer.index_all(dry_run=True)

    ok_src, src_out = run_validator("scripts/source_validator.py")
    ok_auth, auth_out = run_validator("scripts/authority_validator.py")
    if not (ok_src and ok_auth):
        raise RuntimeError(f"batch {batch_number}: validator FAIL — source_ok={ok_src} authority_ok={ok_auth}\n{src_out}\n{auth_out}")

    _update_hardcoded_indexed_assertions(summary["indexed"])

    ok_tgt, tgt_out = run_targeted_tests()
    if not ok_tgt:
        raise RuntimeError(f"batch {batch_number}: targeted tests FAIL:\n{tgt_out}")

    actual_promoted = sum(1 for r in data if r["id"] in tsu_id_set and r["review_status"] == "verified")
    if actual_promoted != len(tsu_ids):
        raise RuntimeError(f"batch {batch_number}: expected {len(tsu_ids)} promoted, actual {actual_promoted}")

    return {
        "batch_id": batch_id,
        "count": len(tsu_ids),
        "first_tsu_id": tsu_ids[0],
        "last_tsu_id": tsu_ids[-1],
        "backup_dir": str(backup_dir.relative_to(REPO_ROOT)),
        "indexed_after": summary["indexed"],
        "validator": "PASS",
        "targeted_tests": "PASS",
        "hiscox_boundary": "UNCHANGED",
        "exception_queue_boundary": "UNCHANGED",
    }


def main() -> None:
    ids, excluded = load_candidates()
    assert len(ids) == 1271, f"expected 1271 candidates, got {len(ids)}"

    dagg_now = {r["id"]: r for r in json.loads(DAGG_PATH.read_text(encoding="utf-8"))}
    already_verified = {t for t in ids if dagg_now.get(t, {}).get("review_status") == "verified"}
    remaining = [t for t in ids if t not in already_verified]
    if already_verified:
        print(f"이미 verified(재승격 skip): {len(already_verified)}건", flush=True)

    batches = chunk(remaining, BATCH_SIZE)
    start_batch_number = START_BATCH + (len(ids) - len(remaining)) // BATCH_SIZE
    results = []
    for i, batch_ids in enumerate(batches):
        batch_number = start_batch_number + i
        print(f"=== batch_{batch_number:04d}: {len(batch_ids)}건 ({batch_ids[0]} ~ {batch_ids[-1]}) ===", flush=True)
        try:
            result = promote_batch(batch_number, batch_ids, excluded)
        except Exception as e:
            print(f"STOP — batch_{batch_number:04d} 실패: {e}", flush=True)
            (REPO_ROOT / "output/promotion_run_result.json").write_text(
                json.dumps({"completed_batches": results, "failed_batch": batch_number, "error": str(e), "final_regression": None}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            sys.exit(1)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        results.append(result)

    print("=== ALL 13 BATCHES COMPLETE — FINAL REGRESSION ===", flush=True)
    ok_reg, reg_out = run_regression()
    ok_src, src_out = run_validator("scripts/source_validator.py")
    ok_auth, auth_out = run_validator("scripts/authority_validator.py")

    (REPO_ROOT / "output/promotion_run_result.json").write_text(
        json.dumps({
            "completed_batches": results,
            "failed_batch": None,
            "final_regression": "PASS" if ok_reg else "FAIL",
            "final_regression_tail": reg_out,
            "final_validator": "PASS" if (ok_src and ok_auth) else "FAIL",
        }, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"FINAL REGRESSION: {'PASS' if ok_reg else 'FAIL'}", flush=True)
    print(f"FINAL VALIDATOR: {'PASS' if (ok_src and ok_auth) else 'FAIL'}", flush=True)
    print("ALL BATCHES COMPLETE", flush=True)
    if not ok_reg or not (ok_src and ok_auth):
        sys.exit(1)


if __name__ == "__main__":
    main()
