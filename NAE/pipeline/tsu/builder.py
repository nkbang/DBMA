"""Phase 3 - TSU (Theological Semantic Unit) Builder orchestrator.

canonical.json -> claim candidates (parser.py) -> LLM claim extraction
(claim.py, doctrine-vocabulary-enforced) -> TSU records with global IDs.
"""
from __future__ import annotations

import json
import logging
import os
import time
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


def _atomic_write_json(path: Path, obj: Any) -> None:
    """Write `obj` as JSON via a sibling .tmp file + os.replace, so a mid-write
    crash never leaves a 0-byte / truncated file (NAE-TSU-BUILDER-EXECUTION-
    RECOVERY-001 Phase 1 observed exactly that). Serialization format is
    unchanged — output stays byte-identical to the previous direct write."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _write_tsu_output(out_dir: Path, tsu_records: list[dict[str, Any]], report: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # tsu.json first, tsu_report.json second: a crash between the two leaves the
    # report describing a checkpoint <= the one tsu.json holds (never ahead), so
    # resume (_load_resume_state + candidate reconciliation) can recover cleanly.
    _atomic_write_json(out_dir / "tsu.json", tsu_records)
    _atomic_write_json(out_dir / "tsu_report.json", report)


def _load_resume_state(out_dir: Path, progress_log) -> dict[str, Any] | None:
    """Read the last checkpoint pair (tsu.json, tsu_report.json) for a resume.

    Returns None when there is nothing usable to resume from (no prior report,
    or a corrupt one) — the caller then starts fresh. Otherwise returns the
    prior report, its records, and the derived resume fields.
    """
    report_path = out_dir / "tsu_report.json"
    tsu_path = out_dir / "tsu.json"
    if not report_path.exists():
        return None
    try:
        with open(report_path, encoding="utf-8") as fh:
            report = json.load(fh)
        records: list[dict[str, Any]] = []
        if tsu_path.exists():
            with open(tsu_path, encoding="utf-8") as fh:
                records = json.load(fh)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        progress_log(f"[tsu-builder] resume: unreadable checkpoint ({exc}) — starting fresh")
        return None
    return {
        "partial": bool(report.get("partial", False)),
        "candidates_evaluated": int(report.get("candidates_evaluated", 0)),
        "llm_errors": int(report.get("llm_errors", 0)),
        "elapsed_seconds": float(report.get("elapsed_seconds", 0.0) or 0.0),
        "records": records,
        "report": report,
    }


def _recount_doctrines(tsu_records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for rec in tsu_records:
        doc = rec.get("doctrine")
        if doc:
            counts[doc] = counts.get(doc, 0) + 1
    return counts


def _resume_next_id(tsu_records: list[dict[str, Any]], fallback_next_id: int,
                    identifier: str, progress_log) -> int:
    """The last id actually written to tsu.json is authoritative for id
    contiguity; tsu_id_state.json is only advisory (it can be saved a step
    ahead of tsu.json inside a checkpoint)."""
    if not tsu_records:
        return fallback_next_id
    try:
        derived = int(str(tsu_records[-1]["id"]).split("-")[1]) + 1
    except (KeyError, IndexError, ValueError):
        return fallback_next_id
    if derived != fallback_next_id:
        progress_log(
            f"[tsu-builder] {identifier}: tsu_id_state next_id={fallback_next_id} "
            f"!= tsu.json last id + 1 = {derived}; using {derived} to keep ids contiguous"
        )
    return derived


def _reconcile_resume_point(identifier: str, candidates: list[Any],
                            tsu_records: list[dict[str, Any]], report_evaluated: int) -> int:
    """Map every loaded record back to its candidate position and return the
    candidate index to resume *after*.

    - Each record must correspond to a candidate in the current list. If one
      does not, `canonical.json` changed since the partial run (candidate order
      is no longer the same) and the byte-identical invariant cannot hold ->
      abort instead of writing a misaligned tsu.json.
    - Normally `report_evaluated` is the resume point. If tsu.json got one
      checkpoint further than tsu_report.json (crash between the two atomic
      writes), the highest covered candidate position wins so those already
      written records are kept, not re-evaluated.
    """
    pos = {
        (c.page, c.paragraph_index, c.sentence_index): i
        for i, c in enumerate(candidates, start=1)
    }
    max_covered = 0
    missing = 0
    for rec in tsu_records:
        key = (rec.get("page"), rec.get("paragraph"), rec.get("sentence"))
        idx = pos.get(key)
        if idx is None:
            missing += 1
        elif idx > max_covered:
            max_covered = idx
    if missing:
        raise RuntimeError(
            f"resume aborted for {identifier}: {missing}/{len(tsu_records)} loaded records "
            f"do not map to current candidates — canonical.json changed since the partial run"
        )
    return max(report_evaluated, max_covered)


def build_tsu_for_identifier(identifier: str, *, model: str = config.DEFAULT_CLAIM_MODEL,
                              max_candidates: int | None = None,
                              canonical_root: Path = config.CANONICAL_ROOT,
                              raw_root: Path = config.RAW_ROOT,
                              tsu_root: Path = config.TSU_ROOT,
                              checkpoint_every: int = 100,
                              progress_log=print,
                              resume: bool = False) -> dict[str, Any]:
    """`checkpoint_every`마다 지금까지의 결과를 tsu.json/tsu_report.json에
    즉시 기록한다 — 장시간 실행(수천 candidate) 도중 프로세스가 예기치
    않게 종료되더라도 마지막 checkpoint까지는 보존되도록 하기 위함
    (NAE-TSU-BUILDER-EXECUTION-RECOVERY-001 Phase 2/3). 추출 로직
    자체(claim/doctrine 판정)는 변경하지 않는다.

    `resume=True`: `tsu_root/<identifier>/tsu_report.json`가 존재하고
    `partial: true`면 `candidates_evaluated` 지점부터 이어서 처리한다
    (기존 tsu.json 레코드를 그대로 로드해 이어붙임). `partial: false`(완료본)
    면 아무 것도 하지 않고 skip한다. 결과 tsu.json은 처음부터 돌린 것과
    byte-identical해야 한다(candidate 순서가 결정론적이므로 성립 —
    NAE-TSU-BUILDER-RESUME-001, docs/NAE_FULLER_TSU_BUILDER_RESUME_DESIGN_v1.md)."""
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
    resume_from = 0
    resume_elapsed_base = 0.0

    if resume:
        prior = _load_resume_state(out_dir, progress_log)
        if prior is None:
            progress_log(f"[tsu-builder] {identifier}: --resume set but no usable checkpoint — starting fresh")
        elif not prior["partial"]:
            progress_log(f"[tsu-builder] {identifier}: already complete (partial=false) — skip")
            return {"records": prior["records"], "report": prior["report"], "skipped": True}
        else:
            tsu_records = prior["records"]
            errors = prior["llm_errors"]
            doctrine_counts = _recount_doctrines(tsu_records)
            resume_elapsed_base = prior["elapsed_seconds"]
            resume_from = _reconcile_resume_point(
                identifier, candidates, tsu_records, prior["candidates_evaluated"],
            )
            next_id = _resume_next_id(tsu_records, next_id, identifier, progress_log)
            progress_log(
                f"[tsu-builder] {identifier}: resuming from candidate {resume_from}/{total} "
                f"(claims so far={len(tsu_records)}, errors={errors}, next_id={next_id})"
            )

    def _build_report(evaluated: int, *, partial: bool) -> dict[str, Any]:
        elapsed = time.monotonic() - start + resume_elapsed_base
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

    for idx, cand in enumerate(candidates[resume_from:], start=resume_from + 1):
        result = claim_mod.extract_claim(
            cand.text,
            context_before=cand.context_before,
            context_after=cand.context_after,
            candidate_scriptures=cand.candidate_scriptures,
            candidate_citations=cand.candidate_citations,
            model=model,
        )
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

        if idx % checkpoint_every == 0 or idx == total:
            elapsed = time.monotonic() - start + resume_elapsed_base
            rate = elapsed / idx if idx else 0.0
            eta_seconds = rate * (total - idx)
            progress_log(
                f"[tsu-builder] {identifier}: candidate {idx}/{total} | "
                f"claims={len(tsu_records)} errors={errors} | "
                f"elapsed={elapsed:.1f}s | ETA={eta_seconds:.1f}s"
            )
            _save_next_id(next_id, tsu_root / "tsu_id_state.json")
            _write_tsu_output(out_dir, tsu_records, _build_report(idx, partial=(idx != total)))

    report = _build_report(total, partial=False)
    _save_next_id(next_id, tsu_root / "tsu_id_state.json")
    _write_tsu_output(out_dir, tsu_records, report)

    return {"records": tsu_records, "report": report}


def build_tsu_for_all(*, model: str = config.DEFAULT_CLAIM_MODEL,
                       max_candidates_per_item: int | None = None,
                       canonical_root: Path = config.CANONICAL_ROOT,
                       raw_root: Path = config.RAW_ROOT,
                       tsu_root: Path = config.TSU_ROOT,
                       resume: bool = False) -> dict[str, Any]:
    if not canonical_root.exists():
        return {"processed": 0, "claims_extracted": 0, "identifiers": []}

    identifiers = [d.name for d in canonical_root.iterdir() if d.is_dir()]
    summary = {"processed": 0, "claims_extracted": 0, "identifiers": []}
    for identifier in identifiers:
        result = build_tsu_for_identifier(
            identifier, model=model, max_candidates=max_candidates_per_item,
            canonical_root=canonical_root, raw_root=raw_root, tsu_root=tsu_root,
            resume=resume,
        )
        summary["processed"] += 1
        summary["claims_extracted"] += len(result["records"])
        summary["identifiers"].append({
            "identifier": identifier,
            "claims_extracted": len(result["records"]),
        })
    return summary
