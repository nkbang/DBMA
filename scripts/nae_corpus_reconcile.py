"""scripts/nae_corpus_reconcile.py — NAE Corpus Reconciliation Tool (read-only).

read-only drift reporter. No --apply flag. No file writes. No state/Qdrant mutation.

Four authorities reconciled at the ID level:
  1. incremental_state.json  — per-TSU processing stage (INDEXED)
  2. tsu.json review_status  — per-TSU human review result
  3. Qdrant nae_tsu_v1       — physical vector store (points / point IDs)
  4. source_manifest.yaml    — M2 source registry

Invariant checks:
  INV-1: verified_ids == indexed_ids
  INV-2: (when Qdrant reachable) qdrant_ids == verified_ids
  INV-3: (generated|rejected|other) ∩ (indexed∪qdrant) == empty
  INV-4: each TSU record's M2-linkage metadata exists in M2

Governance Consistency (GC):
  GC-1: all corpus_admissions source_ids exist in M2
  GC-2: source with verified TSUs but no admission -> GOVERNANCE DRIFT
  GC-3: tsu-track admission with missing TSU dir -> INFO only

Usage:
    python scripts/nae_corpus_reconcile.py
    python scripts/nae_corpus_reconcile.py --json

Exit code:
    0 -- no drift detected
    1 -- any drift found
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml


# ── Default paths (overridable via function args) ─────────────────────────────

DEFAULT_M2_PATH = PROJECT_ROOT / "NAE" / "pipeline" / "registration" / "state" / "source_manifest.yaml"
DEFAULT_INCREMENTAL_STATE = PROJECT_ROOT / "NAE" / "pipeline" / "ingest" / "state" / "incremental_state.json"
DEFAULT_TSU_DIR = PROJECT_ROOT / "NAE" / "corpus" / "tsu"
DEFAULT_ADMISSIONS = PROJECT_ROOT / "NAE" / "governance" / "corpus_admissions.jsonl"


# ── Qdrant URL from production config (not hardcoded) ─────────────────────────

try:
    from NAE.pipeline.index.config import QDRANT_URL as _DEFAULT_QDRANT_URL
except ImportError:
    _DEFAULT_QDRANT_URL = "http://localhost:7333"


# ── Data loading functions ────────────────────────────────────────────────────

def load_incremental_indexed_ids(path: Path = DEFAULT_INCREMENTAL_STATE) -> set[str]:
    """Return set of tsu_id keys where state == 'INDEXED'."""
    if not path.exists():
        return set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return set()
    return {k for k, v in data.items() if isinstance(v, dict) and v.get("state") == "INDEXED"}


def load_review_status(tsu_dir: Path = DEFAULT_TSU_DIR) -> dict[str, str]:
    """Return {tsu_id: review_status} from all non-_ TSU subdirectories.

    Excludes pilot dirs and *_backup* dirs. Reads tsu.json record 'id' (or 'tsu_id')
    as the key.
    """
    status_map: dict[str, str] = {}
    if not tsu_dir.exists():
        return status_map
    for subdir in sorted(tsu_dir.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue
        tsu_json = subdir / "tsu.json"
        if not tsu_json.exists():
            continue
        with open(tsu_json, "r", encoding="utf-8") as f:
            records = json.load(f)
        if not isinstance(records, list):
            continue
        for rec in records:
            if not isinstance(rec, dict):
                continue
            tsu_id = rec.get("id") or rec.get("tsu_id")
            if tsu_id is None:
                continue
            status_map[tsu_id] = rec.get("review_status", "unknown")
    return status_map


def tsu_m2_linkage(record: dict[str, Any]) -> str | None:
    """Extract M2 linkage value from a TSU record.

    Priority: source_id -> work_id -> source_file / document_id.
    Returns the first found value or None.
    """
    for field in ("source_id", "work_id", "source_file", "document_id"):
        val = record.get(field)
        if val:
            return str(val)
    return None


def build_m2_index(path: Path = DEFAULT_M2_PATH) -> dict[str, list[dict[str, Any]]]:
    """Build reverse index of M2 by source_id / work_id / edition_id.

    Returns {linkage_value: [source_record, ...]}.
    """
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return {}
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        return {}
    index: dict[str, list[dict[str, Any]]] = {}
    for src in sources:
        if not isinstance(src, dict):
            continue
        for key_field in ("source_id", "work_id", "edition_id"):
            val = src.get(key_field)
            if val:
                index.setdefault(str(val), []).append(src)
    return index


def probe_qdrant(
    url: str = _DEFAULT_QDRANT_URL,
    collection: str = "nae_tsu_v1",
) -> tuple[str, Any]:
    """Probe Qdrant and return (status, value).

    Status values:
      - ("reachable", ids_set_or_count)  -- connection OK, can enumerate or count
      - ("unreachable", reason_str)       -- connection refused / timeout / DNS failure
      - ("error", detail_str)             -- other errors (collection not found, auth, etc.)

    Distinguishes network-level failures (unreachable) from HTTP-level errors (error).
    Does NOT use bare except.
    """
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http.exceptions import ApiException

        client = QdrantClient(url=url)
        # Try to get collection info first
        info = client.get_collection(collection)
        # If we got here, connection is reachable. Try to enumerate IDs (count fallback).
        try:
            points = client.scroll(collection, limit=100000, with_payload=["tsu_id"])
            ids: set[str] = set()
            for point in points[0]:
                tsu_id = point.payload.get("tsu_id") if isinstance(point.payload, dict) else None
                if isinstance(tsu_id, str) and tsu_id:
                    ids.add(tsu_id)
                elif point.payload is not None:
                    # tsu_id missing or malformed in payload — surface as error
                    return ("error", f"point {point.id}: payload missing valid 'tsu_id'")
            return ("reachable", ids)
        except Exception as scroll_err:
            # Scroll failed but connection is OK -- use count as fallback
            count = info.points_count if hasattr(info, "points_count") else 0
            return ("reachable", count)

    except (ConnectionError, TimeoutError, OSError) as e:
        return ("unreachable", str(e))
    except ImportError:
        return ("unreachable", "qdrant_client not installed")
    except ApiException as e:
        # ApiException is base for both ResponseHandlingException and UnexpectedResponse.
        # If it has status_code, we got an HTTP response -> error (collection not found, auth, etc.)
        # If no status_code, connection failed before HTTP -> unreachable
        if hasattr(e, "status_code") and e.status_code is not None:
            return ("error", f"HTTP {e.status_code}: {str(e)}")
        else:
            return ("unreachable", str(e))
    except Exception as e:
        # Other application-level errors (not network)
        return ("error", str(e))


def load_admissions(path: Path = DEFAULT_ADMISSIONS) -> list[dict[str, Any]]:
    """Parse corpus_admissions.jsonl and return list of admission records."""
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ── Reconciliation engine ─────────────────────────────────────────────────────

class ReconcileResult:
    """Holds all reconciliation results."""

    def __init__(self) -> None:
        self.authorities: dict[str, Any] = {}
        self.invariants: list[dict[str, str]] = []
        self.governance: list[dict[str, str]] = []
        self.qdrant_status: str = "unreachable"
        self.core_drift: list[str] = []
        self.governance_drift: list[str] = []
        self.info_lines: list[str] = []


def reconcile(
    m2_path: Path = DEFAULT_M2_PATH,
    incremental_state: Path = DEFAULT_INCREMENTAL_STATE,
    tsu_dir: Path = DEFAULT_TSU_DIR,
    admissions_path: Path = DEFAULT_ADMISSIONS,
    qdrant_url: str = _DEFAULT_QDRANT_URL,
) -> ReconcileResult:
    """Run full reconciliation across all four authorities.

    Returns ReconcileResult with invariants, governance checks, drift lists.
    """
    result = ReconcileResult()

    # ── Load authorities ────────────────────────────────────────────────────

    indexed_ids = load_incremental_indexed_ids(incremental_state)
    review_status = load_review_status(tsu_dir)
    m2_index = build_m2_index(m2_path)
    admissions = load_admissions(admissions_path)

    # Derived sets
    verified_ids = {tid for tid, st in review_status.items() if st == "verified"}
    # INV-3: generated/rejected + any non-(verified|generated|rejected) are all "bad"
    bad_status_ids = {
        tid for tid, st in review_status.items()
        if st not in ("verified",)
    }

    # ── Qdrant probe ────────────────────────────────────────────────────────

    qdrant_status, qdrant_value = probe_qdrant(qdrant_url)
    result.qdrant_status = qdrant_status
    qdrant_ids: set[str] | int | None = None

    if qdrant_status == "reachable":
        if isinstance(qdrant_value, set):
            qdrant_ids = qdrant_value
        elif isinstance(qdrant_value, int):
            qdrant_ids = qdrant_value  # count-only fallback
    elif qdrant_status == "error":
        result.core_drift.append(f"Qdrant error: {qdrant_value}")

    # ── INV-1: verified_ids == indexed_ids ──────────────────────────────────

    if verified_ids == indexed_ids:
        result.invariants.append({"id": "INV-1", "ok": True, "detail": "verified_ids == indexed_ids"})
    else:
        verified_only = verified_ids - indexed_ids
        indexed_only = indexed_ids - verified_ids
        detail_parts = []
        if verified_only:
            detail_parts.append(f"verified_only ({len(verified_only)}): {sorted(verified_only)[:20]}")
        if indexed_only:
            detail_parts.append(f"indexed_only ({len(indexed_only)}): {sorted(indexed_only)[:20]}")
        result.invariants.append({"id": "INV-1", "ok": False, "detail": "; ".join(detail_parts)})
        result.core_drift.append(f"INV-1: verified_ids != indexed_ids -- {len(verified_only)} verified not indexed, {len(indexed_only)} indexed not verified")

    # ── INV-2: qdrant_ids == verified_ids (when reachable) ──────────────────

    if qdrant_status == "unreachable":
        result.invariants.append({"id": "INV-2", "ok": False, "skipped": True, "detail": "INV-2 not checked (Qdrant unreachable)"})
    elif qdrant_ids is None:
        result.invariants.append({"id": "INV-2", "ok": False, "skipped": True, "detail": "INV-2 not checked (no Qdrant IDs)"})
    elif isinstance(qdrant_ids, int):
        # Count-only fallback
        if qdrant_ids == len(verified_ids):
            result.invariants.append({"id": "INV-2", "ok": True, "detail": f"qdrant count ({qdrant_ids}) == verified count ({len(verified_ids)}) -- id-level not verified"})
        else:
            result.invariants.append({"id": "INV-2", "ok": False, "detail": f"qdrant count ({qdrant_ids}) != verified count ({len(verified_ids)})"})
            result.core_drift.append(f"INV-2: qdrant count ({qdrant_ids}) != verified count ({len(verified_ids)})")
    else:
        # Full ID set comparison
        if qdrant_ids == verified_ids:
            result.invariants.append({"id": "INV-2", "ok": True, "detail": "qdrant_ids == verified_ids"})
        else:
            q_only = qdrant_ids - verified_ids
            v_only = verified_ids - qdrant_ids
            detail_parts = []
            if q_only:
                detail_parts.append(f"qdrant_only ({len(q_only)}): {sorted(q_only)[:20]}")
            if v_only:
                detail_parts.append(f"verified_only ({len(v_only)}): {sorted(v_only)[:20]}")
            result.invariants.append({"id": "INV-2", "ok": False, "detail": "; ".join(detail_parts)})
            result.core_drift.append(f"INV-2: qdrant_ids != verified_ids -- {len(q_only)} in qdrant not verified, {len(v_only)} verified not in qdrant")

    # ── INV-3: (generated|rejected|other) ∩ (indexed∪qdrant) == empty ───────

    all_bad_ids = bad_status_ids
    indexed_or_qdrant: set[str] = set(indexed_ids)
    if isinstance(qdrant_ids, set):
        indexed_or_qdrant |= qdrant_ids

    intersection = all_bad_ids & indexed_or_qdrant
    if not intersection:
        result.invariants.append({"id": "INV-3", "ok": True, "detail": "No embedded non-verified/rejected/other TSU"})
    else:
        result.invariants.append({"id": "INV-3", "ok": False, "detail": f"Found {len(intersection)} embedded TSUs with bad status: {sorted(intersection)[:20]}"})
        result.core_drift.append(f"INV-3: {len(intersection)} non-verified/rejected/other TSU found in indexed/qdrant: {sorted(intersection)[:20]}")

    # ── INV-4: each TSU record's M2-linkage exists in M2 ────────────────────

    if not tsu_dir.exists():
        result.info_lines.append("INV-4: TSU dir does not exist, skipping linkage check")
    else:
        for subdir in sorted(tsu_dir.iterdir()):
            if not subdir.is_dir() or subdir.name.startswith("_"):
                continue
            tsu_json = subdir / "tsu.json"
            if not tsu_json.exists():
                continue
            with open(tsu_json, "r", encoding="utf-8") as f:
                records = json.load(f)
            if not isinstance(records, list):
                continue
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                linkage_val = tsu_m2_linkage(rec)
                if linkage_val is None:
                    result.info_lines.append(f"INV-4b: {subdir.name}: TSU record has no machine-verifiable M2 linkage (pre-migration metadata)")
                    break  # one per dir is enough
                if linkage_val not in m2_index:
                    result.core_drift.append(f"INV-4: {subdir.name}: linkage '{linkage_val}' not in M2")

    # ── GC-1: all admission source_ids exist in M2 ───────────────────────────

    m2_source_ids = set(m2_index.keys())
    admission_source_ids = {a.get("source_id") for a in admissions if isinstance(a, dict)}
    gc1_missing = admission_source_ids - m2_source_ids
    if not gc1_missing:
        result.governance.append({"id": "GC-1", "ok": True, "detail": "All admission source_ids exist in M2"})
    else:
        result.governance.append({"id": "GC-1", "ok": False, "detail": f"Missing from M2: {sorted(gc1_missing)[:20]}"})
        result.governance_drift.append(f"GC-1: {len(gc1_missing)} admission source_id(s) not in M2: {sorted(gc1_missing)[:10]}")

    # ── GC-2: source with verified TSUs but no admission ─────────────────────

    # Build source -> verified TSU mapping via linkage
    source_verified: dict[str, set[str]] = {}
    if not tsu_dir.exists():
        pass  # skip
    else:
        for subdir in sorted(tsu_dir.iterdir()):
            if not subdir.is_dir() or subdir.name.startswith("_"):
                continue
            tsu_json = subdir / "tsu.json"
            if not tsu_json.exists():
                continue
            with open(tsu_json, "r", encoding="utf-8") as f:
                records = json.load(f)
            if not isinstance(records, list):
                continue
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                if rec.get("review_status") != "verified":
                    continue
                linkage_val = tsu_m2_linkage(rec)
                if linkage_val and linkage_val in m2_source_ids:
                    source_verified.setdefault(linkage_val, set()).add(rec.get("id") or rec.get("tsu_id"))

    verified_sources = set(source_verified.keys())
    admitted_sources = admission_source_ids - {None}
    unadmitted_verified = verified_sources - admitted_sources
    if not unadmitted_verified:
        result.governance.append({"id": "GC-2", "ok": True, "detail": "All sources with verified TSUs have admissions"})
    else:
        detail_parts = []
        for src in sorted(unadmitted_verified)[:10]:
            count = len(source_verified.get(src, set()))
            detail_parts.append(f"{src} ({count} verified)")
        result.governance.append({"id": "GC-2", "ok": False, "detail": "; ".join(detail_parts)})
        result.governance_drift.append(f"GC-2: {len(unadmitted_verified)} source(s) with verified TSUs but no admission")

    # ── GC-3: tsu-track admission with missing TSU dir ───────────────────────

    tsu_admissions = [a for a in admissions if isinstance(a, dict) and a.get("track") == "tsu"]
    gc3_missing_dirs = []
    for adm in tsu_admissions:
        src_id = adm.get("source_id")
        if not src_id:
            continue
        # Check if any TSU dir exists for this source (by linkage match)
        found = False
        if src_id in m2_index:
            for subdir in sorted(tsu_dir.iterdir()) if tsu_dir.exists() else []:
                if not subdir.is_dir() or subdir.name.startswith("_"):
                    continue
                tsu_json = subdir / "tsu.json"
                if not tsu_json.exists():
                    continue
                with open(tsu_json, "r", encoding="utf-8") as f:
                    recs = json.load(f)
                if isinstance(recs, list):
                    for r in recs:
                        if isinstance(r, dict) and tsu_m2_linkage(r) == src_id:
                            found = True
                            break
                if found:
                    break
        if not found:
            gc3_missing_dirs.append(src_id)

    if gc3_missing_dirs:
        result.info_lines.append(f"GC-3: {len(gc3_missing_dirs)} tsu-track admission(s) with no TSU dir: {gc3_missing_dirs[:10]}")
    else:
        result.governance.append({"id": "GC-3", "ok": True, "detail": "All tsu-track admissions have corresponding TSU dirs"})

    # ── Authorities summary ───────────────────────────────────────────────────

    # Count actual M2 sources (not index keys — each source maps to 3 keys)
    m2_source_count = 0
    seen_ids = set()
    for key, srcs in m2_index.items():
        for s in srcs:
            sid = s.get("source_id")
            if sid and sid not in seen_ids:
                seen_ids.add(sid)
                m2_source_count += 1

    result.authorities = {
        "m2_sources": m2_source_count,
        "indexed_ids_count": len(indexed_ids),
        "verified_ids_count": len(verified_ids),
        "qdrant_status": qdrant_status,
    }
    if isinstance(qdrant_ids, int):
        result.authorities["qdrant_value"] = qdrant_ids
    elif isinstance(qdrant_ids, set):
        result.authorities["qdrant_ids_count"] = len(qdrant_ids)

    return result


# ── Output formatting ─────────────────────────────────────────────────────────

def format_human_report(result: ReconcileResult) -> str:
    """Format reconciliation result as human-readable report."""
    lines = []
    a = result.authorities
    lines.append("=" * 70)
    lines.append("NAE Corpus Reconciliation Report (read-only)")
    lines.append("=" * 70)
    lines.append(f"  M2 (source_manifest.yaml):    {a.get('m2_sources', '?')} sources")
    lines.append(f"  Incremental state (INDEXED):  {a.get('indexed_ids_count', '?')} entries")
    lines.append(f"  TSU verified:                 {a.get('verified_ids_count', '?')} records")
    qdrant = a.get("qdrant_status", "unknown")
    lines.append(f"  Qdrant (nae_tsu_v1):          {qdrant}")
    if isinstance(a.get("qdrant_value"), int):
        lines.append(f"    points_count:               {a['qdrant_value']}")
    elif isinstance(a.get("qdrant_ids_count"), int):
        lines.append(f"    points_count:               {a['qdrant_ids_count']}")
    lines.append("-" * 70)

    # Invariants
    lines.append("\n[INVARIANTS]")
    for inv in result.invariants:
        status = inv["ok"]
        if status is True:
            icon = "\u2713"
        elif status is False:
            icon = "\u2717"
        else:
            icon = "\u2298"
        lines.append(f"  {icon} {inv['id']}: {inv['detail']}")

    # Core drift
    if result.core_drift:
        lines.append("\n[CORE DRIFT]")
        for d in result.core_drift:
            lines.append(f"  ! {d}")

    # Governance drift
    if result.governance_drift:
        lines.append("\n[GOVERNANCE DRIFT]")
        for d in result.governance_drift:
            lines.append(f"  ! {d}")

    # Governance checks
    if result.governance and not result.governance_drift:
        lines.append("\n[GOVERNANCE]")
        for gc in result.governance:
            icon = "\u2713" if gc["ok"] is True else "\u2717"
            lines.append(f"  {icon} {gc['id']}: {gc['detail']}")

    # Info
    if result.info_lines:
        lines.append("\n[INFO]")
        for info in result.info_lines:
            lines.append(f"  i {info}")

    if not result.core_drift and not result.governance_drift:
        lines.append("\nNo drift detected.")

    lines.append("=" * 70)
    return "\n".join(lines)


def format_json_report(result: ReconcileResult) -> str:
    """Format reconciliation result as JSON."""
    report = {
        "authorities": result.authorities,
        "invariants": result.invariants,
        "governance": result.governance,
        "qdrant": result.qdrant_status,
        "drift": {
            "core": result.core_drift,
            "governance": result.governance_drift,
        },
    }
    return json.dumps(report, indent=2, ensure_ascii=False)


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output reconciliation result as JSON",
    )
    args = parser.parse_args()

    result = reconcile()

    if args.json:
        print(format_json_report(result))
    else:
        print(format_human_report(result))

    return 1 if (result.core_drift or result.governance_drift) else 0


if __name__ == "__main__":
    raise SystemExit(main())
