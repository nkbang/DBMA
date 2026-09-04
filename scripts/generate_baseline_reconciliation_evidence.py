"""NAE Baseline Reconciliation Evidence Package 생성 (READ-ONLY).

3,319 verified TSU / 3,319 Qdrant vector 기준선 확정, incremental_state.json
version-control 결정, GATE 문서 797 오기 정정을 뒷받침하는 forensic evidence를
CUE가 이 스크립트를 직접 실행한 결과만으로 생성한다. output/ 산출물 2개
(evidence.json, evidence.md) 외에는 어떤 파일도 쓰지 않는다. Qdrant/Production
에 write하지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "output"

CHECKPOINT_COMMIT = "1e338af"
GATE_TYPO_COMMIT = "6198e08"
STATE_COMMIT = "909b1f1"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def gitcmd(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO_ROOT).stdout.strip()


def sha256_of_id_list(ids: list[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(ids)).encode()).hexdigest()


def main() -> None:
    sys.path.insert(0, str(REPO_ROOT))
    from NAE.pipeline.index import qdrant_store, config as index_config

    dagg = json.loads((REPO_ROOT / "NAE/corpus/tsu/Dagg_Church_Order/tsu.json").read_text(encoding="utf-8"))
    hiscox = json.loads((REPO_ROOT / "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json").read_text(encoding="utf-8"))
    records = dagg + hiscox
    status_counts = Counter(r.get("review_status") for r in records)
    verified_ids = sorted(r["id"] for r in records if r.get("review_status") == "verified")

    # --- Qdrant 실측 ---
    client = qdrant_store.get_client()
    info = client.get_collection(index_config.COLLECTION_NAME)
    qdrant_ids: list[str] = []
    offset = None
    while True:
        pts, offset = client.scroll(
            collection_name=index_config.COLLECTION_NAME, limit=1000, offset=offset,
            with_payload=True, with_vectors=False,
        )
        qdrant_ids.extend(p.payload["tsu_id"] for p in pts)
        if offset is None:
            break

    qdrant_set = set(qdrant_ids)
    verified_set = set(verified_ids)
    orphan = sorted(qdrant_set - verified_set)
    missing = sorted(verified_set - qdrant_set)

    # --- incremental_state.json 실측 ---
    state_path = REPO_ROOT / "NAE/pipeline/ingest/state/incremental_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state_ids = sorted(state.keys())
    state_status = Counter(v.get("state") for v in state.values())

    # --- Production mutation forensic (기준: checkpoint commit) ---
    def show(ref: str, path: str) -> str:
        return gitcmd("show", f"{ref}:{path}")

    ckpt_dagg = json.loads(show(CHECKPOINT_COMMIT, "NAE/corpus/tsu/Dagg_Church_Order/tsu.json") or "[]")
    ckpt_hiscox = json.loads(show(CHECKPOINT_COMMIT, "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json") or "[]")
    ckpt_status = {r["id"]: r.get("review_status") for r in (ckpt_dagg + ckpt_hiscox)}
    cur_status = {r["id"]: r.get("review_status") for r in records}
    added = sorted(set(cur_status) - set(ckpt_status))
    removed = sorted(set(ckpt_status) - set(cur_status))
    modified = sorted(k for k in (set(ckpt_status) & set(cur_status)) if ckpt_status[k] != cur_status[k])

    # --- Manifest 값 ---
    manifest_path = REPO_ROOT / "NAE/pipeline/ingest/manifests/manifest_gen0002.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # --- Git status/diff 요약 ---
    git_status = gitcmd("status", "--short")
    gate_doc_797 = gitcmd("show", f"{GATE_TYPO_COMMIT}^:docs/NAE_INCREMENTAL_INGESTION_FINAL_GATE_001.md")
    gate_doc_776 = gitcmd("show", f"{GATE_TYPO_COMMIT}:docs/NAE_INCREMENTAL_INGESTION_FINAL_GATE_001.md")

    evidence = {
        "generated_at": now(),
        "generated_by": "CUE (direct execution, no estimation/plan values)",
        "scope": "NAE Baseline Reconciliation Finalization (3,319 verified TSU / 3,319 Qdrant vectors)",
        "related_commits": {
            "checkpoint": CHECKPOINT_COMMIT,
            "gate_797_typo_fix": GATE_TYPO_COMMIT,
            "incremental_state_committed": STATE_COMMIT,
        },
        "baseline": {
            "verified_tsu": status_counts.get("verified", 0),
            "generated_tsu": status_counts.get("generated", 0),
            "rejected_tsu": status_counts.get("rejected", 0),
            "total_tsu_records": len(records),
            "arithmetic_check": status_counts.get("verified", 0) + status_counts.get("generated", 0) + status_counts.get("rejected", 0) == len(records),
        },
        "qdrant_state": {
            "collection": index_config.COLLECTION_NAME,
            "points_count": info.points_count,
            "vector_size": info.config.params.vectors.size,
            "distance": str(info.config.params.vectors.distance),
            "unique_ids_scrolled": len(qdrant_set),
            "id_set_sha256": sha256_of_id_list(qdrant_ids),
        },
        "id_reconciliation": {
            "verified_id_set_sha256": sha256_of_id_list(verified_ids),
            "match_count": len(verified_set & qdrant_set),
            "orphan_in_qdrant": orphan,
            "orphan_count": len(orphan),
            "missing_from_qdrant": missing,
            "missing_count": len(missing),
            "exact_match": (len(orphan) == 0 and len(missing) == 0),
        },
        "incremental_state": {
            "path": "NAE/pipeline/ingest/state/incremental_state.json",
            "entry_count": len(state_ids),
            "state_distribution": dict(state_status),
            "id_set_sha256": sha256_of_id_list(state_ids),
            "matches_verified_id_set": sha256_of_id_list(state_ids) == sha256_of_id_list(verified_ids),
            "version_control_decision": "A — commit to Git",
            "decision_rationale": [
                "ADR-020 §5 defines this file as the persistent processing-state store, deliberately decoupled from the Production TSU schema — it is architecturally a first-class artifact, not scratch/cache.",
                "Precedent: NAE/pipeline/ingest/manifests/manifest_gen*.json (same category of derived pipeline output) is already Git-tracked — treating state.json differently would be an inconsistent policy.",
                ".gitignore has no rule matching NAE/pipeline/ingest/state/ or incremental_state.json — no existing policy excludes it (only generic output/ and AI-agent-runtime-state patterns exist, neither applies here).",
                "Content contains no absolute paths or environment-specific values — tsu_id, state enum, content_hash, ISO8601 updated_at only. Portable across machines.",
                "NOT byte-for-byte deterministically regenerable: content_hash values are derived from Production TSU (deterministic), but updated_at timestamps are wall-clock and would differ on any re-run — Git is the only mechanism that preserves the actual historical record, since a regenerated file would not equal the original bit-for-bit.",
                "It was in fact already committed in a prior session turn (commit 909b1f1) before this formal decision framework was applied — this evidence retroactively validates that action against ADR-020/.gitignore/repo precedent rather than reverting it.",
            ],
        },
        "production_mutation_since_checkpoint": {
            "compared_against_commit": CHECKPOINT_COMMIT,
            "added": added,
            "removed": removed,
            "modified_review_status": modified,
            "added_count": len(added),
            "removed_count": len(removed),
            "modified_count": len(modified),
            "unchanged": (len(added) == 0 and len(removed) == 0 and len(modified) == 0),
        },
        "manifest_gen0002_values": {
            "total_tsu": manifest.get("total_tsu"),
            "total_vectors": manifest.get("total_vectors"),
            "note": "Schema has no verified_tsu/generated_tsu/rejected_tsu breakdown fields — only aggregate total_tsu. Adding such fields would be an ADR-020 schema change requiring an ADR Amendment (Architecture Freeze Rule); not performed here, reported as finding only.",
        },
        "gate_doc_797_typo": {
            "before_commit": GATE_TYPO_COMMIT + "^",
            "after_commit": GATE_TYPO_COMMIT,
            "before_contains_797": "generated 797" in gate_doc_797,
            "after_contains_776": "generated 776" in gate_doc_776,
            "after_contains_797_uncorrected": "generated 797" in gate_doc_776.replace("generated 776", ""),
        },
        "git_status_at_evidence_time": git_status,
    }

    findings = []
    if not evidence["baseline"]["arithmetic_check"]:
        findings.append("baseline arithmetic mismatch")
    if not evidence["id_reconciliation"]["exact_match"]:
        findings.append("orphan/missing vectors detected")
    if not evidence["incremental_state"]["matches_verified_id_set"]:
        findings.append("incremental_state id set does not match verified TSU id set")
    if not evidence["production_mutation_since_checkpoint"]["unchanged"]:
        findings.append("production mutation detected since checkpoint")

    evidence["findings"] = findings
    evidence["overall_gate"] = "PASS" if not findings else "HOLD"

    OUT.mkdir(exist_ok=True)
    (OUT / "nae_baseline_reconciliation_evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md = f"""# NAE Baseline Reconciliation Evidence Package

생성 시각: {evidence['generated_at']}
생성자: CUE (직접 실행, 추정/계획값 미사용)

## 1. Baseline

```
verified_tsu = {evidence['baseline']['verified_tsu']}
generated_tsu = {evidence['baseline']['generated_tsu']}
rejected_tsu = {evidence['baseline']['rejected_tsu']}
total_tsu_records = {evidence['baseline']['total_tsu_records']}
arithmetic_check = {evidence['baseline']['arithmetic_check']}
```

## 2. Qdrant point count

```
points_count = {evidence['qdrant_state']['points_count']}
collection = {evidence['qdrant_state']['collection']}
vector_size/distance = {evidence['qdrant_state']['vector_size']} / {evidence['qdrant_state']['distance']}
```

## 3. Verified TSU count

```
{evidence['baseline']['verified_tsu']}
```

## 4-5. Qdrant <-> TSU ID reconciliation / Orphan / Missing

```
match = {evidence['id_reconciliation']['match_count']}
orphan_count = {evidence['id_reconciliation']['orphan_count']}
missing_count = {evidence['id_reconciliation']['missing_count']}
exact_match = {evidence['id_reconciliation']['exact_match']}
verified_id_set_sha256 = {evidence['id_reconciliation']['verified_id_set_sha256']}
qdrant_id_set_sha256   = {evidence['qdrant_state']['id_set_sha256']}
```

## 7-8. incremental_state count / reconciliation

```
entry_count = {evidence['incremental_state']['entry_count']}
state_distribution = {json.dumps(evidence['incremental_state']['state_distribution'])}
matches_verified_id_set = {evidence['incremental_state']['matches_verified_id_set']}
version_control_decision = {evidence['incremental_state']['version_control_decision']}
```

## 9-10. Generated / Rejected count

```
generated = {evidence['baseline']['generated_tsu']}
rejected = {evidence['baseline']['rejected_tsu']}
```

## 11. Manifest values

```
{json.dumps(evidence['manifest_gen0002_values'], ensure_ascii=False, indent=2)}
```

## 12. 797 typo correction

```
{json.dumps(evidence['gate_doc_797_typo'], ensure_ascii=False, indent=2)}
```

## 13. Production mutation verification (since checkpoint {CHECKPOINT_COMMIT})

```
added = {evidence['production_mutation_since_checkpoint']['added_count']}
removed = {evidence['production_mutation_since_checkpoint']['removed_count']}
modified = {evidence['production_mutation_since_checkpoint']['modified_count']}
unchanged = {evidence['production_mutation_since_checkpoint']['unchanged']}
```

## 14-15. Git/version-control status of incremental_state.json + decision rationale

```
{json.dumps(evidence['incremental_state']['decision_rationale'], ensure_ascii=False, indent=2)}
```

## 18. Final Gate

**{evidence['overall_gate']}**

findings: {evidence['findings'] if evidence['findings'] else '(none)'}
"""
    (OUT / "nae_baseline_reconciliation_evidence.md").write_text(md, encoding="utf-8")

    print(json.dumps({
        "baseline": evidence["baseline"],
        "id_reconciliation_exact_match": evidence["id_reconciliation"]["exact_match"],
        "incremental_state_matches": evidence["incremental_state"]["matches_verified_id_set"],
        "production_mutation_unchanged": evidence["production_mutation_since_checkpoint"]["unchanged"],
        "overall_gate": evidence["overall_gate"],
        "findings": evidence["findings"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
