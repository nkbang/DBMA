---
title: "ADR-007: Semantic Boundary Detector — D-5 Chunk Boundary Rebuild Gate"
category: architecture
sprint: SPRINT33-C
based_on:
  - docs/SPRINT33-C-phase1-baseline.md
  - docs/SPRINT33-C-phase3-score-distribution.md
  - docs/SPRINT33-C-phase4c-scripture-reference-validation.md
  - docs/SPRINT33-C-phase6b-boundary-delta.md
created: 2026-07-19
status: Architecture Decision (구현 전, 승인 대기 — Rebuild Gate 실행은 별도 승인 필요)
scope_modified: docs/architecture/ only (코드 미수정)
---

# ADR-007: Semantic Boundary Detector — D-5 Chunk Boundary Rebuild Gate

| | |
|---|---|
| Status | Proposed |
| Date | 2026-07-19 |
| Deciders | HQ (Task Order 승인) / CUE (조사·구현) |
| Supersedes | — |
| Superseded by | — |

> **명명 참고**: 본 문서는 최초 작성 시 ADR-006으로 번호가 매겨졌으나,
> 이전 세션(SPRINT30-31)에서 논의·승인된 "ADR-006 Document Structure
> Source Strategy"와의 번호 충돌 가능성이 확인되어 HQ 결정에 따라
> ADR-007로 재번호했다(2026-07-19). ADR-006 번호는 해당 과거 결정
> 사항을 위해 예약된 상태로 유지한다 — 소급 작성 여부는 별도 판단
> 대상.

---

## Context

SPRINT33-C는 SPRINT31-32에서 구축한 Heading Provider/Assembler 인프라를
"Boundary Feature"로 승격시켜(SPRINT33-B), heading 외에도 paragraph/tiny
fragment/sentence completion/scripture reference 5개 feature로 구성된
가중치 기반 Boundary Score 모델(`core/semantic_boundary_detector.py`)을
전 과정 dormant 상태로 구축·검증했다(Phase 1~5, 모두 shadow 모드,
production 미접촉).

Phase 6은 "이 dormant detector가 실제로 production chunking을
재구성(rebuild)할 근거가 되는가"를 판정하는 게이트(D-5)를 설계하는
단계다. Phase 6-A(Input Schema)와 Phase 6-B(실측)를 통해 다음이
확인되었다:

- 기존 `chunking_optimizer.py`의 길이 기반 청크 경계는 semantic
  boundary와 거의 상관관계가 없다(confirmed rate 2.19~2.5%).
- semantic boundary의 63~70%가 기존 청커에 의해 완전히 무시된다
  (orphaned rate).
- 이 결론은 offset 재구성 신뢰도(HIGH/MEDIUM confidence label)와
  무관하게 안정적으로 재현된다(교차 검증 완료).

동시에 Phase 4-C Validation은 feature 자체의 정밀도가 문서 장르에 따라
20~40%로 편차가 크다는 것을 확인했으며, Phase 5-A/5-B는 가중치 조정만으로
이 정밀도 문제를 완전히 해결할 수 없음을 실측으로 보였다. 즉 "기존
청커가 나쁘다"는 근거는 강하지만, "새 detector가 충분히 좋다"는 근거는
아직 부족하다 — D-5 게이트는 이 비대칭을 반영해야 한다.

---

## Decision

### 원칙 — 계층 분리 유지

```text
Semantic Boundary Detector = rebuild 승인 판단 계층 (shadow authority)
core/chunking_optimizer.py  = production 계층 (변경 없음, 이번 ADR 범위 밖)
```

D-5 게이트 통과는 rebuild "실행 승인"이 아니라 "rebuild 검토 개시
자격"을 의미한다. D-4(TSU rebuild gate)와 동일하게, 실제 rebuild는
게이트 통과 이후에도 별도의 명시적 HQ 승인을 요구한다.

### 1. Minimum Semantic Improvement Threshold — 수치 미확정, 이연

구체적 개선폭 수치는 이번 ADR에서 확정하지 않는다. 현재 존재하는 것은
dormant detector(측정 계층)뿐이며, 실제 semantic-aware 청커가 아직
없어 "적용 후 orphaned rate가 얼마로 개선되는가"를 측정할 대상이
없다. SPRINT33-D(Hierarchical Chunk Builder) 시제품 완성 후, 그
결과물을 대상으로 동일한 Phase 6-B 방법론(confirmed/orphaned rate)을
재적용해 목표치를 재산정한다.

### 2. Orphaned Boundary 허용 범위 — 2단계 기준

heading이 관여한 조합(heading 단독 또는 heading+타 feature)으로 판정된
boundary와, heading 없이 낮은 weight 조합만으로 판정된 boundary를
분리 평가한다. 전자의 orphaned rate가 게이트의 핵심 기준이며, 후자는
Phase 4-C 실측 정밀도(20~40%)를 고려해 더 관대한 허용 범위를 적용한다.
구체적 임계값은 §1과 함께 SPRINT33-D 이후 재산정.

### 3. False-positive 보호 조건

- 문서/장르 정밀도가 실측 최저치(20%, WBC 학술 주석) 미만으로 확인되면
  해당 장르에는 게이트를 열지 않는다.
- "단일 feature만으로 판정된 boundary 비율"을 추적 지표로 채택 — 전체
  boundary 중 이 비율이 일정 수준(예: 30%)을 넘으면 경고를 발생시킨다.
  구체 임계값은 후속 조사 대상.
- PageHeaderArtifact(ADR 후보, 미구현)로 식별될 running-header 반복이
  현재 측정에 여전히 섞여 있으므로, 정식 feature로 승격되기 전까지
  게이트 통과 기준에 안전 마진(10~15%)을 추가한다.

### 4. Document Genre별 Gate 적용 — Signal-Profile 방식 채택

게이트를 corpus 전체에 일괄 적용하지 않고, 문서 신호 프로파일별로
분리 적용한다(publisher-keyed가 아닌 signal-profile 방식 — 이는 앞서
세션에서 합의된 "Signal-Profile Calibration, publisher-keyed 아님"
원칙과 동일 철학이며, 이번 ADR에서도 그대로 계승한다). 장르 자동
분류 방식은 별도 Preflight로 조사한다(이번 ADR 범위 밖).

### 5. Rollback 조건

- Beta corpus 전체 재검증에서 pytest regression 실패 시 즉시 중단.
- rebuild 후 orphaned/confirmed rate가 rebuild 전보다 악화되면 자동
  롤백 대상(수치 기준은 §1 확정 후 정의).
- production 문서 표본(Beta corpus 밖) 사전 합의 검수 통과 필요 —
  SPRINT32-B Gate B(격리 rebuild 환경, 현재까지 미사용)를 최초로
  실사용하는 시점이 될 것으로 예상.
- 롤백은 TSU/chunk 데이터셋 자체를 이전 버전으로 되돌리는 작업이므로,
  D-4와 동일하게 별도의 명시적 HQ 승인 없이는 실행하지 않는다.

---

## Consequences

### 이번 ADR로 확정되는 것
- D-5 게이트의 존재와 5개 심사 항목의 틀(threshold 방향성, orphaned
  2단계 평가, false-positive 보호, genre 분리, rollback 절차).
- Detector(판단 계층)와 Chunker(production 계층)의 분리 원칙이 D-5
  단계에서도 계속 유지됨을 명문화.

### 이번 ADR로 확정되지 않는 것(의도적으로 미룸)
- §1/§2의 구체적 수치 임계값 — SPRINT33-D 이후 재산정 필요.
- §4의 genre 자동 분류 알고리즘 — 별도 Preflight 필요.
- PageHeaderArtifact의 정식 feature 승격 여부 — 별도 ADR 후보로 유지.
- TinyFragment × Heading interaction 문제(Phase 5 Preflight에서 발견,
  heading 동반 시 tiny penalty가 threshold를 못 넘김) — calibration
  이후 별도 ADR로 처리할지는 여전히 검토 대상.

### 리스크
- §1이 미확정 상태로 남아 있어, SPRINT33-D 완료 전까지는 D-5 게이트가
  "통과/실패"를 실제로 판정할 수 없다 — 이는 의도된 상태이며, 조기에
  임의 수치를 확정하는 것보다 안전하다고 판단.
- (해결됨) ADR 번호 충돌 — HQ 결정에 따라 006 → 007로 재번호 완료.
  006은 과거 결정 사항을 위해 예약 상태로 유지.

---

## Frozen Artifact Set (SPRINT33-C 전체)

```text
docs/SPRINT33-C-phase1-baseline.md                        Phase 1
docs/SPRINT33-C-phase3-score-distribution.md               Phase 3
docs/SPRINT33-C-phase4c-scripture-reference-validation.md  Phase 4-C
docs/SPRINT33-C-phase6b-boundary-delta.md                  Phase 6-B
docs/architecture/ADR-007-Semantic-Boundary-Detector-D5-Rebuild-Gate.md  Phase 6-D(본 문서)

core/semantic_boundary_detector.py       (dormant, 5 features)
scripts/shadow_boundary_analysis.py      (Phase 1/2/3 shadow driver)
scripts/shadow_score_distribution.py     (Phase 3 분석)
scripts/shadow_boundary_delta.py         (Phase 6-B 분석)
tests/test_semantic_boundary_detector.py
tests/test_shadow_boundary_analysis.py
tests/test_shadow_boundary_delta.py
```

## Next Steps

1. SPRINT33-D(Hierarchical Chunk Builder) Preflight 착수 시, §1/§2 수치
   재산정을 명시적 선행 작업으로 포함.
2. PageHeaderArtifact 별도 Preflight(ADR 후보 1) — 필요 시점은
   SPRINT33-D 착수 이전 권고(현재 orphaned/false-positive 측정치를
   오염시키는 주요 원인 중 하나이므로).
3. TinyFragment × Heading interaction(ADR 후보 2) — SPRINT33-D 착수
   전 calibration 재검토 권고.
4. (완료) ADR 번호 충돌 — 007로 재번호 완료.
