# STEP4 Pilot Execution Readiness Report

작성일: 2026-07-31
갱신일: 2026-07-31 (STEP4-B, Metadata Flow Trace 반영 재평가)

## 판정

**NOT READY** (변경 없음 — 단, 사유 세분화됨)

## 근거 (재평가)

| 선행 조건 | 상태 | STEP4-B 반영 |
|---|---|---|
| 원문 확보(다운로드) | 미실행 — 별도 승인 필요 | 변경 없음 |
| Registry 등록 | 미실행 — 원문 없이 등록 불가 | 변경 없음 |
| `nae_metadata` 코드 반영 | 미실행 | **세분화**: STEP4_METADATA_ADAPTER_PROPOSAL.md에서 확정 가능 부분(4개 파일, 약 25~30줄)과 미확정 부분(`core/processing.py`의 NAE 사전 등록 정보 lookup 메커니즘)으로 나뉨을 확인 |
| Dry-run 실행 명령 승인 | 미승인 | 변경 없음 |
| **(신규) NAE metadata lookup 메커니즘 설계** | 미설계 | STEP4-B에서 새로 발견된 선행 조건 — title/author와 달리 `theological_position` 등은 파일 자체에서 자동 추출 불가능하므로, 별도 입력 경로 설계가 코드 변경보다 먼저 필요 |

Pilot을 "코드 없이 기존 필드만으로" 실행할지, "NAE 필드까지 포함해" 실행할지에 따라 필요 조건이 갈림 — 아래 두 갈래로 재평가.

## 판정 세분화 (STEP4-B 신규 관찰)

### 갈래 A — 기존 필드만으로 제한된 dry-run (nae_metadata 제외)
- 필요 조건: 원문 확보 + registry 등록 + dry-run 승인 (기존 3개)
- **코드 수정 불필요** — STEP4_TSU_QUALITY_CRITERIA.md의 5개 기준 중 1,2,3,5(+4의 일부)는 이 경로로도 검증 가능
- 이 갈래는 여전히 원문 미확보로 NOT READY

### 갈래 B — nae_metadata 포함 전체 검증
- 필요 조건: 갈래 A의 3개 + `core/processing.py` lookup 메커니즘 설계 + 4개 파일 코드 변경(약 25~30줄, STEP4_METADATA_ADAPTER_PROPOSAL.md) 승인 및 실행
- 코드 변경은 additive-only, rollback 안전성 높음으로 확인되었으나 **아직 실행되지 않음**
- 이 갈래는 원문 미확보 + 코드 미반영 이중으로 NOT READY

## 준비 완료된 것 (문서/계획 단계, 누적)

- 대상 문서 명세: [STEP4_SOURCE_REGISTRATION.md](STEP4_SOURCE_REGISTRATION.md), [STEP4_PILOT_SOURCE_ENTRY.md](STEP4_PILOT_SOURCE_ENTRY.md)
- 실행 계획: [STEP4_PIPELINE_DRYRUN.md](STEP4_PIPELINE_DRYRUN.md)
- 채점 기준: [STEP4_TSU_QUALITY_CRITERIA.md](STEP4_TSU_QUALITY_CRITERIA.md)
- PD 검증 절차: [STEP4_PD_VERIFICATION.md](STEP4_PD_VERIFICATION.md)
- 코드 영향 조사: [STEP4_CODE_IMPACT_REVIEW.md](STEP4_CODE_IMPACT_REVIEW.md)
- Metadata 흐름 추적: [STEP4_PROCESSING_METADATA_FLOW.md](STEP4_PROCESSING_METADATA_FLOW.md), [STEP4_METADATA_FLOW_DIAGRAM.md](STEP4_METADATA_FLOW_DIAGRAM.md)
- Adapter 설계 제안: [STEP4_METADATA_ADAPTER_PROPOSAL.md](STEP4_METADATA_ADAPTER_PROPOSAL.md)

## READY 전환을 위한 다음 단계

1. HQ가 "원문 확보(다운로드) 승인" — Public Domain 1건, 소규모 (갈래 A/B 공통)
2. 확보된 원문을 `DEFAULT_RAW_DIR`에 배치, registry 등록 (기존 ingest 경로, 코드 변경 없음)
3. (갈래 A만 원할 경우) `--dry-run` 실행 승인 → 즉시 READY 전환 가능
4. (갈래 B 원할 경우) `core/processing.py` lookup 메커니즘 설계 승인 + STEP4_METADATA_ADAPTER_PROPOSAL.md 4개 파일 변경 승인 및 실행 → 이후 `--dry-run` 실행 승인

## 금지 사항 준수 확인

- 실제 TSU 생성: 미실행
- Embedding: 미실행
- Vector DB 변경: 미실행
- Code 수정: 미실행
- Git commit: 미실행
