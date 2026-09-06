# SESAME C1 Task Order Draft — C1 독립 리뷰 요청 (REQUEST-001)

**발행**: CUE
**수신**: C1 (Fuller C1 Token-Regulated Execution)
**일자**: 2026-09-05
**대상 문서**: [`docs/architecture/notes/SESAME-C1-Task-Order-DRAFT.md`](architecture/notes/SESAME-C1-Task-Order-DRAFT.md) (commit `b644dbf`)
**근거 ADR**: [`docs/architecture/ADR-032-SESAME-Sermon-Style-Engine.md`](architecture/ADR-032-SESAME-Sermon-Style-Engine.md)
**Git 상태**: 대상 초안 커밋·푸시 완료 (`dev/dbma-engine`, `b644dbf`). 이 요청서도 동일 브랜치에 커밋.

---

## 1. 요청 성격 — 무엇을 리뷰하는가

이것은 **ADR-032 §11 P1 "C1 독립 리뷰"가 아니다.** 그 리뷰는 ADR-032 §15에 따라
HQ의 SESAME 착수 지시 + CUE의 본안(P0) 산출 이후에만 발동한다. 현재 SESAME는
동결 보존 상태다.

이 요청은 **검토 프로세스 설계 자체에 대한 독립 점검**이다. 즉, 첨부 초안이
ADR-032 §11 Work Sequence·§13 C1 Triggers·§15 Immediate Disposition·CUE Operating
Policy와 **모순 없이** C1 검토 라운드(C1-R0~R8)를 배치했는지만 본다.

**동결 위반 여부 확인 요청 포함**: 이 초안 작성 및 이 리뷰 요청 자체가
ADR-032 §15("CUE는 착수 지시 전까지 SESAME 관련 선행 작업을 일절 수행하지 않는다")
위반인지 C1이 판정해 달라. CUE 판단은 "docs/architecture/notes/ 한정, 코드·데이터·
스키마·본안 미생성 → 선행 작업 아님"이나, 이견이 있으면 BLOCK 처리 바람.

---

## 2. 리뷰 체크리스트 (C1)

### 2.1 ADR-032 정합성

| # | 확인 항목 | 근거 |
|---|---|---|
| C-1 | C1-R1이 §11 P1에, C1-R2가 P2에 … C1-R8이 P8–P9에 정확히 대응하는가 | ADR-032 §11 |
| C-2 | "P2를 P4보다 먼저" 제약이 초안 의존 관계도에 반영됐는가 | §11 말미, R-1 |
| C-3 | C1-R1을 필수 게이트로 둔 근거가 §13 트리거(새 ADR·새 Layer·Metadata Model)와 일치하는가 | §13 |
| C-4 | C1-R6(독립 검증)을 C1 주도로, DBMA-SEQ harness 재사용으로 명시했는가 | §11 P6, §5.3, §8 |
| C-5 | 백분율 유사도 점수 금지가 C1-R4·R6 체크 항목에 포함됐는가 | §5.3, R-3 |
| C-6 | Voice/TTS 상시 BLOCK 감시(P10)가 별도 ADR 부재 시 차단으로 규정됐는가 | §3.1, R-4 |
| C-7 | 승격 4조건 중 "C1 완료"를 C1-R7 게이트로 옳게 배치했는가 | §14 |

### 2.2 CUE Operating Policy 정합성

| # | 확인 항목 |
|---|---|
| P-1 | C1이 구현하지 않고 검토만 한다는 역할 한정이 문서 전체에서 유지되는가 |
| P-2 | 각 라운드 산출물이 "Review Report / 확인 메모"로만 한정됐는가 |
| P-3 | Architecture Freeze Rule / Evidence Before Promotion Rule과 충돌하는 서술이 없는가 |

### 2.3 누락·과잉

| # | 확인 항목 |
|---|---|
| M-1 | §11 P0~P10 중 C1 라운드가 대응되지 않은 단계가 정당하게 비어 있는가 (P0은 CUE 단독 본안 작성 → C1-R1 이전이 맞는가) |
| M-2 | 초안이 ADR-032가 확정하지 않은 사항(어휘·임계값·최종 스키마·저장 위치 O-3 등)을 임의로 확정하지 않았는가 |
| M-3 | 초안이 새 리스크를 유발하는 검토 절차를 넣지 않았는가 |

---

## 3. 기대 산출물 (C1)

`docs/NAE_C1_OPERATING_POLICY_REVISION.md` §11 Future Review Template 형식:

```
# C1 Review — SESAME C1 Task Order Draft (REQUEST-001)
STATUS: <APPROVED / APPROVED WITH CONDITIONS / BLOCKED / REJECTED>
Architecture Impact: <NONE / LOW / MEDIUM / HIGH>
## Findings — BLOCKER / WARNING / INFO
## §15 동결 위반 여부: <위반 아님 / 위반 — 사유>
## Final Judgment (5개 항목)
## Review Efficiency
```

- 결과 파일 제안: `docs/SESAME_C1_TASK_ORDER_DRAFT_REVIEW_001.md`
- BLOCKED 판정 시 초안을 `docs/architecture/notes/`에서 보류 상태로 표기하고 CUE 재작업.

---

## 4. 참고 — 대상 초안 구조 요약

C1-R0(착수 전 상태 점검) → **C1-R1**(본안 아키텍처 리뷰, 필수/게이트) →
C1-R2(자산 재고 감사, 읽기 전용) → C1-R3(Style Corpus/Admission) →
**C1-R4**(style_profile 스키마, 필수/게이트) → C1-R5(프로토타입 배치 점검) →
**C1-R6**(독립 검증, C1 주도/게이트) → C1-R7(승격 게이트) → C1-R8(구현 통합 감사).
상시: P10 Voice/TTS BLOCK 감시.

---

*이 요청서는 `docs/`만 대상이며 어떤 코드·데이터·코퍼스·config·ADR도 수정하지 않는다.*
