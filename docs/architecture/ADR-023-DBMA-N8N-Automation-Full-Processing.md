---
title: "ADR-023: DBMA n8n Automation Full Processing (VALIDATION_PASSED → PROCESSING → COMPLETED)"
category: architecture
based_on:
  - docs/architecture/ADR-022-DBMA-N8N-Automation-State-Machine.md (Approved)
  - docs/architecture/ADR-021-NAE-Source-Registration-Raw-Preservation-Extraction.md (Approved)
  - NAE/pipeline/registration/pipeline.py (register_source(), 실제 코드 확인)
  - .automation/audit/ADR-022-NIGHT-SHIFT-CUE-FINAL-AUDIT.md (137사이클/10시간+ 무결성 실측 근거)
created: 2026-08-14
revised: 2026-08-14 (CUE 사전 검토 1차 반영 — "Full Processing" 정의 명문화,
  unknown-state fail-closed 원칙, dependency boundary 강화, idempotency
  계층 분리 재확인, CLI Exit Code Contract 신설, 8개 Approval Gate 체크리스트
  명문화)
scope: n8n workflow에서 ADR-021의 register_source()를 호출하는 신규 **얇은
  CLI 드라이버**(`NAE/pipeline/registration/cli_driver.py`, 신규 파일) 1개만
  추가한다. register_source() 자체, NAE/pipeline/registration/*의 다른
  모듈, NAE/pipeline/tsu/*, NAE/pipeline/ingest/*, NAE/pipeline/embed/*,
  NAE/pipeline/index/*, Qdrant는 전부 무수정·무호출.
---

# ADR-023: DBMA n8n Automation Full Processing (VALIDATION_PASSED → PROCESSING → COMPLETED)

| | |
|---|---|
| Status | **Approved** (2026-08-15, Rev. Bang 최종 승인. §14 승격 조건 4개 전부 충족 — `.automation/audit/ADR-023-CUE-FINAL-AUDIT.md` 참고. Test 6 구조적 한계는 별도 Pipeline Architecture 개선 검토 대상으로 기록만 하고 이 ADR 범위에서는 다루지 않음(아래 참고)) |
| 후속 기록(이 ADR 범위 밖) | ADR-021 `pipeline.py`가 Source Validation과 Quality Gate에서 동일 metadata 필드(`publication_year`/`copyright_status`)를 중복 검사하는 구조라, "Extraction 성공 후 Quality Gate 자체에서 최초로 실패"하는 경로가 안전하게 재현 불가능함을 CUE가 확인(2026-08-15). Production 위험은 아니나, 향후 Pipeline Architecture 개선 검토 시 참고할 것 — ADR-023은 이 구조를 변경하지 않는다 |
| Date | 2026-08-14 |
| Deciders | CUE (초안), Rev. Bang (승인 대기) |
| Supersedes | — |
| Extends | ADR-022 §5/§9의 Future 상태(`PROCESSING`, `COMPLETED`)를 실제 구현으로 승격 |
| Does NOT extend | ADR-021의 `RegistrationState` machine, `NAE/pipeline/registration/pipeline.py`의 `register_source()` 함수 자체 — 이 ADR은 그 함수를 **무수정으로 호출만** 한다(§4) |
| Superseded by | — |
| **"Full Processing"의 정의 (CUE Review 반영, 필수 명문화)** | 이 ADR에서 "Full Processing"은 **n8n automation 관점에서 `register_source()`를 끝까지 수행하는 등록 처리(Source Registration Full Processing)**를 의미한다. `NAE 전체 ingestion → TSU → embedding → indexing` 같은 시스템 전체의 처리를 의미하지 않는다. TSU Builder 핸드오프 이후의 downstream(embedding/indexing/Retrieval)은 이 ADR의 범위에 포함되지 않으며, 그걸 다루려면 완전히 별도의 ADR이 필요하다(§14). |

**핵심 원칙(CUE Review 문구 그대로 채택):** ADR-023은 새로운 Processing Engine을 만드는 ADR이 아니라, 이미 승인된 ADR-021 Source Registration을 n8n에서 안전하게 호출하기 위한 최소한의 orchestration boundary를 정의하는 ADR이다.

---

## 1. Status

Proposed. ADR-022가 10시간+/137사이클/재시작 10회 무인 검증을 통과해 상태·증거·동시성 기반이 견고함이 실측으로 확인됐다(`.automation/audit/ADR-022-NIGHT-SHIFT-CUE-FINAL-AUDIT.md`). 이 ADR은 그 기반 위에 실제 production mutation(신학 원문 등록·보존·추출)을 처음으로 연결한다. **C1 구현 전, CUE 설계 검토가 먼저 완료되어야 한다** — ADR-022와 동일한 절차.

## 2. Context

ADR-021(Approved)이 이미 `register_source()`라는 완결된 함수를 구현해뒀다(`NAE/pipeline/registration/pipeline.py`). 이 함수는:

- **입력**: `RegistrationRequest`(raw 파일이 이미 존재하는 디렉터리 경로, 저자/제목/판본 메타데이터, source_id) + 기존 ID 집합들 + ledger/state_store/exception_queue
- **동작**: Identity Resolution → Raw Preservation → Source Validation → Extraction(`extract_pages()` 재사용) → Quality Gate → Manifest 기록을 순서대로 실행하며, 각 단계마다 `RegistrationState`(`DISCOVERED→REGISTERED→RAW_PRESERVED→VALIDATED→EXTRACTED→QUALITY_PASSED`, 실패 시 `REGISTRATION_FAILED`/`RAW_CHECKSUM_MISMATCH`/`EXTRACTION_FAILED`/`QUALITY_GATE_FAILED`)를 `RegistrationStateStore`에 기록
- **호출자**: 현재 `scripts/generate_adr021_final_evidence.py`(ADR-021 자체 증거 생성용 1회성 스크립트) 외에는 **아무도 없다** — 재사용 가능한 CLI/드라이버가 존재하지 않는다(CUE가 코드베이스 검색으로 직접 확인)
- **명시적으로 하지 않는 것**: TSU Builder 호출, raw 파일 자체의 확보(수집/다운로드) — `pipeline.py` 모듈 docstring이 "TSU generation is explicitly NOT invoked by this module"이라고 스스로 명시

즉 이 함수를 n8n에서 호출 가능하게 만들면, **ADR-022가 검증한 견고한 automation 껍데기 위에 이미 승인된 ADR-021 파이프라인을 실제로 실행하는 것**이 이번 ADR의 전부다. 새로운 Production 로직을 발명하지 않는다.

## 3. Problem

1. `register_source()`를 n8n(JS/TypeScript 실행 환경)에서 직접 호출할 수 없다 — Python 함수이고 CLI 진입점이 없다
2. n8n의 `automation.state`(ADR-022, 문자열 enum)와 ADR-021의 `RegistrationState`(Python enum, 6개 성공 상태 + 4개 실패 상태)는 **어휘 집합이 다르다** — 1:1 매핑이 필요하다
3. `register_source()`가 요구하는 입력(raw_item_dir, existing_*_ids 집합, ledger, state_store, exception_queue)을 n8n의 task JSON(현재 스키마는 `title`/`owner`/`phase` 등 automation 메타데이터 위주)이 그대로 담고 있지 않다 — 매핑 계층이 필요하다
4. raw 파일이 애초에 디스크에 없는 경우(가장 흔한 실패 케이스) automation이 "새로 만들어서 어떻게든 처리"하려 들면 안 된다 — 명시적 실패로 끝나야 한다(§9)

## 4. Decision — 얇은 CLI 드라이버 신설, register_source() 무수정

신규 파일 **`NAE/pipeline/registration/cli_driver.py`** 1개만 추가한다:

```
n8n (PROCESSING 진입)
   ↓
Execute Command 노드 (신규)
   ↓
python -m NAE.pipeline.registration.cli_driver --request-json <task 파일 경로>
   ↓
cli_driver.py:
   1. task JSON 파싱
   2. RegistrationRequest 조립 (§6 필드 매핑)
   3. existing_*_ids 집합 로드 (기존 Authority 파일에서 읽기만, §4 참고 — 무수정)
   4. register_source() 그대로 호출 (import만, 코드 복사/재구현 금지)
   5. RegistrationResult를 stdout에 JSON으로 출력
   ↓
n8n Code 노드가 stdout JSON 파싱 → RegistrationState를 automation.state로 매핑(§7)
```

`cli_driver.py`는 **오케스트레이션만** 한다 — Identity/Preservation/Validation/Extraction/QualityGate 로직을 단 한 줄도 재구현하지 않고 `register_source()`를 그대로 import해서 호출한다. 이건 ADR-021 자신이 `extract_pages()`를 "재사용만, 무수정"으로 다뤘던 것과 동일한 원칙이다.

## 5. State Model — Full Extension

```
RECEIVED → VALIDATION_PASSED → PROCESSING → COMPLETED
                              → PROCESSING → FAILED   (RegistrationState 실패 4종 매핑)
RECEIVED → FAILED
FAILED → RETRY_PENDING → PROCESSING
```

`PROCESSING`, `COMPLETED`는 ADR-022 §5에서 vocabulary만 예약됐던 상태 — 이번 ADR로 실제 전이 코드가 처음 생긴다.

## 6. Task 스키마 확장 — `automation.processing_input`

ADR-022 §13.1의 `automation` 객체(`additionalProperties: false`)에 `processing_input`을 추가한다(schema `1.1.0 → 1.2.0`, additive):

```json
{
  "automation": {
    "state": "PROCESSING",
    "failure_code": null,
    "last_transition_id": "...",
    "processing_input": {
      "raw_item_dir": "NAE/corpus/raw/archive_org/<category>/<work>/",
      "surname": "...",
      "given_name": "...",
      "title": "...",
      "edition_slug": "...",
      "publication_year": 1850,
      "copyright_status": "public_domain",
      "archive_source": "archive_org",
      "source_id": "..."
    }
  }
}
```

`processing_input`이 없거나 필드가 불완전하면 `VALIDATION_PASSED → PROCESSING` 전이 자체를 거부한다(§9) — 즉 Phase B~D/E의 schema validation(Code 노드)이 이 필드도 함께 검증하도록 확장해야 한다(기존 검증 스크립트에 `processing_input` 필수 필드 체크 추가, 기존 체크 항목은 무수정).

**`raw_item_dir`가 가리키는 디렉터리에 실제 파일이 있어야 한다 — 없으면 원문을 자동으로 가져오는 로직을 이 automation이 만들지 않는다.** 그 경우 `register_source()`가 스스로 `RAW_CHECKSUM_MISMATCH`로 실패 처리하고, cli_driver는 그 결과를 그대로 전달한다(§9 명시적 실패 원칙과 일치).

## 7. RegistrationState ↔ automation.state 매핑

| `RegistrationState`(ADR-021) | `automation.state`(ADR-022) | `automation.failure_code` |
|---|---|---|
| `QUALITY_PASSED` | `COMPLETED` | `null` |
| `REGISTRATION_FAILED` | `FAILED` | `REGISTRATION_FAILED` |
| `RAW_CHECKSUM_MISMATCH` | `FAILED` | `RAW_CHECKSUM_MISMATCH` |
| `EXTRACTION_FAILED` | `FAILED` | `EXTRACTION_FAILED` |
| `QUALITY_GATE_FAILED` | `FAILED` | `QUALITY_GATE_FAILED` |
| (중간 상태: `DISCOVERED`/`REGISTERED`/`RAW_PRESERVED`/`VALIDATED`/`EXTRACTED`) | 도달하지 않음(동기 호출이므로 중간 상태는 ADR-021 자신의 `registration_state.json`에만 기록되고, n8n은 최종 상태만 받는다) | — |
| **(위 표에 없는 임의의 문자열, 즉 unknown/unmapped state)** | **`FAILED`** | **`INTERNAL_STATE_MAPPING_ERROR`**(신규 failure_code) |

**CUE Review 필수 반영 — Fail-Closed 원칙**: `RegistrationState`는 현재 정확히 6개 성공 경로 상태 + 4개 실패 상태, 총 10개 값으로 `NAE/pipeline/registration/state.py`에서 코드로 확인했다(§2 근거). 이 표는 그 10개 전부를 다룬다. 매핑 로직(Code 노드)은 **whitelist 방식**이어야 한다 — 위 표에 명시된 값만 처리하고, `register_source()`가 향후 새 상태값을 추가하거나(예: ADR-021 개정) cli_driver의 버그로 예상치 못한 문자열이 오면 **절대 `COMPLETED`로 간주하지 않고 즉시 `FAILED`+`INTERNAL_STATE_MAPPING_ERROR`로 fail-closed**한다. "unknown state를 성공으로 간주"하는 매핑 버그는 이 ADR에서 가장 위험한 실패 모드이므로, C1 구현 시 CUE가 이 분기를 반드시 실행 재현으로 검증한다(§12 테스트 11번 참고).

ADR-022 §6의 `failure_code` enum(`VALIDATION_FAILED`/`FILE_ERROR`/`PARSE_ERROR`/`TASK_ID_PAYLOAD_CONFLICT`)에 위 4개(`REGISTRATION_FAILED`/`RAW_CHECKSUM_MISMATCH`/`EXTRACTION_FAILED`/`QUALITY_GATE_FAILED`) + `INTERNAL_STATE_MAPPING_ERROR` 총 5개를 **추가**해야 한다(schema `1.2.0`에서 enum 확장, additive). ADR-021의 실패 상태명을 그대로 재사용해 이름이 또 충돌하는 것을 방지한다 — namespace 충돌 여부는 §8에서 확인.

## 8. Namespace 재확인 (ADR-022 §3 원칙 계승)

`register_source()`가 내부적으로 쓰는 `RegistrationStateStore`(→ `NAE/pipeline/registration/state/registration_state.json`)는 **이 ADR이 절대 직접 쓰지 않는다** — `cli_driver.py`가 `register_source()`에 넘겨서 그 함수 내부에서만 쓰게 한다. n8n 쪽 `automation.state`는 §7 매핑표대로 **최종 결과만** 반영하는 별도 캐시일 뿐, `registration_state.json`의 authority를 대체하지 않는다. 이건 ADR-021이 이미 확립한 "별도 파일, 별도 authority" 원칙을 n8n 쪽 상태에도 동일하게 적용하는 것이다.

## 9. Production Mutation Boundary — 이번 ADR에서 처음으로 실제 발생

**이게 이 ADR의 핵심 위험 지점이다.** ADR-022까지는 `production_mutation: false`가 코드 자체의 부재로 보장됐다. 이번엔 실제로 `NAE/corpus/`(raw preservation 체크섬 기록), `NAE/pipeline/registration/state/`(state store), Authority 파일에 쓰기가 발생한다. 경계를 명확히 한다:

- **쓰기 허용**: `register_source()`가 이미 ADR-021에서 승인받은 범위(raw checksum ledger, registration_state.json, exception_queue.json, registration manifest, Author/Work/Edition Authority 신규 엔트리) — **이 이상 어떤 파일도 추가로 쓰지 않는다**
- **쓰기 절대 금지**: `NAE/pipeline/tsu/*`, `NAE/pipeline/ingest/*`, `NAE/pipeline/embed/*`, `NAE/pipeline/index/*`, Qdrant — `cli_driver.py`는 이 모듈들을 **import조차 하지 않는다**(TSU Builder 핸드오프는 ADR-021 자신도 명시적으로 범위 밖으로 뒀다 — 계승)

**CUE Review 반영 — 이건 실행 제한이 아니라 architectural dependency boundary다.** `cli_driver.py`의 import 목록 자체가 이 경계를 강제한다:

```
ADR-023 cli_driver.py
       │
       └── NAE.pipeline.registration.pipeline (register_source) — 이것만
```

`Retrieval Engine`, `TSU Pipeline`, `Embedding`, `Qdrant`는 `cli_driver.py`의 **dependency graph에 아예 등장하지 않는다** — 런타임에 안 부르는 정도가 아니라, import문 자체에 없어야 한다. C1 구현 후 CUE 재감사에서 `cli_driver.py`의 import 목록을 grep으로 직접 확인하는 것이 §9 준수의 1차 증거가 된다(§12 테스트 9). 이는 ADR-001/003의 Core Engine 보호 원칙과도 정합적이다.
- **Raw 원본 파일 자체**: `register_source()`는 raw 파일을 읽기만 하고 체크섬만 기록한다(ADR-021 §6 immutability) — cli_driver도 raw 파일 쓰기/삭제/이동을 하지 않는다
- 기존 Production Registry(`core/dataset_registry.py`)는 ADR-021 §12에서 이미 별도 dataset_id로 격리하기로 확정 — 이 ADR은 그 정책을 그대로 상속, 변경하지 않는다

## 10. Idempotency / Retry

- `register_source()` 자체가 ADR-021 §9(2계층 duplicate detection)로 이미 idempotent-safe하게 설계돼 있다 — 동일 원문을 두 번 등록 시도하면 `preservation.duplicate_of`로 감지된다(§107 라인 근거, 코드 확인됨)
- ADR-022 §7(payload conflict)은 **n8n 레벨의 idempotency**(동일 task_id + 동일 요청)이고, ADR-021의 duplicate detection은 **콘텐츠 레벨의 idempotency**(동일 원문, 다른 task_id로 요청되어도 감지)다. 둘은 서로 다른 계층이며 상호 대체하지 않는다 — 둘 다 유지한다

**CUE Review 필수 반영**: n8n execution_id(ADR-022 §11에서 race-condition 완화에 쓰인 그 값)를 이용해 "이미 한 번 처리된 execution이면 register_source() 재호출을 건너뛴다" 같은 **자체적인 콘텐츠 중복 판정 로직을 cli_driver.py에 새로 만들지 않는다.** automation retry 방지(n8n의 일)와 원문 콘텐츠 중복 방지(ADR-021 duplicate detection의 일)를 뒤섞으면 두 계층의 책임이 흐려진다 — `cli_driver.py`는 매 호출마다 `register_source()`를 그대로 호출하고, 중복 판정은 전적으로 그 함수 내부의 §9 로직에 맡긴다.
- `FAILED → RETRY_PENDING → PROCESSING` 재시도 시, `cli_driver.py`는 `register_source()`를 처음부터 다시 호출한다(ADR-021의 duplicate detection이 중복 raw 재처리를 막아줌 — 재구현 불필요)

## 11. Rollback

- `register_source()`가 실패하면(`*_FAILED` 4종) ADR-021 자신의 exception queue에 기록되고, **부분적으로 쓰인 raw preservation/manifest 엔트리를 롤백하지 않는다** — 이건 ADR-021 자신의 기존 동작이며 이 ADR이 바꾸지 않는다(§107 라인: RAW_CHECKSUM_MISMATCH여도 raw_files 자체는 그대로 둠, 이미 ADR-021이 "raw는 절대 삭제 안 함" 원칙을 §6에서 확정했으므로 일관적)
- n8n 쪽 롤백: `automation.state`가 `FAILED`로 남고, `.automation/evidence/`에 실패 evidence가 append됨 — task 파일 자체나 raw 데이터를 되돌리지 않는다(ADR-022 §11 원칙 그대로)

## 12. CLI Exit Code Contract (신규, CUE Review 필수 반영)

n8n이 `cli_driver.py`의 stdout JSON 파싱 결과만으로 성공/실패를 판단하지 않도록, exit code를 **1차 판정 근거**로 삼는다. n8n Execute Command 노드는 exit code를 먼저 확인하고, 0이 아니면 stdout JSON을 신뢰하지 않는다.

**CUE 최종 감사 반영(2026-08-15) — 아래 표는 최초 초안의 오류를 실제 구현대로 정정한 것이다.** 최초 초안은 exit 1을 `INTERNAL_ERROR`로 지정했으나, 이 값은 `schema.json`의 `failure_codes` enum에 애초에 존재하지 않았다(§13 schema diff에 추가한 적이 없음 — CUE 설계 검토 단계의 누락). C1 구현은 유효한 enum 값만 쓰도록 스스로 조정했고, CUE 재감사에서 이 조정이 개념적으로 더 낫다고 판단해(§8 참고) 문서를 구현에 맞춰 정정한다:

| Exit Code | 의미 | n8n 쪽 처리 |
|---|---|---|
| `0` | `register_source()` 정상 완료(성공/실패 결과 불문 — §7 매핑표로 최종 판정은 stdout JSON이 담당) | stdout JSON 파싱 → §7 매핑 적용 |
| `1` | `register_source()` 호출 자체는 됐으나 예외 발생(Python exception) | `FAILED` + `FILE_ERROR`(정정 전: 존재하지 않는 `INTERNAL_ERROR`였음), stderr 내용을 evidence에 기록 |
| `2` | 입력 검증 실패(`processing_input` 파싱 불가, 필수 필드 누락 — cli_driver 자체 레벨) | `FAILED` + `VALIDATION_FAILED` |
| `3` | `raw_item_dir` 접근 불가(경로 없음/권한 없음, `register_source()` 호출 전 단계) | `FAILED` + `RAW_CHECKSUM_MISMATCH`(정정 전: `FILE_ERROR`였음 — ADR-021 자신이 "raw 파일 없음"에 쓰는 상태명과 통일해 더 일관적) |

**출력 채널 분리**: `stdout`은 machine-readable JSON 결과만(사람이 읽는 로그 섞지 않음), `stderr`는 진단 정보(스택트레이스 등), **exit code가 authoritative**. 이 세 채널을 섞으면 Phase B~D에서 겪었던 "n8n이 실제로는 실패했는데 200을 반환" 같은 침묵 실패가 cli_driver 레벨에서 재발할 수 있다 — 절대 금지.

## 13. Test Matrix

| # | 시나리오 | 기대 결과 |
|---|---|---|
| 1 | 정상 원문(raw 파일 실재, 메타데이터 완전) | `PROCESSING → COMPLETED`, `registration_state.json`에 `QUALITY_PASSED` 기록, manifest 엔트리 생성 확인, exit code 0 |
| 2 | `raw_item_dir`에 파일 없음 | `PROCESSING → FAILED`(`RAW_CHECKSUM_MISMATCH`), raw 관련 파일 생성 없음, exit code 0(호출 자체는 정상, 결과가 실패) |
| 3 | 동일 원문 중복 등록 시도(다른 source_id) | ADR-021 duplicate detection 발동, `preservation.duplicate_of` 확인, `COMPLETED`이지만 notes에 duplicate 기록 |
| 4 | `processing_input` 필드 누락 | `VALIDATION_PASSED` 자체에 도달하지 못하고 `FAILED`(`VALIDATION_FAILED`) — PROCESSING 진입 자체가 차단됨(n8n Code 노드 레벨, cli_driver 호출 전) |
| 5 | Extraction 실패(0 페이지) | `PROCESSING → FAILED`(`EXTRACTION_FAILED`) |
| 6 | `RegistrationState.QUALITY_GATE_FAILED`가 발생했을 때 n8n 매핑 정확성(CUE 최종 감사로 재정의됨 — 최초 의도는 "extraction 성공 후 Quality Gate 자체가 FAIL"이었으나, `pipeline.py`의 Source Validation이 Extraction보다 먼저 동일 metadata 필드를 검사하는 구조상 그 경로는 안전하게 재현 불가능함을 CUE가 소스 분석으로 확인함. `register_source()`는 Protected라 수정 대상 아님) | `PROCESSING → FAILED`(`QUALITY_GATE_FAILED`), 도달 경로(Source Validation 경유든 Quality Gate 자체든)는 무관 |
| 7 | Quality Gate WARNING(non-blocking) | `PROCESSING → COMPLETED`, notes에 warning 기록(§14 line 179 근거) |
| 8 | `FAILED → RETRY_PENDING → PROCESSING` 재시도, 원인 해결 후 | 두 번째 시도에서 `COMPLETED` |
| 9 | `NAE/pipeline/tsu/*`, `ingest/*`, `embed/*`, `index/*`, Qdrant 무변경 확인 | 구현 전/후 관련 파일 SHA256 또는 mtime 동일, `cli_driver.py`의 import 문을 grep으로 직접 확인해 위 모듈이 하나도 없음을 증명(§9) |
| 10 | ADR-022 승인 범위(`RECEIVED→VALIDATION_PASSED/FAILED→RETRY_PENDING`) 회귀 | 기존 137사이클 테스트 스위트 재실행, 전부 PASS 유지 |
| 11 | **(신규) Unknown state fail-closed** — cli_driver 출력의 상태 문자열을 §7 표에 없는 임의값(예: 테스트용 mock)으로 바꿔 n8n Code 노드에 전달 | **반드시 `FAILED`+`INTERNAL_STATE_MAPPING_ERROR`** — `COMPLETED`로 잘못 판정되면 이 ADR 전체를 REJECT한다(§7 fail-closed 원칙의 실행 검증) |
| 12 | **(신규) Exit code 계약** — cli_driver를 강제로 exit 1/2/3 각각 내도록 만들어 n8n이 stdout JSON을 무시하고 exit code만으로 올바르게 분기하는지 확인 | exit 0이 아닌 경우 stdout 파싱 자체를 시도하지 않고 §12 표대로 정확히 분기 |

## 14. CUE Approval Gate

CUE 사전 검토(2026-08-14)에서 요구한 7개 필수 확인 항목 + exit code 계약을 승격 조건으로 명문화한다:

| # | 검토 항목 | 판정 기준 | 근거 절 |
|---|---|---|---|
| 1 | Scope | "Full Processing"의 의미가 Source Registration 단계로 명확히 고정되어 있는가 | 헤더 표 |
| 2 | Entry Point | `cli_driver.py`만 신규 진입점이며 기존 `NAE/pipeline/registration/*`을 변경하지 않는가 | §4 |
| 3 | State Contract | `RegistrationState` 전체 10개 값(성공 6·실패 4)이 명시되어 있는가 | §2, §7 |
| 4 | State Mapping | unknown/unmapped state가 fail-closed(`FAILED`+`INTERNAL_STATE_MAPPING_ERROR`)되는가 | §7, §13 테스트 11 |
| 5 | Mutation Boundary | `cli_driver.py`의 import 문에 TSU/embedding/index/Retrieval/Qdrant가 전혀 없는가 | §9, §13 테스트 9 |
| 6 | Idempotency | n8n retry(execution_id 기반)와 콘텐츠 duplicate(ADR-021 자체)가 뒤섞이지 않고 독립적으로 처리되는가 | §10 |
| 7 | Regression | ADR-021/022의 기존 승인 상태가 이번 구현으로 깨지지 않는가 | §13 테스트 9·10 |
| 8 | Exit Code Contract | stdout(JSON)/stderr(진단)/exit code(authoritative) 3채널이 분리되고, n8n이 exit code를 1차 판정 근거로 쓰는가 | §12 |

```
CUE
 ├── 위 8개 항목 — 소유
 ├── register_source() 무수정 원칙 감사
 └── acceptance criteria(§13)

C1
 ├── cli_driver.py 구현(오케스트레이션만, 로직 재구현 금지)
 ├── n8n Execute Command 노드 + state 매핑 Code 노드 구현(UI-generated/export-verified 원칙 유지)
 ├── schema 1.2.0 diff 구현
 └── §13 Test Matrix 12개 실행 증거

CUE
 └── 독립 재감사(register_source() 소스 diff로 무수정 확인, cli_driver.py import 목록 grep 확인 포함)
```

**절대 금지**: `register_source()`, `NAE/pipeline/registration/`의 다른 기존 모듈, TSU/ingest/embed/index 파이프라인, Qdrant — 이번 ADR 구현 범위에서 **한 줄도 수정하지 않는다.** 새로 추가하는 파일은 `cli_driver.py` 하나와 n8n 워크플로우 확장뿐이다.

## 15. 알려진 미해결 gap (이 ADR의 범위 밖으로 명시)

- **원문 자체의 확보(YouTube 다운로드, 신규 archive.org 수집 등)는 이 ADR이 다루지 않는다.** `raw_item_dir`에 파일이 이미 있어야 한다는 전제다. 향후 이 전제 자체를 자동화하려면(예: n8n이 YouTube URL을 받아 다운로드까지 수행) **완전히 별도의 ADR**이 필요하며, 그건 `NAE/collectors/*`의 새 모듈을 요구할 수 있고 이번 ADR의 승인 범위에 포함되지 않는다
- Author/Work/Edition Authority 파일의 `existing_*_ids` 집합을 cli_driver가 매 호출마다 어떻게 로드할지(전체 스캔 vs 캐시)는 구현 세부사항으로 남겨두되, **읽기 전용**이어야 하며 C1 구현 시 CUE가 재감사한다
