"""Phase 3 - TSU (Theological Semantic Unit) Builder orchestrator.

canonical.json -> claim candidates (parser.py) -> LLM claim extraction
(claim.py, doctrine-vocabulary-enforced) -> TSU records with global IDs.
"""
from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import claim as claim_mod
from . import config, parser

logger = logging.getLogger("nae.tsu.builder")

_ID_STATE_PATH = config.TSU_ROOT / "tsu_id_state.json"


def _load_next_id(state_path: Path = _ID_STATE_PATH) -> int:
    if not state_path.exists():
        return 1
    try:
        with open(state_path, encoding="utf-8") as fh:
            return int(json.load(fh).get("next_id", 1))
    except (json.JSONDecodeError, OSError, ValueError):
        return 1


def _save_next_id(next_id: int, state_path: Path = _ID_STATE_PATH) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump({"next_id": next_id}, fh)


def _format_tsu_id(n: int) -> str:
    return f"TSU-{n:07d}"


def _write_tsu_output(out_dir: Path, tsu_records: list[dict[str, Any]], report: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "tsu.json", "w", encoding="utf-8") as fh:
        json.dump(tsu_records, fh, ensure_ascii=False, indent=2)
    with open(out_dir / "tsu_report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)


def build_tsu_for_identifier(identifier: str, *, model: str = config.DEFAULT_CLAIM_MODEL,
                              max_candidates: int | None = None,
                              canonical_root: Path = config.CANONICAL_ROOT,
                              raw_root: Path = config.RAW_ROOT,
                              tsu_root: Path = config.TSU_ROOT,
                              checkpoint_every: int = 100,
                              progress_log=print,
                              max_workers: int = 1) -> dict[str, Any]:
    """`checkpoint_every`마다 지금까지의 결과를 tsu.json/tsu_report.json에
    즉시 기록한다 — 장시간 실행(수천 candidate) 도중 프로세스가 예기치
    않게 종료되더라도 마지막 checkpoint까지는 보존되도록 하기 위함
    (NAE-TSU-BUILDER-EXECUTION-RECOVERY-001 Phase 2/3). 추출 로직
    자체(claim/doctrine 판정)는 변경하지 않는다.

    `max_workers` (NAE-FULLER-F2-PARALLEL-001): checkpoint 청크 안에서
    `claim.extract_claim` 호출을 병렬 실행하는 스레드 수. **기본값 1 =
    현행 순차 경로와 완전히 동일** (executor 미사용). >=2 는 Ollama 서버
    `-np >= 2` 환경에서만 이득. id 할당·record append·doctrine 집계는
    항상 candidate 순서대로 메인 스레드에서만 수행하므로, `max_workers`
    값과 무관하게 `tsu.json` 출력은 결정적으로 동일하다."""
    start = time.monotonic()
    candidates = parser.build_candidates(identifier, canonical_root=canonical_root, raw_root=raw_root)
    if max_candidates is not None:
        candidates = candidates[:max_candidates]
    total = len(candidates)

    next_id = _load_next_id(tsu_root / "tsu_id_state.json")
    tsu_records: list[dict[str, Any]] = []
    doctrine_counts: dict[str, int] = {}
    errors = 0
    out_dir = tsu_root / identifier

    def _build_report(evaluated: int, *, partial: bool) -> dict[str, Any]:
        elapsed = time.monotonic() - start
        return {
            "identifier": identifier,
            "builder_version": config.BUILDER_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "candidates_evaluated": evaluated,
            "candidates_total": total,
            "claims_extracted": len(tsu_records),
            "llm_errors": errors,
            "doctrine_breakdown": doctrine_counts,
            "elapsed_seconds": round(elapsed, 2),
            "partial": partial,
            "note": "confidence is model self-reported and uncalibrated; review_status=generated until a human review promotes it to verified (see NAE/pipeline/tsu/review_promotion.py)",
        }

    def _extract_one(cand) -> "claim_mod.ClaimResult":
        # claim.extract_claim is already fail-soft; guard anyway so no worker
        # thread can raise out of the executor.
        try:
            return claim_mod.extract_claim(
                cand.text,
                context_before=cand.context_before,
                context_after=cand.context_after,
                candidate_scriptures=cand.candidate_scriptures,
                candidate_citations=cand.candidate_citations,
                model=model,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("[tsu-builder] extract_claim raised for %s: %s", identifier, exc)
            return claim_mod.ClaimResult(model=model, error=str(exc))

    workers = max(1, int(max_workers))
    evaluated = 0
    for chunk_start in range(0, total, checkpoint_every):
        chunk = candidates[chunk_start:chunk_start + checkpoint_every]

        # LLM calls: parallel within the chunk when workers > 1, else the
        # exact sequential path. executor.map preserves input order.
        if workers == 1:
            results = [_extract_one(c) for c in chunk]
        else:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                results = list(executor.map(_extract_one, chunk))

        # id assignment / record append / doctrine tally: always sequential,
        # candidate order, main thread -> deterministic output.
        for cand, result in zip(chunk, results):
            if result.error:
                errors += 1
            elif result.is_claim:
                record = {
                    "id": _format_tsu_id(next_id),
                    "tsu_schema_version": config.TSU_SCHEMA_VERSION,
                    "book": cand.book,
                    "author": cand.author,
                    "identifier": cand.identifier,
                    "source_identifier": cand.identifier,
                    "collector_version": cand.collector_version,
                    "canonical_version": cand.canonical_version,
                    "page": cand.page,
                    "paragraph": cand.paragraph_index,
                    "sentence": cand.sentence_index,
                    "source_text": cand.text,
                    "claim": result.claim,
                    "doctrine": result.doctrine,
                    "scriptures": result.scriptures,
                    "citations": result.citations,
                    "confidence": result.confidence,
                    "extraction_method": result.extraction_method,
                    "review_status": result.review_status,
                    "model": result.model,
                }
                tsu_records.append(record)
                if result.doctrine:
                    doctrine_counts[result.doctrine] = doctrine_counts.get(result.doctrine, 0) + 1
                next_id += 1

        evaluated += len(chunk)
        elapsed = time.monotonic() - start
        rate = elapsed / evaluated if evaluated else 0.0
        eta_seconds = rate * (total - evaluated)
        progress_log(
            f"[tsu-builder] {identifier}: candidate {evaluated}/{total} | "
            f"claims={len(tsu_records)} errors={errors} | "
            f"elapsed={elapsed:.1f}s | ETA={eta_seconds:.1f}s | workers={workers}"
        )
        _save_next_id(next_id, tsu_root / "tsu_id_state.json")
        _write_tsu_output(out_dir, tsu_records, _build_report(evaluated, partial=(evaluated != total)))

    if total == 0:
        _save_next_id(next_id, tsu_root / "tsu_id_state.json")
        _write_tsu_output(out_dir, tsu_records, _build_report(0, partial=False))

    report = _build_report(total, partial=False)
    _write_tsu_output(out_dir, tsu_records, report)

    return {"records": tsu_records, "report": report}


def build_tsu_for_all(*, model: str = config.DEFAULT_CLAIM_MODEL,
                       max_candidates_per_item: int | None = None,
                       canonical_root: Path = config.CANONICAL_ROOT,
                       raw_root: Path = config.RAW_ROOT,
                       tsu_root: Path = config.TSU_ROOT,
                       max_workers: int = 1) -> dict[str, Any]:
    """`max_workers` is passed through to each `build_tsu_for_identifier`
    call (default 1 = sequential, unchanged)."""
    if not canonical_root.exists():
        return {"processed": 0, "claims_extracted": 0, "identifiers": []}

    identifiers = [d.name for d in canonical_root.iterdir() if d.is_dir()]
    summary = {"processed": 0, "claims_extracted": 0, "identifiers": []}
    for identifier in identifiers:
        result = build_tsu_for_identifier(
            identifier, model=model, max_candidates=max_candidates_per_item,
            canonical_root=canonical_root, raw_root=raw_root, tsu_root=tsu_root,
            max_workers=max_workers,
        )
        summary["processed"] += 1
        summary["claims_extracted"] += len(result["records"])
        summary["identifiers"].append({
            "identifier": identifier,
            "claims_extracted": len(result["records"]),
        })
    return summary
