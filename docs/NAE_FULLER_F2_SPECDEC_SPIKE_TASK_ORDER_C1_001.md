# Task Order — F2 Speculative Decoding 스파이크 (측정 전용)

- 발급: CUE (HQ 지시 2026-09-10)
- 실행: **C1** (bounded 측정 · 스크립트 CUE 제공, C1은 그대로 실행하고 raw 출력 보고)
- 검증: CUE (C1 보고를 raw 산출물과 대조)
- 근거: F2 병목 = `my-theology-bot-v2` 순차 추론 ~10.5s/candidate, 7권 ≈ 4.3일. 병렬화(`-np 2`+workers)는 이미 폐기(1.24x + 결정성 붕괴, `NAE_FULLER_F2_PARALLEL_SPEEDUP_RESULT_001.md`). Speculative decoding은 **출력이 수학적으로 동일**(draft는 제안, target이 검증)하므로 결정성 게이트를 못 깨는 유일한 가속 후보.
- 작업 위치: `/Users/David/DBMA` @ `dev/dbma-engine`, venv `~/envs/dbma311`
- **실행 타이밍: F2가 완전히 끝난 뒤**(또는 HQ가 명시적으로 F2를 일시중단한 뒤). F2 실행 중 착수 금지 — GPU 경합이 측정을 오염시키고 hang을 유발함.

---

## 0. 목적과 GO / NO-GO 기준

`llama3.x`/`qwen` 소형 모델을 draft로, `my-theology-bot-v2`를 target으로 speculative decoding을 걸었을 때:

- **GO**: (a) throughput B/A **≥ 1.5x** (b) A·B의 추출 결과 **byte-identical**(claim·doctrine·id·confidence·scriptures·citations 전부) (c) `llm_errors` 증가 없음.
- **NO-GO**: 위 중 하나라도 실패, 또는 Stage 0에서 구조적 blocker.

GO이면 별도 구현 Task Order + C1 Review로 진행. NO-GO이면 폐기하고 결과만 기록.

---

## 1. Stage 0 — Feasibility (구조적 blocker 먼저 확인, ~30분)

### 0-1. target 모델 아키텍처·토크나이저 식별
```bash
ollama show my-theology-bot-v2:latest
ollama show my-theology-bot-v2:latest --modelfile | head -5
```
보고할 것: `architecture` 라인 (예: `llama`, `qwen2`, `qwen3`), `parameters`, `quantization`, `context length`, `FROM` 블롭 경로.

### 0-2. vocab 호환 draft 모델 확보
Speculative decoding은 **draft와 target이 동일 tokenizer/vocab**를 써야 작동한다. 0-1의 architecture에 따라:

| target architecture | draft 후보 (pull) | 크기 |
|---|---|---|
| `llama` (Llama-3.x 70B 계열) | `ollama pull llama3.2:1b` | ~1.3GB |
| `qwen2` / `qwen2.5` (72B 계열) | `ollama pull qwen2.5:0.5b` (없으면 `qwen2.5:1.5b`) | ~0.4–1GB |
| `qwen3` 계열 | `ollama pull qwen3:1.7b` (없으면 목록의 `qwen3.8:27b`는 draft로 부적합 — 너무 큼) | — |
| 그 외 / 불명 | **STOP · 보고** — 호환 draft 없음 |

`llama3.1:8b`는 draft로 쓰지 말 것 — 8B는 draft로 너무 크고(가속 이득 상쇄), target이 Qwen 계열이면 vocab 불일치.

draft 블롭 경로 확보:
```bash
ollama show <draft-model> --modelfile | grep -i "^FROM"
```

### 0-3. llama-server가 `--model-draft`를 지원하는지 확인
Ollama는 `--model-draft`를 Modelfile/API로 노출하지 않으므로, **번들된 llama-server를 직접 실행**한다.
```bash
LS="/Applications/Ollama.app/Contents/Resources/llama-server"
"$LS" --help 2>&1 | grep -iE "model-draft|draft-max|draft-min|-md |speculat"
```
`--model-draft` / `-md` 옵션이 **없으면 STOP · 보고** (이 Ollama 빌드는 spec decoding 불가).

### Stage 0 산출물
`docs/NAE_FULLER_F2_SPECDEC_SPIKE_RESULT_C1_001.md` 에 0-1/0-2/0-3 결과 기록. blocker 있으면 여기서 종료하고 NO-GO 보고.

---

## 2. Stage 1 — A/B 측정 (Stage 0 통과 시에만, ~1시간)

### 2-1. 준비
- 대상: `Fuller_Complete_Works_Vol03` canonical, **처음 200 candidate** (병렬 벤치와 동일 기준).
- target 블롭 = 0-1의 FROM, draft 블롭 = 0-2의 FROM.
- 다른 부하 없는 상태(F2 정지, 다른 모델 언로드: `ollama ps`가 비어야 함. `ollama stop`은 쓰지 말고 idle-out 대기).

### 2-2. 벤치 스크립트 (CUE 제공 — C1은 그대로 저장·실행)
`/private/tmp/specdec_spike/bench.py` 로 저장:
```python
import json, sys, time, subprocess, socket, urllib.request, os, signal
sys.path.insert(0, "/Users/David/DBMA")
from NAE.pipeline.tsu import parser as P, config as C
from NAE.pipeline.tsu.claim import _CLAIM_PROMPT, _parse_claim_json, _clip_confidence
from NAE.pipeline.tsu import doctrine as D

LS = "/Applications/Ollama.app/Contents/Resources/llama-server"
TARGET = os.environ["TARGET_BLOB"]      # 0-1 FROM
DRAFT  = os.environ["DRAFT_BLOB"]       # 0-2 FROM
N = 200
CANDS = P.build_candidates("Fuller_Complete_Works_Vol03")[:N]

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def start_server(with_draft):
    port = free_port()
    args = [LS, "--model", TARGET, "--port", str(port), "--host", "127.0.0.1",
            "-c", "32768", "-np", "1", "--flash-attn", "auto", "-b", "1024", "-ub", "1024",
            "--no-webui", "--offline", "--no-jinja", "--chat-template", "chatml", "--keep", "4"]
    if with_draft:
        args += ["--model-draft", DRAFT, "--draft-max", "16", "--draft-min", "1"]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # wait for health
    for _ in range(120):
        time.sleep(2)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3); return proc, port
        except Exception: pass
    proc.kill(); raise SystemExit("server did not come up")

def one(port, cand):
    prompt = _CLAIM_PROMPT.format(
        context_before=cand.context_before or "(없음)", sentence=cand.text,
        context_after=cand.context_after or "(없음)",
        candidate_scriptures=", ".join(cand.candidate_scriptures) or "(없음)",
        candidate_citations=", ".join(cand.candidate_citations) or "(없음)",
        doctrine_categories=", ".join(C.DOCTRINE_CATEGORIES))
    body = json.dumps({"prompt": prompt, "temperature": 0.0, "n_predict": 512, "cache_prompt": True}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/completion", data=body,
                                 headers={"Content-Type": "application/json"})
    raw = json.loads(urllib.request.urlopen(req, timeout=300).read())["content"]
    try:
        data = _parse_claim_json(raw)
    except Exception as e:
        return {"error": str(e)}
    if not data.get("is_claim"):
        return {"is_claim": False}
    return {"is_claim": True, "claim": str(data.get("claim") or "").strip() or None,
            "doctrine": D.normalize_doctrine(data.get("doctrine")),
            "scriptures": [s for s in (data.get("scriptures") or []) if s in cand.candidate_scriptures],
            "citations": [c for c in (data.get("citations") or []) if c in cand.candidate_citations],
            "confidence": _clip_confidence(data.get("confidence"))}

def run(with_draft, tag):
    proc, port = start_server(with_draft)
    try:
        t0 = time.monotonic(); out = []
        for i, cand in enumerate(CANDS, 1):
            out.append(one(port, cand))
            if i % 50 == 0: print(f"  [{tag}] {i}/{N}  {time.monotonic()-t0:.0f}s")
        el = time.monotonic() - t0
    finally:
        proc.send_signal(signal.SIGTERM); time.sleep(2); proc.kill()
    errs = sum(1 for r in out if "error" in r)
    claims = sum(1 for r in out if r.get("is_claim"))
    print(f"=== {tag}: {el:.1f}s  claims={claims}  errors={errs}")
    return el, out, errs, claims

a_el, a_out, a_err, a_cl = run(False, "A(no-draft)")
b_el, b_out, b_err, b_cl = run(True,  "B(spec-decode)")
identical = a_out == b_out
speed = a_el / b_el if b_el else 0
print(f"\n=== RESULT ===\nA {a_el:.1f}s  B {b_el:.1f}s  speedup {speed:.2f}x  (gate >=1.5)")
print(f"byte-identical A==B: {identical}   claims A/B {a_cl}/{b_cl}   errors A/B {a_err}/{b_err}")
if not identical:
    diff = [i for i,(x,y) in enumerate(zip(a_out,b_out)) if x!=y]
    print(f"differing indices ({len(diff)}): {diff[:20]}")
    for i in diff[:3]: print("  A", a_out[i]); print("  B", b_out[i])
print("GATE:", "PASS" if (speed>=1.5 and identical and b_err<=a_err) else "FAIL")
```

실행:
```bash
mkdir -p /private/tmp/specdec_spike
export TARGET_BLOB="<0-1 FROM 경로>"
export DRAFT_BLOB="<0-2 FROM 경로>"
~/envs/dbma311/bin/python /private/tmp/specdec_spike/bench.py 2>&1 | tee /private/tmp/specdec_spike/bench.out
```

### 2-3. 보고할 것 (raw, 가공 없이)
- `bench.out` 전문
- `=== RESULT ===` 블록의 speedup, `byte-identical A==B`, `claims A/B`, `errors A/B`, `GATE`
- byte-identical이 False면 `differing indices` 목록과 예시 3건

---

## 3. Stage 2 — 판정 및 산출물

`docs/NAE_FULLER_F2_SPECDEC_SPIKE_RESULT_C1_001.md` 에 기록:
- Stage 0 결과 (arch / draft 모델 / llama-server 지원 여부)
- Stage 1 표: A elapsed / B elapsed / speedup / byte-identical / claims A·B / errors A·B
- **판정: GO / NO-GO** (§0 기준 그대로 적용)
- NO-GO면 사유 (blocker / <1.5x / 결정성 깨짐 중 무엇인지)

CUE가 `bench.out`과 대조 검증한다.

---

## 4. 금지 / STOP

- **금지**: F2 실행 중 착수 / `run_fuller_f2.sh`·`builder.py`·`claim.py`·`runner.py`·production Modelfile 수정 / `ollama stop` / `nae_tsu_v1`·`nae_ref_v1`·`tsu_dataset.jsonl` 접촉 / Vol.03 실제 `tsu.json` 덮어쓰기 (벤치는 llama-server 직접 호출, 파이프라인 미경유·디스크 미기록).
- **STOP·보고**: Stage 0에서 arch 불명/호환 draft 없음/`--model-draft` 미지원 / target·draft 로드 시 VRAM 부족 / bench.py가 서버 기동 실패.

---

## 5. 예상 효과 / 후속

JSON 출력은 예측 가능도가 높아 **1.5–2.5x** 기대. 성공 시 F2 잔여 ~3일 → ~1.5–2일, 출력 불변이라 `builder_version 3.0.0`·Amendment A 무영향. 이후 구현 Task Order에서 "Ollama가 draft를 노출하지 않으므로 F2 러너가 어떻게 spec-decode 서버를 쓸지"(직접 llama-server 관리 vs Ollama 버전 업 대기)를 다룬다.

---

## 6. Cline 릴레이 스니펫 (붙여넣기용)

```
[C1 Task Order — F2 Speculative Decoding 스파이크 · 측정 전용]

목적: llama3.x/qwen 소형 모델을 draft로, my-theology-bot-v2를 target으로 speculative
decoding을 걸었을 때 F2 claim 추출이 ≥1.5x 빨라지면서 출력이 byte-identical인지 측정.
GO면 별도 구현 Task Order로. 이번엔 측정만.

작업 위치: /Users/David/DBMA @ dev/dbma-engine, venv ~/envs/dbma311
전제: F2가 완전히 끝난 뒤 실행. F2 도는 중이면 착수하지 말고 CUE에 보고.

Stage 0 — Feasibility (blocker 먼저):
  1) `ollama show my-theology-bot-v2:latest` 와 `--modelfile | head -5` 실행.
     architecture / parameters / quantization / context / FROM 블롭 경로를 보고.
  2) architecture에 따라 vocab 호환 draft를 pull:
     - llama 계열 → `ollama pull llama3.2:1b`
     - qwen2/2.5 계열 → `ollama pull qwen2.5:0.5b` (없으면 qwen2.5:1.5b)
     - qwen3 계열 → `ollama pull qwen3:1.7b`
     - 불명/그 외 → STOP, CUE 보고
     draft FROM 경로: `ollama show <draft> --modelfile | grep -i "^FROM"`
  3) `"/Applications/Ollama.app/Contents/Resources/llama-server" --help 2>&1 | grep -iE "model-draft|-md |draft-max"`
     → --model-draft 옵션이 없으면 STOP, CUE 보고.

Stage 1 — 측정 (Stage 0 전부 통과 시에만):
  - `ollama ps`가 비어있는지 확인(다른 모델 언로드 대기. ollama stop 쓰지 말 것).
  - CUE가 제공한 벤치 스크립트를 /private/tmp/specdec_spike/bench.py 로 저장
    (docs/NAE_FULLER_F2_SPECDEC_SPIKE_TASK_ORDER_C1_001.md §2-2 전문 그대로).
  - 실행:
      mkdir -p /private/tmp/specdec_spike
      export TARGET_BLOB="<Stage0-1 FROM>"
      export DRAFT_BLOB="<Stage0-2 FROM>"
      ~/envs/dbma311/bin/python /private/tmp/specdec_spike/bench.py 2>&1 | tee /private/tmp/specdec_spike/bench.out

보고 (가공 없이):
  - bench.out 전문
  - === RESULT === 의 speedup / byte-identical A==B / claims A·B / errors A·B / GATE
  - byte-identical False면 differing indices + 예시 3건

산출물: docs/NAE_FULLER_F2_SPECDEC_SPIKE_RESULT_C1_001.md
  (Stage 0 결과 + Stage 1 표 + GO/NO-GO 판정 + NO-GO 사유).
CUE가 bench.out과 대조 검증함.

금지: F2 실행 중 착수 / builder.py·claim.py·runner.py·run_fuller_f2.sh·production
Modelfile 수정 / ollama stop / nae_tsu_v1·nae_ref_v1·tsu_dataset.jsonl 접촉.
STOP·보고: arch 불명 / 호환 draft 없음 / --model-draft 미지원 / VRAM 부족 / 서버 기동 실패.
```
