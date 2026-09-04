# C1 Task Order — ADR-022 야간 회귀 안정성 검증 (Night Shift)

**Task Order:** C1-TASK-ORDER-ADR022-NIGHT-SHIFT-REGRESSION
**Date:** 2026-08-14
**발주자:** CUE
**대상:** C1
**프로토콜:** NAE Night Shift Protocol v1 적용(2026-08-13 채택, DBMA n8n automation에도 동일 원칙 적용)

---

## 오늘 밤의 목표 (한 문장)

**"n8n을 밤새 돌려서 DBMA를 처리한다"가 아니라, "n8n이 밤새 살아 있어도 상태·증거·중복·동시성이 절대로 무너지지 않는다는 것을 증명한다."**

Full Processing을 돌리는 것이 아니다. ADR-022 Approved 범위(`RECEIVED → VALIDATION_PASSED/FAILED → RETRY_PENDING`)의 **운영 수준 안정성**만 검증한다.

## Governance 원칙 (NAE Night Shift Protocol 그대로 적용)

- CUE는 Governance verifier이자 Safety Gate이며 구현을 대신하지 않는다
- Workflow: **C1 Build/Run → C1 Test → CUE Audit → {PASS→다음 라운드, CORRECT→C1로 반송, HOLD→STOP}**
- **자동 Stop 조건**(발생 즉시 중단, C1이 임의 해제 안 함):
  - `VALIDATION_PASSED → PROCESSING` 또는 `→ COMPLETED` 전이가 단 1건이라도 발생
  - `.automation/tasks/`, `.automation/evidence/` 밖의 어떤 파일이라도 쓰기 발생(특히 `NAE/pipeline/`, `NAE/corpus/tsu/`, ADR/governance 정본 문서, `schema.json`, `PRODUCTION_RULES.md`)
  - `NAE/pipeline/ingest/state/incremental_state.json` 또는 `NAE/pipeline/registration/state/*` 변경
  - `phase-e.json` 워크플로우 노드/연결 구조 변경(자정 이후 손편집 금지 원칙 재확인)
  - evidence 유실/중복/불일치, transition_id 충돌 재발
  - 알 수 없는 예외, timeout, n8n 컨테이너 반복 재시작 실패
- **Correction loop 최대 3회** — 초과 시 즉시 STOP하고 `STOPPED / REPEATED_CORRECTION_FAILURE`로 기록, 다음 작업 임의 시작 금지
- **Protected Paths**(read-only 취급): `NAE/pipeline/`, `NAE/corpus/tsu/`, Production Qdrant, ADR/governance 정본 문서, `.automation/PRODUCTION_RULES.md`, `.automation/tasks/schema.json`
- **C1 self-report를 최종 증거로 쓰지 않는다** — CUE가 다음날 아침 파일 hash·evidence 원문·docker logs를 직접 재확인한다(이번 세션 내내 적용해온 원칙)
- 야간 허용 범위: **Implementation → Verification → Documentation까지.** Full Processing 설계나 Production Admission은 항상 아침 owner-controlled gate로 남긴다

## 야간 회귀 시나리오 9종

각 시나리오를 **반복(최소 수십 회 이상, 가능하면 장시간 루프)** 실행하고 매 라운드 결과를 evidence로 남긴다:

| # | 시나리오 | 확인 사항 |
|---|---|---|
| 1 | 동일 task 반복 요청 | 매번 `duplicate` 응답, state/evidence 불변 |
| 2 | 동일 task **동시** 요청(병렬 5개 이상) | transition_id 전부 고유, evidence 유실/중복 없음 |
| 3 | 잘못된 task(스키마 위반) | 항상 `validation_failed`, 침묵 실패(200+빈바디) 재발 없음 |
| 4 | 존재하지 않는 파일 | 항상 `file_error`, 명시적 메시지 |
| 5 | validation failure(다양한 필드 조합) | 매번 정확한 `errors` 배열 |
| 6 | 이미 처리된 state에 대한 illegal transition | 매번 `illegal_transition`, 파일 state 불변 |
| 7 | **n8n restart 후 state/evidence 지속성** | `docker restart dbma_n8n` 후 이전에 쓴 task/evidence 파일 내용이 그대로 남아있는지, 재시작 후 첫 요청이 정상 동작하는지 |
| 8 | **Docker restart 후 workflow activation** | 재시작 후 `docker logs`에서 "Activated workflow" 자동 확인, 수동 재활성화 없이 정상 응답하는지 |
| 9 | 장시간 반복 실행 후 evidence integrity | 수백 회 누적 실행 후 evidence 파일들의 JSON Lines 무결성(각 줄이 valid JSON인지), transition_id 순서 이상 없는지 |

## 매 라운드 절차

```
C1 Build/Run (시나리오 실행)
   ↓
C1 Test (즉시 자체 확인)
   ↓
Evidence 기록 (.automation/evidence/night-shift/ 하위, 라운드별 파일)
   ↓
자동 Stop 조건 해당 여부 자체 점검
   ↓
{정상 → 다음 라운드} / {이상 → 즉시 STOP, 원인 기록, 다음 작업 시작 안 함}
```

## 종료 시 필수 산출물

`.automation/evidence/night-shift/DBMA_N8N_NIGHT_SHIFT_REPORT_20260814.md` 생성, 최소 다음 포함:

- 9개 시나리오별 실행 횟수, PASS/FAIL 카운트
- 발견된 이상 현상(있다면) 원문 그대로
- restart 관련 시나리오(7, 8)의 docker logs 발췌
- evidence 파일 무결성 점검 결과(총 라인 수, 파싱 실패 라인 유무)
- 마지막 줄에 정확히 다음 중 하나만 기재:
  - `NIGHT SHIFT STATUS: COMPLETED`
  - `NIGHT SHIFT STATUS: STOPPED — GOVERNANCE DECISION REQUIRED`

## 절대 금지

- `PROCESSING`/`COMPLETED`로의 실제 전이 코드 추가 — 오늘 밤은 §5 Future 범위를 절대 건드리지 않는다
- `phase-e.json` 손편집(수정이 필요하면 STOP하고 CUE에게 보고, 임의로 UI에서 고쳐서 계속 진행하지 않는다 — correction 3회 제한 적용)
- Protected Paths 쓰기
- 이상 현상을 숨기거나 "재시도해서 통과"로 덮어쓰기
- STOPPED 상태에서 다음 작업 임의 시작

## 다음 날 아침

CUE가 `DBMA_N8N_NIGHT_SHIFT_REPORT_20260814.md`와 raw evidence를 직접 재확인(hash 대조, 로그 원문 확인)한 뒤 Rev. Bang에게 보고. COMPLETED로 안정성이 확인되면 그 지점에서 **Full Processing ADR**(신규, `VALIDATION_PASSED → PROCESSING → COMPLETED`, production mutation 경계, rollback/idempotency 포함) 설계 착수를 CUE가 제안한다.
