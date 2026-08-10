"""NAE/review/human/batch_manager.py — Human Review 확장 배치 관리
(NAE-TSU-4107-EXPANSION-001).

Pilot 001(10건, 완료)을 넘어선 나머지 `review_status="generated"`
4,107건을 `MAX_PENDING_REVIEW`(schema.py, 100) 이하 크기의 배치로
나눠 순차 진행하기 위한 모듈. 정렬 순서는 source 단위(Dagg 전체 →
Hiscox 전체) × TSU ID 오름차순 — Pilot 001과 동일한 추적 가능성
원칙을 따른다(임의 순서 금지).

이 모듈은 Production TSU 파일을 읽기 전용으로만 사용하고, 절대
수정하지 않는다. `decisions/`에도 쓰지 않는다(그건 언제나 사용자
본인의 몫).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from NAE.pipeline.index.config import CORPUS_ROOT

from . import decision_gate
from .schema import MAX_PENDING_REVIEW, PILOT_TSU_IDS

TSU_IDENTIFIERS: tuple[str, ...] = ("Dagg_Church_Order", "Hiscox_Standard_Manual")

BATCH_STATE_PATH = Path(__file__).resolve().parent / "batch_state.json"
BATCH_SIZE = MAX_PENDING_REVIEW  # 기존 안전 게이트(100)를 배치 크기 상한으로 재사용


def load_generated_records() -> list[dict[str, Any]]:
    """`review_status="generated"`인 레코드를 source 단위(Dagg→Hiscox)
    × TSU ID 오름차순으로 정렬해 반환한다. Pilot 10건(PILOT_TSU_IDS)은
    이미 verified 상태라 자연히 제외되지만, 방어적으로 한 번 더
    걸러낸다."""
    records: list[dict[str, Any]] = []
    for identifier in TSU_IDENTIFIERS:
        path = CORPUS_ROOT / "tsu" / identifier / "tsu.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        generated = [
            r for r in data
            if r.get("review_status") == "generated" and r["id"] not in PILOT_TSU_IDS
        ]
        generated.sort(key=lambda r: r["id"])
        records.extend(generated)
    return records


def total_batches(batch_size: int = BATCH_SIZE) -> int:
    total = len(load_generated_records())
    return (total + batch_size - 1) // batch_size


def get_batch_records(batch_number: int, batch_size: int = BATCH_SIZE) -> list[dict[str, Any]]:
    """1-indexed 배치 번호. batch_number=1 → 첫 100건(Dagg TSU ID 최소값부터)."""
    if batch_number < 1:
        raise ValueError("batch_number must be >= 1")
    records = load_generated_records()
    start = (batch_number - 1) * batch_size
    end = start + batch_size
    return records[start:end]


def _load_state() -> dict[str, Any]:
    if BATCH_STATE_PATH.exists():
        return json.loads(BATCH_STATE_PATH.read_text(encoding="utf-8"))
    return {"schema_version": "1.0.0", "batch_size": BATCH_SIZE, "batches": {}}


def _save_state(state: dict[str, Any]) -> None:
    BATCH_STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def generate_batch(batch_number: int, batch_size: int = BATCH_SIZE) -> Path:
    """배치 N의 HumanReviewRequest를 생성해 `requests/batch_{NNNN}_requests.json`에
    쓰고, `batch_state.json`에 상태(pending)를 기록한다. 이미 생성된
    배치를 다시 생성하면 덮어쓴다(재현 가능, 결정적)."""
    records = get_batch_records(batch_number, batch_size)
    if not records:
        raise ValueError(f"batch {batch_number} is empty — no generated records left")

    batch_id = f"batch_{batch_number:04d}"
    requests = decision_gate.build_requests_from_records(records)
    path = decision_gate.write_batch_requests(requests, batch_id)

    state = _load_state()
    state["batch_size"] = batch_size
    state["batches"][batch_id] = {
        "batch_number": batch_number,
        "tsu_count": len(records),
        "first_tsu_id": records[0]["id"],
        "last_tsu_id": records[-1]["id"],
        "status": "requests_generated",
    }
    _save_state(state)
    return path


def progress_summary() -> dict[str, Any]:
    """전체 대비 진행률 — 리뷰 완료(review_promotion으로 verified 승격된)
    건수가 아니라, 이 배치 매니저가 다룬 배치 상태 기준."""
    state = _load_state()
    total = len(load_generated_records())
    generated_batches = [b for b in state["batches"].values() if b["status"] != "not_started"]
    reviewed_tsu_count = sum(
        b["tsu_count"] for b in state["batches"].values() if b["status"] == "completed"
    )
    return {
        "total_generated": total,
        "total_batches": total_batches(state.get("batch_size", BATCH_SIZE)),
        "batches_with_requests": len(generated_batches),
        "tsu_reviewed_and_completed": reviewed_tsu_count,
        "percent_complete": round(100 * reviewed_tsu_count / total, 2) if total else 0.0,
    }
