#!/usr/bin/env python3
"""scripts/j7_scoring/build_scoring_artifact.py — J7 채점표 아티팩트 생성.

[J7, 2026-10-19] 사용자 승인 후 작성. 2026-09-12 채점표 아티팩트는 09-12
시범 실행(코퍼스=매튜 풀 1권) 답변을 담고 있어 그대로 채점하면 옛 답을
채점하게 된다. 이 스크립트는 **현재 수집된 두 모델의 24건 답변**을 그대로
주입한 새 채점표를 만든다 — 기존 아티팩트는 건드리지 않는다.

한 화면에서 두 가지를 끝낸다:
  1) A/B 선택  — 모델 전환 결정(J6)
  2) 채점      — PASS/FLAG/FAIL(G7). 축·판정식·정직유보 규칙은
                 docs/NAE_GOLD_QUERY_SET_P0_5_001.md가 정한 그대로다.

사용:
    python3 scripts/j7_scoring/build_scoring_artifact.py --out <경로>.html
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.p0_5_run_all import QUERIES  # noqa: E402

A_FILE = ROOT / "docs/NAE_ANSWER_QUALITY_J6_MODEL_AB_001.json"
B_FILE = ROOT / "docs/NAE_ANSWER_QUALITY_J6_MODEL_AB_002_candidates.json"
A_KEY = "my-theology-bot-v2:latest"
B_KEY = "nae-gen-qwen38:ab"

# 유형 정의 — docs/NAE_GOLD_QUERY_SET_P0_5_001.md의 8유형과 1:1.
CATS = [
    ("A", "본문 주해", "자의적 해석 대신 역사-문법적 근거로 답하는가"),
    ("B", "교리 질문", "개혁파 침례교 정합성, 근거 없는 단정 여부"),
    ("C", "설교 적용", "목회적 유용성, 완결된 문단 형태의 설교 대지"),
    ("D", "신학적 논쟁", "상충하는 전통이 표지 없이 섞이지 않는가"),
    ("E", "목회상담", "목회적 유용성 + 단정적 판단을 남발하지 않는가"),
    ("F", "한영 자료 기반 질의", "번역투 여부, 영어 원문 미번역 노출 여부"),
    ("G", "근거 불충분 질의", "지어내지 않고 유보·정직하게 밝히는가"),
    ("H", "난제 연구", "신정론·성경 난제·신앙과 과학의 긴장을 회피하지 않는가"),
]

# 답변이 "유보성"인지 판단하는 문구 — 정직 유보 → 수동 PASS 규칙 안내용 배지.
HOLD_FRAGMENTS = (
    "답할 수 없습니다", "찾을 수 없습니다", "자료에는",
    "언급되어 있지 않", "충분하지 않", "찾아볼 수 없",
)


def _rows(path: Path, key: str) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {r["tag"]: r for r in data[key]["rows"]}


def _side(row: dict | None) -> dict:
    if row is None:
        return {"text": "", "chars": 0, "secs": 0, "markers": 0,
                "events": 0, "src": False, "latin": [], "hold": False}
    text = row.get("answer") or ""
    return {
        "text": text,
        "chars": row.get("chars") or len(text),
        "secs": row.get("seconds") or 0,
        "markers": row.get("markers") or 0,
        "events": row.get("events") or 0,
        "src": bool(row.get("has_source_label")),
        "latin": row.get("residual_latin") or [],
        "hold": any(f in text for f in HOLD_FRAGMENTS),
    }


def build_payload() -> dict:
    A, B = _rows(A_FILE, A_KEY), _rows(B_FILE, B_KEY)
    items = []
    for tag, question in QUERIES:
        items.append({
            "id": tag,
            "cat": tag[0],
            "q": question,
            "a": _side(A.get(tag)),
            "b": _side(B.get(tag)),
        })
    return {
        "cats": [{"id": c, "name": n, "target": t} for c, n, t in CATS],
        "items": items,
        "scores": {},          # 사용자 입력이 여기 쌓인다
        "updatedAt": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--template", default=str(Path(__file__).resolve().parent / "template.html"))
    a = ap.parse_args()

    payload = build_payload()
    tpl = Path(a.template).read_text(encoding="utf-8")
    if "__DATA_JSON__" not in tpl:
        print("템플릿에 __DATA_JSON__ 자리표시자가 없다", file=sys.stderr)
        return 1
    # </script> 조기 종료 방지 — JSON을 <script type=application/json>에 심는다.
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    out = tpl.replace("__DATA_JSON__", blob)
    Path(a.out).write_text(out, encoding="utf-8")
    n = len(payload["items"])
    print(f"작성: {a.out}  ({len(out):,}바이트, 질의 {n}건)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
