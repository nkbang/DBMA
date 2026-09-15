# NAE Fuller F2 — Hang Resilience Spec (3 logic gaps)

- 작성: 2026-09-10, baptist-theology-research 세션
- 트리거: F2 실행 중 Ollama 데몬 wedge로 `my-theology-bot-v2` 추론 hang 4회 반복. 매번 volume 전체(수천 candidate·~13h) 재계산. 2026-09-10 Vol.03가 4,400/5,812에서 hang → 복구 재시작 시 candidate 0부터.
- 이 스펙의 3개 항목은 **한 번의 C1 Review 사이클**로 처리 권장 (Gap 1·2는 TSU Pipeline). Gap 1은 이미 `task_f0907969`로 착수됨 — Gap 2를 거기에 합치고, Gap 3(드라이버/워치독)은 별도 파일이라 병행 가능.

---

## Gap 1 — `build_tsu_for_identifier`에 resume 없음 (핵심, 착수됨)

### 현상
`NAE/pipeline/tsu/builder.py`:
```python
start = time.monotonic()
candidates = parser.build_candidates(identifier, canonical_root=..., raw_root=...)   # 항상 index 0..N
if max_candidates is not None:
    candidates = candidates[:max_candidates]
total = len(candidates)
next_id = _load_next_id(tsu_root / "tsu_id_state.json")   # id만 이어감
tsu_records: list[dict[str, Any]] = []                     # ← 빈 리스트로 시작
...
for idx, cand in enumerate(candidates, start=1):           # ← candidate 1부터
```
`checkpoint_every`마다 `tsu.json` + `tsu_report.json`(`candidates_evaluated`, `partial`)을 쓰지만, 재시작 시 그걸 되읽는 경로가 없음.

### 수정 (task_f0907969)
`--resume`: `tsu_report.json`이 `partial: true`면 `candidates_evaluated = N`을 읽어
- `tsu_records = json.load(tsu_root/<id>/"tsu.json")` (N까지의 claim)
- `candidates = candidates[N:]` (또는 enumerate offset N)
- `next_id`는 현행대로 `tsu_id_state.json`에서
로 재개. **불변식**: `--resume`으로 이어붙인 최종 `tsu.json`이 처음부터 돌린 것과 claim·doctrine·id 순서까지 byte-identical (candidate 순서는 `parser.build_candidates`가 결정적).

`scripts/run_fuller_f2.sh`: 현재 partial volume을 candidate 0부터 재실행. `--resume`을 붙이도록 갱신.

---

## Gap 2 — `ollama.generate`에 timeout 없음 → hang이 무한·무음

### 현상
`NAE/pipeline/tsu/claim.py:121`:
```python
try:
    result = ollama.generate(model=model, prompt=prompt, options={"temperature": config.CLAIM_TEMPERATURE})
    data = _parse_claim_json(result["response"])
except Exception as e:  # noqa: BLE001
    logger.error("[extract_claim] 실패 (model=%s): %s", model, e)
    return ClaimResult(model=model, error=str(e))
```
`ollama` 모듈 레벨 `generate()`는 기본 `Client`를 쓰며 HTTP read timeout이 사실상 무한. Ollama 데몬이 wedge되면 이 호출이 영원히 블록 → runner 0% CPU, 소켓 ESTABLISHED, **에러·로그 없음**. 2026-09-10 Vol.03는 이 상태로 146분 정지.

### 수정
per-request timeout을 준다. `ollama` 0.6.x에서:
```python
from ollama import Client
_CLIENT = Client(timeout=config.CLAIM_HTTP_TIMEOUT_S)   # 모듈 레벨, 재사용
...
result = _CLIENT.generate(model=model, prompt=prompt, options={"temperature": config.CLAIM_TEMPERATURE})
```
- `config.CLAIM_HTTP_TIMEOUT_S` 신설 (예: `180` — 정상 추론 ~10s의 넉넉한 상한. 재추출/repair 스크립트도 동일 값 참조 가능).
- timeout 시 `httpx.ReadTimeout` 등 예외 → 기존 `except Exception`이 잡아 `ClaimResult(model=model, error="timeout ...")` 반환.
- builder는 `result.error` → `errors += 1` 후 다음 candidate로. **hang이 아니라 error 카운트로 전환.**
- Ollama가 진짜 wedge면 연속 candidate가 전부 timeout → `errors` 급증 → `run_fuller_f2.sh`의 `gate_ok`가 `llm_errors / candidates_total >= 2%`에서 실패 → runner 비정상 종료 → 드라이버 `STOP`. **무음 146분 hang → 수 분 내 가시적 실패.**

### 부가
- `ollama.generate` 대신 `Client(timeout=...)`로 바꾸는 것 외 추출 로직(prompt·model·doctrine 분류) 불변.
- `builder_version` 영향: **불변 (`3.0.0` 유지)** — 출력 결정성·스키마 불변, timeout은 실패 처리 경로만 추가. Amendment A F2 게이트(`builder_version == "3.0.0"`) 무영향.
- 회귀: `tests/test_nae_tsu_builder.py` / `test_tsu_pipeline_wiring.py`의 `extract_claim` monkeypatch가 `Client` 사용 여부와 무관하게 통과하는지 확인.

---

## Gap 3 — hang 감지·복구 자동화 없음 (드라이버/워치독)

### 현상
`scripts/run_fuller_f2.sh`가 `runner.py --identifier`를 **동기 실행**하고 `wait`. runner가 hang하면 드라이버도 무한 대기. stall 감지·타임아웃·auto-restart 없음. → 밤새 방치.

### 수정 — 신규 `scripts/nae_f2_watchdog.sh` (detached, 드라이버와 병행)

폴링 루프 (`POLL_SECS` 기본 120):
1. `run_fuller_f2.sh` 프로세스 없으면 idle (F2 done/stopped).
2. runner 프로세스 없으면 "볼륨 간 전환" — skip.
3. 활성 volume의 `tsu_report.json`(`partial: true` 중 최신) mtime age 측정.
4. `age > STALL_SECS`(기본 1500) **AND** runner etime `> STALL_SECS` (첫 checkpoint 기회는 준다) → 의심.
5. 의심 시 소형 프롬프트로 Ollama probe (`timeout PROBE_TIMEOUT curl /api/generate num_predict=2`):
   - **200 응답** → runner가 느린 것뿐, 무조치 (재시작 오탐 방지).
   - **timeout/실패 2회 연속** → hang 확정.
6. hang 확정 시 (`AUTO_RECOVER=1` 기본):
   - `pkill` runner + 드라이버 (SIGTERM → 3s → SIGKILL)
   - `launchctl kickstart -k gui/$UID/com.ollama.ollama`
   - probe로 health 확인 (최대 ~2min)
   - health OK → `nohup bash scripts/run_fuller_f2.sh > f2_run.log 2>&1 &` 재기동
     - **Gap 1(`--resume`) 반영 후엔 마지막 checkpoint부터 재개** → 손실 ≈ 1 checkpoint(100 candidate/~15min)
     - 반영 전엔 candidate 0부터 (현행 수동 복구와 동일 비용)
   - health 실패 → 로그 + `AUTO_RECOVER=0`처럼 ALERT만, 수동 개입 요청
   - `AUTO_RECOVER=0` 모드: 감지·경보만, 복구는 사람이.

실행:
```bash
nohup bash scripts/nae_f2_watchdog.sh > f2_watchdog.log 2>&1 &
```

### 거버넌스 주의
- `run_fuller_f2.sh` / `nae_f2_watchdog.sh`는 TSU Pipeline이 아닌 **드라이버 스크립트** — C1 Review 불필요, 사소한 보강.
- 단 "무인 자동 복구 루프"는 [메모리: CUE↔C1 Unattended Loop CLOSED]와 인접 → **auto-recover 기본 활성화는 HQ 승인** 후. 기본은 `AUTO_RECOVER=0`(감지·경보)로 출시하고, HQ가 승인하면 `AUTO_RECOVER=1`.

---

## 손실 비교

| 시나리오 | hang 발견까지 | 복구 후 재계산 |
|---|---|---|
| **현재** | 사람이 대시보드 볼 때까지 (이번엔 146분) | volume 전체 (Vol.03 = 4,400 candidate ≈ 13h) |
| Gap 2만 | 수 분 (errors 급증 → gate 실패 → 드라이버 STOP) | volume 전체 (수동 재시작) |
| Gap 3만 | ~STALL_SECS (25min) + probe | volume 전체 (auto, 사람 개입 불필요) |
| **Gap 1+2+3** | 수 분 | **~1 checkpoint (100 candidate/~15min)**, auto-recover |

---

## 권장 순서

1. **Gap 1 (`--resume`)** — `task_f0907969` 진행 중. builder + runner + `run_fuller_f2.sh` + 회귀 테스트 + C1 Review.
2. **Gap 2 (timeout)** — Gap 1과 **같은 PR/커밋 세트**에 합쳐 한 번의 C1 Review. `claim.py` + `config.py`.
3. **Gap 3 (watchdog)** — 별도, C1 Review 불필요. `AUTO_RECOVER=0`으로 먼저 배포, HQ 승인 후 `=1`.
4. 3개 반영 후 F2 재개 시 watchdog 동반 기동.
