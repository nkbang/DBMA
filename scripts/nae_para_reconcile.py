"""Stage 1 정합성 게이트 — canonical.json ↔ nae_tsu_v1 payload 대조 (읽기 전용).

[PM 정렬 감사 선결 #4 / 옵션 A]
Task Order: docs/NAE_PARAGRAPH_ANSWER_DELIVERY_IMPL_TASK_ORDER_001.md §1-3, §1-4

이 스크립트는 **라이브 nae_qdrant(포트 7333)** 가 필요하다. 이 워크트리의
샌드박스 환경에는 Qdrant가 없어 CI/유닛테스트로 돌리지 않는다 —
`nae_pd`가 켜진 실서버(또는 NAS)에서 수동 실행한다.

무엇도 쓰지 않는다: Qdrant scroll(payload only), canonical.json read.

게이트 (TO §1-3):
  임의 체크 실패율 ≤ 1%          → GO
  부분문자열 실패 1~5%          → GO (정규화 강화 후 재측정)
  임의 체크 실패율 > 5%         → STOP · HQ 보고 (NO-GO)

사용:
  ~/envs/dbma311/bin/python scripts/nae_para_reconcile.py \
      [--limit N] [--out docs/NAE_PARAGRAPH_ANSWER_DELIVERY_RECONCILE_001.md]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

_WS_RE = re.compile(r"\s+")


def _norm(s: str) -> str:
    """OCR/공백 정규화 — 부분문자열 대조용."""
    return _WS_RE.sub(" ", (s or "").strip()).lower()


def _load_canonical_paragraphs(identifier: str, canonical_root: Path) -> dict[int, dict] | None:
    p = canonical_root / identifier / "canonical.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    out: dict[int, dict] = {}
    for para in data.get("paragraphs", []):
        idx = para.get("index")
        if isinstance(idx, int):
            para = dict(para)
            para["_pipeline_version"] = str(data.get("pipeline_version", ""))
            out[idx] = para
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = 전체")
    ap.add_argument("--out", default="docs/NAE_PARAGRAPH_ANSWER_DELIVERY_RECONCILE_001.md")
    args = ap.parse_args()

    try:
        from NAE.pipeline.index import qdrant_store, config as index_config
        from NAE.pipeline.tsu import config as tsu_config
    except Exception as exc:  # noqa: BLE001
        print(f"[reconcile] NAE 모듈 import 실패: {exc}", file=sys.stderr)
        return 2

    canonical_root = tsu_config.CANONICAL_ROOT
    client = qdrant_store.get_client()
    collection = index_config.COLLECTION_NAME

    checks = Counter()
    total = 0
    fail_samples: list[str] = []
    para_lengths: list[int] = []
    seen_para: set[tuple[str, int]] = set()

    next_page = None
    while True:
        points, next_page = client.scroll(
            collection_name=collection, limit=512, offset=next_page,
            with_payload=True, with_vectors=False,
        )
        for pt in points:
            total += 1
            pl = pt.payload or {}
            ident = pl.get("identifier")
            para_idx = pl.get("paragraph")
            tsu_id = pl.get("tsu_id")

            if not ident:
                checks["no_identifier"] += 1
            if para_idx is None:
                checks["no_paragraph"] += 1
            if not ident or para_idx is None:
                if len(fail_samples) < 20:
                    fail_samples.append(f"{tsu_id}: identifier/paragraph 결측")
                continue

            paras = _load_canonical_paragraphs(ident, canonical_root)
            if paras is None:
                checks["canonical_missing"] += 1
                if len(fail_samples) < 20:
                    fail_samples.append(f"{tsu_id}: canonical.json 없음 ({ident})")
                continue

            base = paras.get(para_idx)
            if base is None:
                checks["index_missing"] += 1
                if len(fail_samples) < 20:
                    fail_samples.append(f"{tsu_id}: 문단 index {para_idx} 없음 ({ident})")
                continue

            pv_payload = str(pl.get("canonical_version") or "")
            pv_canon = base.get("_pipeline_version", "")
            if pv_payload and pv_canon and pv_payload != pv_canon:
                checks["version_mismatch"] += 1
                if len(fail_samples) < 20:
                    fail_samples.append(f"{tsu_id}: canonical_version {pv_payload}≠{pv_canon}")

            para_text = base.get("text", "")
            key = (ident, para_idx)
            if key not in seen_para:
                seen_para.add(key)
                para_lengths.append(len(para_text))

            src = pl.get("source_text") or ""
            if src and _norm(src) not in _norm(para_text):
                checks["substring_fail"] += 1
                if len(fail_samples) < 20:
                    fail_samples.append(f"{tsu_id}: source_text ⊄ 문단 ({ident}#{para_idx})")

            checks["ok"] += 1

        if args.limit and total >= args.limit:
            break
        if next_page is None:
            break

    # 게이트 판정
    def pct(n): return (100.0 * n / total) if total else 0.0
    substr_pct = pct(checks["substring_fail"])
    hard_fail = sum(
        checks[k] for k in ("no_identifier", "no_paragraph", "canonical_missing",
                            "index_missing", "version_mismatch")
    )
    hard_pct = pct(hard_fail)

    if hard_pct > 5.0:
        verdict = "NO-GO — STOP · HQ 보고 (임의 체크 실패율 > 5%)"
    elif substr_pct > 5.0:
        verdict = "NO-GO — 부분문자열 실패 > 5%"
    elif substr_pct > 1.0:
        verdict = "GO (조건부) — 부분문자열 실패 1~5%, 정규화 강화 후 재측정"
    else:
        verdict = "GO — 임의 체크 실패율 ≤ 1%"

    para_lengths.sort()
    def q(frac):
        return para_lengths[int(frac * (len(para_lengths) - 1))] if para_lengths else 0

    lines = [
        "---",
        "title: NAE 문단 앵커드 근거 — 정합성 스캔 결과 (Stage 1)",
        "generated_by: scripts/nae_para_reconcile.py",
        "---",
        "",
        f"- 총 point: {total}",
        f"- 고유 (identifier, paragraph): {len(seen_para)}",
        "",
        "## 체크 실패 분포",
        "",
        "| 체크 | 건수 | 비율 |",
        "|---|---|---|",
    ]
    for k in ("no_identifier", "no_paragraph", "canonical_missing", "index_missing",
              "version_mismatch", "substring_fail", "ok"):
        lines.append(f"| {k} | {checks[k]} | {pct(checks[k]):.2f}% |")
    lines += [
        "",
        f"- hard 실패율(결측·부재·버전): **{hard_pct:.2f}%**",
        f"- 부분문자열 실패율: **{substr_pct:.2f}%**",
        "",
        "## 문단 길이 분포 (가정 8 — 컨텍스트 예산)",
        "",
        f"- 중앙값: {q(0.5)}자 · p95: {q(0.95)}자 · max: {max(para_lengths) if para_lengths else 0}자",
        f"- >1,500자 비율: {pct(sum(1 for x in para_lengths if x > 1500)):.2f}%",
        f"- top_k=10 × p95 문단 ≈ {10 * q(0.95)}자 (num_ctx 32768 예산 대비 확인 필요)",
        "",
        "## 게이트 판정",
        "",
        f"**{verdict}**",
        "",
        "## 실패 샘플 (최대 20)",
        "",
    ]
    lines += [f"- {s}" for s in fail_samples] or ["- (없음)"]

    out = Path(args.out)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n[reconcile] → {out}")
    return 0 if verdict.startswith("GO") else 1


if __name__ == "__main__":
    raise SystemExit(main())
