# CUE Authorized Task — Corpus Factory Integration Pilot 001

**Task Order:** CORPUS-FACTORY-INTEGRATION-PILOT-001
**Date:** 2026-08-17
**발주자:** CUE (Architecture / Governance / Independent Verification)
**실행자:** CUE (C1 relay 불가 시간대이므로 CLAUDE.md CUE Operating Policy에 따라 CUE 직접 실행. C1이 가용해지면 이후 작업은 C1에게 이관 가능)
**근거 문서:** `docs/architecture/ADR-026-Control-Plane-Corpus-Factory-Integration-Design.md`(Proposed), `.automation/audit/AUTONOMOUS-NIGHT-SHIFT-001-RESILIENCE-MATRIX.md`

---

## 목표 (한 문장)

ADR-026의 17개 계약 중, **아직 실제로 증명되지 않은 부분만** — 네임스페이스 분리(`corpus-factory-pilot`), CLI-driver-boundary 실행 패턴, `authorized_by_task_order` 필드 — 격리된 pilot에서 end-to-end로 증명한다. 이미 증명된 나머지(canonical signature propagation, evidence integrity, heartbeat/crash recovery, dependency handling, duplicate/conflict, human-only retry 부재증명)는 재사용하고 재구현하지 않는다.

## 절대 금지 (변경 없음)

`core/retrieval.py`, `data/제련완성본/`, NAE production corpus, Fuller Vol.02-08, Approved workflow 직접 수정, 자동 retry/promotion/approval, C1을 runtime executor로 사용. 실제 Corpus Factory 데이터/task_type 연결 금지 — 이번 task 이후로도 별도 승인 전까지 금지 유지.

## 구현 범위

1. **`.automation/control-plane/task-contract.schema.json`** additive 확장: `authorized_by_task_order`(required, non-empty string) 필드 추가. 기존 필드 무변경.
2. **신규 task_type**: `corpus_pilot_echo` — `pilot_echo`와 기능적으로 동일(안전한 echo)하지만, **CLI-driver-boundary 패턴**을 증명하기 위해 실제 별도 스크립트(`.automation/control-plane/fixtures/corpus_pilot_driver.py`, 신규, NAE import 0개, 고정 echo만 수행)를 `subprocess.run([...])`으로 호출한다 — executor 코드 안에 그 스크립트의 로직을 인라인하지 않는다(ADR-023의 cli_driver.py 패턴을 그대로 미러링, 실제 NAE 코드는 무관).
3. **신규 네임스페이스**: `scope.namespace == "corpus-factory-pilot"`. task_id prefix `CORPUS-FACTORY-PILOT-`. `pilot_executor.py`의 `ALLOWED_TASK_TYPES`/`REQUIRED_NAMESPACE`를 이 신규 조합에 한해 별도 allowlist 항목으로 추가(기존 `control-plane-pilot`/`pilot_echo` 조합은 무변경 유지 — 두 네임스페이스가 서로 다른 executor 정책을 가질 수 있음을 증명).
4. **n8n gateway**: 기존 `Control Plane Pilot (Isolated)` 워크플로우의 Schema Validation 노드에 `authorized_by_task_order` 필수 검사만 추가(다른 노드 무변경).

## 실행 순서 및 요구 evidence

1. 위 스키마/executor/gateway 변경 (diff로 남길 것)
2. 정상 케이스: `CORPUS-FACTORY-PILOT-001` (전체 필드 포함, task_type=corpus_pilot_echo) → 실제 curl 웹훅 제출 → `pilot_executor.py --once` 처리 → COMPLETED, evidence에 CLI driver subprocess의 실제 stdout 포함
3. 격리 위반 시도: `scope.namespace`를 `control-plane-pilot`으로 잘못 지정한 `corpus_pilot_echo` task → executor가 독자적으로 거부하는지 확인(namespace/task_type 조합 검사)
4. `authorized_by_task_order` 누락 케이스 → 게이트웨이 VALIDATION_FAILED
5. 기존 `control-plane-pilot`/`pilot_echo` 조합이 이번 변경으로 회귀하지 않았는지 pytest 및 실제 curl 재확인
6. production isolation 최종 재확인(registration_state.json 해시, Phase E 노드 수, git status)

## CUE Gate

이 task는 CUE가 발행하고 CUE가 직접 실행하므로, **자기 자신의 결과를 스스로 PASS로 선언하지 않는다** — 완료 후 별도로 raw evidence를 다시 읽고 독립 재검토 섹션을 결과 보고에 명시적으로 분리해서 작성한다(자기감사의 한계를 인정하고, 사용자가 원하면 나중에 C1에게 동일 evidence의 교차검증을 요청할 수 있도록 재현 가능한 명령을 전부 남긴다).

## 완료 후

Corpus Factory 실제 연결은 여전히 금지. 다음 단계(있다면)는 Rev. Bang의 별도 승인을 기다린다.
