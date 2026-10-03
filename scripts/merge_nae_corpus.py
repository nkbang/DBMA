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
  - No implicit production default — data_root must be explicit
  - dataset/manifest/registry must share the same data root
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

# Default config path — used when config_path is not explicitly provided
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

# Approval gate import — mutation code의 진입점 (PR #111)
from scripts.corpus_approval_gate import (
    CorpusMutationBlockedError,
    verify_corpus_mutation_approval,
    build_approval_manifest,
    validate_merge_plan_against_manifest,
)

from core.tsu_builder import (
    tsu_dataset_lock,
    write_tsu_dataset,
    write_manifest,
)
from core.identity_registry import load_identity_registry, save_identity_registry


# ---------------------------------------------------------------------------
# Registry comparison allowlist (Rev.2 + Rev.3)
# ---------------------------------------------------------------------------
# ONLY these two fields are excluded from registry document comparison.
# Every other field — including pipeline_state, last_processed_at,
# ingest_status, chunk_count, corpus_membership, pipeline_flags, etc. —
# is a comparison target (fail-closed).
#
# Rationale: reader usage in ui/pages/library.py:593-594,606 is for
# screen display only; these fields still affect dataset inclusion/exclusion
# and TSU record content via readers in hybrid_candidate_pipeline.py and
# index_orchestrator.py.
#
# [Rev.3] Both single and double quotes are searched:
#   git grep -nE "['\"]<field>['\"]" 6f311d1f -- core scripts ui NAE
EXCLUDED_FROM_COMPARISON: frozenset[str] = frozenset({"excluded_at", "exclude_reason"})


def compute_registry_preimage_hash(doc_entry: dict[str, object]) -> str:
    """Compute SHA-256 pre-image hash of a registry document entry.

    Uses ALL fields except those in EXCLUDED_FROM_COMPARISON.
    This includes pipeline_flags sub-fields.

    Returns hex digest string.
    """
    import json as _json

    # Build a canonical representation excluding the allowlist fields
    filtered: dict[str, object] = {}
    for key, value in doc_entry.items():
        if key in EXCLUDED_FROM_COMPARISON:
            continue
        # Deep-copy nested dicts (e.g., pipeline_flags)
        if isinstance(value, dict):
            filtered[key] = {k: v for k, v in value.items()}
        elif isinstance(value, list):
            filtered[key] = list(value)
        else:
            filtered[key] = value

    canonical = _json.dumps(filtered, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compare_registry_entries(
    existing: dict[str, object],
    incoming: dict[str, object],
) -> tuple[bool, list[str]]:
    """Compare two registry document entries for equality.

    Returns (is_equal, list_of_differences).
    Fields in EXCLUDED_FROM_COMPARISON are always skipped.
    All other fields are compared (fail-closed).

    Nested dicts (pipeline_flags) and lists are compared element-wise.
    """
    differences: list[str] = []

    all_keys = set(existing.keys()) | set(incoming.keys())
    for key in sorted(all_keys):
        if key in EXCLUDED_FROM_COMPARISON:
            continue

        has_existing = key in existing
        has_incoming = key in incoming

        if has_existing and not has_incoming:
            differences.append(f"missing_in_incoming: {key}")
            continue
        if has_incoming and not has_existing:
            differences.append(f"missing_in_existing: {key}")
            continue

        old_val = existing[key]
        new_val = incoming[key]

        if isinstance(old_val, dict) and isinstance(new_val, dict):
            # Recurse into nested dicts (e.g., pipeline_flags)
            sub_equal, sub_diffs = compare_registry_entries(old_val, new_val)
            if not sub_equal:
                for d in sub_diffs:
                    differences.append(f"{key}.{d}")
        elif isinstance(old_val, list) and isinstance(new_val, list):
            if old_val != new_val:
                differences.append(f"{key}: {old_val!r} != {new_val!r}")
        else:
            if old_val != new_val:
                differences.append(f"{key}: {old_val!r} != {new_val!r}")

    return (len(differences) == 0, differences)


# ---------------------------------------------------------------------------
# Production path safety infrastructure
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TargetPaths:
    """Resolved mutation target paths — all derived from a single data_root."""
    data_root: Path | None
    dataset_path: Path
    manifest_path: Path
    registry_path: Path
    is_production: bool


def resolve_target_paths(
    data_root: Optional[Path],
    config_path: Optional[Path] = None,
) -> TargetPaths:
    """Resolve mutation target paths from explicit data_root."""
    if data_root is not None:
        resolved = Path(data_root).resolve()

        # R3: hardlink detection — FAIL-CLOSED
        if _detect_hardlink_alias(resolved, config_path):
            raise CorpusMutationBlockedError(
                f"Hardlink alias to production detected: {resolved}"
            )

        # Canonical target paths (R1)
        dataset_path = resolved / "output" / "bench" / "tsu_dataset.jsonl"
        manifest_path_resolved = resolved / "output" / "bench" / "tsu_manifest.json"
        registry_path_resolved = resolved / "data" / "제련완성본" / "registry" / "documents.json"

        # R2: production identity check
        is_production = _is_production_identity(resolved, config_path)
        return TargetPaths(
            data_root=resolved,
            dataset_path=dataset_path,
            manifest_path=manifest_path_resolved,
            registry_path=registry_path_resolved,
            is_production=is_production,
        )

    # No data_root provided — fail closed (no implicit defaults)
    return TargetPaths(
        data_root=None,
        dataset_path=Path(""),
        manifest_path=Path(""),
        registry_path=Path(""),
        is_production=False,
    )


def _load_production_root(config_path: Optional[Path] = None) -> str:
    """Load merge-safety.production_root from config.yaml.

    Returns the absolute path string.
    Fails closed on missing config, missing key, read errors, relative paths,
    or non-existent directories.

    Note: config_path=None uses _DEFAULT_CONFIG_PATH (the project's config.yaml).
    """
    import yaml

    # Use default config when not specified
    if config_path is None:
        config_path = _DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise CorpusMutationBlockedError(
            f"Config file not found: {config_path!r}"
        )

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except Exception as exc:
        raise CorpusMutationBlockedError(
            f"Failed to read config file {config_path!r}: {exc}"
        ) from exc

    if not isinstance(cfg, dict):
        raise CorpusMutationBlockedError(
            f"Config file {config_path!r} does not contain a YAML mapping"
        )

    merge_safety = cfg.get("merge-safety")
    if not isinstance(merge_safety, dict):
        raise CorpusMutationBlockedError(
            f"Config missing 'merge-safety' section: {config_path!r}"
        )

    prod_root = merge_safety.get("production_root")
    if prod_root is None:
        raise CorpusMutationBlockedError(
            f"Config 'merge-safety.production_root' key not found: {config_path!r}"
        )

    # Must be absolute path
    if not os.path.isabs(prod_root):
        raise CorpusMutationBlockedError(
            f"merge-safety.production_root must be an absolute path, got: {prod_root!r}"
        )

    prod_path = Path(prod_root)
    if not prod_path.is_dir():
        raise CorpusMutationBlockedError(
            f"merge-safety.production_root does not exist: {prod_root!r}"
        )

    return str(prod_path.resolve())


def _is_production_identity(candidate: Path, config_path: Optional[Path] = None) -> bool:
    """Determine if candidate is the production target.

    Uses a single common function for all production checks:
    - existing target: os.path.samefile based
    - missing target: parent identity + lexical containment
    - mixed definition: fail-closed (handled by caller)

    Does NOT use: cwd, relative path equivalence, __file__ (except config lookup),
    stored (st_dev, st_ino).

    Returns True only if config is valid AND candidate matches production root.
    Raises CorpusMutationBlockedError on any config failure (fail-closed).
    """
    prod_root_str = _load_production_root(config_path)
    # _load_production_root now raises on any config failure, so we only get here
    # when config is valid and production_root is set.

    prod_root = Path(prod_root_str)

    # Resolve candidate to absolute
    try:
        candidate_resolved = candidate.resolve()
    except (OSError, ValueError):
        return False

    # Case 1: candidate exists and is samefile as production root
    if candidate_resolved.exists() and prod_root.exists():
        try:
            if os.path.samefile(str(candidate_resolved), str(prod_root)):
                return True
        except OSError:
            pass

    # Case 2: candidate doesn't exist — check parent identity + containment
    if not candidate_resolved.exists():
        # Check if the parent directory is production root
        parent = candidate_resolved.parent
        try:
            parent_resolved = parent.resolve()
            if parent_resolved.exists() and os.path.samefile(str(parent_resolved), str(prod_root)):
                return True
        except OSError:
            pass

        # Check lexical containment under production root (NFC + case normalized)
        import unicodedata

        candidate_norm = unicodedata.normalize("NFC", str(candidate_resolved))
        prod_norm = unicodedata.normalize("NFC", str(prod_root))
        candidate_lower = candidate_norm.casefold()
        prod_lower = prod_norm.casefold()

        if candidate_lower.startswith(prod_lower + os.sep):
            return True

    # Case 3: mixed definition — candidate resolves to production inode
    # but data_root is not production root → fail-closed (handled by caller)
    return False


def _detect_hardlink_alias(candidate: Path, config_path: Optional[Path] = None) -> bool:
    """Detect if candidate is a hardlink alias to production.

    FAIL-CLOSED: checks the three canonical target files (dataset, manifest,
    documents.json) for hardlink/symlink aliases to production.

    Does NOT use directory st_nlink (directories always have nlink > 1 due to
    subdirectory entries). Only checks actual target files.
    """
    prod_root_str = _load_production_root(config_path)
    # _load_production_root now raises on any config failure, so we only get here
    # when config is valid and production_root is set.

    prod_root = Path(prod_root_str)

    # If candidate IS the production root itself, it's not an alias — it's production.
    try:
        if candidate.resolve() == prod_root.resolve():
            return False
    except OSError:
        pass

    # Check the three canonical target files under candidate
    target_files = [
        candidate / "output" / "bench" / "tsu_dataset.jsonl",
        candidate / "output" / "bench" / "tsu_manifest.json",
        candidate / "data" / "제련완성본" / "registry" / "documents.json",
    ]

    for target_file in target_files:
        if not target_file.exists():
            continue

        try:
            # Check if this file is a symlink pointing to production
            if target_file.is_symlink():
                link_target = target_file.resolve()
                if link_target.exists() and os.path.samefile(str(link_target), str(prod_root)):
                    return True
                # Also check if the symlink target is under production root
                try:
                    prod_resolved = prod_root.resolve()
                    if str(link_target).startswith(str(prod_resolved) + os.sep):
                        return True
                except OSError:
                    pass

            # Check if this file has same inode as a file in production root
            try:
                target_stat = target_file.stat()
                # Check st_nlink > 1 (actual hardlink evidence for files)
                if target_stat.st_nlink > 1:
                    return True
            except OSError:
                pass

        except OSError:
            continue

    return False


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
    target_root: Path,
    source_id: str,
    dataset_path: Path,
    decisions_dir: Path,
    approval_dir: Path | None = None,
) -> tuple[bool, str]:
    """Verify production target approval artifact exists and is valid.

    Args:
        target_root: The resolved output root path.
        source_id: Source ID to look up.
        dataset_path: Current dataset path for SHA comparison.
        decisions_dir: Decisions directory (for context).
        approval_dir: Explicit approval directory override (for testing).
                      Defaults to NAE/review/human/production_targets/.
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
        "schema_version", "source_id", "target_root_realpath",
        "reviewer_id", "gate_id", "dataset_sha256_before",
        "final_decision", "approved_at",
    ]
    for field in required_fields:
        if field not in approval or not approval[field]:
            return False, f"Missing required field in approval artifact: {field}"

    sv = approval["schema_version"]
    if not isinstance(sv, int) or sv < 1:
        return False, f"Invalid schema_version: {sv}"

    if approval["source_id"] != source_id:
        return False, (
            f"source_id mismatch: approval={approval['source_id']!r}, "
            f"current={source_id!r}"
        )

    target_realpath = str(target_root.resolve())
    if approval["target_root_realpath"] != target_realpath:
        return False, (
            f"target_root_realpath mismatch: approval={approval['target_root_realpath']!r}, "
            f"current={target_realpath!r}"
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
    data_root: Optional[Path] = None,
    nae_corpus_dir: Optional[Path] = None,
    decisions_dir: Optional[Path] = None,
    config_path: Optional[Path] = None,
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
      - data_root must be explicit — no implicit production default
      - dataset/manifest/registry derived from data_root
      - Production target requires separate approval artifact
      - config_path defaults to _DEFAULT_CONFIG_PATH when not specified
    """
    # Path resolution via resolve_target_paths() — no implicit defaults
    target = resolve_target_paths(
        data_root=data_root,
        config_path=config_path,
    )

    # Block if no mutation paths specified at all
    if target.data_root is None:
        raise CorpusMutationBlockedError(
            "No data_root or mutation paths specified. "
            "Provide explicit --data-root."
        )

    # Use resolved paths
    tsu_dataset_path = target.dataset_path
    manifest_path = target.manifest_path
    registry_path = target.registry_path

    # Corpus and decisions dir defaults (non-mutation paths — safe to default)
    nae_corpus_dir = Path(nae_corpus_dir or (Path("NAE") / "corpus" / "tsu"))
    decisions_dir = Path(decisions_dir or (Path("NAE") / "review" / "human" / "decisions"))

    # Production target approval gate — before any mutation
    if target.is_production:
        print(f"\nProduction target detected: {target.data_root}")
        valid, reason = verify_production_target_approval(
            target_root=target.data_root,
            source_id=source_id or "",
            dataset_path=target.dataset_path,
            decisions_dir=decisions_dir,
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
    parser.add_argument("--data-root", required=True,
        help="Explicit data root for dataset/manifest/registry mutation")
    parser.add_argument("--corpus-dir", default=None,
        help="NAE corpus TSU directory")
    parser.add_argument("--decisions-dir", default=None,
        help="Human decisions directory")
    args = parser.parse_args()

    try:
        result = merge_nae_corpus(
            source_id=args.source,
            data_root=Path(args.data_root),
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
