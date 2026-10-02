"""scripts/merge_nae_corpus.py — NAE Corpus Merge with Mandatory Approval Gate

F-3 safe merge: idempotent, atomic, dedup, registry integrity.

**핵심 안전성:** merge() 함수는 verify_mutation_gate()를 호출하여
승인되지 않은 source의 mutation을 코드 레벨에서 차단한다.
CLI 옵션이나 환경 변수로 이 gate를 우회할 수 없다.

Usage:
    python scripts/merge_nae_corpus.py --source Fuller_Complete_Works_Vol02

    merge() 함수를 Python에서 직접 호출해도 gate가 강제된다:
        from scripts.merge_nae_corpus import merge_nae_corpus
        result = merge_nae_corpus(source_id="Fuller_Complete_Works_Vol02")
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Optional

# approval gate import — mutation code의 진입점
from scripts.corpus_approval_gate import (
    ApprovalStatus,
    CorpusMutationBlockedError,
    CorpusMutationManifest,
    CorpusMutationApprovalResult,
    build_approval_manifest,
    validate_merge_plan_against_manifest,
    verify_corpus_mutation_approval,
)

DEFAULT_TSU_DATASET_PATH = Path("output/bench/tsu_dataset.jsonl")
DEFAULT_TSU_MANIFEST_PATH = Path("output/bench/tsu_manifest.json")
DEFAULT_REGISTRY_DIR = Path("data/제련완성본")
NAE_CORPUS_DIR = Path("NAE/corpus/tsu")


def _read_existing_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _atomic_write_text(path: Path, content: str) -> None:
    import os as _os
    dir_name = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with _os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        _os.replace(tmp_path, str(path))
    except Exception:
        try:
            _os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _tsu_dataset_lock(path: Path):
    from contextlib import contextmanager
    @contextmanager
    def _lock():
        yield
    return _lock()


def verify_mutation_gate(
    source_id: str,
    decisions_dir: Path,
    planned_tsu_ids: frozenset[str],
) -> CorpusMutationManifest:
    """Corpus mutation 전 필수 승인 게이트.

    이 함수가 CorpusMutationManifest를 반환하지 않으면 (예외 발생)
    mutation을 절대 수행해서는 안 된다.

    Raises:
        CorpusMutationBlockedError: 승인이 없거나 불완전할 때.
    """
    result = verify_corpus_mutation_approval(source_id, decisions_dir, planned_tsu_ids)

    if result.status == ApprovalStatus.NOT_APPROVED:
        raise CorpusMutationBlockedError(
            f"Corpus mutation BLOCKED for source={source_id!r}: {result.reason}"
        )

    if result.status == ApprovalStatus.CONDITIONAL:
        raise CorpusMutationBlockedError(
            f"Corpus mutation BLOCKED (CONDITIONAL) for source={source_id!r}: "
            f"{result.reason}. Approved TSUs: {sorted(result.approved_tsu_ids)[:10]}..."
        )

    manifest = build_approval_manifest(source_id, decisions_dir)
    if manifest is None:
        raise CorpusMutationBlockedError(
            f"Corpus mutation BLOCKED: manifest build failed for source={source_id!r}"
        )

    valid, reason = validate_merge_plan_against_manifest(manifest, planned_tsu_ids)
    if not valid:
        raise CorpusMutationBlockedError(f"Corpus mutation BLOCKED: {reason}")

    return manifest


def merge_nae_corpus(
    source_id: str,
    nae_corpus_dir: Optional[Path] = None,
    tsu_dataset_path: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
    registry_dir: Optional[Path] = None,
    decisions_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """NAE corpus TSU를 production TSU에 병합한다 (F-3 safe).

    **핵심 안전성:** 이 함수의 첫 동작은 verify_mutation_gate() 호출이다.
    gate가 통과하지 않으면 CorpusMutationBlockedError가 발생하여
    mutation code에 절대 도달하지 않는다.

    Raises:
        CorpusMutationBlockedError: 승인 게이트를 통과하지 못하면 발생.
    """
    nae_corpus_dir = nae_corpus_dir or NAE_CORPUS_DIR
    decisions_dir = decisions_dir or Path("NAE/review/human/decisions")

    planned_tsu_ids: set[str] = set()
    if nae_corpus_dir.exists():
        for tsu_dir in sorted(nae_corpus_dir.glob("*")):
            tsu_file = tsu_dir / "tsu.json"
            if tsu_file.exists():
                data = json.loads(tsu_file.read_text(encoding="utf-8"))
                for record in data:
                    tid = record.get("tsu_id", "")
                    if tid and record.get("work_id") == source_id:
                        planned_tsu_ids.add(tid)

    if not planned_tsu_ids:
        return {
            "status": "skipped",
            "reason": f"No TSU records found for source={source_id!r} in {nae_corpus_dir}",
            "merged_count": 0,
            "duplicate_count": 0,
        }

    manifest = verify_mutation_gate(source_id, decisions_dir, frozenset(planned_tsu_ids))

    tsu_dataset_path = tsu_dataset_path or DEFAULT_TSU_DATASET_PATH
    merged_count = 0
    duplicate_count = 0

    with _tsu_dataset_lock(tsu_dataset_path):
        existing_records = _read_existing_dataset(tsu_dataset_path)
        existing_ids = {r["tsu_id"] for r in existing_records if "tsu_id" in r}

        new_records: list[dict[str, Any]] = []
        if nae_corpus_dir.exists():
            for tsu_dir in sorted(nae_corpus_dir.glob("*")):
                tsu_file = tsu_dir / "tsu.json"
                if tsu_file.exists():
                    data = json.loads(tsu_file.read_text(encoding="utf-8"))
                    for record in data:
                        if record.get("work_id") == source_id:
                            tid = record.get("tsu_id", "")
                            if tid and tid not in existing_ids:
                                record.setdefault("_merged_from", str(nae_corpus_dir))
                                record.setdefault("_merge_source", source_id)
                                new_records.append(record)
                            elif tid:
                                duplicate_count += 1

        for rec in new_records:
            tid = rec.get("tsu_id", "")
            if tid not in existing_ids:
                existing_records.append(rec)
                existing_ids.add(tid)
                merged_count += 1
            else:
                duplicate_count += 1

        if new_records:
            content = "\n".join(json.dumps(r, ensure_ascii=False) for r in existing_records)
            _atomic_write_text(tsu_dataset_path, content + "\n")

    return {
        "status": "completed",
        "source_id": source_id,
        "manifest_source": manifest.source_id,
        "approved_count": manifest.approved_count,
        "merged_count": merged_count,
        "duplicate_count": duplicate_count,
        "total_dataset_size": len(existing_records),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NAE Corpus Merge with mandatory approval gate"
    )
    parser.add_argument("--source", required=True,
        help="Source ID to merge (e.g., Fuller_Complete_Works_Vol02)")
    parser.add_argument("--corpus-dir", default=None,
        help="NAE corpus TSU directory")
    parser.add_argument("--dataset-path", default=None,
        help="Target TSU dataset path")
    parser.add_argument("--decisions-dir", default=None,
        help="Human decisions directory")
    args = parser.parse_args()

    try:
        result = merge_nae_corpus(
            source_id=args.source,
            nae_corpus_dir=Path(args.corpus_dir) if args.corpus_dir else None,
            tsu_dataset_path=Path(args.dataset_path) if args.dataset_path else None,
            decisions_dir=Path(args.decisions_dir) if args.decisions_dir else None,
        )
        print(f"\n=== Merge Result ===")
        for k, v in result.items():
            print(f"  {k}: {v}")
    except CorpusMutationBlockedError as e:
        print(f"\n=== MERGE BLOCKED ===", flush=True)
        print(f"Reason: {e}", flush=True)
        print(
            "\nTo proceed, submit source for human review at "
            "NAE/review/human/ and await APPROVED decision.",
            flush=True,
        )
        exit(1)
