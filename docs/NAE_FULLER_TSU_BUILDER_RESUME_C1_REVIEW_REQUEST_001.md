# C1 Review 요청 — NAE-TSU-BUILDER-RESUME-001 (Gap 1 resume + Gap 2 claim.py timeout)

- 요청자: CUE
- 일자: 2026-09-10
- 유형: **C1 Independent Review** (독립 검토 — 구현 아님, 문서 검토 + 코드 read-only)
- 트리거: CLAUDE.md CUE Operating Policy "C1 Review 요청 시점: **TSU Pipeline 진입/변경**"
- 관련: `docs/NAE_FULLER_F2_HANG_RESILIENCE_SPEC_v1.md` (baptist-theology-research 세션, Gap 1/2/3 우산 스펙)

---

## 1. 배경

2026-09-10 F2(`scripts/run_fuller_f2.sh`, Fuller Vol.02–08 TSU 생성) detached 실행 중
`my-theology-bot-v2:latest` 추론이 Ollama 데몬 wedge로 hang하는 사고가 4회 반복.
- **Gap 1**: `build_tsu_for_identifier`에 resume/skip 경로가 없어 재시작 시 volume 전체를
  candidate 0부터 재계산 (Vol.03 = 5,812 candidate, 진행분 ~4,400 + ~13h GPU 손실).
- **Gap 2**: `claim.py`의 `ollama.generate()`가 HTTP read timeout 무한 → wedge 시 무음·무한
  hang (Vol.03가 4,400/5,812에서 ~146분 정지, 에러·로그 전무).

HQ가 본 작업의 "claim.py 무접촉" 제약을 **Gap 2에 한해 해제** (2026-09-10). Gap 1+2는
동일 커밋 세트·동일 C1 Review로 진행.

---

## 2. 검토 대상 산출물

**브랜치:** `claude/tsu-builder-resume-abf035` (HEAD `fbcdeef`, base `origin/dev/dbma-engine` @ `daca402`)

| # | 커밋 | 대상 |
|---|---|---|
| A | — | `docs/NAE_FULLER_TSU_BUILDER_RESUME_DESIGN_v1.md` (설계 + 불변식 논증 + 회귀 계획 + builder_version 판단; §8.5 = Gap 2) |
| B | `ed4f8cf` | **Gap 1** `NAE/pipeline/tsu/builder.py` (`resume` param, `_load_resume_state`, `_reconcile_resume_point`, `_resume_next_id`, `_atomic_write_json`, `_write_tsu_output` 순서 변경, 루프 `candidates[resume_from:]`, `total==0` 블록 제거) |
| B | `ed4f8cf` | **Gap 1** `NAE/pipeline/tsu/runner.py` (`--resume` + 전 경로 pass-through), `NAE/pipeline/tsu/builder.py::build_tsu_for_all` (`resume` pass-through) |
| B | `ed4f8cf` | **Gap 1** `scripts/run_fuller_f2.sh` (partial → `--resume`, 완료본 → skip 유지, 헤더 주석) |
| B | `ed4f8cf` | **Gap 1** `tests/test_nae_tsu_builder.py` +4, `tests/test_tsu_pipeline_wiring.py` stub 1줄 |
| C | `fbcdeef` | **Gap 2** `NAE/pipeline/tsu/config.py` (`CLAIM_HTTP_TIMEOUT_S = 180`) |
| C | `fbcdeef` | **Gap 2** `NAE/pipeline/tsu/claim.py` (`from ollama import Client`, 모듈 레벨 `_CLIENT = Client(timeout=…)`, `ollama.generate()` → `_CLIENT.generate()`; `except Exception` fail-soft 불변) |
| C | `fbcdeef` | **Gap 2** `scripts/nae_fuller_cjk_reextract.py` (동일 `Client(timeout=…)` 패턴) |
| C | `fbcdeef` | **Gap 2** `tests/test_nae_tsu_claim.py` (patch 대상 7건 갱신 + 신규 2건) |
| D | — | `docs/NAE_FULLER_TSU_BUILDER_RESUME_BUILD_REPORT_001.md` (Build Report) |

**무접촉 (확인 대상):** `NAE/pipeline/tsu/doctrine.py`, `claim.py::_CLAIM_PROMPT`,
`config.DEFAULT_CLAIM_MODEL`, `config.BUILDER_VERSION`, `config.TSU_SCHEMA_VERSION`,
TSU 레코드 필드 집합, `docs/architecture/ADR-030-*.md`.

---

## 3. C1 검토 질문

### Gap 1 — resume

1. **Candidate 정합성 키** (`_reconcile_resume_point`, `builder.py`): 로드한 record ↔
   현재 candidate 매핑 키가 `(page, paragraph, sentence)` 3-튜플이다. 이 키가 실제
   `canonical.json`에서 유일한가? (CUE 실측: Fuller Vol.01–03 candidate 전량 dup=0,
   `paragraphs[].index`가 canonical.json 내 유일 → `(paragraph, sentence)`만으로도 유일.
   **Vol.04–08 재확인 요청**.) 키 충돌 시 `max_covered` 계산이 어긋날 수 있는지.
2. **canonical.json drift abort**: record 중 하나라도 현재 candidate에 매핑 안 되면
   `RuntimeError`로 중단(기록 전). 이 판정이 "resume해도 안전한 경우"를 잘못 막거나,
   반대로 "위험한 drift"를 통과시키는 경계 사례가 있는가?
3. **`next_id` 파생** (`_resume_next_id`): `tsu.json` 마지막 record의 id + 1을 권위
   기준으로 하고 `tsu_id_state.json`은 advisory(불일치 시 WARN 후 tsu.json 기준 채택).
   F2가 volume을 **순차** 처리하고 partial volume을 다음 volume 전에 재개한다는 전제
   하에서, 전역 id 충돌·중복이 발생할 수 있는 시나리오가 있는가?
4. **원자적 기록 + torn write** (`_atomic_write_json`, `_write_tsu_output`):
   `tsu.json` → `tsu_report.json` 순서 + `os.replace`. "`tsu.json`은 새 checkpoint까지
   썼는데 `tsu_report.json`을 못 씀" 창을 `_reconcile_resume_point`의
   `max(report_evaluated, max_covered)`가 실제로 닫는가? 역방향(report가 tsu.json보다
   앞섬)이 이 기록 순서에서 정말 불가능한가?
5. **불변식 논증** (설계 §4): "candidate k에서 중단 후 resume 완료 = 처음부터 완료"가
   `tsu.json` byte-identical이라는 주장. 논증의 허점, 그리고 "순차 `-np 1` 결정성이
   깨지면 구조적 불변식(id·건수·순서·doctrine 동일, claim 문자열만 상이)으로 degrade,
   손실·중복 없음"이라는 서술이 정확한가? (2026-09-08 parallel-speedup 실측:
   `-np 2` 동시성에서만 llama.cpp 비결정 관측.)
6. **회귀 커버리지**: `tests/test_nae_tsu_builder.py` 신규 4건(byte-identical /
   skip-noop / no-prior / drift-abort)이 불변식·skip·drift 경계를 충분히 덮는가?
   `resume=False` 기본이 기존 동작을 정말 무변경으로 두는가(기존 4건 회귀 게이트).

### Gap 2 — claim.py HTTP timeout

7. **결정성 무영향**: `ollama.generate()` → `Client(timeout=180).generate()` 전환이
   추출 프롬프트·모델·파라미터·응답 파싱·doctrine 분류·출력에 영향이 없고 오직
   transport(HTTP read timeout)만 bounded 하는가?
8. **Fail-soft + 게이트 흐름**: timeout 예외를 기존 `except Exception`이 흡수 →
   `ClaimResult(error=str(e))` → builder `errors += 1` → 다음 candidate. 진짜 wedge면
   연속 candidate 전부 timeout → `run_fuller_f2.sh::gate_ok`의
   `llm_errors / candidates_total >= 2%` 실패 → runner 비정상 종료 → 드라이버 STOP.
   이 체인이 실제로 성립하는가? (checkpoint된 partial은 다음 실행에서 `--resume`으로 회수.)
9. **timeout 값**: `CLAIM_HTTP_TIMEOUT_S = 180` 이 정상 추론(~10s) 대비 넉넉하면서
   wedge 감지 지연이 과하지 않은 값인가? `_CLIENT` 모듈 레벨 재사용(요청별 생성 아님)에
   부작용이 있는가?
10. **`nae_fuller_cjk_reextract.py`**: 동일 패턴 적용이 이 스크립트(F2 완료 직후 무인
    실행)에 맞는가? (스크립트라 C1 필수는 아니나 같은 커밋에 포함.)

### 공통

11. **`builder_version` 유지**: Gap 1·2 모두 `3.0.0` 유지. 근거 = 추출 로직·레코드
    shape·출력 결정성 불변, F2 parallel-speedup 선례(`NAE_FULLER_F2_PARALLEL_SPEEDUP_RESULT_001.md` §4).
    `run_fuller_f2.sh::gate_ok`의 `builder_version == "3.0.0"` 및 ADR-030 Amendment A §3
    F2 게이트 무영향. 동의하는가, 아니면 `3.1.0` 승격 + Amendment A 갱신이 필요한가?
12. **ADR 정합**: 본 변경이 ADR-030(§4 TSU Track 순서, §11 human-review, §12 N-9),
    Amendment A(PROPOSED — 상태 변화 없음), ADR-013/024/029 중 위반·우회하는 것이 있는가?

---

## 4. 실행 근거 (CUE 측 사전 검증)

```
$ ~/envs/dbma311/bin/python -m pytest tests/test_nae_tsu_claim.py tests/test_nae_tsu_builder.py \
      tests/test_tsu_worker.py tests/test_tsu_pipeline_wiring.py -q
61 passed

$ ~/envs/dbma311/bin/python -m pytest tests/ -k "nae or tsu or crosswalk or corpus or fuller or claim or sermon" -q
1397 passed, 2 skipped, 1445 deselected
```

- `python -m NAE.pipeline.tsu.runner --help` → `--resume` 노출.
- `bash -n scripts/run_fuller_f2.sh` → OK.
- `claim._CLIENT._client.timeout.read == 180` (config 배선 lock 테스트).
- Fuller Vol.01–03 candidate key uniqueness dup=0 (실측).

---

## 5. 요청 형식

- 판정: **GREEN / YELLOW(조건부) / RED**
- YELLOW/RED 시: 질문 번호별 구체 findings + 해소 방안
- 산출물: `docs/NAE_FULLER_TSU_BUILDER_RESUME_C1_REVIEW_RESULT_001.md`
- C1은 이 검토에서 **구현하지 않는다** (문서 검토 + 코드 read-only). 필요한 수정은
  findings로만 제시, 반영은 CUE가 사용자 승인 후 수행.

---

## 6. 게이트

- **C1 GREEN + HQ 승인** → Evidence Before Promotion Rule 4조건 중 3·4 충족.
  이후 갱신된 `run_fuller_f2.sh`(+`--resume`)/`claim.py`(timeout)로 F2 재개 가능
  (단, 현재 실행 중인 F2 완료 후 · `dev/dbma-engine` 병합 후).
- YELLOW → 조건 해소 후 재검토. RED → 재설계.
- 본 변경은 `nae_tsu_v1` 3,319 / `nae_ref_v1` 34,948 baseline과 production Qdrant에
  **무접촉** (TSU 생성 단계 코드만). F4/F5/F6는 본 검토 범위 밖.

---

## 7. C1 붙여넣기용 지시 (relay)

```
Task: NAE-TSU-BUILDER-RESUME-001 독립 검토 (C1 Review, 구현 아님).

브랜치 claude/tsu-builder-resume-abf035 (HEAD fbcdeef, base origin/dev/dbma-engine@daca402).
먼저 git -C ~/DBMA fetch 후 이 브랜치를 read-only로 확인:
  git log --oneline daca402..fbcdeef
  git diff daca402..fbcdeef -- NAE/pipeline/tsu/ scripts/ tests/

읽을 문서 (같은 브랜치):
  docs/NAE_FULLER_TSU_BUILDER_RESUME_DESIGN_v1.md
  docs/NAE_FULLER_TSU_BUILDER_RESUME_BUILD_REPORT_001.md
  docs/NAE_FULLER_TSU_BUILDER_RESUME_C1_REVIEW_REQUEST_001.md  ← 검토 질문 12개

수행:
1. 위 요청서 §3 질문 1–12에 각각 답한다 (근거는 코드 라인 인용).
2. 코드는 read-only. 수정하지 말 것. 테스트도 새로 돌릴 필요 없음
   (CUE 결과 §4 참고, 필요하면 ~/envs/dbma311 venv로 재현만).
3. 판정 GREEN / YELLOW(조건부, findings) / RED.
4. 결과를 docs/NAE_FULLER_TSU_BUILDER_RESUME_C1_REVIEW_RESULT_001.md 로 작성,
   같은 브랜치에 커밋 (커밋만, push는 CUE가).

핵심 확인 포인트:
- resume 후 tsu.json이 from-scratch와 byte-identical이라는 불변식 (설계 §4).
- _reconcile_resume_point의 (page,paragraph,sentence) 키 유일성 — Vol.04–08.
- _write_tsu_output 원자적 기록 순서가 torn-write를 닫는지.
- claim.py Client(timeout=180) 전환이 transport만 바꾸고 추출 결정성 불변인지.
- builder_version 3.0.0 유지 타당성 (Amendment A F2 게이트 무영향).
```
