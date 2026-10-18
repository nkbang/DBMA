#!/usr/bin/env python3
"""scripts/j6_generation_model_ab.py — 생성 모델 A/B 실측 (J6).

[J6, 2026-10-18] 조건 ④(한국어 문법·문학적 완결 문장)의 남은 원인은 필터가
아니라 **생성 모델**이다. `core/generation.py`의 오염 방어는 이미 설계 한계에
가깝다 — 문자 체계 9종 + 라틴 문맥 기준 탐지 + 재시도 2회 + 소진 시 표식·고지
(삭제는 2026-09-26에 폐지). 그런데도 P0-5 24건 재실행에서 오염 탐지 이벤트가
28회였고, 한글 토큰 드롭("그리스도의 **의**가" → "그리스도의 가")은 남은
글자가 전부 한글이어서 **문자 체계 검사로는 원리상 탐지 불가**다. 이 결함군은
`my-theology-bot-v2`(llama3.3:70b **Q4_K_M**) 양자화 모델의 "개념 주변
크로스링구얼 오염"으로 2026-07-21에 이미 실측된 바 있다.

그래서 모델을 바꿔 본다. 공정한 비교를 위해 두 가지를 통제한다:

1. **근거 동일** — 질의당 검색을 1회만 돌리고 그 ResponsePackage를 모든
   모델에 그대로 넘긴다. 모델별로 검색을 다시 돌리면 캐시·색인 상태에 따라
   근거가 달라져 비교가 무의미해진다.
2. **SYSTEM 프롬프트 동일** — 현행 모델에는 한국어 신학 SYSTEM 프롬프트가
   있고 후보 모델은 맨몸이다. 그대로 비교하면 모델이 아니라 프롬프트를
   비교하게 되므로, 후보에도 **같은 SYSTEM 전문**을 입힌 파생 모델을 만들어
   비교한다(`nae-gen-qwen38:ab`, `nae-gen-qwen36:ab`).

측정 축 (모두 산출물에서 직접 센다):
  - 오염 **이벤트** 수: `core.generation` 로거의 "한국어 출력 오염 감지"
    경고를 핸들러로 가로채 센다(재시도를 유발한 횟수).
  - **잔존** 오염: 최종 답변에 남은 비한글 문자 체계·라틴 외국어.
  - 표식(□) 개수와 고지 문구 부착 여부(재시도 소진 흔적).
  - 답변 길이, 생성 지연(p50/p90).
  - 출처 표기율: 답변에 "출처" 표기가 들어간 비율(근거 추적 가능성).

채점(PASS/FLAG/FAIL)은 하지 않는다 — 신학적 정합성 판단은 사용자 몫이다.
이 스크립트는 객관 신호만 모은다.

사용:
    # 프로덕션 루트를 CWD로 두고 실행(코퍼스 상대경로)
    python3 scripts/j6_generation_model_ab.py --out /path/to/j6_result.json
    python3 scripts/j6_generation_model_ab.py --queries 8   # 표본 줄여 시험
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.generation import (  # noqa: E402
    _CONTAMINATION_MARKER,
    _detect_latin_contamination,
    _detect_script_contamination,
    GenerationService,
)
from core.hybrid_candidate_pipeline import HybridQueryProcessor, is_enabled  # noqa: E402
from core.retrieval import QueryProcessor  # noqa: E402
from scripts.p0_5_run_all import QUERIES, _K  # noqa: E402

_MODELS = [
    "my-theology-bot-v2:latest",  # 현행 (llama3.3:70b Q4_K_M)
    "nae-gen-qwen38:ab",          # 후보 1 (qwen3.8:27b-q8_0, dense·Q8)
    "nae-gen-qwen36:ab",          # 후보 2 (qwen3.6:35b, MoE)
]


class _ContaminationCounter(logging.Handler):
    """`core.generation`이 재시도를 유발할 때 남기는 경고를 센다."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.events = 0
        self.retry_exhausted = 0

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if "한국어 출력 오염 감지" in msg:
            self.events += 1
        elif "재시도 소진" in msg:
            self.retry_exhausted += 1

    def reset(self) -> None:
        self.events = 0
        self.retry_exhausted = 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="결과 JSON 경로")
    parser.add_argument("--queries", type=int, default=0, help="앞 N건만 (0=전체 24건)")
    parser.add_argument("--models", default=",".join(_MODELS))
    args = parser.parse_args()

    queries = QUERIES[: args.queries] if args.queries else QUERIES
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    processor = HybridQueryProcessor() if is_enabled() else QueryProcessor()
    generator = GenerationService()

    # ── 1) 검색은 질의당 1회만. 모든 모델이 같은 근거를 본다. ──
    print(f"[J6] 검색 1회차 — 질의 {len(queries)}건", flush=True)
    responses: list[tuple[str, str, object]] = []
    for tag, question in queries:
        r = processor.process(question, query_id=f"j6-{tag}", k=_K, file_scope=None)
        n = len(r.top_k_results or [])
        print(f"  [{tag}] 근거 {n}건", flush=True)
        responses.append((tag, question, r))

    counter = _ContaminationCounter()
    logging.getLogger("core.generation").addHandler(counter)

    # ── 2) 모델 바깥 루프 — 모델을 한 번 적재해 24건을 돌린다. ──
    out: dict[str, dict] = {}
    for model in models:
        print(f"\n[J6] ===== {model} =====", flush=True)
        per_query = []
        for tag, question, response in responses:
            if not (response.top_k_results or []):
                print(f"  [{tag}] 근거 0건 — 생성 건너뜀(유보 게이트)", flush=True)
                continue
            counter.reset()
            t0 = time.time()
            result = generator.generate(response, gen_model=model)
            took = time.time() - t0
            answer = result.answer or ""
            ctx = response.llm_context_block or ""
            residual_script = _detect_script_contamination(answer)
            residual_latin = _detect_latin_contamination(answer, ctx)
            row = {
                "tag": tag,
                "seconds": round(took, 1),
                "chars": len(answer),
                "events": counter.events,
                "retry_exhausted": counter.retry_exhausted,
                "residual_script": residual_script,
                "residual_latin": residual_latin,
                "markers": answer.count(_CONTAMINATION_MARKER),
                "has_source_label": ("출처" in answer),
                "error": result.error,
                "answer": answer,
            }
            per_query.append(row)
            flags = []
            if row["events"]:
                flags.append(f"오염 {row['events']}회")
            if row["markers"]:
                flags.append(f"표식 {row['markers']}자")
            if residual_latin:
                flags.append(f"라틴 {residual_latin[:3]}")
            print(f"  [{tag}] {took:5.1f}s {len(answer):5,}자"
                  f"{'  ⚠ ' + ', '.join(flags) if flags else ''}", flush=True)

        secs = sorted(r["seconds"] for r in per_query) or [0]
        out[model] = {
            "queries": len(per_query),
            "events_total": sum(r["events"] for r in per_query),
            "queries_with_events": sum(1 for r in per_query if r["events"]),
            "retry_exhausted": sum(r["retry_exhausted"] for r in per_query),
            "markers_total": sum(r["markers"] for r in per_query),
            "residual_script_queries": sum(1 for r in per_query if r["residual_script"]),
            "residual_latin_queries": sum(1 for r in per_query if r["residual_latin"]),
            "source_label_rate": round(
                sum(1 for r in per_query if r["has_source_label"]) / max(len(per_query), 1), 3
            ),
            "chars_median": int(statistics.median(r["chars"] for r in per_query)) if per_query else 0,
            "sec_p50": secs[len(secs) // 2],
            "sec_p90": secs[int(len(secs) * 0.9)] if len(secs) > 1 else secs[0],
            "errors": sum(1 for r in per_query if r["error"]),
            "rows": per_query,
        }

    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 3) 비교표 ──
    print("\n[J6] 요약")
    hdr = f"{'모델':28} {'오염ev':>6} {'질의':>5} {'소진':>5} {'표식':>5} {'잔존':>5} {'출처%':>6} {'중위자':>7} {'p50s':>6} {'p90s':>6}"
    print(hdr)
    for m, s in out.items():
        print(f"{m:28} {s['events_total']:>6} {s['queries_with_events']:>5} "
              f"{s['retry_exhausted']:>5} {s['markers_total']:>5} "
              f"{s['residual_script_queries'] + s['residual_latin_queries']:>5} "
              f"{s['source_label_rate'] * 100:>5.0f}% {s['chars_median']:>7,} "
              f"{s['sec_p50']:>6.1f} {s['sec_p90']:>6.1f}")
    print(f"\n[J6] 결과 → {args.out}")
    print("채점(PASS/FLAG/FAIL)은 사용자 몫이다 — 이 표는 객관 신호다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
