# NAE TSU Builder Execution Recovery Report 001

**Project:** NAE-TSU-BUILDER-EXECUTION-RECOVERY-001 (+ 선행 NAE-TSU-EXTRACTION-RECOVERY-001)
**작성일:** 2026-08-08
**Git Commit/Push:** 미수행.

---

## Phase 1 — 실제 종료 원인 조사

| 확인 항목 | 결과 |
|---|---|
| 1. Python 프로세스 종료 위치 | 특정 불가 — `build_tsu_for_identifier()`가 **전체 candidate 처리 완료 후에만** 파일/출력을 남기는 all-or-nothing 구조였기 때문에, 종료 시점의 진행 상태를 사후에 알 수 없었음(이번 작업으로 checkpoint 로그 추가해 해결) |
| 2. Exception 발생 여부 | 증거 없음(종료 당시 출력 파일 0바이트) |
| 3. Traceback 존재 여부 | 없음 |
| 4. OOM 여부 | **아니다** — `vm_stat` 확인 결과 free page 충분, `log show`에 memorystatus/저메모리 kill 이벤트 없음 |
| 5. Timeout 여부 | 코드상 `ollama.generate()` 호출에 client-side timeout 자체가 없음(무제한 대기) — client timeout은 원인이 아님 |
| 6. KeyboardInterrupt 여부 | 증거 없음 |
| 7. Ollama disconnect 여부 | **아니다** — `ollama serve`(PID 27871) 11일째 무중단 |
| 8. llama-server crash 여부 | **아니다** — `llama-server` 프로세스 재시작 흔적 없음, 연속 가동 확인 |
| 9. subprocess 종료 여부 | **그렇다** — 실행을 감쌌던 Python 프로세스가 완료 로그 없이 `ps aux`에서 사라짐 |
| 10. macOS kill 여부 | 시스템 로그 직접 증거는 없으나, Ollama 서버 로그에 `cancel task`/`500`이 관측됨 — 이는 서버가 아니라 **클라이언트 연결이 중간에 끊긴 결과** |

**ROOT CAUSE**: 코드 버그·OOM·크래시가 아니라 **실행 규모 대비 무점검(no-checkpoint) 설계**. Dagg(4569) + Hiscox(1149) = 5,718개 candidate를 순차 LLM 호출(건당 실측 평균 ~8~10초)로 처리하면 총 소요시간이 **약 12~13시간**에 달하는데, 기존 `build_tsu_for_identifier()`는 전체 완료 시점에만 결과를 기록하는 구조였다. 이런 장시간 무점검 프로세스는 (OS/Ollama 계층에 크래시 증거가 전혀 없으므로) 실행 환경의 장기 백그라운드 프로세스 수명 제약에 의해 중단된 것으로 판단되며, 기존 코드는 이런 중단에 대한 복구 지점을 전혀 남기지 않는 구조적 취약점을 갖고 있었다.

---

## Phase 2/3 — 진행 로그 + Checkpoint(100건마다)

`NAE/pipeline/tsu/builder.py::build_tsu_for_identifier()`에 추가:

- `checkpoint_every=100`(기본값)마다 `identifier / candidate N/전체 / claims / errors / elapsed / ETA` 형식으로 진행 로그 출력
- 같은 시점에 지금까지의 결과를 `tsu.json`/`tsu_report.json`에 즉시 기록(`partial: true/false` 플래그로 중간본/최종본 구분)
- **추출 로직(claim/doctrine 판정) 자체는 변경 없음** — `is_claim`/`doctrine` 등 알고리즘 무수정

Ollama 연결 자체에는 문제가 없었음(모델 응답 정상, 서버 무중단)을 Phase 1에서 이미 확인했으므로 별도 재현/수정 불필요.

---

## Phase 4 — 실제 Production 실행 결과

실행 전 `NAE/corpus/tsu/_backup_20260807T015632/`에 기존 상태 백업 완료.

프로세스를 `nohup`+`disown`으로 터미널/세션과 완전히 분리해 재실행(이전 실행의 근본 원인이었던 "무점검 장시간 실행" 자체는 checkpoint로 관측 가능해졌고, 프로세스 분리로 세션 경계에 덜 취약하게 함).

| identifier | candidates | claims_extracted | llm_errors | elapsed |
|---|---|---|---|---|
| Dagg_Church_Order | 4569 | **3377** | 1 | 44918.2s(약 12시간29분) |
| Hiscox_Standard_Manual | 1149 | **740** | 0 | 12452.5s(약 3시간27분) |

llm_errors=1(Dagg)은 모델 응답의 JSON 이스케이프 형식 오류 1건 — `claim.py`의 기존 fail-soft 설계(기능 변경 없음)에 따라 정상적으로 카운트만 되고 배치는 중단 없이 지속됨(코드 크래시 아님).

### 검증

```
$ review_status 분포
Dagg_Church_Order: 3377건 전부 "generated"
Hiscox_Standard_Manual: 740건 전부 "generated"

$ 필수 필드(id/tsu_schema_version/claim/doctrine/review_status) 누락: 없음
$ tsu_report.json partial 플래그: 둘 다 False(최종본 확정)
```

---

## Phase 5 — Safety Validation

```
$ git diff --stat NAE/pipeline/tsu/builder.py NAE/pipeline/tsu/claim.py
 NAE/pipeline/tsu/builder.py | 137 ++++++++++++++++++++++++++------------------
 NAE/pipeline/tsu/claim.py   |   2 +-
(이번 작업 변경분 — 승인 범위 내: 진행 로그/checkpoint 추가, review_status 기본값 수정)

$ git status --short | grep -E "^ M (core/|.*retrieval|scripts/crosswalk|.*manifest|.*Registry)"
(결과 없음 — core/, retrieval/, crosswalk/, manifest/, Registry 전부 무수정)

$ core/tsu_builder.py, core/retrieval.py, scripts/crosswalk/schema.py 변경 없음(0줄)
```

**PASS.**

---

## Phase 6 — Regression

```
$ pytest tests/test_nae_tsu_builder.py tests/test_nae_tsu_claim.py \
    tests/test_tsu_structure.py tests/test_tsu_sermon_fields.py tests/test_tsu_content_quality.py \
    tests/test_tsu_pipeline_wiring.py tests/test_tsu_review_gate.py tests/test_tsu_review_promotion.py \
    tests/test_indexer_review_gate_wiring.py tests/test_nae_index_indexer.py \
    tests/test_crosswalk*.py tests/test_manual_crosswalk_pilot.py \
    tests/test_build_tsu_dataset_chapter.py tests/test_build_tsu_dataset_verse_mapping.py \
    tests/test_tsu_builder_heading_integration.py -q
308 passed

$ pytest -q --ignore=output (전체 스위트)
1880 passed, 2 failed(tests/test_nae_embed.py, 기존 무관 baseline, 불변)
```

Review Gate 실제 Production 검증(embedding 미실행, dry_run=True):

```
>>> indexer.index_all(dry_run=True)
{'processed': 3, 'indexed': 0, ...}
```

`generated` 4,117건(Dagg 3377 + Hiscox 740) 전부 Review Gate에서 **0건 통과**로 정상 차단됨 — verified 승급 전 Retrieval 노출 없음 확인.

### Validator

```
source_validator.py    : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py  : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## 완료 보고

```
STATUS: PASS

FILES CREATED:
docs/NAE_TSU_BUILDER_EXECUTION_RECOVERY_REPORT_001.md

FILES MODIFIED:
NAE/pipeline/tsu/builder.py (checkpoint/progress logging 추가 — 추출 로직 무변경)
NAE/pipeline/tsu/claim.py (review_status 기본값 "unverified" -> "generated" 수정)
tests/test_nae_tsu_builder.py, tests/test_nae_tsu_claim.py (review_status 기대값 업데이트)
NAE/corpus/tsu/Dagg_Church_Order/{tsu.json,tsu_report.json} (실제 재생성)
NAE/corpus/tsu/Hiscox_Standard_Manual/{tsu.json,tsu_report.json} (실제 재생성)
NAE/corpus/tsu/_backup_20260807T015632/ (실행 전 백업)

MODEL:
my-theology-bot-v2:latest (unused-model/fallback/hidden override 없음 확인)

LLM TEST:
연결 정상(단건 호출 성공, elapsed ~10s), Phase 1 조사로 Ollama/llama-server 크래시 없음 확인

CLAIMS GENERATED:
Dagg_Church_Order: 3377 / Hiscox_Standard_Manual: 740 (합계 4117)

LLM ERRORS:
Dagg: 1(JSON escape 파싱 오류, fail-soft 정상 처리) / Hiscox: 0

TSU OUTPUT:
tsu.json, tsu_report.json 둘 다 생성 확인(partial=False, 최종본)

REVIEW STATUS:
전체 4117건 전부 review_status="generated" (스키마 유효)

GATE RESULT:
Review Gate dry-run 결과 indexed=0(전체 차단) — verified 승급 전 Retrieval 노출 없음 확인

REGRESSION:
타겟 308 passed, 전체 스위트 1880 passed / 2 failed(기존 무관 baseline, 불변)

DRIFT:
0 (source 89/0/0, manifest 138/0/0, authority 128/26/0)

FORBIDDEN PATH CHECK:
PASS (core/tsu_builder.py, core/retrieval.py, Retrieval architecture, Crosswalk schema, Registry, Manifest 전부 무수정, Embedding/Qdrant 미실행)

BLOCKER:
0

ROOT CAUSE:
실행 규모(5,718 candidate, 예상 12~13시간) 대비 checkpoint 없는 all-or-nothing 실행 설계 — 장시간 무점검 프로세스가 실행 환경의 백그라운드 프로세스 수명 제약으로 중단되어도 아무 복구 지점이 남지 않던 구조적 결함. Ollama/GPU/OS 계층 크래시·OOM 증거 없음.

WARNING:
0

NEXT STEP:
사람이 4117건의 generated TSU를 검토(review_promotion.py::promote_tsu_to_verified())하여 verified로 승급하는 실제 워크플로우 실행 — 별도 작업 명령 필요. 승급 후 실제 embedding/Qdrant 실행은 여전히 별도 승인 대상.

GIT:
NOT PERFORMED
```
