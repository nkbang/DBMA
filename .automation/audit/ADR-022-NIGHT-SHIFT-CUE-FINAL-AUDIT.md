# CUE 최종 감사 — ADR-022 야간 회귀 안정성 검증

- reviewer: CUE
- date: 2026-08-14
- 대상: `.automation/evidence/night-shift/DBMA_N8N_NIGHT_SHIFT_REPORT_20260814.md` (C1 작성, CUE가 수치 2건 정정)
- production_mutation: false

## 판정: **COMPLETED — 승인**

## 독립 재검증 요약

C1의 자체 보고를 신뢰하지 않고 raw 데이터(cycle-summary.log, DB execution_entity, 파일시스템, 프로세스 목록, SHA256)를 CUE가 직접 재조회해 대조했다.

| 항목 | 결과 |
|---|---|
| 실제 경과 시간 | 10시간 28분(04:54:33 ~ 15:22:43 UTC) — C1 원 보고(15h22m)는 가짜 seed 시각을 기준점으로 잘못 계산한 오류, CUE가 리포트 원문 정정 |
| 총 실행 사이클 | 137회(C1 원 보고 130회는 초기 번호 매김 버그로 7회 누락 집계 — CUE가 리포트 원문 정정) |
| PASS/FAIL | 137/0 — 재계산해도 실패 0건 동일 |
| Restart 테스트(scenario 7/8, ~1시간 간격) | 10/10 PASS, cycle-summary.log grep 재확인 |
| NAE `incremental_state.json` SHA256 | `e10a396674f4d9084997f21a2d7586d674a3541b6fe356bfd47f4a808c52524a` — 감사 시작부터 지금 이 순간 재조회까지 완전히 동일 |
| n8n 총 execution 수 | 11,160+ (DB `execution_entity` 직접 카운트로 확인) |
| 루프 종료 상태 | 완전 종료 확인 — `ps -ef`에 `run-all-cycle`/`scenario-` 관련 프로세스 전혀 없음 |
| 정리(cleanup) 상태 | `.automation/tasks/`에 canonical 2개(`ADR-021-PILOT-001.json`, `schema.json`)만 존재, `NS-*.jsonl` 0개 |

## 이번 밤샘 전체 과정에서 CUE가 개입해 바로잡은 사항 (참고, 이번 137사이클 결과와는 별개)

야간 진행 중 아래 문제들이 발생했고 CUE-C1 협업으로 해결됐다. 최종 137사이클의 0 FAIL 결과는 이 수정들이 이미 반영된 **이후**의 안정 상태를 측정한 것이다:

1. 초기 race-condition 오탐(스크립트 자체의 bash/python 변수 치환 버그, 워크플로우 결함 아님) — 실행 재현으로 원인 규명 후 스크립트 수정
2. 중복 `run-all-cycle.sh` 프로세스 동시 실행으로 사이클 간격 붕괴(24~90초, 목표 300초) 및 컨테이너 1분 미만 간격 재시작 — 중복 프로세스 종료로 해결
3. restart 시나리오(7/8)가 매 사이클 실행되어 컨테이너가 과도하게 자주 재시작되던 설계 결함 — 12사이클(~1시간)마다 1회로 조정
4. 테스트 픽스처 미정리로 `.automation/tasks/` 843개, evidence 7,452개(29MB) 누적 — 사이클마다 자동 정리 로직 추가

이 문제들은 전부 **자동화 하네스(테스트 스크립트) 자체의 결함**이었고, ADR-022가 승인한 n8n 워크플로우 로직(`RECEIVED → VALIDATION_PASSED/FAILED → RETRY_PENDING`) 자체의 결함이 아니었다. 워크플로우 로직은 이 전체 기간 동안 단 한 번도 잘못된 응답을 내지 않았다.

## 최종 판정

**ADR-022의 Approved 범위(`RECEIVED → VALIDATION_PASSED/FAILED → RETRY_PENDING`)는 장시간(10시간+) 무인 반복 운영, 재시작 10회, 11,160+ 요청 처리 조건에서 상태·증거·동시성·NAE 격리가 전혀 무너지지 않음을 실측으로 증명했다.**

```
NIGHT SHIFT STATUS: COMPLETED (CUE 독립 재감사로 확정, 수치 2건 정정 반영)
```

## 다음 단계 권고

이 결과는 "Full Processing ADR(`VALIDATION_PASSED → PROCESSING → COMPLETED`, 실제 production mutation) 설계에 착수해도 되는 기반이 충분히 견고하다"는 근거로 사용할 수 있다. 다만 Full Processing ADR 자체는 이번 문서의 범위 밖이며, 별도 CUE 초안 작성 → 설계 검토 → C1 구현 → 독립 재감사 → Rev. Bang 승인의 동일한 절차를 처음부터 다시 거쳐야 한다.
