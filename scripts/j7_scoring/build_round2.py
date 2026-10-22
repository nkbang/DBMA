#!/usr/bin/env python3
"""scripts/j7_scoring/build_round2.py — G7 2차 채점표(남은 건만) 생성.

[J7, 2026-10-21] 1차 채점에서 판정은 24건 전부 PASS로 들어왔으나 슬라이더가
1건을 빼고 전부 0이라 승인된 PASS 정의(평균 ≥4 + 체크 둘)로는 기록이
성립하지 않았다. 사용자 지적대로 **자료 충실성을 사람이 다시 매기는 것은
비현실적**이다 — 19세기 영문 근거 120덩어리를 대조해야 하기 때문이다.

그래서 축을 성격별로 나눴다:

  자료 충실성   → 기계 측정(core/citation_verifier.py). 사람 대상 아님.
  신학적 정합성 → 사용자 전용. 원문 불필요.
  목회적 유용성 → 사용자 전용. 원문 불필요.
  언어 완성도   → 답변만 읽으면 됨. 원문 불필요.

그리고 24건을 세 갈래로 나눠 사람이 볼 것만 남긴다:

  순수 유보(13) — 자료에 없다고 밝히고 멈춤. 실질 주장이 없다.
                  "정직 유보 → 수동 PASS" 규칙을 그대로 적용한다(판단이 아니라
                  규칙 적용이므로 미리 기록하고, 화면에서는 접어서 확인만 받는다).
  부분 유보(4)  — 범위를 먼저 밝히고 **자료에 있는 만큼은 답한다**. 주장이
                  있으므로 채점 대상이다. 1차에서 이 넷을 유보로 뭉뚱그린 것은
                  분류 오류였다.
  실답변(7)     — 채점 대상.

사용:
    python3 scripts/j7_scoring/build_round2.py --out <경로>.html
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.p0_5_run_all import QUERIES  # noqa: E402

B_FILE = ROOT / "docs/NAE_ANSWER_QUALITY_J6_MODEL_AB_002_candidates.json"
B_KEY = "nae-gen-qwen38:ab"
CITE_FILE = ROOT / "docs/NAE_ANSWER_QUALITY_J7_CITATION_CHECK_001.json"

# 분류 — 답변 전문을 읽고 사람이 확인한 결과다(문구 매칭이 아니다).
# 순수 유보: 자료에 없다고 밝히고 멈춘 것. 실질 주장이 없다.
PURE_HOLD = ["A2", "B3", "C1", "D2", "D3", "E3", "F1", "F2", "F3", "G1", "G2", "G3", "H3"]
# 부분 유보: 범위를 밝히되 자료에 있는 내용을 실제로 정리한 것.
PARTIAL = ["A1", "D1", "E1", "E2"]
# 나머지는 실답변.

CATS = {
    "A": "본문 주해", "B": "교리 질문", "C": "설교 적용", "D": "신학적 논쟁",
    "E": "목회상담", "F": "한영 자료 기반 질의", "G": "근거 불충분 질의", "H": "난제 연구",
}

# 유보가 정답인 질의 — 해당 문헌이 코퍼스에 없거나(F), 존재하지 않는 대상을
# 묻는다(G). 사용자가 확인할 때 근거가 되도록 표시한다.
HOLD_IS_CORRECT = {
    "F1": "Hiscox 『The Standard Manual』 미보유",
    "F2": "Dagg 『Church Order』 미보유",
    "F3": "Fuller 『The Gospel Worthy』 미보유",
    "G1": "존재하지 않는 '공식 입장'을 묻는 질의",
    "G2": "가상 인물(존 스미스 3세) — 환각 함정",
}


def build_payload() -> dict:
    rows = {r["tag"]: r for r in json.loads(B_FILE.read_text(encoding="utf-8"))[B_KEY]["rows"]}
    cites = {c["tag"]: c for c in json.loads(CITE_FILE.read_text(encoding="utf-8"))}
    questions = dict(QUERIES)

    def entry(tag: str, kind: str) -> dict:
        r = rows.get(tag) or {}
        c = cites.get(tag) or {}
        return {
            "id": tag,
            "cat": tag[0],
            "catName": CATS[tag[0]],
            "q": questions.get(tag, ""),
            "kind": kind,
            "text": r.get("answer") or "",
            "chars": r.get("chars") or 0,
            "secs": r.get("seconds") or 0,
            "markers": r.get("markers") or 0,
            "events": r.get("events") or 0,
            "src": bool(r.get("has_source_label")),
            "citations": c.get("citations", 0),
            "issues": c.get("messages") or [],
            "holdNote": HOLD_IS_CORRECT.get(tag, ""),
        }

    to_score = [entry(t, "full") for t, _ in QUERIES if t not in PURE_HOLD and t not in PARTIAL]
    to_score += [entry(t, "partial") for t, _ in QUERIES if t in PARTIAL]
    held = [entry(t, "hold") for t, _ in QUERIES if t in PURE_HOLD]

    return {
        "toScore": to_score,
        "held": held,
        "scores": {},
        "updatedAt": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--template", default=str(Path(__file__).resolve().parent / "template_round2.html"))
    a = ap.parse_args()

    payload = build_payload()
    tpl = Path(a.template).read_text(encoding="utf-8")
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    Path(a.out).write_text(tpl.replace("__DATA_JSON__", blob), encoding="utf-8")
    print(f"작성: {a.out} — 채점 {len(payload['toScore'])}건 "
          f"(실답변 {sum(1 for x in payload['toScore'] if x['kind']=='full')} · "
          f"부분유보 {sum(1 for x in payload['toScore'] if x['kind']=='partial')}) · "
          f"규칙적용 유보 {len(payload['held'])}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
