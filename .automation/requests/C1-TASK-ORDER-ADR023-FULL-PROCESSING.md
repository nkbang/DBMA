# C1 Task Order — ADR-023 Full Processing 구현

**Task Order:** C1-TASK-ORDER-ADR023-FULL-PROCESSING
**Date:** 2026-08-14
**발주자:** CUE
**대상:** C1
**근거 문서:** `docs/architecture/ADR-023-DBMA-N8N-Automation-Full-Processing.md`
**ADR-023 현재 상태:** `Proposed / Design Review Complete / Implementation Authorized` — Rev. Bang 설계 승인 완료("GREEN"), **Approved 아님.** 최종 승격은 (1)구현완료 (2)Test Matrix 12개 증거 (3)CUE 독립 재감사 (4)Rev. Bang 최종 승인 4개 전부 충족 후. **C1은 ADR 문서의 Status를 직접 바꾸지 않는다.**

---

## 이번 작업의 성격 — 반드시 이해하고 시작할 것

**이번 ADR은 처음으로 실제 Production 데이터(신학 원문 등록·보존)에 쓰기가 발생한다.** ADR-022까지는 실수해도 automation 메타데이터만 오염됐지만, 이번엔 `NAE/corpus/`, `NAE/pipeline/registration/state/`, Authority 파일에 실제로 쓴다. 그래서 이번 지시서는 다른 어떤 것보다 "절대 금지" 항목을 엄격하게 지켜야 한다.

**한 문장 요약**: ADR-023은 새 Processing Engine을 만드는 게 아니라, 이미 승인된 `register_source()`(ADR-021)를 n8n에서 안전하게 호출하는 최소한의 orchestration만 추가하는 것이다.

## 1. 만들 파일은 딱 하나 — `NAE/pipeline/registration/cli_driver.py`

- `NAE.pipeline.registration.pipeline.register_source()`를 **import해서 그대로 호출**한다. Identity/Preservation/Validation/Extraction/QualityGate 로직을 단 한 줄도 재구현하지 않는다.
- import 문에 `NAE.pipeline.tsu`, `NAE.pipeline.ingest`, `NAE.pipeline.embed`, `NAE.pipeline.index`, Qdrant 관련 모듈이 **하나도 없어야 한다.** 이건 ADR-023 §9의 핵심 안전장치이자 §14 체크리스트 5번 항목이다.
- 역할: (a) task JSON의 `automation.processing_input`을 읽어 `RegistrationRequest` 조립 (b) `existing_*_ids` 집합을 Authority 파일에서 **읽기 전용**으로 로드 (c) `register_source()` 호출 (d) `RegistrationResult`를 stdout에 JSON으로 출력

## 2. CLI Exit Code Contract (ADR-023 §12, 정확히 지킬 것)

| Exit Code | 상황 |
|---|---|
| `0` | `register_source()` 정상 완료(내부적으로 성공/실패 불문 — 결과 판정은 stdout JSON) |
| `1` | Python 예외 발생 |
| `2` | 입력 검증 실패(`processing_input` 파싱 불가/필수 필드 누락) |
| `3` | `raw_item_dir` 접근 불가 |

**stdout = JSON 결과만. stderr = 진단 정보. 절대 섞지 마라.** Phase B~D에서 "n8n이 실제로는 실패했는데 200 반환" 침묵 실패를 겪었다 — 이걸 cli_driver 레벨에서 재발시키면 안 된다.

## 3. State Mapping (ADR-023 §7, whitelist + fail-closed)

| RegistrationState | automation.state | failure_code |
|---|---|---|
| `QUALITY_PASSED` | `COMPLETED` | `null` |
| `REGISTRATION_FAILED` | `FAILED` | `REGISTRATION_FAILED` |
| `RAW_CHECKSUM_MISMATCH` | `FAILED` | `RAW_CHECKSUM_MISMATCH` |
| `EXTRACTION_FAILED` | `FAILED` | `EXTRACTION_FAILED` |
| `QUALITY_GATE_FAILED` | `FAILED` | `QUALITY_GATE_FAILED` |
| **그 외 임의 문자열(표에 없는 값)** | **`FAILED`** | **`INTERNAL_STATE_MAPPING_ERROR`** |

이 매핑을 하는 n8n Code 노드는 **whitelist 방식**이어야 한다 — 위 5개 알려진 값만 명시적으로 처리하고, 나머지는 전부 마지막 행(fail-closed)으로 떨어지게 만들어라. "모르는 값이면 일단 COMPLETED로 넘기자" 같은 코드는 절대 금지 — 이게 이 ADR에서 가장 위험한 실패 모드로 지정되어 있다.

## 4. n8n 워크플로우 확장

- 기존 Phase E 워크플로우(`phase-e.json`)의 `VALIDATION_PASSED` 분기 뒤에 **새로 추가**: Execute Command 노드(`python -m NAE.pipeline.registration.cli_driver ...`) → exit code 분기 → State Mapping Code 노드 → task 파일/evidence 갱신(기존 write 패턴 재사용) → Respond
- 기존 노드(Webhook, Read/Write Files, Extract From File, Schema Validation, IF, 기존 Respond들)는 **건드리지 않는다** — Phase B~D/E에서 이미 검증된 것들이다
- **손편집 금지, n8n UI → export → import 원칙 유지.** 이번엔 Execute Command 노드가 새로 등장하므로 그 노드의 실제 파라미터 계약(command, 출력 캡처 방식)도 추측하지 말고 n8n UI에서 만들어서 export한 실제 값을 써라

## 5. Schema 확장

`.automation/tasks/schema.json`을 `1.1.0 → 1.2.0`으로 additive 변경:
- `automation.processing_input` 객체 추가(ADR-023 §6 구조 그대로: `raw_item_dir`, `surname`, `given_name`, `title`, `edition_slug`, `publication_year`, `copyright_status`, `archive_source`, `source_id`)
- `automation.failure_code` enum에 `REGISTRATION_FAILED`/`RAW_CHECKSUM_MISMATCH`/`EXTRACTION_FAILED`/`QUALITY_GATE_FAILED`/`INTERNAL_STATE_MAPPING_ERROR` 5개 추가
- 기존 필드는 한 글자도 안 건드림

## 6. 테스트용 원문 데이터

Test Matrix 1번(정상 케이스)을 돌리려면 실제로 `raw_item_dir`에 파일이 있어야 한다. **새로 원문을 다운로드하거나 수집하지 마라** — 이건 ADR-023 §15에서 범위 밖으로 명시된 것이다. 기존에 이미 `NAE/corpus/raw/` 아래 있는 실제 public-domain 원문 중 하나(ADR-021 자신의 평가 스크립트 `scripts/generate_adr021_final_evidence.py`가 어떤 걸 썼는지 참고)를 테스트 입력으로 재사용해라. 새 원문이 필요하면 CUE에게 먼저 물어봐라.

## 7. Test Matrix 12개 전부 실행 (ADR-023 §13)

특히 아래 2개는 이번에 신규 추가된 것이니 빠뜨리지 마라:
- **테스트 11 (Unknown state fail-closed)**: cli_driver 출력의 상태값을 §7 표에 없는 임의값으로 강제로 바꿔서 n8n에 전달 → 반드시 `FAILED`+`INTERNAL_STATE_MAPPING_ERROR`가 나와야 한다. `COMPLETED`로 잘못 나오면 이 항목은 즉시 REJECT 사유다.
- **테스트 12 (Exit code 계약)**: cli_driver를 강제로 exit 1/2/3 각각 내게 만들어서 n8n이 stdout을 무시하고 exit code만으로 올바르게 분기하는지 확인

테스트 9(Production 코드 무변경)는 반드시 `cli_driver.py` 소스 자체를 `grep -n "^import\|^from"`으로 열어서 TSU/ingest/embed/index/Qdrant 관련 모듈이 하나도 없음을 직접 보여줘라.

테스트 10(ADR-022 회귀)은 기존 137사이클 스위트를 전부 다시 돌릴 필요는 없고, 최소 5종 핵심 케이스(정상/duplicate/conflict/validation FAIL/파일없음)가 여전히 통과하는지만 확인하면 된다.

## 8. 절대 금지

- `register_source()`, `NAE/pipeline/registration/`의 다른 기존 파일(`identity.py`, `manifest_writer.py`, `quality_gate.py`, `raw_preservation.py`, `source_validator.py`, `state.py`) — **한 줄도 수정하지 않는다**
- `NAE/pipeline/tsu/*`, `NAE/pipeline/ingest/*`, `NAE/pipeline/embed/*`, `NAE/pipeline/index/*`, Qdrant — import조차 금지
- raw 원문 파일 신규 다운로드/수집
- unknown state를 COMPLETED로 처리하는 로직
- n8n execution_id로 콘텐츠 중복 판정을 자체 구현(ADR-021의 duplicate detection과 역할 중복시키지 말 것)
- ADR-023 문서의 Status 직접 수정
- Phase B~D/E의 기존 승인된 노드 파라미터 변경

## 9. 제출

Test Matrix 12개 전부의 실제 실행 원문(curl/명령/응답/exit code/stdout/stderr)을 `.automation/evidence/`에 남기고 `READY_FOR_CUE_RE_AUDIT`로 제출하라. 실패가 나오면 숨기지 말고 그대로 포함해서 제출하라.
