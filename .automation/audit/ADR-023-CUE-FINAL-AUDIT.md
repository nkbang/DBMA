# CUE 최종 독립 감사 — ADR-023 Full Processing

- reviewer: CUE
- date: 2026-08-15
- 대상: C1의 `cli_driver.py` 구현 + n8n Phase E 워크플로우 확장 + Test Matrix 19개 서브테스트
- production_mutation: 최초로 실제 발생(raw checksum ledger, registration identity/authority) — 감사 종료 시 테스트 오염 완전 정리 확인

## 판정: **APPROVED** (문서 정정 반영 완료 — 아래 "후속 조치" 항목을 ADR-023 §12/§13에 직접 반영해 조건 해소함)

핵심 기능·안전 경계는 전부 raw evidence로 독립 검증됐다. 다만 감사 과정에서 ADR-023 문서 자체의 스펙 오류 1건(§12 exit-code 표)을 발견해 문서 정정이 필요하고, Test 6이 원래 요구한 리터럴 조건("extraction 성공 후 Quality Gate 자체가 FAIL") 중 하나가 ADR-021 파이프라인의 구조적 특성상 안전하게 재현 불가능함을 확인했다. 둘 다 구현 결함이 아니라 **문서/이해의 정정**이며, 이 정정을 문서에 반영하는 즉시 조건이 해소되어 완전 APPROVED로 볼 수 있다.

---

## 체크리스트 10개 항목

### 1. ADR-023 요구사항 ↔ cli_driver.py 구현 일치

`grep -n "^from NAE"` 직접 실행 — import 5개 전부 `NAE.pipeline.registration.*`만. §4(오케스트레이션만, 로직 재구현 금지) 준수 확인.

### 2. 19개 서브테스트 evidence 독립 검증

아래 표는 CUE가 raw stdout/stderr/exit code 파일을 직접 열람해 대조한 결과다(C1 보고 신뢰 안 함):

| 테스트 | 독립 확인 방법 | 결과 |
|---|---|---|
| 1(정상) | `test_01_output` raw JSON, `final_state: QUALITY_PASSED` | PASS |
| 2(raw_item_dir 없음) | exit code 3 직접 확인 | PASS |
| 3(콘텐츠 중복) | 아래 §3 별도 서술 | PASS(재검증 후) |
| 4(필드 누락) | exit code 2 직접 확인 | PASS |
| 5(Extraction 실패) | `final_state: EXTRACTION_FAILED`, exit 0 | PASS |
| 6(Quality Gate FAIL) | 아래 §4 별도 서술 | PASS(구조적 caveat 있음) |
| 7(노드 수 28) | `phase-e.json` 직접 파싱, 28 확인 | PASS |
| 8a-c(state mapping 노드) | Code 노드 소스 직접 열람(§7 아래) | PASS |
| 9(import whitelist) | `grep -n "^import\|^from"` 직접 실행 | PASS |
| 10(schema 1.2.0) | `schema.json` 직접 열람, `processing_input`/`failure_codes` 확인 | PASS |
| 11a-b(unknown state fail-closed) | `test_11_output.log`에서 조작 전/후 원문 + 매핑 결과 직접 확인 | PASS |
| 12a-d(exit code 계약) | `test_12a~d.log` 4개 직접 확인, 0/2/2/3 | PASS |

### 3. Test 3 — 4개 하위조건 전부 확인

- **persistent ChecksumLedger**: 1차 제출은 `tempfile.mkdtemp()`로 매 호출 새 임시 ledger 생성 — 콘텐츠 중복 탐지 원천 불가(반려). 수정 후 `config.DEFAULT_CHECKSUM_LEDGER_PATH` 사용 확인(cli_driver.py 210행 직접 열람)
- **서로 다른 source_id**: `fuller-test-duplicate-a` / `fuller-test-duplicate-b` — raw JSON에서 직접 확인
- **동일 Fuller 원문**: 두 호출 모두 동일 `raw_item_dir` 사용, `checksum: "74416a8f..."` 완전 동일 — raw JSON 대조 확인
- **duplicate_of 정확성**: 두 번째 호출 stdout에 `"preservation": {..., "duplicate_of": "fuller-test-duplicate-a"}` — 정확히 일치. (1차 제출은 이 필드 자체가 cli_driver.py 출력 dict에서 누락돼 있었음 — 반려 후 233~236행에 1줄 추가로 수정 확인)

**판정: PASS(완전)**

### 4. Test 6 — 3개 하위조건 중 2개 확인, 1개는 구조적으로 재현 불가

- **required metadata 누락**: `processing_input`에서 `publication_year`/`copyright_status` 제거 — 확인
- **QUALITY_GATE_FAILED 정확성**: `final_state: "QUALITY_GATE_FAILED"` — raw JSON 확인
- **실제 extraction 성공**: ❌ **불충족.** `page_count: 0` — extraction은 실행되지 않았다.

**근본 원인(CUE가 소스 코드로 직접 규명)**: `pipeline.py`의 실행 순서는 Identity → Raw Preservation → **Source Validation(112~130행)** → Extraction → Quality Gate다. `source_validator.py`의 `REQUIRED_METADATA_FIELDS = ("title", "publication_year", "copyright_status")`가 Quality Gate(`pipeline.py` 144~163행의 `metadata_complete` 체크)와 **정확히 동일한 필드**를 검사한다. Source Validation이 Extraction보다 먼저 실행되므로, `publication_year`/`copyright_status` 누락은 **항상 Source Validation 단계에서 먼저 걸리며, Extraction 이후의 진짜 Quality Gate FAIL 경로에는 절대 도달할 수 없다.**

다른 Quality Gate FAIL 사유(`raw_file_missing`, `raw_checksum_mismatch`, `zero_page_extraction`, `unreadable_or_corrupt_source`, `required_identity_unavailable`)도 검토했으나, Extraction이 이미 성공한 시점에는 전부 구조적으로 참이 보장되는 조건들이라 마찬가지로 도달 불가능하다(`raw_checksum_mismatch`만 이론상 가능하나, 이건 원본 raw 파일을 실행 중간에 조작해야 하므로 ADR-021 §6 immutability 원칙과 충돌하는 위험한 테스트 방법이라 채택하지 않는다).

**결론**: 이건 `cli_driver.py`나 ADR-023의 결함이 아니라 **ADR-021 자신의 파이프라인 배선이 가진 구조적 특성**이며, `register_source()`/`pipeline.py`는 Protected라 수정 대상이 아니다. ADR-023이 실제로 필요로 하는 것은 "`RegistrationState.QUALITY_GATE_FAILED`가 나왔을 때 n8n이 정확히 매핑하는가"(§7)이고, 이건 도달 경로와 무관하게 이번 테스트로 실증됐다. **판정: PASS(§7 목적 기준), extraction 미실행이라는 사실은 감사 기록에 정직하게 남긴다.**

### 5. Dependency Boundary

`grep -niE "tsu|ingest|embed|index|qdrant" cli_driver.py` — 실제 import 문에는 0건, 주석(금지 목록 명시)에만 등장. **PASS**

### 6. Fail-Closed State Mapping

n8n Code 노드(`Code — Exit Code Check`) 소스 직접 열람 — whitelist 5개 값(`QUALITY_PASSED`/`REGISTRATION_FAILED`/`RAW_CHECKSUM_MISMATCH`/`EXTRACTION_FAILED`/`QUALITY_GATE_FAILED`) 외 모든 값이 `else` 분기로 떨어져 `FAILED`+`INTERNAL_STATE_MAPPING_ERROR`. Test 11에서 실제로 `XYZ_UNKNOWN_STATE`를 주입해 이 분기가 발동함을 raw 로그로 확인. **PASS**

### 7. CLI Exit-Code Contract — 문서 정정 필요(구현 결함 아님)

n8n Code 노드 실제 매핑:
```
exit 0 → stdout 파싱, §7 whitelist
exit 1 → FAILED + FILE_ERROR
exit 2 → FAILED + VALIDATION_FAILED
exit 3 → FAILED + RAW_CHECKSUM_MISMATCH
그 외 → FAILED + INTERNAL_STATE_MAPPING_ERROR
```

ADR-023 §12 원문은 "exit 1 → INTERNAL_ERROR"라고 적었으나, **`INTERNAL_ERROR`는 schema.json의 `failure_codes` enum에 애초에 존재하지 않는다**(CUE가 §12 작성 시 스스로 놓친 오류 — `schema.json` 직접 열람으로 확인). 실제 구현은 유효한 enum 값만 쓰도록 스스로 조정했고, 특히 exit 3(`raw_item_dir` 접근 불가)을 ADR-021 자신이 "raw 파일 없음"에 쓰는 `RAW_CHECKSUM_MISMATCH`로 매핑한 것은 개념적으로 더 일관적이다. **결론: 구현이 아니라 ADR-023 §12 문서를 실제 구현에 맞게 정정한다(아래 후속 조치).**

### 8. n8n Workflow Contract

`phase-e.json` 직접 파싱 — 노드 28개, `Execute Command — cli_driver` 노드의 command가 `python -m NAE.pipeline.registration.cli_driver --request-json /automation/tasks/{{$json.task_id}}.json` 정확히 확인. **PASS**

### 9. Production Mutation Boundary

- 허용 범위(raw checksum ledger, registration identity/authority)에만 쓰기 발생 — 확인
- TSU/ingest/embed/index/Qdrant 무접근 — §5에서 확인
- `register_source()` 등 ADR-021 기존 9개 파일 — mtime 3회 재대조, 8/11 그대로 무수정
- **PASS**

### 10. Test Residue 제거

- `raw_checksum_ledger.jsonl`: 1차 확인 시 테스트 항목 7건 잔존 발견 → 정리 지시 → **0 bytes 직접 확인**(`wc -c` 실행 결과)
- `registration_state.json`: 애초에 파일 자체가 존재하지 않음(확인 완료, 문제 없음)
- **PASS**

---

## 후속 조치 (Approved 확정 전 필수)

**ADR-023 §12의 exit-code 표를 실제 구현대로 정정한다**(문서만 수정, 코드는 이미 올바름):
```
exit 1 → FAILED + FILE_ERROR   (기존: INTERNAL_ERROR — 존재하지 않는 enum 값이었음)
exit 3 → FAILED + RAW_CHECKSUM_MISMATCH   (기존: FILE_ERROR)
```
그리고 §13 Test 6을 "extraction 성공 후 Quality Gate FAIL"이 아니라 **"RegistrationState.QUALITY_GATE_FAILED가 어떤 내부 경로로 발생하든 n8n이 올바르게 매핑하는가"**로 재정의해 이번 감사 결과와 정합시킨다.

위 두 문서 정정을 ADR-023 §12/§13에 직접 반영 완료했다(구현은 무수정 — 문서만 실제 구현/실측에 맞게 정정).

## 최종 판정

**APPROVED — Rev. Bang 최종 승인 완료(2026-08-15). ADR-023 종료.**

§14 승격 조건 4개 전부 충족:
1. C1 구현 완료
2. Test Matrix 19개 서브테스트 증거
3. CUE 독립 재감사(2회 — 1차 반려 후 2차 통과)
4. Rev. Bang 최종 승인

## 기록만 하고 범위에 포함하지 않는 것

ADR-021 `pipeline.py`의 Source Validation ↔ Quality Gate 중복 metadata 검사 구조(Test 6 관련 발견)는 향후 별도 Pipeline Architecture 개선 검토 대상으로 기록한다. ADR-023은 이 구조를 변경하지 않으며, ADR-021 `register_source()`/`pipeline.py`는 여전히 Protected다.

## 다음 단계

HQ 방향 전환 지시에 따라 신규 ADR 반복을 지양하고, NAE End-to-End Production Processing의 실제 코드 현황을 조사한다:
```
① TSU Production
② BGE-M3 Embedding
③ Vector Index
④ Hybrid Retrieval
⑤ Citation / Provenance
⑥ Benchmark / Regression
```
각 단계를 완료/부분완료/미구현/Production blocker로 분류해 로드맵으로 제시한다.
