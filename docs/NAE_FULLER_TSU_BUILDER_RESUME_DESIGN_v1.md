# NAE TSU Builder — Checkpoint Resume 설계 v1

**Project:** NAE-TSU-BUILDER-RESUME-001 (선행: NAE-TSU-BUILDER-EXECUTION-RECOVERY-001)
**작성:** CUE · 2026-09-10
**대상:** `NAE/pipeline/tsu/builder.py::build_tsu_for_identifier`
**성격:** TSU Pipeline 변경 → CUE Operating Policy상 **C1 Independent Review 트리거**
(구현 → 회귀 → C1 독립 검토 → HQ 승인 순서. 본 문서는 그 1단계 산출물.)
**Git:** 구현·회귀 PASS 후 Conventional Commit + push (`origin` 작업 브랜치). Force/history rewrite 없음.

---

## 0. 결론 먼저

| 항목 | 판단 |
|---|---|
| 신규 파라미터 | `build_tsu_for_identifier(..., resume: bool = False)` — runner `--resume`로 노출 |
| Resume 앵커 | 디스크의 `(tsu.json, tsu_report.json)` checkpoint 쌍. `tsu_report.json.candidates_evaluated = N` → candidate `N`부터 재개, 기존 `tsu.json` 레코드를 메모리로 로드해 이어붙임 |
| 완료본(`partial: false`) | 아무 것도 안 하고 **skip** — 기존 `run_fuller_f2.sh` gate와 동일 의미 |
| 불변식(요구사항 #2) | **`tsu.json` byte-identical** (claim 내용·doctrine·id·순서 동일). `tsu_report.json`은 안정 필드 동일, `generated_at`/`elapsed_seconds`는 실행 종속이라 제외 |
| `builder_version` | **`3.0.0` 유지.** 추출 로직·레코드 shape 무변경. F2 parallel-speedup 선례(`NAE_FULLER_F2_PARALLEL_SPEEDUP_RESULT_001.md` §4)와 동일 근거. **ADR-030 Amendment A 갱신 불필요** (F2 gate `builder_version == "3.0.0"` 그대로 통과) |
| C1 Review 대상 | 본 설계 + `builder.py`/`runner.py` diff + 회귀 테스트 (`test_nae_tsu_builder.py` resume 3~4건) |

---

## 1. 배경

2026-09-10 F2(`scripts/run_fuller_f2.sh`, Fuller Vol.02–08 TSU 생성)를 detached
드라이버로 실행 중 `my-theology-bot-v2:latest` 추론이 Ollama 데몬 wedge로 hang하는
사고가 4회 반복. 매 복구 = hung runner kill + `launchctl kickstart` + F2 재시작.

`build_tsu_for_identifier`에는 **resume/skip 경로가 없다.** 재시작 시 volume 전체를
candidate 0부터 재계산 (Vol.03 = 5,812 candidate, 진행분 4,400 + ~13h GPU 재계산
손실). 그런데 `checkpoint_every`(기본 100)마다 `_write_tsu_output`가 `tsu.json` +
`tsu_report.json`(`partial: true`)을 이미 즉시 기록한다 — **마지막 checkpoint 상태는
디스크에 있고, 그걸 읽어 이어가는 경로만 없다.**

### 1.1 "resume" 용어 구분

이전 `NAE_TSU_PIPELINE_RESUME_PREFLIGHT_REPORT_001.md` / `..._READINESS_REVIEW_001.md`의
"resume"은 **pipeline activation gating**(Crosswalk Gate 배선)이다. 본 문서의
"resume"은 **단일 identifier 실행의 checkpoint 재개**로 서로 다른 개념이다.

---

## 2. 현재 구조 (변경 전)

```
build_tsu_for_identifier(identifier, *, model, max_candidates, ...roots,
                         checkpoint_every=100, progress_log=print)
  candidates = parser.build_candidates(identifier, ...)   # 결정론적 순서
  candidates = candidates[:max_candidates]                # 옵션
  total      = len(candidates)
  next_id    = _load_next_id(tsu_root/"tsu_id_state.json") # 전역 ID 카운터
  tsu_records=[]; doctrine_counts={}; errors=0
  for idx, cand in enumerate(candidates, start=1):
      result = claim_mod.extract_claim(cand.text, ...)     # 순차 LLM 1건
      if result.error:      errors += 1
      elif result.is_claim: append record(id=_format_tsu_id(next_id)); next_id += 1
      if idx % checkpoint_every == 0 or idx == total:
          _save_next_id(next_id, ...)
          _write_tsu_output(out_dir, tsu_records, _build_report(idx, partial=(idx != total)))
  # total==0 처리 + 최종 partial=false 기록
```

### 2.1 결정론 근거 (불변식의 전제)

- **`parser.build_candidates`**: `canonical.json`의 `paragraphs`를 순서대로, 각
  paragraph의 `sentences`를 순서대로 순회하고 `type == "prose"` + `len(text) >=
  MIN_CLAIM_SENTENCE_CHARS`로만 필터. 같은 `canonical.json`이면 **항상 같은 리스트**를
  같은 순서로 반환. (`NAE/pipeline/tsu/parser.py:47-95`)
- **`claim.extract_claim`**: `ollama.generate(..., temperature=0.0)` 순차 단일 요청.
  2026-09-08 F2 parallel-speedup 실측(`NAE_FULLER_F2_PARALLEL_SPEEDUP_RESULT_001.md`
  §2)에서 **동시성(`-np 2`)일 때만** llama.cpp 배치 추론이 비결정적(134건 중 1건
  claim/confidence 불일치)임이 확인됐고, `--max-workers 1` 순차 실행(run A)은
  결정적 기준선으로 취급됐다. Resume는 **순차(`-np 1`) 의미를 그대로 유지**하므로
  from-scratch 실행과 같은 결정성을 물려받는다.

즉 "candidate N부터 이어 돌리면 처음부터 돌린 것과 같은 claim이 나온다"는
**이미 from-scratch F2 재현성이 의존하는 것과 동일한 가정**이다. Resume가 새 가정을
도입하지 않는다.

---

## 3. 설계

### 3.1 시그니처

```python
def build_tsu_for_identifier(identifier, *, model=config.DEFAULT_CLAIM_MODEL,
                             max_candidates=None,
                             canonical_root=..., raw_root=..., tsu_root=...,
                             checkpoint_every=100, progress_log=print,
                             resume: bool = False) -> dict[str, Any]:
```

`resume` 기본값 `False` → 기존 호출부 전부 무영향(byte-identical). `build_tsu_for_all`,
`runner._run_gate_wired`에도 `resume` 파라미터를 추가해 pass-through(대칭성).
`runner.py`에 `--resume` (store_true) 노출.

### 3.2 Resume 상태 로드 — `_load_resume_state(out_dir) -> dict | None`

`out_dir/tsu_report.json`을 읽는다.

| 디스크 상태 | 동작 |
|---|---|
| `tsu_report.json` 없음 | `None` 반환 → 호출부가 fresh 실행으로 진행(`resume_from=0`), 로그 1줄 |
| `partial == false` | **skip.** 디스크의 `tsu.json` 레코드 + `tsu_report.json`을 그대로 로드해 `{"records": ..., "report": ..., "skipped": True}` 반환. `extract_claim` 0회 호출 |
| `partial == true` | resume 진행 (§3.3) |
| JSON 파싱 실패 / OSError | `None` 반환(fresh) + WARN 로그 — 손상된 checkpoint로 이어가지 않음 |

### 3.3 Partial 재개 절차

1. `report_evaluated = int(report["candidates_evaluated"])` (= N)
2. `tsu_records = json.load(out_dir/"tsu.json")` (없으면 `[]`)
3. `errors = int(report["llm_errors"])`
4. `doctrine_counts` = `tsu_records`의 non-empty `doctrine` 값 재집계
5. **candidate 정합성 + torn-write 보정** (§3.4)
6. `next_id` = §3.5
7. `resume_elapsed_base = float(report.get("elapsed_seconds", 0.0))` — `_build_report`의
   `elapsed_seconds`가 누적값이 되도록(운영 가독성). 불변식 대상 아님.
8. 루프: `for idx, cand in enumerate(candidates[resume_from:], start=resume_from + 1)`
   — `idx`가 절대 candidate 위치를 유지 → checkpoint 조건(`idx % checkpoint_every`,
   `idx == total`)과 report `candidates_evaluated=idx`, ETA 계산 전부 그대로 성립.
9. `resume_from >= total` (이미 전량 평가됐는데 `partial:true`인 비정상) → 루프
   생략하고 `partial=false`로 최종 기록만 수행(방어).

`total`, `candidates_total`은 **전체 candidate 수**를 유지(슬라이스 전 길이).

### 3.4 Candidate 정합성 + torn-write 보정 (안전 장치)

`_write_tsu_output`는 `tsu.json` → `tsu_report.json` 순으로 쓴다(§3.6). 따라서
어떤 중단 시점에도 **`tsu_report.json`의 진행도 ≤ `tsu.json`의 진행도**.

현재 candidate 리스트로 위치 맵을 만든다:

```python
pos = {(c.page, c.paragraph_index, c.sentence_index): i
       for i, c in enumerate(candidates, start=1)}
```

- 로드한 각 record의 키 `(record["page"], record["paragraph"], record["sentence"])`가
  `pos`에 **모두 존재해야 한다.**
  - 하나라도 없으면 → `canonical.json`이 partial 실행 이후 바뀌어 candidate 순서가
    달라진 것. 불변식을 보장할 수 없으므로 **`RuntimeError`로 중단**
    (`"resume aborted: N records do not map to current candidates — canonical.json changed?"`).
    조용히 이어가면 id/내용이 어긋난 `tsu.json`이 생긴다.
- `max_covered = max(pos[key] for record in tsu_records)` (records 비면 0)
- `resume_from = max(report_evaluated, max_covered)`
  - 정상 checkpoint: `report_evaluated == max_covered에 대응하는 위치 이상` → 보통
    `resume_from == report_evaluated`.
  - torn write(`tsu.json`은 새 checkpoint까지 썼는데 `tsu_report.json`을 못 씀):
    `max_covered > report_evaluated` → `resume_from`을 올려 이미 만든 레코드를
    **재평가하지 않고 그대로 채택**. 결과 byte-identical 유지, 중복 없음.

### 3.5 `next_id` 결정 — `_resume_next_id(tsu_records, fallback, identifier, progress_log)`

- `tsu_records` 비어 있음 → `fallback = _load_next_id(tsu_root/"tsu_id_state.json")`.
- 비어 있지 않음 → `derived = int(tsu_records[-1]["id"].split("-")[1]) + 1`.
  `tsu.json`은 `_write_tsu_output`가 report와 한 쌍으로 기록하는 실제 출력이므로,
  **id 연속성의 권위 기준은 `tsu.json`의 마지막 레코드**다. `tsu_id_state.json`은
  전역 파일이고 checkpoint 중간(`_save_next_id` 직후, `_write_tsu_output` 전) 중단 시
  `tsu.json`보다 앞설 수 있어 **보조(advisory)**로만 사용.
- `derived != fallback` → WARN 로그 후 `derived` 채택.
- **전제(문서화):** F2는 volume을 **순차 처리**하고 partial volume은 다음 volume
  시작 전에 재개된다(`run_fuller_f2.sh` gate). 따라서 한 identifier의 재개 도중
  다른 identifier가 전역 id를 소비하는 상황은 없음 → `tsu.json` 기준 파생이 안전.

### 3.6 원자적 기록 — `_write_tsu_output` 강화

현행은 `open(...,"w")` 직접 쓰기 → 중단 시 0-byte/부분 파일 가능(RECOVERY_REPORT_001
Phase 1의 "출력 파일 0바이트" 관측). 변경:

```python
def _atomic_write_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)          # 같은 dir 내 rename → 원자적

def _write_tsu_output(out_dir, tsu_records, report):
    out_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(out_dir / "tsu.json", tsu_records)      # 먼저
    _atomic_write_json(out_dir / "tsu_report.json", report)    # 나중
```

각 파일은 개별적으로 완전. 쌍 사이 창(`tsu.json` 갱신 완료, `tsu_report.json`
미갱신)은 §3.4가 흡수. **직렬화 형식/내용 불변** → 기존 완료본과 byte-identical.

### 3.7 변경 없는 것

- `claim.py`(추출 프롬프트·모델·파싱), `doctrine.py` 분류기 — **무접촉**(제약 명시).
- 레코드 필드 집합, `_format_tsu_id`, `TSU_SCHEMA_VERSION`, `BUILDER_VERSION`.
- `resume=False` 경로의 모든 동작(회귀로 고정).
- `checkpoint_every` 의미, 진행 로그 포맷.

---

## 4. 불변식 (요구사항 #2) 과 검증 논리

**주장:** 같은 `canonical.json` + 같은 `model` + 결정적 순차 `extract_claim`에 대해,
candidate `k`에서 중단 후 `--resume`으로 완료한 `tsu.json` ≡ 처음부터 완료한 `tsu.json`
(바이트 단위).

**근거:**
1. `candidates`는 `k`와 무관하게 동일 리스트·동일 순서(§2.1).
2. Resume는 `candidates[resume_from:]`만 순서대로 재개하고 `resume_from` 이전 레코드는
   디스크에서 그대로 로드 → 앞부분 identical.
3. `resume_from` 이후 각 candidate의 `extract_claim` 입력은 from-scratch와 동일
   (`cand.text`/context/scriptures/citations는 parser 결정론). 순차 `-np 1`이므로
   출력도 동일(§2.1).
4. id는 `resume_from` 이전 레코드의 마지막 id에서 연속(§3.5). from-scratch도 같은
   지점에서 같은 값 → 동일.
5. `doctrine_counts`/`errors`는 report 필드일 뿐 `tsu.json` 레코드에 안 들어감.
   레코드의 `doctrine`은 `extract_claim` 결과 그대로 → 3에 의해 동일.

**degradation(정직한 한계):** 3의 순차 결정성이 깨지면(백엔드가 동일 순차 입력에
다른 토큰 반환), 불변식은 **구조적 불변식**으로 약화 — id·건수·순서·doctrine 라벨은
동일, 재평가된 candidate의 `claim` 문자열만 달라질 수 있음. **데이터 손실·중복은
어떤 경우에도 없음**(§3.4 보정). 이는 resume 고유 문제가 아니라 from-scratch 재실행도
겪는 backend 특성이다.

---

## 5. 회귀 계획 (요구사항 #4)

`tests/test_nae_tsu_builder.py`에 추가. `extract_claim`은 기존 테스트처럼
`patch(...)`로 결정적 mock → 불변식 검증이 총체적으로 성립.

| 테스트 | 시나리오 | 단언 |
|---|---|---|
| `test_build_tsu_resume_byte_identical` | K=6 sentence canonical. (a) fresh 완주 → `tsu.json` bytes 저장. (b) 새 tsu_root: mock `side_effect`가 3번째 호출 후 `RuntimeError` → `checkpoint_every=2`로 candidate 2까지 checkpoint 후 crash catch. (c) 같은 tsu_root에 `resume=True` + 정상 mock. | (c)의 `tsu.json` bytes == (a) bytes. report 안정 필드(claims_extracted/candidates_evaluated/candidates_total/llm_errors/doctrine_breakdown/partial/builder_version/model) 동일 |
| `test_build_tsu_resume_noop_when_complete` | fresh 완주 후 `resume=True` 재호출 | 반환 `skipped is True`, `extract_claim` mock `call_count`가 1차 실행분에서 증가 안 함, `tsu.json` 내용 불변 |
| `test_build_tsu_resume_without_prior_report` | 깨끗한 tsu_root에 `resume=True` | crash 없이 fresh와 동일 결과(`records` 길이·id) |
| `test_build_tsu_resume_aborts_on_canonical_drift` | candidate 2까지 partial 후 `canonical.json` 첫 문단에 문장 추가(위치 shift) → `resume=True` | `RuntimeError` 발생(정합성 실패), `tsu.json` 미변형 |

기존 4개 테스트(`test_build_tsu_for_identifier_writes_records_and_report`,
`test_build_tsu_id_counter_persists_across_calls`, `..._skips_non_claim_sentences`,
`..._counts_llm_errors_without_crashing`)는 `resume=False` 기본이므로 무영향 — 회귀
게이트로 사용.

인접 스위트: `tests/test_tsu_worker.py`, `tests/test_nae_tsu_runner*.py`(있으면),
`NAE.pipeline.tsu` import 경로. `builder_version` 불변이므로 embedding cache hash·
F2 gate 스크립트 회귀 불필요.

---

## 6. `builder_version` 판단 (요구사항 #5)

**`3.0.0` 유지가 맞다. 승격 불필요.**

| 기준 | 판단 |
|---|---|
| 추출 로직(claim/doctrine 판정) | 무변경 (`claim.py`/`doctrine.py` 무접촉) |
| TSU 레코드 shape(필드 add/remove/rename) | 무변경 → `TSU_SCHEMA_VERSION`도 불변 |
| 동일 입력 → 동일 출력(`tsu.json`) | §4 불변식으로 유지 |
| 선례 | `NAE_FULLER_F2_PARALLEL_SPEEDUP_RESULT_001.md` §4: "`builder_version` `3.0.0` 유지 — 추출 로직·출력 불변, Amendment A F2 게이트 무영향." 당시 max_workers 배선 변경도 버전 안 올림 |

`config.BUILDER_VERSION`은 "출력 semantics"를 식별한다. Resume는 *언제 멈췄다
이어가는지*만 바꾸고 *무엇을 만드는지*는 안 바꾼다.

### 6.1 ADR-030 Amendment A 영향

`scripts/run_fuller_f2.sh::gate_ok`는 `builder_version != "3.0.0"`을 STOP 조건으로
검사한다. `3.0.0` 유지 → **gate 그대로 통과, Amendment A 문서 갱신 불필요.**

Amendment A §3 F2 게이트("권별 `tsu_report.json` 정상 + doctrine 분포 이상치 없음"),
§8 승격 4조건 — resume는 이 중 어느 것도 건드리지 않는다(F2 산출물의 *내용*이
동일하므로). Amendment A는 여전히 PROPOSED이며 본 작업으로 상태 변화 없음.

---

## 7. `runner.py` / `run_fuller_f2.sh` 변경

### 7.1 `runner.py`

- `--resume` (`action="store_true"`): "Resume `--identifier`'s partial run from its
  last checkpoint (`tsu_report.json.candidates_evaluated`). No-op if already complete."
- `args.identifier` 분기 → `build_tsu_for_identifier(..., resume=args.resume)`.
- `_run_gate_wired(model, max_candidates, resume)` + 기본 분기에서 pass-through.
- `--legacy-scan` → `build_tsu_for_all(..., resume=args.resume)`.

### 7.2 `scripts/run_fuller_f2.sh`

헤더 주석의 "RESTARTS from candidate 0 on every invocation (no resume)" 갱신.
volume 루프:

```bash
RESUME_FLAG=""
if [ -f "$RPT" ]; then
  if "$PY" -c "import json,sys; sys.exit(0 if json.load(open('$RPT')).get('partial') is False else 1)"; then
    log "Vol${v}: already complete (partial=false) — skip"; continue
  fi
  RESUME_FLAG="--resume"
  log "Vol${v}: partial report found — resuming from last checkpoint"
fi
"$PY" -m NAE.pipeline.tsu.runner --identifier "$ID" --model "$MODEL" $RESUME_FLAG
```

기존 "partial이면 overwrite(재계산)" 동작 → "partial이면 `--resume`(이어서)". 완료본
skip 동작은 그대로. gate·commit·push 로직 무변경.

---

## 8. 제약 준수 / 안전

- **TSU Pipeline 변경** → C1 Independent Review 요청(본 §9). 구현 → 회귀 → C1 → HQ.
- `claim.py`·doctrine 분류기 **무접촉**.
- 작업 위치 `/Users/David/DBMA` @ `dev/dbma-engine`, venv `~/envs/dbma311`.
- **현재 F2 실행 중**(`pgrep -f run_fuller_f2` = live, Vol.02 완료·Vol.03+ 진행).
  `builder.py`/`runner.py` 수정은 이미 import된 실행 프로세스에 무영향(Python
  재로딩 없음). `run_fuller_f2.sh` 수정은 **이 worktree의 파일**이라 메인 체크아웃의
  실행 중 스크립트와 별개. **새 실행 시작은 F2 완료 후.**
- Commit/Push는 회귀 PASS 후 자동(정책). Force/history rewrite 없음.

---

## 8.5 Gap 2 동반 변경 — `claim.py` HTTP timeout (같은 커밋 세트·같은 C1 Review)

**근거:** resume는 "재시작 손실"을 줄이지만 "hang이 무음·무한"인 문제(2026-09-10
Vol.03가 4,400/5,812에서 Ollama wedge로 ~146분 무음 정지)는 안 푼다. baptist-theology-
research 세션의 `docs/NAE_FULLER_F2_HANG_RESILIENCE_SPEC_v1.md` Gap 2. HQ 승인으로
본 작업 제약("claim.py 무접촉")을 이 건에 한해 해제(2026-09-10).

**문제:** `NAE/pipeline/tsu/claim.py`의 모듈 레벨 `ollama.generate()`는 HTTP read
timeout이 사실상 무한. Ollama 데몬 wedge 시 이 호출이 영원히 블록 → runner 0% CPU,
소켓 ESTABLISHED, 에러·로그 전무.

**변경:**
- `config.CLAIM_HTTP_TIMEOUT_S = 180` 신설 (정상 추론 ~10s의 넉넉한 상한).
- `claim.py`: `import ollama` → `from ollama import Client`; 모듈 레벨
  `_CLIENT = Client(timeout=config.CLAIM_HTTP_TIMEOUT_S)` (배치 전체에서 재사용);
  `ollama.generate(...)` → `_CLIENT.generate(...)`.
- timeout 시 예외 → **기존 `except Exception` (claim.py)이 그대로** 잡아
  `ClaimResult(model=model, error=str(e))` 반환. builder는 `errors += 1` 후 다음
  candidate. **추출 프롬프트·모델·doctrine 분류·출력 결정성 전부 불변** — 실패
  처리 경로만 bounded.
- 파급: Ollama가 진짜 wedge면 연속 candidate가 전부 timeout → `errors` 급증 →
  `run_fuller_f2.sh::gate_ok`의 `llm_errors/candidates_total >= 2%` 실패 → runner
  비정상 종료 → 드라이버 STOP. **무음 146분 hang → 수 분 내 가시적 실패.**
- `scripts/nae_fuller_cjk_reextract.py`(직접 `ollama.generate`, F2 완료 직후
  무인 실행)도 같은 `_CLIENT = Client(timeout=tsu_config.CLAIM_HTTP_TIMEOUT_S)`
  패턴 적용 — 동일 취약점, 스크립트라 C1 불필요하나 같은 커밋에 포함.

**`builder_version` 영향:** 없음. `3.0.0` 유지 (출력 결정성·스키마 불변, timeout은
실패 처리만 추가). Amendment A F2 게이트 무영향 — Gap 1과 동일 논리(§6).

**회귀:** `tests/test_nae_tsu_claim.py`의 `extract_claim` monkeypatch 대상을
`ollama.generate` → `_CLIENT.generate`로 갱신(7건). 신규 2건: timeout 예외 fail-soft,
`_CLIENT`가 `CLAIM_HTTP_TIMEOUT_S`를 실제로 물고 있는지(config 배선 lock).

**Gap 3 (본 작업 범위 밖):** `scripts/nae_f2_watchdog.sh` — checkpoint mtime +
Ollama probe로 hang 감지 → kill + `launchctl kickstart` + 드라이버 재기동. resume
반영 후 재기동이 `--resume`을 타서 손실 ≈ 1 checkpoint. baptist 세션에서 별도 처리.

---

## 9. C1 Independent Review 요청

**검토 범위 (Gap 1 — resume):**
1. §3.4 candidate 정합성 로직 — `(page, paragraph, sentence)` 3-튜플 키의 유일성
   가정이 실제 `canonical.json`에서 성립하는가(Fuller Vol.01–03 실측 dup=0 확인,
   Vol.04–08 재확인 요청).
2. §3.5 `next_id` 파생 규칙 — `tsu.json` 마지막 id 기준 vs `tsu_id_state.json` 기준
   충돌 시 선택이 F2 순차 워크플로에서 안전한지.
3. §3.6 원자적 기록 — `os.replace` 순서(`tsu.json` → report)와 §3.4 보정이 torn
   write를 실제로 닫는지.
4. §4 불변식 논증의 허점, degradation 서술의 정확성.
5. 회귀 4건이 불변식·skip·drift-abort를 충분히 덮는지.
6. `builder_version` `3.0.0` 유지 판단(§6) 동의 여부.

**검토 범위 (Gap 2 — §8.5 claim.py timeout):**
7. `Client(timeout=180)` 전환이 추출 결정성/출력에 영향 없음을 확인 (실패 경로만).
8. timeout 예외가 기존 `except Exception` fail-soft로 흡수되고, 연속 timeout →
   `run_fuller_f2.sh` `llm_errors ≥ 2%` 게이트 → 드라이버 STOP 흐름이 맞는지.
9. `CLAIM_HTTP_TIMEOUT_S = 180` 값 적정성.
10. `builder_version` `3.0.0` 유지 동의(Gap 2도).

**비대상:** doctrine 분류기(무접촉), F2 실행 자체, Amendment A 승격, Gap 3 watchdog.

---

## 10. 산출물 체크리스트

- [x] 설계 문서(본 문서, Gap 1 + Gap 2 §8.5)
- [x] **Gap 1** `builder.py` (`resume` param + `_load_resume_state` + `_reconcile_resume_point` + `_resume_next_id` + `_atomic_write_json`)
- [x] **Gap 1** `runner.py` `--resume` 노출 + pass-through (`--identifier` / `--legacy-scan` / gate-wired 전부)
- [x] **Gap 1** `scripts/run_fuller_f2.sh` resume 루프 (partial → `--resume`, 완료본 → skip 유지)
- [x] **Gap 1** `tests/test_nae_tsu_builder.py` resume 4건 (byte-identical / skip-noop / no-prior / drift-abort)
- [x] **Gap 2** `config.CLAIM_HTTP_TIMEOUT_S = 180` + `claim.py` `Client(timeout=...)` + `scripts/nae_fuller_cjk_reextract.py` 동일 패턴
- [x] **Gap 2** `tests/test_nae_tsu_claim.py` patch 대상 갱신(7) + 신규 2건 (timeout fail-soft / config 배선 lock)
- [x] 회귀: 대상 스위트 61 passed, NAE 서브셋(`-k "nae or tsu or crosswalk or corpus or fuller or claim or sermon"`) 1397 passed / 2 skipped
- [x] Build Report → `docs/NAE_FULLER_TSU_BUILDER_RESUME_BUILD_REPORT_001.md`
- [x] C1 Review 요청서 → `docs/NAE_FULLER_TSU_BUILDER_RESUME_C1_REVIEW_REQUEST_001.md` (질문 12개 + relay)
- [ ] C1 Independent Review 수행 → `docs/NAE_FULLER_TSU_BUILDER_RESUME_C1_REVIEW_RESULT_001.md`
- [ ] HQ 승인
