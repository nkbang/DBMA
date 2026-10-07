#!/usr/bin/env python3
"""MLX vs Ollama 생성 벤치마크 (B0, 읽기 전용 — DBMA 코드 비수정).

동일 프롬프트로 두 백엔드의 prefill/decode 속도, TTFT, 메모리, 출력을 측정한다.
한 번에 한 백엔드만 실행해 메모리 경합을 피한다(--backend).

사용 예:
  # Ollama (어느 venv든 가능, requests 불필요 — urllib 사용)
  python scripts/bench_mlx_vs_ollama.py --backend ollama \
      --model qwen3.6:35b --out /tmp/bench_ollama.json

  # MLX (mlx-lm 설치된 venv: ~/envs/mlx)
  python scripts/bench_mlx_vs_ollama.py --backend mlx \
      --model mlx-community/Qwen3-30B-A3B-4bit --out /tmp/bench_mlx.json

  # 비교
  python scripts/bench_mlx_vs_ollama.py --compare /tmp/bench_ollama.json /tmp/bench_mlx.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"

# 신학 RAG 대표 프롬프트: (id, 근거 컨텍스트 길이 구분, 프롬프트)
_CTX = (
    "다음은 참고 자료이다.\n"
    "[1] 로마서 3:23-24 — 모든 사람이 죄를 범하였으매 하나님의 영광에 이르지 못하더니, "
    "그리스도 예수 안에 있는 속량으로 말미암아 하나님의 은혜로 값없이 의롭다 하심을 얻은 자 되었느니라.\n"
    "[2] 칭의(δικαίωσις)는 법정적 선언이며 성화와 구별된다는 것이 개혁주의 전통의 이해이다.\n"
)
PROMPTS = [
    ("short", "짧은 질의", "칭의와 성화의 차이를 세 문장으로 설명하라."),
    ("ctx", "근거 포함(prefill 중심)",
     _CTX * 6 + "\n위 자료만 근거로 로마서 3:24의 '값없이'(δωρεάν)의 의미를 설교자를 위해 해설하라."),
    ("greek", "헬라어/히브리어",
     "요한복음 1:1의 λόγος와 창세기 1:1의 בָּרָא를 각각 한 단락씩 주해하라."),
]


def bench_ollama(model: str, prompt: str, max_tokens: int, temperature: float, think: bool = False) -> dict:
    body = json.dumps({
        "model": model, "prompt": prompt, "stream": False, "think": think,
        "options": {"num_predict": max_tokens, "temperature": temperature},
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, body, {"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.load(r)
    wall = time.perf_counter() - t0
    pe, ee = d.get("prompt_eval_duration", 0) / 1e9, d.get("eval_duration", 0) / 1e9
    return {
        "text": d.get("response", "") or d.get("thinking", ""),
        "prompt_tokens": d.get("prompt_eval_count", 0),
        "gen_tokens": d.get("eval_count", 0),
        "prefill_tps": d.get("prompt_eval_count", 0) / pe if pe else 0.0,
        "decode_tps": d.get("eval_count", 0) / ee if ee else 0.0,
        "ttft_s": (d.get("load_duration", 0) / 1e9) + pe,
        "wall_s": wall,
        "peak_mem_gb": None,  # Ollama는 응답에 메모리 미포함
    }


_mlx_cache: dict = {}


def bench_mlx(model: str, prompt: str, max_tokens: int, temperature: float, think: bool = False) -> dict:
    import mlx.core as mx
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler

    if model not in _mlx_cache:
        _mlx_cache[model] = load(model)
    m, tok = _mlx_cache[model]
    if getattr(tok, "chat_template", None):
        prompt = tok.apply_chat_template(
            [{"role": "user", "content": prompt}], add_generation_prompt=True, tokenize=False,
            enable_thinking=think)
    mx.reset_peak_memory()
    t0 = time.perf_counter()
    ttft, last, parts = None, None, []
    for resp in stream_generate(m, tok, prompt, max_tokens=max_tokens,
                                sampler=make_sampler(temp=temperature)):
        if ttft is None:
            ttft = time.perf_counter() - t0
        parts.append(resp.text)
        last = resp
    return {
        "text": "".join(parts),
        "prompt_tokens": last.prompt_tokens,
        "gen_tokens": last.generation_tokens,
        "prefill_tps": last.prompt_tps,
        "decode_tps": last.generation_tps,
        "ttft_s": ttft,
        "wall_s": time.perf_counter() - t0,
        "peak_mem_gb": mx.get_peak_memory() / 1e9,
    }


def run(args) -> None:
    fn = bench_ollama if args.backend == "ollama" else bench_mlx
    # warmup (모델 로드 비용 제외)
    print(f"[bench] warmup backend={args.backend} model={args.model}", file=sys.stderr)
    fn(args.model, "안녕", 8, args.temperature, args.think)
    rows = []
    for pid, label, prompt in PROMPTS:
        for i in range(args.repeats):
            # 프롬프트 캐시(Ollama KV 재사용) 적중 방지: 실행마다 고유 접두어
            uniq = f"[bench-{time.time_ns()}]\n{prompt}"
            r = fn(args.model, uniq, args.max_tokens, args.temperature, args.think)
            r.update(prompt_id=pid, label=label, run=i)
            rows.append(r)
            print(f"[bench] {pid}#{i} decode={r['decode_tps']:.1f} tok/s "
                  f"prefill={r['prefill_tps']:.1f} ttft={r['ttft_s']:.2f}s", file=sys.stderr)
    out = {"backend": args.backend, "model": args.model, "max_tokens": args.max_tokens,
           "temperature": args.temperature, "think": args.think, "rows": rows}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"[bench] saved {args.out}", file=sys.stderr)


def _med(rows, pid, key):
    v = [r[key] for r in rows if r["prompt_id"] == pid and r[key] is not None]
    return statistics.median(v) if v else None


def compare(a_path: str, b_path: str) -> None:
    a, b = (json.loads(Path(p).read_text()) for p in (a_path, b_path))
    print(f"A={a['backend']}:{a['model']}\nB={b['backend']}:{b['model']}\n")
    print(f"{'prompt':8} {'metric':12} {'A':>10} {'B':>10} {'B/A':>7}")
    for pid, _, _ in PROMPTS:
        for key, better_high in (("decode_tps", True), ("prefill_tps", True), ("ttft_s", False)):
            x, y = _med(a["rows"], pid, key), _med(b["rows"], pid, key)
            ratio = (y / x if better_high else x / y) if x and y else None
            print(f"{pid:8} {key:12} {x or 0:10.2f} {y or 0:10.2f} "
                  f"{(f'{ratio:.2f}x' if ratio else '-'):>7}")
    mem = [r["peak_mem_gb"] for r in b["rows"] + a["rows"] if r["peak_mem_gb"]]
    if mem:
        print(f"\nMLX peak mem: {max(mem):.1f} GB")
    print("\n※ 품질은 수치로 판정 불가 — JSON의 rows[].text 를 prompt_id별로 눈으로 비교할 것.")
    print("※ 채택 기준: decode ≥1.3x(B/A) AND 품질 동등 AND 장시간 안정.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--backend", choices=["ollama", "mlx"])
    p.add_argument("--model")
    p.add_argument("--out")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--max-tokens", type=int, default=256)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--think", action="store_true", help="thinking 모드 켜기(기본 꺼짐, 양쪽 동일 적용)")
    p.add_argument("--compare", nargs=2, metavar=("A_JSON", "B_JSON"))
    args = p.parse_args()
    if args.compare:
        compare(*args.compare)
        return
    if not (args.backend and args.model and args.out):
        p.error("--backend, --model, --out 필요 (또는 --compare)")
    run(args)


if __name__ == "__main__":
    main()
