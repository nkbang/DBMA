#!/usr/bin/env python3
"""scripts/merge_nae_corpus.py — Merge NAE corpus TSU into production TSU.

Safety contract (F-3):
  - Idempotent by tsu_id (never document_id)
  - Atomic dataset write via core.tsu_builder helpers
  - Validation before replace
  - Provenance preservation (scriptures, copyright_status, etc.)
  - Manifest via core.tsu_builder.write_manifest()

Approval gate (PR #111):
  - Mandatory verify_mutation_gate() before any mutation
  - Fail-closed: no approval -> no mutation
  - CLI option cannot circumvent the gate

Production path safety (NAE-MERGE-PRODUCTION-PATH-SAFETY-001):
  - No implicit production default — output_root must be explicit
  - dataset/manifest/registry must share the same output root
  - Production target requires separate approval artifact
  - realpath-based production detection (no string comparison)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Approval gate import — mutation code의 진입점 (PR #111)
from scripts.corpus_approval_gate import (
    CorpusMutationBlockedError,
    verify_corpus_mutation_approval,
    build_approval_manifest,
    validate_merge_plan_against_manifest,
)

from core.identity_registry import load_identity_registry, save_identity_registry
from core.tsu_builder import (
    tsu_dataset_lock,
    write_tsu_dataset,
    write_manifest,
)


# ---------------------------------------------------------------------------
# Production path safety constants (monkeypatchable for tests)
# ---------------------------------------------------------------------------

_REPO_ROOT: Path = Path(__file__).resolve().parent.parent

_PRODUCTION_DATASET_REALPATH: Path = _REPO_ROOT / "output" / "bench" / "tsu_dataset.jsonl"
_PRODUCTION_MANIFEST_REALPATH: Path = _REPO_ROOT / "output" / "bench" / "tsu_manifest.json"
_PRODUCTION_REGISTRY_REALPATH: Path = _REPO_ROOT / "data" / "제련완성본" / "registry" / "documents.json"

_PRODUCTION_DIRS: tuple[Path, ...] = (
    _REPO_ROOT / "output" / "bench",
    _REPO_ROOT / "data" / "제련완성본" / "registry",
)


@dataclass(frozen=True)
class ResolvedPaths:
    """Three individually-specified mutation target paths with production status."""
    dataset_path: Path
    manifest_path: Path
    registry_path: Path
    is_production: bool  # True if ANY of the three targets production
    mixed_paths: bool = False  # True if some but not all are production


def _realpath(p: Path) -> Path:
    """Resolve to absolute realpath (follows symlinks, .., etc.)."""
    return p.resolve()


def _is_production_realpath(resolved: Path) -> bool:
    """Check if resolved path equals one of the three production targets OR is under a production dir."""
    for prod_target in (_PRODUCTION_DATASET_REALPATH, _PRODUCTION_MANIFEST_REALPATH, _PRODUCTION_REGISTRY_REALPATH):
        if resolved == prod_target:
            return True
    for prod_dir in _PRODUCTION_DIRS:
        try:
            resolved.relative_to(prod_dir)
            return True
        except ValueError:
            pass
    return False


def resolve_mutation_paths(
    tsu_dataset_path: Path,
    manifest_path: Path,
    registry_path: Path,
) -> ResolvedPaths:
    """Resolve and validate three individually-specified mutation paths.

    R1: All three are mandatory — no defaults, no output_root derivation.
    R2: Production detection via realpath (cwd-independent).
    R3: Mixed-path blocking — if some but not all point to production, BLOCK.
    R5: No string heuristics ("bench" in str(p), etc.).
    """
    ds = _realpath(tsu_dataset_path)
    mf = _realpath(manifest_path)
    rg = _realpath(registry_path)

    ds_prod = _is_production_realpath(ds)
    mf_prod = _is_production_realpath(mf)
    rg_prod = _is_production_realpath(rg)

    any_prod = ds_prod or mf_prod or rg_prod
    mixed = (ds_prod or mf_prod or rg_prod) and not (ds_prod and mf_prod and rg_prod)

    if mixed:
        raise CorpusMutationBlockedError(
            f"Mixed mutation paths detected — some but not all point to production. "
            f"dataset={'PROD' if ds_prod else 'tmp'}, "
            f"manifest={'PROD' if mf_prod else 'tmp'}, "
            f"registry={'PROD' if rg_prod else 'tmp'}"
        )

    return ResolvedPaths(
        dataset_path=ds,
        manifest_path=mf,
        registry_path=rg,
        is_production=any_prod,
        mixed_paths=mixed,
    )


def compute_dataset_sha256(dataset_path: Path) -> str:
    """Compute SHA-256 hash of a dataset file."""
    h = hashlib.sha256()
    if not dataset_path.exists():
        return ""
    with open(dataset_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_production_target_approval(
    target_paths_realpath: list[str],
    source_id: str,
    dataset_path: Path,
    decisions_dir: Path,
    approval_dir: Path | None = None,
) -> tuple[bool, str]:
    """Verify production target approval artifact exists and is valid.

    R4: Changed from target_root_realpath to target_paths_realpath (3 paths).
    """
    if approval_dir is not None:
        approval_path = approval_dir / f"{source_id}.json"
    else:
        approval_path = Path("NAE") / "review" / "human" / "production_targets" / f"{source_id}.json"

    if not approval_path.exists():
        return False, f"Production target approval artifact not found: {approval_path}"

    try:
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return False, f"Failed to read production target approval: {e}"

    required_fields = [
        "schema_version", "source_id", "target_paths_realpath",
        "reviewer_id", "gate_id", "dataset_sha256_before",
        "final_decision", "approved_at",
    ]
    for field_name in required_fields:
        if field_name not in approval or not approval[field_name]:
            return False, f"Missing required field in approval artifact: {field_name}"

    sv = approval["schema_version"]
    if not isinstance(sv, int) or sv < 1:
        return False, f"Invalid schema_version: {sv}"

    if approval["source_id"] != source_id:
        return False, (
            f"source_id mismatch: approval={approval['source_id']!r}, "
            f"current={source_id!r}"
        )

    # R4: target_paths_realpath check (was target_root_realpath)
    approval_paths = approval["target_paths_realpath"]
    if not isinstance(approval_paths, list) or len(approval_paths) != 3:
        return False, f"target_paths_realpath must be a list of 3 strings"
    for i, (app_path, cur_path) in enumerate(zip(approval_paths, target_paths_realpath)):
        if app_path != cur_path:
            return False, (
                f"target_paths_realpath[{i}] mismatch: approval={app_path!r}, "
                f"current={cur_path!r}"
            )

    if approval["final_decision"] != "APPROVED":
        return False, f"final_decision is not APPROVED: {approval['final_decision']!r}"

    current_sha = compute_dataset_sha256(dataset_path)
    if approval["dataset_sha256_before"] != current_sha:
        return False, (
            f"dataset_sha256 mismatch: approval={approval['dataset_sha256_before']!r}, "
            f"current={current_sha!r}"
        )

    return True, "Production target approval verified"


def _nae_tsu_id(nae_rec: dict) -> str | None:
    """NAE record의 production tsu_id. 명시된 tsu_id 우선, 없으면 NAE-{id}.

    planned_tsu_ids 계산과 실제 기록(_transform_nae_record)이 같은 함수를 쓰도록
    하여 승인 범위와 mutation 범위의 불일치를 구조적으로 막는다.
    """
    if nae_rec.get("tsu_id"):
        return nae_rec["tsu_id"]
    if nae_rec.get("id") is not None:
        return f"NAE-{nae_rec['id']}"
    return None


def _transform_nae_record(nae_rec: dict, doc_id: str) -> dict:
    """Transform a NAE corpus TSU record to production TSU format.

    F-3 provenance fix: preserve NAE scriptures instead of discarding them.
    """
    claim = nae_rec.get("claim", "")
    has_korean = any("\uac00" <= c <= "\ud7a3" for c in claim)
    language = "ko" if has_korean else "en"

    doctrine = nae_rec.get("doctrine", "")
    doctrine_category = [doctrine] if doctrine else []

    baptist_themes = []
    if doctrine:
        doc_lower = doctrine.lower()
        if "soteriology" in doc_lower:
            baptist_themes.append("soteriology")
        elif "ecclesiology" in doc_lower:
            baptist_themes.append("ecclesiology")
        elif "pneumatology" in doc_lower:
            baptist_themes.append("pneumatology")
        elif "christology" in doc_lower:
            baptist_themes.append("christology")
        elif "trinitarian" in doc_lower or "trinity" in doc_lower:
            baptist_themes.append("trinitarian_doctrine")
        elif "baptism" in doc_lower:
            baptist_themes.append("baptism")
        elif "covenant" in doc_lower:
            baptist_themes.append("covenant_theology")
        elif "eschatology" in doc_lower:
            baptist_themes.append("eschatology")
        elif "hermeneutics" in doc_lower or "exegesis" in doc_lower:
            baptist_themes.append("biblical_hermeneutics")

    nae_scriptures = nae_rec.get("scriptures")
    verse_mapping = {}
    if nae_scriptures is not None and nae_scriptures:
        verse_mapping = {"_nae_scriptures": nae_scriptures}

    return {
        "tsu_id": _nae_tsu_id(nae_rec),
        "document_id": doc_id,
        "chunk_id": _nae_tsu_id(nae_rec),
        "content": nae_rec.get("source_text", ""),
        "verse_mapping": verse_mapping,
        "themes": [],
        "title": nae_rec.get("book", ""),
        "author": nae_rec.get("author", ""),
        "metadata_source": "nae_canonical",
        "chapter": None,
        "page": nae_rec.get("page"),
        "source_file": f"{nae_rec.get('identifier', '')}.jsonl",
        "language": language,
        "source_type": "nae_canonical",
        "content_quality": {
            "noise_type": "NAE_CANONICAL",
            "quality_score": 1.0,
            "section_type": "claim",
        },
        "structure": {},
        "theological_claim": claim,
        "doctrine_category": doctrine_category,
        "baptist_theme": baptist_themes,
        "source_provenance": None,
        "nae_metadata": {
            "nae_id": nae_rec.get("id"),
            "nae_doctrine": doctrine,
            "nae_confidence": nae_rec.get("confidence"),
            "nae_extraction_method": nae_rec.get("extraction_method"),
            "nae_review_status": nae_rec.get("review_status"),
            "source_type": nae_rec.get("source_type"),
            "copyright_status": nae_rec.get("copyright_status"),
            "author_id": nae_rec.get("author_id"),
            "work_id": nae_rec.get("work_id"),
            "scriptures": nae_scriptures,
        },
    }


def _read_existing_dataset(dataset_path: Path) -> list[dict]:
    """Read existing TSU dataset, return list of records.

    Returns [] for missing files or empty content — never crashes on
    empty/invalid input.
    """
    p = Path(dataset_path)
    if not p.exists():
        return []
    records = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _validate_dataset(records: list[dict], dataset_path: Path) -> None:
    """Validate candidate dataset before atomic replace. Raises ValueError on failure."""
    if not records:
        raise ValueError("Dataset contains zero records")
    for i, rec in enumerate(records):
        if "tsu_id" not in rec or not rec["tsu_id"]:
            raise ValueError(f"Record {i} missing tsu_id")
    tsu_ids = [rec["tsu_id"] for rec in records]
    if len(tsu_ids) != len(set(tsu_ids)):
        duplicates = [tid for tid in tsu_ids if tsu_ids.count(tid) > 1]
        raise ValueError(f"Duplicate tsu_id found: {set(duplicates)}")
    if dataset_path.exists():
        existing = _read_existing_dataset(dataset_path)
        existing_ids = {r["tsu_id"] for r in existing}
        new_ids = {rec["tsu_id"] for rec in records}
        preserved = existing_ids & new_ids
        if len(preserved) != len(existing_ids):
            missing = existing_ids - preserved
            raise ValueError(f"Unrelated TSU not preserved: {missing}")


def merge_nae_corpus(
    source_id: Optional[str] = None,
    nae_corpus_dir: Optional[Path] = None,
    tsu_dataset_path: Path | None = None,
    manifest_path: Path | None = None,
    registry_path: Path | None = None,
    decisions_dir: Optional[Path] = None,
    approval_dir: Optional[Path] = None,
) -> dict:
    """Merge NAE corpus TSU into production TSU (F-3 safe).

    F-3 contract:
      - Idempotent by tsu_id
      - Atomic dataset write
      - Validation before replace
      - Manifest via core.tsu_builder.write_manifest()
      - Provenance preservation

    Approval gate (PR #111):
      - verify_mutation_gate() is called BEFORE any mutation
      - No CLI option or environment variable can circumvent this gate
      - Function-level enforcement: direct Python call also triggers gate

    Production path safety (NAE-MERGE-PRODUCTION-PATH-SAFETY-001):
      - tsu_dataset_path, manifest_path, registry_path — 모두 필수 명시
      - 개별 경로 각각 realpath 판정
      - Production target requires separate approval artifact (target_paths_realpath)
    """
    # R1: All three paths mandatory — no defaults, no output_root
    if tsu_dataset_path is None or manifest_path is None or registry_path is None:
        missing = []
        if tsu_dataset_path is None:
            missing.append("tsu_dataset_path")
        if manifest_path is None:
            missing.append("manifest_path")
        if registry_path is None:
            missing.append("registry_path")
        raise CorpusMutationBlockedError(
            f"Required mutation paths not specified: {', '.join(missing)}. "
            "All three must be explicitly provided."
        )

    # R2/R3: Resolve and validate paths (realpath-based, mixed-path blocking)
    target = resolve_mutation_paths(
        tsu_dataset_path=tsu_dataset_path,
        manifest_path=manifest_path,
        registry_path=registry_path,
    )

    # Use resolved paths
    tsu_dataset_path = target.dataset_path
    manifest_path = target.manifest_path
    registry_path = target.registry_path

    # Corpus and decisions dir defaults (non-mutation paths — safe to default)
    nae_corpus_dir = Path(nae_corpus_dir or (Path("NAE") / "corpus" / "tsu"))
    decisions_dir = Path(decisions_dir or (Path("NAE") / "review" / "human" / "decisions"))

    # R6: Production target approval gate — before any mutation
    if target.is_production:
        print(f"\nProduction target detected: dataset={target.dataset_path}")
        tp_realpath = [str(target.dataset_path), str(target.manifest_path), str(target.registry_path)]
        valid, reason = verify_production_target_approval(
            target_paths_realpath=tp_realpath,
            source_id=source_id or "",
            dataset_path=tsu_dataset_path,
            decisions_dir=decisions_dir,
            approval_dir=approval_dir,
        )
        if not valid:
            raise CorpusMutationBlockedError(
                f"Production target approval FAILED: {reason}"
            )
        print(f"  Production target approval PASSED: {reason}")

    # 0. TSU planning — planned_tsu_ids 생성 (approval gate용)
    planned_tsu_ids: set[str] = set()
    if source_id is not None and nae_corpus_dir.exists():
        for tsu_dir in sorted(nae_corpus_dir.glob("*")):
            tsu_file = tsu_dir / "tsu.json"
            if tsu_file.exists():
                data = json.loads(tsu_file.read_text(encoding="utf-8"))
                for record in data:
                    # planned ID는 실제 기록될 ID와 동일한 _nae_tsu_id()로 계산
                    if record.get("work_id") == source_id:
                        tid = _nae_tsu_id(record)
                        if tid:
                            planned_tsu_ids.add(tid)

    if not planned_tsu_ids:
        return {
            "status": "skipped",
            "reason": f"No TSU records found for source={source_id!r} in {nae_corpus_dir}",
            "merged_count": 0,
            "duplicate_count": 0,
        }

    # 1. APPROVAL GATE — mutation 전 필수 승인 검증 (PR #111)
    print(f"\nVerifying corpus mutation approval gate for source={source_id!r}...")
    gate_result = verify_corpus_mutation_approval(
        source_id, decisions_dir, frozenset(planned_tsu_ids)
    )

    if not gate_result.approved:
        raise CorpusMutationBlockedError(
            f"Corpus mutation BLOCKED for source={source_id!r}: {gate_result.reason}"
        )

    # Build manifest for audit trail
    approval_manifest = build_approval_manifest(source_id, decisions_dir)
    if approval_manifest is None:
        raise CorpusMutationBlockedError(
            f"Corpus mutation BLOCKED: manifest build failed for source={source_id!r}"
        )

    # Validate merge plan against manifest
    valid, reason = validate_merge_plan_against_manifest(
        approval_manifest, frozenset(planned_tsu_ids)
    )
    if not valid:
        raise CorpusMutationBlockedError(f"Corpus mutation BLOCKED: {reason}")

    print(f"  Gate PASSED: {approval_manifest.approved_count} TSUs approved by {approval_manifest.reviewer_id}")

    # 2. Read existing dataset (moved inside lock)
    with tsu_dataset_lock(tsu_dataset_path):
        print(f"\nReading existing TSU dataset from {tsu_dataset_path}...")
        existing_records = _read_existing_dataset(tsu_dataset_path)
        print(f"  Found {len(existing_records)} existing records")

        # 3. Read NAE corpus TSU records
        print(f"\nScanning NAE corpus TSU at {nae_corpus_dir}...")
        if not nae_corpus_dir.exists():
            raise FileNotFoundError(
                f"NAE corpus directory not found: {nae_corpus_dir}"
            )

        nae_records = []
        nae_docs_info: dict[Path, dict] = {}

        for item in sorted(nae_corpus_dir.glob("*")):
            if not item.is_dir():
                continue
            tsu_file = item / "tsu.json"
            if not tsu_file.exists():
                continue

            # 레코드 단위 source filter: 승인 범위 밖 work_id는 절대 병합하지 않는다
            data = [
                r for r in json.loads(tsu_file.read_text(encoding="utf-8"))
                if r.get("work_id") == source_id
            ]
            if not data:
                continue
            doc_id = f"nae_{item.name}"
            nae_docs_info[item] = {
                "document_id": doc_id,
                "title": data[0].get("book", ""),
                "author": data[0].get("author", ""),
                "record_count": len(data),
            }

            for nae_rec in data:
                prod_rec = _transform_nae_record(nae_rec, doc_id)
                nae_records.append(prod_rec)

        print(f"  Read {len(nae_records)} NAE corpus records from {len(nae_docs_info)} documents")

        # 승인 범위 방어선: mutation 대상 ID 집합 == 승인된 planned 집합이어야 한다
        mutation_ids = {r["tsu_id"] for r in nae_records}
        if mutation_ids != planned_tsu_ids:
            raise CorpusMutationBlockedError(
                "Corpus mutation BLOCKED: mutation set != approved plan "
                f"(extra={sorted(mutation_ids - planned_tsu_ids)[:5]}, "
                f"missing={sorted(planned_tsu_ids - mutation_ids)[:5]})"
            )

        # 4. Dedup by tsu_id (F-3 idempotency)
        existing_ids = {r["tsu_id"] for r in existing_records}
        new_records = [
            rec for rec in nae_records
            if rec["tsu_id"] not in existing_ids
        ]

        # 5. Compose candidate dataset
        all_records = existing_records + new_records

        # 6. Validation before replace (F-3)
        print("\nValidating candidate dataset...")
        _validate_dataset(all_records, tsu_dataset_path)
        print(f"  Validation passed: {len(all_records)} records, no duplicates")

        # 7. Atomic write (F-3) — now inside lock
        print(f"\nWriting merged TSU to {tsu_dataset_path}...")
        write_tsu_dataset(all_records, tsu_dataset_path)
        print(f"  Written {len(all_records)} records atomically")

        # 8. Update registry (F-3: corpus_membership="default")
        print(f"\nUpdating registry at {registry_path}...")
        registry = load_identity_registry(registry_path)

        for item, info in nae_docs_info.items():
            doc_id = info["document_id"]
            if doc_id not in registry["documents"]:
                registry["documents"][doc_id] = {
                    "document_id": doc_id,
                    "source_file": f"{item.name}.jsonl",
                    "title": info["title"],
                    "author": info["author"],
                    "status": "processed",
                    "chunk_count": info["record_count"],
                    "language": "en",
                    "source_type": "nae_canonical",
                    "doc_type": "신학",
                    "ingest_status": "PROCESSED",
                    "pipeline_state": "INDEXED",
                    "created_at": datetime.now().isoformat(),
                    "last_processed_at": datetime.now().isoformat(),
                    "last_content_hash": f"nae_{item.name}",
                    "corpus_membership": "default",
                    "pipeline_flags": {
                        "ingested": True,
                        "copied": True,
                        "extracted": True,
                        "cleaned": True,
                        "chunked": True,
                        "output_generated": True,
                        "verified": True,
                    },
                }

        save_identity_registry(registry, str(registry_path))
        print(f"  Updated registry with {len(nae_docs_info)} new documents")

        # 9. Update manifest via core.tsu_builder.write_manifest() (F-3)
        print(f"\nUpdating manifest at {manifest_path}...")
        final_manifest = write_manifest(
            records=all_records,
            registry=registry,
            manifest_path=manifest_path,
            registry_path=registry_path,
            dataset_path=tsu_dataset_path,
        )
        print(f"  Updated manifest (tsu_count={final_manifest['tsu_count']})")

    return {
        "status": "completed",
        "source_id": source_id,
        "manifest_source": approval_manifest.source_id,
        "approved_count": approval_manifest.approved_count,
        "existing_records": len(existing_records),
        "nae_records": len(nae_records),
        "new_records_after_dedup": len(new_records),
        "duplicate_count": len(nae_records) - len(new_records),
        "total_records": len(all_records),
        "new_documents": len(nae_docs_info),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NAE Corpus Merge with mandatory approval gate"
    )
    parser.add_argument("--source", required=True,
        help="Source ID to merge (e.g., Fuller_Complete_Works_Vol02)")
    parser.add_argument("--dataset-path", required=True,
        help="Absolute path to tsu_dataset.jsonl")
    parser.add_argument("--manifest-path", required=True,
        help="Absolute path to tsu_manifest.json")
    parser.add_argument("--registry-path", required=True,
        help="Absolute path to documents.json (identity registry)")
    parser.add_argument("--corpus-dir", default=None,
        help="NAE corpus TSU directory")
    parser.add_argument("--decisions-dir", default=None,
        help="Human decisions directory")
    args = parser.parse_args()

    try:
        result = merge_nae_corpus(
            source_id=args.source,
            tsu_dataset_path=Path(args.dataset_path),
            manifest_path=Path(args.manifest_path),
            registry_path=Path(args.registry_path),
            nae_corpus_dir=Path(args.corpus_dir) if args.corpus_dir else None,
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
