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
from contextlib import contextmanager
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
from core.identity_registry import load_identity_registry, save_identity_registry, registry_lock


# ---------------------------------------------------------------------------
# B2: Common identity building blocks (must be used by _is_production_identity
#     and evaluate_approval_v2 — no duplicate NFC/casefold/samefile impl)
# ---------------------------------------------------------------------------

def _normalize_path_for_comparison(p: Path) -> str:
    """Return an NFC-normalized, casefolded string of a path.

    This is the single source of truth for path comparison normalization.
    """
    import unicodedata

    return unicodedata.normalize("NFC", str(p)).casefold()


def _paths_are_samefile(p1: Path, p2: Path) -> bool:
    """Compare two *existing* paths using os.path.samefile with OSError guard.

    Returns False when either path does not exist or samefile raises OSError.
    """
    try:
        return p1.exists() and p2.exists() and os.path.samefile(str(p1), str(p2))
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Approval v2 immutable validation boundary (S2-A)
# ---------------------------------------------------------------------------
from enum import Enum
import re as _re_module


class ApprovalState(str, Enum):
    """Approval evaluation result state."""
    VALID = "VALID"
    REJECTED = "REJECTED"


class ApprovalReasonCode(str, Enum):
    """Reason codes for REJECTED approval evaluations."""
    NOT_FOUND = "NOT_FOUND"
    UNREADABLE = "UNREADABLE"
    MALFORMED = "MALFORMED"
    SCHEMA_VERSION = "SCHEMA_VERSION"
    SOURCE_ID_UNSAFE = "SOURCE_ID_UNSAFE"
    PATH_ESCAPE = "PATH_ESCAPE"
    FIELD_MISSING = "FIELD_MISSING"
    FIELD_TYPE = "FIELD_TYPE"
    FIELD_FORMAT = "FIELD_FORMAT"
    UNKNOWN_FIELD = "UNKNOWN_FIELD"
    TARGET_MISMATCH = "TARGET_MISMATCH"
    DECISION_NOT_APPROVED = "DECISION_NOT_APPROVED"
    FUTURE_APPROVAL = "FUTURE_APPROVAL"
    DATASET_SHA_MISMATCH = "DATASET_SHA_MISMATCH"
    CONFIG_APPROVAL_DIR = "CONFIG_APPROVAL_DIR"
    # S2-B: approved plan (approval.plan_hash) != actual merge plan (computed from nae_records + targets)
    PLAN_HASH_MISMATCH = "PLAN_HASH_MISMATCH"


# Module constant for scope value — used only with DATASET_SHA_MISMATCH
FRESH_MERGE_PRECONDITION = "FRESH_MERGE_PRECONDITION"


@dataclass(frozen=True)
class ApprovalEvaluation:
    """Immutable approval evaluation result (S2-A §3-8)."""
    state: ApprovalState
    reason_code: ApprovalReasonCode | None
    source_id: str
    approved_at: str | None = None
    dataset_sha256_before: str | None = None
    scope: Optional[str] = None
    # S2-B: the approved plan_hash from the artifact. Set ONLY when state == VALID;
    # REJECTED results always carry None (a rejected approval is never a comparison basis).
    plan_hash: Optional[str] = None
    # S2-C: identity of the approval artifact that was actually validated. Set ONLY when
    # state == VALID (sha256 of the very bytes that were decoded, parsed and validated, and the
    # resolved path they were read from); REJECTED results always carry None.
    artifact_sha256: Optional[str] = None
    artifact_path: Optional[str] = None


# ---------------------------------------------------------------------------
# S2-B: plan_hash — immutable binding of "what will be merged, and where"
# ---------------------------------------------------------------------------

# Version of the plan_hash payload layout. Bump when the payload definition changes
# so that hashes of different algorithms can never be confused.
PLAN_HASH_VERSION = 1


def _canonical_json_bytes(obj: object) -> bytes:
    """Single canonical JSON serialisation used for BOTH the per-record content hash
    and the final plan hash (S2-B G-5).

    sort_keys + compact separators + ensure_ascii=False + allow_nan=False, UTF-8.
    No text normalisation (NFC etc.) is applied: content identity is exact.
    Anything that cannot be serialised canonically (NaN/Infinity, non-JSON types,
    non-str keys that cannot be sorted) fails closed.
    """
    try:
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CorpusMutationBlockedError(
            f"plan_hash: value is not canonically serialisable: {exc}"
        ) from exc


def _record_content_sha256(record: dict) -> str:
    """SHA-256 (lowercase hex, no prefix) of the canonical JSON of one transformed record."""
    return hashlib.sha256(_canonical_json_bytes(record)).hexdigest()


def compute_plan_hash(
    source_id: str,
    nae_records: list[dict],
    target_paths: list[Path] | list[str],
) -> str:
    """Compute the plan_hash of a merge plan (S2-B).

    Payload (canonical JSON):
        {"v": 1,
         "source_id": <source_id>,
         "records": [{"tsu_id": ..., "content_sha256": ...}, ...]   # sorted by tsu_id
         "targets": [dataset, manifest, registry]}                   # str(Path.resolve()), fixed order

    Pure function (no file reads; Path.resolve() only normalises the given paths).
    Not part of the hash: dataset SHA, timestamps, registry entries.

    Fails closed (CorpusMutationBlockedError) on: non-str source_id, missing/non-str/
    duplicate tsu_id, non-canonically-serialisable record content, or a target list
    that is not exactly 3 entries.
    """
    if not isinstance(source_id, str):
        raise CorpusMutationBlockedError("plan_hash: source_id must be a str")
    if len(target_paths) != 3:
        raise CorpusMutationBlockedError(
            f"plan_hash: exactly 3 targets (dataset, manifest, registry) required, got {len(target_paths)}"
        )

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for rec in nae_records:
        tsu_id = rec.get("tsu_id") if isinstance(rec, dict) else None
        if not isinstance(tsu_id, str) or not tsu_id:
            raise CorpusMutationBlockedError("plan_hash: record without a valid str tsu_id")
        if tsu_id in seen:
            raise CorpusMutationBlockedError(f"plan_hash: duplicate tsu_id {tsu_id!r}")
        seen.add(tsu_id)
        rows.append({"tsu_id": tsu_id, "content_sha256": _record_content_sha256(rec)})
    rows.sort(key=lambda r: r["tsu_id"])

    payload = {
        "v": PLAN_HASH_VERSION,
        "source_id": source_id,
        "records": rows,
        "targets": [str(Path(p).resolve()) for p in target_paths],
    }
    return "sha256:" + hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


# Required fields and their expected types for Approval v2
_APPROVAL_V2_REQUIRED_FIELDS: frozenset[str] = frozenset({
    "schema_version", "source_id", "target_paths_realpath",
    "plan_hash", "reviewer_id", "gate_id", "dataset_sha256_before",
    "final_decision", "approved_at",
})

_SOURCE_ID_PATTERN = _re_module.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")


def _load_approval_dir(config_path: Optional[Path] = None) -> str:
    """Load approval_dir from config.yaml. Fail-closed on any config failure (S2-A §3-5)."""
    import yaml

    cfg = config_path or _DEFAULT_CONFIG_PATH
    if not cfg.exists():
        raise CorpusMutationBlockedError(f"Config file not found: {cfg}")
    try:
        with open(cfg, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (yaml.YAMLError, OSError) as e:
        raise CorpusMutationBlockedError(f"Failed to read config file {cfg}: {e}") from e

    if not isinstance(data, dict):
        raise CorpusMutationBlockedError(f"Config file {cfg} does not contain a mapping")

    ms = data.get("merge-safety")
    if not isinstance(ms, dict):
        raise CorpusMutationBlockedError("merge-safety section missing in config")

    approval_dir = ms.get("approval_dir")
    if approval_dir is None:
        raise CorpusMutationBlockedError("approval_dir key missing in merge-safety section")
    if not isinstance(approval_dir, str):
        raise CorpusMutationBlockedError(
            f"approval_dir must be a string, got {type(approval_dir).__name__}"
        )
    if approval_dir == "":
        raise CorpusMutationBlockedError("approval_dir is empty")
    if not os.path.isabs(approval_dir):
        raise CorpusMutationBlockedError(
            f"approval_dir must be an absolute path, got relative: {approval_dir}"
        )
    if not os.path.exists(approval_dir):
        raise CorpusMutationBlockedError(f"approval_dir does not exist: {approval_dir}")
    if not os.path.isdir(approval_dir):
        raise CorpusMutationBlockedError(f"approval_dir is not a directory: {approval_dir}")
    if not os.access(approval_dir, os.R_OK):
        raise CorpusMutationBlockedError(f"approval_dir is not readable: {approval_dir}")

    return approval_dir


def _validate_source_id(source_id: object) -> tuple[bool, ApprovalReasonCode]:
    """Validate source_id safety (S2-A §3-4)."""
    if not isinstance(source_id, str):
        return False, ApprovalReasonCode.SOURCE_ID_UNSAFE
    if source_id == "":
        return False, ApprovalReasonCode.SOURCE_ID_UNSAFE
    parts = source_id.split("/")
    for part in parts:
        if part == "..":
            return False, ApprovalReasonCode.PATH_ESCAPE
    if not _SOURCE_ID_PATTERN.match(source_id):
        return False, ApprovalReasonCode.SOURCE_ID_UNSAFE
    if source_id.startswith("."):
        return False, ApprovalReasonCode.PATH_ESCAPE
    return True, ApprovalReasonCode.SOURCE_ID_UNSAFE


def _validate_target_paths(
    approval_target_paths: list,
    expected_paths: list,
) -> tuple[bool, ApprovalReasonCode]:
    """Validate target paths against expected TargetPaths (S2-A §3-6).

    Uses the common identity building blocks (_normalize_path_for_comparison,
    _paths_are_samefile) — no duplicate NFC/casefold/samefile implementation.
    """
    if not isinstance(approval_target_paths, list) or len(approval_target_paths) != 3:
        return False, ApprovalReasonCode.FIELD_TYPE
    if not isinstance(expected_paths, list) or len(expected_paths) != 3:
        return False, ApprovalReasonCode.TARGET_MISMATCH

    for approval_path_str, expected_path in zip(approval_target_paths, expected_paths):
        if not isinstance(approval_path_str, str):
            return False, ApprovalReasonCode.FIELD_TYPE
        approval_p = Path(approval_path_str)
        try:
            approval_resolved = approval_p.resolve()
        except (OSError, ValueError):
            return False, ApprovalReasonCode.TARGET_MISMATCH
        expected_resolved = Path(expected_path).resolve()

        if _paths_are_samefile(approval_resolved, expected_resolved):
            continue

        # Fallback: NFC + casefold lexical comparison (for non-existing paths)
        approval_norm = _normalize_path_for_comparison(approval_resolved)
        expected_norm = _normalize_path_for_comparison(expected_resolved)
        if approval_norm == expected_norm:
            continue
        return False, ApprovalReasonCode.TARGET_MISMATCH

    return True, ApprovalReasonCode.TARGET_MISMATCH


def evaluate_approval_v2(
    approval_path: Path,
    config_path: Optional[Path] = None,
    expected_target_paths: Optional[list[str]] = None,
    *,
    dataset_sha256_current: str,
    now: Optional[datetime] = None,
) -> ApprovalEvaluation:
    """Evaluate an Approval v2 artifact immutably (S2-A §3-8).

    Does NOT modify the approval artifact. Returns an immutable ApprovalEvaluation.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if not approval_path.exists():
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.NOT_FOUND,
            source_id="",
        )

    # S2-C: read the artifact bytes exactly once. The same bytes are decoded, parsed, validated
    # and hashed (artifact_sha256); the file is never re-read afterwards.
    # Existing error mapping is preserved: OSError -> MALFORMED (UNREADABLE is not used here).
    # A non-UTF-8 artifact is MALFORMED as well (previously UnicodeDecodeError escaped).
    try:
        raw_bytes = approval_path.read_bytes()
        raw = raw_bytes.decode("utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.MALFORMED,
            source_id="",
        )

    if not isinstance(data, dict):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.MALFORMED,
            source_id="",
        )

    sv = data.get("schema_version")
    if not isinstance(sv, int) or sv != 2:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.SCHEMA_VERSION,
            source_id=str(data.get("source_id", "")),
        )
    if "target_root_realpath" in data:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_MISSING,
            source_id=str(data.get("source_id", "")),
        )

    source_id = data.get("source_id")
    valid_sid, sid_reason = _validate_source_id(source_id)
    if not valid_sid:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=sid_reason,
            source_id=str(source_id) if isinstance(source_id, str) else "",
        )

    try:
        approval_dir_str = _load_approval_dir(config_path)
    except CorpusMutationBlockedError:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.CONFIG_APPROVAL_DIR,
            source_id=source_id,
        )

    try:
        approval_resolved = approval_path.resolve()
        approval_dir_resolved = Path(approval_dir_str).resolve()
        # Check if approval file is under approval_dir (containment)
        # Uses common identity building blocks — no duplicate NFC/casefold impl
        approval_parent_norm = _normalize_path_for_comparison(approval_resolved.parent)
        dir_norm = _normalize_path_for_comparison(approval_dir_resolved)
        approval_full_norm = _normalize_path_for_comparison(approval_resolved)
        if not (
            approval_parent_norm == dir_norm
            or approval_full_norm.startswith(dir_norm + os.sep)
            or approval_parent_norm.startswith(dir_norm + os.sep)
        ):
            return ApprovalEvaluation(
                state=ApprovalState.REJECTED,
                reason_code=ApprovalReasonCode.PATH_ESCAPE,
                source_id=source_id,
            )
    except OSError:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.PATH_ESCAPE,
            source_id=source_id,
        )

    known_fields = _APPROVAL_V2_REQUIRED_FIELDS
    for key in data:
        if key not in known_fields:
            return ApprovalEvaluation(
                state=ApprovalState.REJECTED,
                reason_code=ApprovalReasonCode.UNKNOWN_FIELD,
                source_id=source_id,
            )

    for field in _APPROVAL_V2_REQUIRED_FIELDS:
        if field not in data:
            return ApprovalEvaluation(
                state=ApprovalState.REJECTED,
                reason_code=ApprovalReasonCode.FIELD_MISSING,
                source_id=source_id,
            )

    # Type validation (S2-A §3-1)
    schema_version = data["schema_version"]
    if not isinstance(schema_version, int):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    target_paths = data["target_paths_realpath"]
    if not isinstance(target_paths, list):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    plan_hash = data["plan_hash"]
    if not isinstance(plan_hash, str):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    reviewer_id = data["reviewer_id"]
    if not isinstance(reviewer_id, str):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    gate_id = data["gate_id"]
    if not isinstance(gate_id, str):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    dataset_sha256_before = data["dataset_sha256_before"]
    if not isinstance(dataset_sha256_before, str):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    final_decision = data["final_decision"]
    if not isinstance(final_decision, str):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    approved_at_str = data["approved_at"]
    if not isinstance(approved_at_str, str):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    # Format validation (S2-A §3-1)
    if not isinstance(plan_hash, str) or not plan_hash.startswith("sha256:"):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_FORMAT,
            source_id=source_id,
        )
    hex_part = plan_hash[7:]
    if len(hex_part) != 64 or not all(c in "0123456789abcdef" for c in hex_part):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_FORMAT,
            source_id=source_id,
        )

    if len(dataset_sha256_before) != 64 or not all(c in "0123456789abcdef" for c in dataset_sha256_before):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_FORMAT,
            source_id=source_id,
        )

    # approved_at: ISO-8601 parsing + future check (S2-A §3-9)
    try:
        approved_dt = datetime.fromisoformat(approved_at_str)
    except (ValueError, TypeError):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_FORMAT,
            source_id=source_id,
        )

    if approved_dt.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=approved_dt.tzinfo)
    elif now.tzinfo is not None and approved_dt.tzinfo is None:
        approved_dt = approved_dt.replace(tzinfo=now.tzinfo)

    diff = approved_dt - now
    if diff.total_seconds() > 300:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FUTURE_APPROVAL,
            source_id=source_id,
            approved_at=approved_at_str,
        )

    # final_decision must be exactly "APPROVED" (S2-A §3-7)
    if final_decision != "APPROVED":
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.DECISION_NOT_APPROVED,
            source_id=source_id,
        )

    # target_paths validation (S2-A §3-6)
    if expected_target_paths is not None:
        paths_valid, _ = _validate_target_paths(target_paths, expected_target_paths)
        if not paths_valid:
            return ApprovalEvaluation(
                state=ApprovalState.REJECTED,
                reason_code=ApprovalReasonCode.TARGET_MISMATCH,
                source_id=source_id,
            )

    # dataset_sha256_before validation (S2-A §3-10)
    # scope="FRESH_MERGE_PRECONDITION" — 이 값은 recovery 자격의 단독 기준이 아니다
    # (recovery invariant 는 S2-E 에서 확정)
    if dataset_sha256_current != dataset_sha256_before:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.DATASET_SHA_MISMATCH,
            source_id=source_id,
            scope=FRESH_MERGE_PRECONDITION,
        )

    return ApprovalEvaluation(
        state=ApprovalState.VALID,
        reason_code=None,
        source_id=source_id,
        approved_at=approved_at_str,
        dataset_sha256_before=dataset_sha256_before,
        plan_hash=plan_hash,
        artifact_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        artifact_path=str(Path(approval_path).resolve()),
    )


# ---------------------------------------------------------------------------
# Registry comparison allowlist (Rev.2 + Rev.3)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# B3: Thin connector between merge_nae_corpus() and evaluate_approval_v2
# ---------------------------------------------------------------------------

def _connect_approval_v2(
    source_id: str,
    target: TargetPaths,
    config_path: Optional[Path],
) -> ApprovalEvaluation:
    """Thin connector: bridge merge_nae_corpus → evaluate_approval_v2.

    Responsibilities (B3):
      1. Read approval_dir from config and validate per S2-A §3-5 rules.
      2. Validate source_id per S2-A §3-4 rules and build approval file path.
      3. Pass expected target paths (dataset_path, manifest_path, registry_path)
         to evaluate_approval_v2 along with the dataset path.
    """
    # (1) Read and validate approval_dir from config
    approval_dir_str = _load_approval_dir(config_path)
    approval_dir = Path(approval_dir_str).resolve()

    # (2) Validate source_id (reuse _validate_source_id)
    valid_sid, sid_reason = _validate_source_id(source_id)
    if not valid_sid:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=sid_reason,
            source_id=source_id,
        )

    # Build approval file path per S2-A §3-4 rules
    approval_path = approval_dir / "production_targets" / f"{source_id}.json"

    # (3) Expected target paths in order: dataset_path, manifest_path, registry_path
    expected_paths = [
        str(target.dataset_path),
        str(target.manifest_path),
        str(target.registry_path),
    ]

    # (4) Compute current dataset SHA-256 for FRESH_MERGE_PRECONDITION check
    current_sha = compute_dataset_sha256(target.dataset_path)

    return evaluate_approval_v2(
        approval_path=approval_path,
        config_path=config_path,
        expected_target_paths=expected_paths,
        dataset_sha256_current=current_sha,
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
    if _paths_are_samefile(candidate_resolved, prod_root):
        return True

    # Case 2: candidate doesn't exist — check parent identity + containment
    if not candidate_resolved.exists():
        # Check if the parent directory is production root
        parent = candidate_resolved.parent
        try:
            parent_resolved = parent.resolve()
            if parent_resolved.exists() and _paths_are_samefile(parent_resolved, prod_root):
                return True
        except OSError:
            pass

        # Check lexical containment under production root (uses common helper)
        candidate_norm = _normalize_path_for_comparison(candidate_resolved)
        prod_norm = _normalize_path_for_comparison(prod_root)
        if candidate_norm.startswith(prod_norm + os.sep):
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

    .. deprecated::
        v1 — Do NOT call from merge_nae_corpus() path.
        Use evaluate_approval_v2() via the thin connector function instead.
        This function is retained for backward compatibility only.
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


# ---------------------------------------------------------------------------
# E-0a — extracted module-level functions (pure / read-only unless noted)
# ---------------------------------------------------------------------------

def _collect_nae_candidates(
    nae_corpus_dir: Path, source_id: str
) -> tuple[list[dict], dict[Path, dict]]:
    """Collect NAE corpus TSU records and document metadata.

    Read-only: never writes to disk.  Raises FileNotFoundError for missing
    directory (same message semantics as the original inline path).
    """
    if not nae_corpus_dir.exists():
        raise FileNotFoundError(
            f"NAE corpus directory not found: {nae_corpus_dir}"
        )

    nae_records: list[dict] = []
    nae_docs_info: dict[Path, dict] = {}

    for item in sorted(nae_corpus_dir.glob("*")):
        if not item.is_dir():
            continue
        tsu_file = item / "tsu.json"
        if not tsu_file.exists():
            continue

        # record-level source filter: work_id outside the approved scope is
        # never merged
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

    return nae_records, nae_docs_info


def _dedup_new_records(
    nae_records: list[dict], existing_records: list[dict]
) -> list[dict]:
    """Deduplicate *nae_records* against *existing_records* by tsu_id.

    Preserves order of first occurrence in *nae_records*.  Returns a new list;
    both inputs are left unchanged.  KeyError on missing 'tsu_id' is preserved
    from the original inline set-comprehension behaviour.
    """
    existing_ids = {r["tsu_id"] for r in existing_records}
    return [rec for rec in nae_records if rec["tsu_id"] not in existing_ids]


def _compose_candidate_dataset(
    existing_records: list[dict], new_records: list[dict]
) -> list[dict]:
    """Return a new list: existing_records + new_records (order preserved).

    Inputs are never mutated.
    """
    return existing_records + new_records


def _new_registry_entry(
    item: Path,
    info: dict,
    created_at: str,
    last_processed_at: str,
) -> dict:
    """Build a registry document entry literal for a new NAE document.

    Inputs are never mutated.  Returns a fresh dict with the same fields and
    values as the original inline literal.
    """
    return {
        "document_id": info["document_id"],
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
        "created_at": created_at,
        "last_processed_at": last_processed_at,
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


def _apply_new_documents(
    registry: dict, nae_docs_info: dict[Path, dict]
) -> list[str]:
    """Add new document_ids to *registry["documents"]* in-place.

    Only modifies the passed *registry* dict; existing entries are preserved
    byte-for-byte.  Never writes to disk.  Returns the list of newly added
    document_id strings (may be empty if all already exist).
    """
    added: list[str] = []
    documents = registry["documents"]
    for item, info in nae_docs_info.items():
        doc_id = info["document_id"]
        if doc_id not in documents:
            documents[doc_id] = _new_registry_entry(
                item, info,
                created_at=datetime.now().isoformat(),
                last_processed_at=datetime.now().isoformat(),
            )
            added.append(doc_id)
    return added


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


# ---------------------------------------------------------------------------
# S2-C: write-ahead intent (schema v1)
#
# The intent records, BEFORE the first production write, what is about to be changed, under which
# approval, and from which pre-state. It is ONE piece of pre-evidence for a later recovery stage
# (S2-E); `phase` is only the last recorded progress state and is never, by itself, the basis of a
# recovery decision. This module reads an existing intent only to decide whether a new merge must be
# blocked; it contains no recovery / resume / rollback logic.
# ---------------------------------------------------------------------------

from core.tsu_builder import _atomic_write_text  # noqa: E402  (reused as-is; core is not modified)

INTENT_VERSION = 1
INTENT_FILENAME = "tsu_merge_intent.json"


class IntentPhase(str, Enum):
    """Last recorded progress of a production merge (diagnostic; not a recovery basis by itself)."""
    INTENT_WRITTEN = "INTENT_WRITTEN"
    DATASET_WRITTEN = "DATASET_WRITTEN"
    REGISTRY_WRITTEN = "REGISTRY_WRITTEN"
    COMMITTED = "COMMITTED"


# The only legal phase transitions, each performed right after the corresponding data write.
_INTENT_NEXT_PHASE: dict[IntentPhase, IntentPhase] = {
    IntentPhase.INTENT_WRITTEN: IntentPhase.DATASET_WRITTEN,
    IntentPhase.DATASET_WRITTEN: IntentPhase.REGISTRY_WRITTEN,
    IntentPhase.REGISTRY_WRITTEN: IntentPhase.COMMITTED,
}

_INTENT_KEYS: frozenset[str] = frozenset({
    "intent_version", "intent_id", "phase", "created_at", "source_id", "approval", "plan_hash",
    "targets", "dataset_pre_image", "registry_pre_image", "mutation_plan", "intent_content_sha256",
})
_INTENT_APPROVAL_KEYS: frozenset[str] = frozenset({"path", "artifact_sha256", "plan_hash", "approved_at"})
_INTENT_MUTATION_KEYS: frozenset[str] = frozenset(
    {"planned_tsu_ids", "new_tsu_ids", "new_document_ids", "new_record_count"}
)
_HEX64_RE = _re_module.compile(r"^[0-9a-f]{64}$")
_PLAN_HASH_RE = _re_module.compile(r"^sha256:[0-9a-f]{64}$")
_UUID4_RE = _re_module.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def _intent_blocked(message: str) -> CorpusMutationBlockedError:
    return CorpusMutationBlockedError(f"Corpus mutation BLOCKED: intent: {message}")


def _intent_checksum(payload: dict) -> str:
    """SHA-256 (lowercase hex) of the canonical JSON of the payload without intent_content_sha256.
    `phase` is part of the hashed payload, so every phase update recomputes it."""
    body = {k: v for k, v in payload.items() if k != "intent_content_sha256"}
    return hashlib.sha256(_canonical_json_bytes(body)).hexdigest()


def _is_hex64(value: object) -> bool:
    return isinstance(value, str) and _HEX64_RE.match(value) is not None


def _check_sorted_unique_str_list(name: str, values: object) -> list[str]:
    if not isinstance(values, list):
        raise _intent_blocked(f"{name} must be a list")
    previous: Optional[str] = None
    for value in values:
        if not isinstance(value, str) or not value:
            raise _intent_blocked(f"{name} elements must be non-empty str")
        if previous is not None and value <= previous:
            raise _intent_blocked(f"{name} must be strictly ascending (sorted, unique) at {value!r}")
        previous = value
    return values


def _validate_intent_payload(raw: bytes) -> dict:
    """Parse and fully validate intent bytes (existing-intent check and self-check of a new intent).

    Rejects (CorpusMutationBlockedError): non-UTF-8, invalid JSON, duplicate keys, NaN/Infinity,
    non-object top level, unknown/missing keys, wrong types or formats (bool/float are not ints),
    unsorted or duplicated lists, mutation_plan invariant violations, plan_hash disagreement and a
    wrong intent_content_sha256. A correct checksum never excuses a wrong schema.
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise _intent_blocked("intent bytes required")
    try:
        text = bytes(raw).decode("utf-8")
    except UnicodeDecodeError:
        raise _intent_blocked("not valid UTF-8") from None

    def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
        result: dict = {}
        for key, value in pairs:
            if key in result:
                raise _intent_blocked(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    def _no_constants(name: str) -> object:
        raise _intent_blocked(f"unsupported JSON constant {name}")

    try:
        data = json.loads(text, object_pairs_hook=_no_duplicate_keys, parse_constant=_no_constants)
    except CorpusMutationBlockedError:
        raise
    except ValueError:
        raise _intent_blocked("invalid JSON") from None
    if not isinstance(data, dict):
        raise _intent_blocked("top level must be a JSON object")
    if set(data) != _INTENT_KEYS:
        raise _intent_blocked(
            f"key set mismatch (extra={sorted(set(data) - _INTENT_KEYS)}, missing={sorted(_INTENT_KEYS - set(data))})"
        )

    if type(data["intent_version"]) is not int or data["intent_version"] != INTENT_VERSION:
        raise _intent_blocked("intent_version must be the integer 1")
    if not isinstance(data["intent_id"], str) or _UUID4_RE.match(data["intent_id"]) is None:
        raise _intent_blocked("intent_id must be a lowercase uuid4")
    if not isinstance(data["phase"], str) or data["phase"] not in {p.value for p in IntentPhase}:
        raise _intent_blocked("phase is not a known IntentPhase")

    created_at = data["created_at"]
    if not isinstance(created_at, str):
        raise _intent_blocked("created_at must be str")
    try:
        parsed_created = datetime.fromisoformat(created_at)
    except ValueError:
        raise _intent_blocked("created_at is not ISO-8601") from None
    if parsed_created.utcoffset() != timedelta(0):
        raise _intent_blocked("created_at must be UTC (+00:00)")

    if not _validate_source_id(data["source_id"])[0]:
        raise _intent_blocked("source_id violates the source_id safety rule")

    approval = data["approval"]
    if not isinstance(approval, dict) or set(approval) != _INTENT_APPROVAL_KEYS:
        raise _intent_blocked("approval must be an object with exactly {path, artifact_sha256, plan_hash, approved_at}")
    if not isinstance(approval["path"], str) or not os.path.isabs(approval["path"]):
        raise _intent_blocked("approval.path must be an absolute path str")
    if not _is_hex64(approval["artifact_sha256"]):
        raise _intent_blocked("approval.artifact_sha256 must be lowercase hex64")
    if not isinstance(approval["plan_hash"], str) or _PLAN_HASH_RE.match(approval["plan_hash"]) is None:
        raise _intent_blocked("approval.plan_hash must be sha256:+hex64")
    if not isinstance(approval["approved_at"], str):
        raise _intent_blocked("approval.approved_at must be str")
    if not isinstance(data["plan_hash"], str) or _PLAN_HASH_RE.match(data["plan_hash"]) is None:
        raise _intent_blocked("plan_hash must be sha256:+hex64")
    if data["plan_hash"] != approval["plan_hash"]:
        raise _intent_blocked("plan_hash differs from approval.plan_hash")

    targets = data["targets"]
    if not isinstance(targets, list) or len(targets) != 3 or not all(
        isinstance(t, str) and os.path.isabs(t) for t in targets
    ):
        raise _intent_blocked("targets must be 3 absolute path strings")

    dataset_pre = data["dataset_pre_image"]
    if not isinstance(dataset_pre, list):
        raise _intent_blocked("dataset_pre_image must be a list")
    previous_tsu: Optional[str] = None
    pre_tsu_ids: set[str] = set()
    for row in dataset_pre:
        if not isinstance(row, list) or len(row) != 3:
            raise _intent_blocked("dataset_pre_image rows must be [tsu_id, document_id, content_sha256]")
        tsu_id, document_id, content_sha = row
        if not isinstance(tsu_id, str) or not tsu_id or not isinstance(document_id, str) or not document_id:
            raise _intent_blocked("dataset_pre_image tsu_id/document_id must be non-empty str")
        if not _is_hex64(content_sha):
            raise _intent_blocked("dataset_pre_image content_sha256 must be lowercase hex64")
        if previous_tsu is not None and tsu_id <= previous_tsu:
            raise _intent_blocked("dataset_pre_image must be strictly ascending by tsu_id (sorted, unique)")
        previous_tsu = tsu_id
        pre_tsu_ids.add(tsu_id)

    registry_pre = data["registry_pre_image"]
    if not isinstance(registry_pre, list):
        raise _intent_blocked("registry_pre_image must be a list")
    previous_doc: Optional[str] = None
    pre_doc_ids: set[str] = set()
    for row in registry_pre:
        if not isinstance(row, list) or len(row) != 2:
            raise _intent_blocked("registry_pre_image rows must be [document_id, entry_sha256]")
        document_id, entry_sha = row
        if not isinstance(document_id, str) or not document_id or not _is_hex64(entry_sha):
            raise _intent_blocked("registry_pre_image row has an invalid document_id/entry_sha256")
        if previous_doc is not None and document_id <= previous_doc:
            raise _intent_blocked("registry_pre_image must be strictly ascending by document_id (sorted, unique)")
        previous_doc = document_id
        pre_doc_ids.add(document_id)

    plan = data["mutation_plan"]
    if not isinstance(plan, dict) or set(plan) != _INTENT_MUTATION_KEYS:
        raise _intent_blocked("mutation_plan must have exactly {planned_tsu_ids, new_tsu_ids, new_document_ids, new_record_count}")
    planned = _check_sorted_unique_str_list("mutation_plan.planned_tsu_ids", plan["planned_tsu_ids"])
    new_ids = _check_sorted_unique_str_list("mutation_plan.new_tsu_ids", plan["new_tsu_ids"])
    new_docs = _check_sorted_unique_str_list("mutation_plan.new_document_ids", plan["new_document_ids"])
    if type(plan["new_record_count"]) is not int or plan["new_record_count"] != len(new_ids):
        raise _intent_blocked("mutation_plan.new_record_count must be the integer len(new_tsu_ids)")
    planned_set, new_set = set(planned), set(new_ids)
    if not new_set <= planned_set:
        raise _intent_blocked("mutation_plan invariant: new_tsu_ids must be a subset of planned_tsu_ids")
    if new_set & pre_tsu_ids:
        raise _intent_blocked("mutation_plan invariant: new_tsu_ids must not already exist in dataset_pre_image")
    if not (planned_set - new_set) <= pre_tsu_ids:
        raise _intent_blocked("mutation_plan invariant: planned ids that are not new must exist in dataset_pre_image")
    if set(new_docs) & pre_doc_ids:
        raise _intent_blocked("mutation_plan invariant: new_document_ids must not already exist in registry_pre_image")

    checksum = data["intent_content_sha256"]
    if not _is_hex64(checksum):
        raise _intent_blocked("intent_content_sha256 must be lowercase hex64")
    if checksum != _intent_checksum(data):
        raise _intent_blocked("intent_content_sha256 mismatch")
    return data


def _build_dataset_pre_image(existing_records: list) -> list[list[str]]:
    """[tsu_id, document_id, content_sha256] for EVERY existing dataset record, sorted by tsu_id.
    A missing / non-str / duplicate tsu_id or a missing / non-str document_id is never collapsed
    away: it blocks the merge."""
    rows: list[list[str]] = []
    seen: set[str] = set()
    for index, record in enumerate(existing_records):
        if not isinstance(record, dict):
            raise _intent_blocked(f"existing dataset record #{index} is not an object")
        tsu_id, document_id = record.get("tsu_id"), record.get("document_id")
        if not isinstance(tsu_id, str) or not tsu_id:
            raise _intent_blocked(f"existing dataset record #{index} has no valid str tsu_id")
        if not isinstance(document_id, str) or not document_id:
            raise _intent_blocked(f"existing dataset record {tsu_id!r} has no valid str document_id")
        if tsu_id in seen:
            raise _intent_blocked(f"existing dataset has duplicate tsu_id {tsu_id!r}")
        seen.add(tsu_id)
        rows.append([tsu_id, document_id, _record_content_sha256(record)])
    rows.sort(key=lambda row: row[0])
    return rows


def _require_str_keys(value: object, where: str) -> None:
    """Registry entries are plain JSON: every dict key (nested too) must be a str."""
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise _intent_blocked(f"{where}: non-str key {key!r}")
            _require_str_keys(item, where)
    elif isinstance(value, list):
        for item in value:
            _require_str_keys(item, where)


def _build_registry_pre_image(registry: object) -> list[list[str]]:
    """[document_id, entry_sha256] for every registry document. The entry fingerprint excludes only
    EXCLUDED_FROM_COMPARISON fields and uses the S2-B canonical JSON (strict; failures block).
    Strict replacement for the lenient compute_registry_preimage_hash, which is left untouched."""
    documents = registry.get("documents") if isinstance(registry, dict) else None
    if not isinstance(documents, dict):
        raise _intent_blocked("registry has no 'documents' object")
    rows: list[list[str]] = []
    for document_id, entry in documents.items():
        if not isinstance(document_id, str) or not document_id:
            raise _intent_blocked(f"registry document_id must be a non-empty str: {document_id!r}")
        if not isinstance(entry, dict):
            raise _intent_blocked(f"registry entry {document_id!r} is not an object")
        if "document_id" in entry and entry["document_id"] != document_id:
            raise _intent_blocked(
                f"registry entry document_id {entry['document_id']!r} differs from its key {document_id!r}"
            )
        _require_str_keys(entry, f"registry entry {document_id!r}")
        fingerprint_body = {k: v for k, v in entry.items() if k not in EXCLUDED_FROM_COMPARISON}
        rows.append([document_id, hashlib.sha256(_canonical_json_bytes(fingerprint_body)).hexdigest()])
    rows.sort(key=lambda row: row[0])
    return rows


def _build_mutation_plan(
    planned_tsu_ids: set[str],
    new_records: list[dict],
    registry_pre_image: list[list[str]],
    nae_docs_info: dict,
) -> dict:
    """planned_tsu_ids = the approved plan BEFORE dedup; new_tsu_ids = ids that are actually appended."""
    new_ids = [record["tsu_id"] for record in new_records]
    if len(new_ids) != len(set(new_ids)):
        raise _intent_blocked("new records contain a duplicate tsu_id")
    registry_ids = {row[0] for row in registry_pre_image}
    new_documents = sorted({info["document_id"] for info in nae_docs_info.values()} - registry_ids)
    return {
        "planned_tsu_ids": sorted(planned_tsu_ids),
        "new_tsu_ids": sorted(new_ids),
        "new_document_ids": new_documents,
        "new_record_count": len(new_ids),
    }


def _build_intent_payload(
    source_id: str,
    approval: ApprovalEvaluation,
    targets: list,
    dataset_pre_image: list[list[str]],
    registry_pre_image: list[list[str]],
    mutation_plan: dict,
) -> dict:
    """Build the immutable fields, compute the checksum, then validate the COMPLETE payload.
    (The validator requires the checksum, so it is never called before the checksum exists.)"""
    if (
        approval.state != ApprovalState.VALID
        or approval.plan_hash is None
        or approval.artifact_sha256 is None
        or approval.artifact_path is None
        or approval.approved_at is None
    ):
        raise _intent_blocked("a VALID approval with plan_hash and artifact identity is required")
    import uuid as _uuid
    payload: dict = {
        "intent_version": INTENT_VERSION,
        "intent_id": str(_uuid.uuid4()),
        "phase": IntentPhase.INTENT_WRITTEN.value,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_id": source_id,
        "approval": {
            "path": approval.artifact_path,
            "artifact_sha256": approval.artifact_sha256,
            "plan_hash": approval.plan_hash,
            "approved_at": approval.approved_at,
        },
        "plan_hash": approval.plan_hash,
        "targets": [str(Path(t).resolve()) for t in targets],
        "dataset_pre_image": dataset_pre_image,
        "registry_pre_image": registry_pre_image,
        "mutation_plan": mutation_plan,
    }
    payload["intent_content_sha256"] = _intent_checksum(payload)
    _validate_intent_payload(_canonical_json_bytes(payload))
    return payload


# ---------------------------------------------------------------------------
# E-0b — durability barrier
# ---------------------------------------------------------------------------

def _fsync_directory_impl(directory: Path) -> None:
    """Low-level directory fsync.  Opens, fsyncs, closes (both success and
    failure paths).  Propagates OSError unchanged."""
    fd = os.open(str(directory), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_directory_strict(directory: Path) -> None:
    """Thin wrapper around _fsync_directory_impl for intent-record calls.

    Preserves the original contract (fsync a directory and PROPAGATE any error).
    The actual fsync implementation lives in _fsync_directory_impl so that the
    durability barrier (_ensure_durable) can call the core logic directly
    without going through the intent-specific wrapper.
    """
    _fsync_directory_impl(directory)


def _ensure_durable(path: Path) -> None:
    """Durability barrier for *path* (file or directory).

    1. Opens the file in read-only mode, calls os.fsync(fd), and closes the fd
       on both success and failure paths.
    2. Then fsyncs the parent directory via _fsync_directory_impl(strict=True).

    Any OSError from either step is converted to
    CorpusMutationBlockedError("Corpus mutation BLOCKED: durability barrier
    failed for <path>: <cause>") and re-raised with ``from exc`` to preserve
    the original cause.
    """
    exc_for_cause: Optional[BaseException] = None
    try:
        fd = os.open(str(path), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        exc_for_cause = exc
        raise CorpusMutationBlockedError(
            f"Corpus mutation BLOCKED: durability barrier failed for {path}: {exc}"
        ) from exc

    parent = Path(path).parent
    try:
        _fsync_directory_impl(parent)
    except OSError as exc:
        if exc_for_cause is None:
            exc_for_cause = exc
        raise CorpusMutationBlockedError(
            f"Corpus mutation BLOCKED: durability barrier failed for {path}: {exc}"
        ) from exc_for_cause



def _write_intent_durable(path: Path, payload: dict) -> None:
    """Durably write the intent: core's atomic writer (temp file + fsync + os.replace), then a strict
    directory fsync whose error is NOT swallowed. Any failure -> CorpusMutationBlockedError.

    Contract: a failure AFTER os.replace may leave the (complete) new intent file in place. The file is
    never deleted or rolled back here; only the temporary file is cleaned up (by the core helper, before
    the replace)."""
    data = _canonical_json_bytes(payload)
    try:
        _atomic_write_text(Path(path), lambda handle: handle.write(data.decode("utf-8")))
        _fsync_directory_strict(Path(path).parent)
    except CorpusMutationBlockedError:
        raise
    except Exception as exc:
        raise CorpusMutationBlockedError(f"Corpus mutation BLOCKED: intent durable write failed: {exc}") from exc


def _advance_intent_phase(path: Path, payload: dict, new_phase: IntentPhase) -> dict:
    """Return the next in-memory payload (only phase and intent_content_sha256 change) after durably
    writing it. Never re-reads the file. A failure raises, which stops every later production write."""
    current = IntentPhase(payload["phase"])
    if _INTENT_NEXT_PHASE.get(current) != new_phase:
        raise _intent_blocked(f"illegal phase transition {current.value} -> {new_phase.value}")
    advanced = dict(payload)
    advanced["phase"] = new_phase.value
    advanced["intent_content_sha256"] = _intent_checksum(advanced)
    _write_intent_durable(path, advanced)
    return advanced


def _intent_file_path(manifest_path: Path, dataset_path: Path) -> Path:
    """tsu_merge_intent.json next to the manifest; its directory must be the dataset's directory too."""
    if _normalize_path_for_comparison(Path(manifest_path).parent) != _normalize_path_for_comparison(
        Path(dataset_path).parent
    ):
        raise _intent_blocked("manifest and dataset must share one directory for the intent file")
    return Path(manifest_path).parent / INTENT_FILENAME


def _same_target(recorded: str, current: object) -> bool:
    recorded_path, current_path = Path(recorded), Path(str(current))
    return _paths_are_samefile(recorded_path, current_path) or (
        _normalize_path_for_comparison(recorded_path) == _normalize_path_for_comparison(current_path)
    )


def _check_existing_intent(intent_path: Path, current_targets: list) -> None:
    """Block unless there is NO intent, or a fully valid COMMITTED intent for the same targets
    (that one is replaced by the new intent). Never modifies the existing file.
    This is a blocking decision only; nothing here resumes, repairs or rolls back anything."""
    if not intent_path.exists() and not intent_path.is_symlink():
        return
    try:
        raw = intent_path.read_bytes()
    except OSError as exc:
        raise _intent_blocked(f"existing intent cannot be read: {exc}") from exc
    existing = _validate_intent_payload(raw)
    if existing["phase"] != IntentPhase.COMMITTED.value:
        raise _intent_blocked(
            f"an incomplete intent exists (phase={existing['phase']}); recovery is required before a new merge"
        )
    for recorded, current in zip(existing["targets"], current_targets):
        if not _same_target(recorded, current):
            raise _intent_blocked("the existing COMMITTED intent belongs to different targets and is not replaced")


@contextmanager
def _merge_locks(registry_path, dataset_path):
    """S2-D: hold registry_lock then tsu_dataset_lock (R -> T) for the whole merge.

    R -> T is the order every other writer already uses (reconcile_pending, delete_raw_source).
    registry_lock is NOT reentrant: it is acquired exactly once here and nothing the merge calls
    takes it again. tsu_dataset_lock is reentrant, so the inner `with tsu_dataset_lock` below nests
    harmlessly. Release is the reverse order (T, then R), also on exceptions."""
    with registry_lock(str(registry_path)):
        with tsu_dataset_lock(dataset_path):
            yield


def merge_nae_corpus(
    source_id: Optional[str] = None,
    data_root: Optional[Path] = None,
    nae_corpus_dir: Optional[Path] = None,
    decisions_dir: Optional[Path] = None,
    config_path: Optional[Path] = None,
) -> dict:
    """Public entry point: resolve targets, take R -> T (S2-D), run the merge under both locks.

    Everything that reads state (approval freshness, existing dataset, registry pre-image) and every
    write happens while both locks are held. Path-safety errors from resolve_target_paths() are raised
    before any lock is taken."""
    target = resolve_target_paths(data_root=data_root, config_path=config_path)
    if target.data_root is None:  # the locked body raises its own explicit error
        return _merge_nae_corpus_locked(source_id, data_root, nae_corpus_dir, decisions_dir, config_path)
    with _merge_locks(target.registry_path, target.dataset_path):
        return _merge_nae_corpus_locked(source_id, data_root, nae_corpus_dir, decisions_dir, config_path)


def _merge_nae_corpus_locked(
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

    # Production target approval gate — before any mutation (B3: use v2 connector)
    if target.is_production:
        print(f"\nProduction target detected: {target.data_root}")
        eval_result = _connect_approval_v2(
            source_id=source_id or "",
            target=target,
            config_path=config_path,
        )
        if eval_result.state != ApprovalState.VALID:
            raise CorpusMutationBlockedError(
                f"Production target approval FAILED: {eval_result.reason_code}"
            )
        print(f"  Production target approval PASSED: VALID")

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

        # 3. Read NAE corpus TSU records (E-0a: extracted)
        print(f"\nScanning NAE corpus TSU at {nae_corpus_dir}...")
        nae_records, nae_docs_info = _collect_nae_candidates(nae_corpus_dir, source_id)
        print(f"  Read {len(nae_records)} NAE corpus records from {len(nae_docs_info)} documents")

        # 승인 범위 방어선: mutation 대상 ID 집합 == 승인된 planned 집합이어야 한다
        mutation_ids = {r["tsu_id"] for r in nae_records}
        if mutation_ids != planned_tsu_ids:
            raise CorpusMutationBlockedError(
                "Corpus mutation BLOCKED: mutation set != approved plan "
                f"(extra={sorted(mutation_ids - planned_tsu_ids)[:5]}, "
                f"missing={sorted(planned_tsu_ids - mutation_ids)[:5]})"
            )

        # S2-B: approved plan == actual plan, or no write at all.
        # Placed right after the mutation-set check, inside the existing tsu_dataset_lock and
        # BEFORE any dataset/registry/manifest write. Order of reads/locks/writes is unchanged.
        if target.is_production:
            approved_plan_hash = eval_result.plan_hash
            if approved_plan_hash is None:
                raise CorpusMutationBlockedError(
                    f"Corpus mutation BLOCKED: {ApprovalReasonCode.PLAN_HASH_MISMATCH.value} "
                    "(VALID approval carries no plan_hash)"
                )
            actual_plan_hash = compute_plan_hash(
                source_id or "",
                nae_records,
                [target.dataset_path, target.manifest_path, target.registry_path],
            )
            if actual_plan_hash != approved_plan_hash:
                raise CorpusMutationBlockedError(
                    f"Corpus mutation BLOCKED: {ApprovalReasonCode.PLAN_HASH_MISMATCH.value} "
                    f"(approved={approved_plan_hash!r}, actual={actual_plan_hash!r})"
                )

        # 4. Dedup by tsu_id (F-3 idempotency, E-0a: extracted)
        new_records = _dedup_new_records(nae_records, existing_records)

        # 5. Compose candidate dataset (E-0a: extracted)
        all_records = _compose_candidate_dataset(existing_records, new_records)

        # 6. Validation before replace (F-3)
        print("\nValidating candidate dataset...")
        _validate_dataset(all_records, tsu_dataset_path)
        print(f"  Validation passed: {len(all_records)} records, no duplicates")

        # S2-C: write-ahead intent (production merges only; inside the existing tsu_dataset_lock).
        # Everything is prepared in memory AFTER candidate validation and BEFORE the first production
        # write, so a validation failure never leaves an intent behind:
        #   (3) existing-intent check (blocks unless none / valid COMMITTED for the same targets)
        #   (4) registry pre-image (read-only), dataset pre-image, mutation plan, checksum, self-validation
        intent_path: Optional[Path] = None
        intent_payload: Optional[dict] = None
        if target.is_production:
            intent_targets = [target.dataset_path, target.manifest_path, target.registry_path]
            intent_path = _intent_file_path(manifest_path, tsu_dataset_path)
            _check_existing_intent(intent_path, intent_targets)
            registry_pre_image = _build_registry_pre_image(load_identity_registry(registry_path))
            intent_payload = _build_intent_payload(
                source_id or "",
                eval_result,
                intent_targets,
                _build_dataset_pre_image(existing_records),
                registry_pre_image,
                _build_mutation_plan(planned_tsu_ids, new_records, registry_pre_image, nae_docs_info),
            )

        # 7. Atomic write (F-3) — now inside lock
        print(f"\nWriting merged TSU to {tsu_dataset_path}...")
        if intent_payload is not None:
            # (5) first durable intent record (INTENT_WRITTEN) — before ANY production write
            _write_intent_durable(intent_path, intent_payload)
        write_tsu_dataset(all_records, tsu_dataset_path)
        print(f"  Written {len(all_records)} records atomically")
        if intent_payload is not None:
            # a failed phase update raises: registry and manifest are then never written
            intent_payload = _advance_intent_phase(intent_path, intent_payload, IntentPhase.DATASET_WRITTEN)

        # 8. Update registry (F-3: corpus_membership="default", E-0a: extracted)
        print(f"\nUpdating registry at {registry_path}...")
        registry = load_identity_registry(registry_path)
        _apply_new_documents(registry, nae_docs_info)

        if not save_identity_registry(registry, str(registry_path)):
            # S2-D: save_identity_registry() reports failure by returning False; never advance the intent phase
            raise CorpusMutationBlockedError(
                f"Corpus mutation BLOCKED: registry write failed for {registry_path}"
            )
        print(f"  Updated registry with {len(nae_docs_info)} new documents")

        # E-0b: durability barrier — after successful registry save, before phase advance
        _ensure_durable(registry_path)

        if intent_payload is not None:
            # a failed phase update raises: the manifest is then never written
            intent_payload = _advance_intent_phase(intent_path, intent_payload, IntentPhase.REGISTRY_WRITTEN)

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
        if intent_payload is not None:
            # COMMITTED: if this update fails the merge must NOT report success (raises)
            intent_payload = _advance_intent_phase(intent_path, intent_payload, IntentPhase.COMMITTED)

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
