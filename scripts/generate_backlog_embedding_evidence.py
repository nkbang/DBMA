"""Batch 1-23 Backlog Embedding(2,038건) Evidence Package 생성 (READ-ONLY).

CUE가 실제 수행한 실행 기록(Qdrant 현재 상태, Production 파일, 이전/이번
checkpoint MANIFEST, embedding cache)만을 근거로 재계산한다. 이 스크립트는
output/ 산출물 2개 외에는 어떤 파일도 쓰지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "output"

PILOT_IDS = {
    "TSU-0000025", "TSU-0000033", "TSU-0000199", "TSU-0000330", "TSU-0000713",
    "TSU-0003524", "TSU-0003525", "TSU-0003647", "TSU-0003661", "TSU-0003893",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    sys.path.insert(0, str(REPO_ROOT))
    from NAE.pipeline.index import qdrant_store, config as index_config

    dagg = json.loads((REPO_ROOT / "NAE/corpus/tsu/Dagg_Church_Order/tsu.json").read_text(encoding="utf-8"))
    hiscox = json.loads((REPO_ROOT / "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json").read_text(encoding="utf-8"))
    from collections import Counter
    dagg_status = Counter(r["review_status"] for r in dagg)
    hiscox_status = Counter(r["review_status"] for r in hiscox)

    # --- Qdrant point ID 집합 직접 재구성 ---
    client = qdrant_store.get_client()
    info = client.get_collection(index_config.COLLECTION_NAME)
    all_ids: set[str] = set()
    offset = None
    while True:
        pts, offset = client.scroll(collection_name=index_config.COLLECTION_NAME, limit=500, offset=offset, with_payload=True, with_vectors=False)
        all_ids.update(p.payload["tsu_id"] for p in pts)
        if offset is None:
            break

    final = json.loads((REPO_ROOT / "output/final_human_review_candidate.json").read_text(encoding="utf-8"))
    batch24_36_ids = set(final["screening_clear"]["tsu_ids"]) | set(final["qa_flag_nonblocking"]["tsu_ids"])
    pre_existing_ids = batch24_36_ids | PILOT_IDS
    backlog_ids = all_ids - pre_existing_ids

    # --- 이전 checkpoint(Batch 24-36) baseline과 비교 ---
    prev_ckpt = REPO_ROOT / "NAE/review/human/checkpoints/batch24_36_green_checkpoint/MANIFEST.json"
    prev_manifest = json.loads(prev_ckpt.read_text(encoding="utf-8"))
    prev_hashes = prev_manifest["file_hashes"]

    current_hashes = {
        "Dagg_Church_Order_tsu.json": sha256(REPO_ROOT / "NAE/corpus/tsu/Dagg_Church_Order/tsu.json"),
        "Hiscox_Standard_Manual_tsu.json": sha256(REPO_ROOT / "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json"),
        "exception_queue.json": sha256(REPO_ROOT / "NAE/review/human/exception_queue.json"),
    }
    production_unchanged = all(current_hashes[k] == prev_hashes[k] for k in current_hashes)

    # --- 신규(Batch 1-23) checkpoint 자체 무결성 ---
    new_ckpt_dir = REPO_ROOT / "NAE/review/human/checkpoints/batch1_23_backlog_embedding_checkpoint"
    new_manifest = json.loads((new_ckpt_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    ckpt_integrity = {
        f: sha256(new_ckpt_dir / f) == h for f, h in new_manifest["file_hashes"].items()
    }

    # --- embedding cache ---
    cache_root = REPO_ROOT / "NAE/corpus/embeddings/cache"
    cache_count = len(list(cache_root.glob("*.json"))) if cache_root.exists() else 0

    # --- 코드 diff 무결성(index_all 등 무변경 재확인) ---
    def gitcmd(*args: str) -> str:
        return subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO_ROOT).stdout.strip()

    index_all_diff = gitcmd("diff", "c061937..HEAD", "--", "NAE/pipeline/index/indexer.py")

    delta_verification = {
        "qdrant_total_points": info.points_count,
        "qdrant_unique_ids_reconstructed": len(all_ids),
        "pre_existing_ids_count": len(pre_existing_ids),
        "pre_existing_ids_still_present": pre_existing_ids.issubset(all_ids),
        "backlog_ids_count": len(backlog_ids),
        "backlog_ids_equals_2038": len(backlog_ids) == 2038,
        "arithmetic": f"{len(pre_existing_ids)} + {len(backlog_ids)} = {len(pre_existing_ids) + len(backlog_ids)}",
        "arithmetic_matches_total": (len(pre_existing_ids) + len(backlog_ids)) == info.points_count,
    }

    verified_recompute = {
        "dagg_verified": dagg_status.get("verified", 0),
        "hiscox_verified": hiscox_status.get("verified", 0),
        "total_verified": dagg_status.get("verified", 0) + hiscox_status.get("verified", 0),
        "matches_qdrant_points": (dagg_status.get("verified", 0) + hiscox_status.get("verified", 0)) == info.points_count,
    }

    evidence = {
        "generated_at": now(),
        "generated_by": "CUE (execution-record based, independent of C1's audit files)",
        "scope": "Batch 1-23 backlog embedding, 2,038 TSUs (Dagg 1,682 + Hiscox 356)",
        "related_commits": {
            "bugfix_and_tests": "cc78781",
            "checkpoint": "1e338af",
        },
        "delta_verification": delta_verification,
        "verified_recompute": verified_recompute,
        "qdrant_state": {
            "collection": index_config.COLLECTION_NAME,
            "points_count": info.points_count,
            "vector_size": info.config.params.vectors.size,
            "distance": str(info.config.params.vectors.distance),
        },
        "embedding_cache_file_count": cache_count,
        "production_mutation": {
            "compared_against": "nae-batch24-36-green-checkpoint MANIFEST.json",
            "current_hashes": current_hashes,
            "previous_hashes": {k: prev_hashes[k] for k in current_hashes},
            "unchanged": production_unchanged,
        },
        "checkpoint_integrity": {
            "checkpoint_dir": "NAE/review/human/checkpoints/batch1_23_backlog_embedding_checkpoint",
            "file_hash_matches": ckpt_integrity,
            "all_match": all(ckpt_integrity.values()),
        },
        "index_all_code_diff_since_promotion": {
            "diff_empty": index_all_diff == "",
            "note": "index_all()/index_identifier() 코드가 c061937(Batch24-36 checkpoint) 이후 전혀 수정되지 않았는지 확인 — 이번 backlog embedding은 scripts/nae_incremental_ingest.py --apply만 사용했다.",
        },
    }

    overall_gate = all([
        delta_verification["backlog_ids_equals_2038"],
        delta_verification["pre_existing_ids_still_present"],
        delta_verification["arithmetic_matches_total"],
        verified_recompute["matches_qdrant_points"],
        production_unchanged,
        evidence["checkpoint_integrity"]["all_match"],
        evidence["index_all_code_diff_since_promotion"]["diff_empty"],
    ])
    evidence["overall_gate"] = "READ_ONLY_EVIDENCE_COMPLETE_PASS" if overall_gate else "READ_ONLY_EVIDENCE_COMPLETE_WITH_FAILURES"

    OUT.mkdir(exist_ok=True)
    (OUT / "batch1_23_backlog_embedding_evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md = f"""# Batch 1-23 Backlog Embedding Evidence Package (2,038 TSUs)

CUE 실행 기록 기반(C1 감사 파일 미참조). 생성 시각: {evidence['generated_at']}

## Delta Verification (핵심 증명)

```
pre-existing IDs (Batch 24-36 1,271 + Pilot 10) = {delta_verification['pre_existing_ids_count']}
backlog IDs (Batch 1-23, Qdrant 전체 - pre-existing)  = {delta_verification['backlog_ids_count']}
Qdrant 실측 총 points                                  = {delta_verification['qdrant_total_points']}

{delta_verification['arithmetic']}
산술 일치: {delta_verification['arithmetic_matches_total']}
backlog = 2038 정확히 일치: {delta_verification['backlog_ids_equals_2038']}
기존 1,281 ID 전부 보존: {delta_verification['pre_existing_ids_still_present']}
```

## Production Verified Recompute

```
Dagg verified: {verified_recompute['dagg_verified']}
Hiscox verified: {verified_recompute['hiscox_verified']}
합계: {verified_recompute['total_verified']}
Qdrant points와 일치: {verified_recompute['matches_qdrant_points']}
```

## Qdrant State

```
collection: {evidence['qdrant_state']['collection']}
points_count: {evidence['qdrant_state']['points_count']}
vector_size: {evidence['qdrant_state']['vector_size']}
distance: {evidence['qdrant_state']['distance']}
```

## Production Mutation (vs nae-batch24-36-green-checkpoint)

```
Dagg hash 일치: {current_hashes['Dagg_Church_Order_tsu.json'] == prev_hashes['Dagg_Church_Order_tsu.json']}
Hiscox hash 일치: {current_hashes['Hiscox_Standard_Manual_tsu.json'] == prev_hashes['Hiscox_Standard_Manual_tsu.json']}
exception_queue hash 일치: {current_hashes['exception_queue.json'] == prev_hashes['exception_queue.json']}
전체 무변경: {production_unchanged}
```

## Checkpoint Integrity

```
{json.dumps(ckpt_integrity, indent=2, ensure_ascii=False)}
전체 일치: {evidence['checkpoint_integrity']['all_match']}
```

## index_all() 코드 무변경 확인

```
diff (c061937..HEAD, NAE/pipeline/index/indexer.py): {'EMPTY' if evidence['index_all_code_diff_since_promotion']['diff_empty'] else 'NON-EMPTY'}
```

## Overall Gate

**{evidence['overall_gate']}**
"""
    (OUT / "batch1_23_backlog_embedding_evidence.md").write_text(md, encoding="utf-8")

    print(json.dumps({
        "delta_verification": delta_verification,
        "verified_recompute": verified_recompute,
        "production_mutation_unchanged": production_unchanged,
        "checkpoint_integrity_all_match": evidence["checkpoint_integrity"]["all_match"],
        "overall_gate": evidence["overall_gate"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
