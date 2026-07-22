"""
scripts/shadow_embedding_similarity_distribution.py — ADR-008 제안 3
재보정 Preflight (2026-07-21).

Diagnostic/analysis artifact only — NOT part of the production pipeline.

scripts/shadow_d5_metrics_embedding_rerun.py의 실측(Profile B 4개 문서
전체)에서 EmbeddingSimilarityBoundaryFeature(drop_threshold=0.5)가 단
한 번도 발화하지 않은 것으로 확인됐다 — 임계값이 이 코퍼스의 실제
인접-후보 유사도 분포에 비해 너무 관대(높음)한지 확인하기 위해, 인접
candidate 쌍의 코사인 유사도 분포(percentile)를 직접 계산한다.

Usage:
    python scripts/shadow_embedding_similarity_distribution.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from core.embedder import get_embedder

_real_embed = get_embedder().embed
from core.semantic_boundary_detector import _cosine_similarity
from core.text_normalizer import normalize_pipeline_text
from shadow_boundary_analysis import MD_DIR, _extract_body_text
from shadow_boundary_delta import candidates_with_offsets
from shadow_d5_metrics_embedding_rerun import PROFILE_B_DOC_STEMS, _cached_embed


def main() -> None:
    embed_fn = _cached_embed()
    all_sims: list[float] = []

    for stem in PROFILE_B_DOC_STEMS:
        md_path = MD_DIR / f"{stem}.md"
        if not md_path.exists():
            continue
        body_text = _extract_body_text(md_path.read_text(encoding="utf-8"))
        normalized = normalize_pipeline_text(body_text)
        candidates = candidates_with_offsets(normalized)
        texts = [t for t, _ in candidates]

        sims = []
        prev_vec = None
        skipped = 0
        for t in texts:
            try:
                v = embed_fn(t)
            except Exception:
                # 안전 토큰 한도(1800)를 넘는 candidate — 실제
                # EmbeddingSimilarityBoundaryFeature.score()도 동일하게
                # 예외를 신호 없음(0.0)으로 흡수하므로, 분포 계산에서도
                # 건너뛰고 이전 벡터를 리셋(다음 쌍은 비교 불가)한다.
                prev_vec = None
                skipped += 1
                continue
            if prev_vec is not None:
                sims.append(_cosine_similarity(prev_vec, v))
            prev_vec = v

        all_sims.extend(sims)
        arr = np.array(sims)
        print(
            f"{stem[:40]:40s} n={len(sims):5d} skipped={skipped:4d} "
            f"min={arr.min():.3f} p10={np.percentile(arr,10):.3f} "
            f"p25={np.percentile(arr,25):.3f} median={np.median(arr):.3f} "
            f"p75={np.percentile(arr,75):.3f} p90={np.percentile(arr,90):.3f} "
            f"max={arr.max():.3f}",
            flush=True,
        )

    arr = np.array(all_sims)
    print("\n=== 전체 (Profile B 4개 문서 합산) ===")
    print(f"n={len(arr)}")
    for p in [1, 5, 10, 20, 25, 50, 75, 90]:
        print(f"  p{p:2d} = {np.percentile(arr, p):.4f}")
    print(f"  min={arr.min():.4f}  max={arr.max():.4f}  mean={arr.mean():.4f}")


if __name__ == "__main__":
    main()
