# GS 운영 통합 ④ 생성·스트리밍 계약 — 현황 보고

- 작성: CUE · 2026-09-30
- STATUS: **HQ 결정 대기** — CUE와 C1 모두 작업을 멈춘 상태다
- 브랜치: `tmp/fu007-integration-trial` (기준 HEAD `7c6b92d5`, 원격과 같음, worktree 0)
- **MUTATION: NONE**
  - 코드·ADR·prompt 변경 없음
  - MAIN 체크아웃의 미커밋 17개는 그대로 보존

## 1. ④ 관련 산출물

모두 CUE가 작성했다.

| 커밋 | 문서 |
|---|---|
| `09cd60dc` | [④ 사실 브리프](NAE_GS_GENERATION_CONTRACT_BRIEF_HQ_REPORT.md) (C1~C10) |
| `802f2e0f` | [⑤ 구현 설계 자료](NAE_GS_IMPLEMENTATION_DESIGN_BRIEF_HQ_REPORT.md) |
| `517c0c2e` | 호출자 수 자기 정정 (dev 4곳 / main·b39572aa 5곳) |
| `8045dcee` | [④ 계약 5항목 결정 자료](NAE_GS_CONTRACT_DECISION_BRIEF_HQ_REPORT.md) (항목 간 의존 관계, 맞지 않는 조합 5건) |
| `69ec97a2` | [④ 결정 기준 상태 고정 기록](NAE_GS_CONTRACT_DECISION_BASELINE_HQ_REPORT.md) |
| `7c6b92d5` | [④ 결정 기록 양식](NAE_GS_CONTRACT_DECISION_RECORD_TEMPLATE.md) (모든 항목 "미결") |

- C1이 낸 산출물은 ⑤ 설계 검토 하나뿐이다. CUE 검증에서 오류 4건이 나와 COMPLETE로 채택하지 않았다.
- 근거를 인용할 때는 CUE 자료와 C1 자료를 구분한다.

## 2. 결정과 관계없이 정해진 사실

- 어떤 조합을 고르든 새 ADR이 필요하다(ADR-036 B1, P12 완료 `ec204adf`).
- GS 계약 범위는 A(provenance)와 B(원문 언어 span)까지다(③ 결정).
- 어떤 조합도 P0-5의 의미 grounding 문제(C)를 해결하지 않는다.
- 현재 앱은 검증보다 답변 표시가 먼저이고, 모든 검증은 경고만 낸다(fail-open).
- 릴리스 라인인 dev에는 GS와 근거 계층이 없다.

## 3. HQ 결정 항목

결정 순서대로 적는다.

| 순서 | 항목 | 선택지 |
|---|---|---|
| 1 | ④-1 생성 방식 | A 구조화 생성 / B 생성 후 추출 / C 혼합 |
| 2 | ④-3 인용 구간 저장 | 3-a B8 변경 / 3-b 검증용 Claim / 3-c 저장하지 않음 |
| 3 | ④-2 스트리밍 | S-A 비스트리밍 / S-B 현행 / S-C 버퍼 |
|   | 차단 정책 | 경고만 / 부분 차단 / 전면 유보 |
| 4 | ④-4 ADR 범위 | 채팅만 / dev 호출자 4곳 전부 |
|   | 추가로 정할 것 | ADR-037 포함 여부, 교단 지시문 처리 방식 |
| 5 | ④-5 노출 문구 | 내부 상태 4종 각각의 사용자 문구 |

## 4. 조합 제약

| 구분 | 조합 |
|---|---|
| **배제 조건** (CONFIRMED) | S-B + 차단 정책 |
| **배제 조건** (CONFIRMED) | "grounded"를 "근거 확인됨"으로 표시 |
| 참고 제약 (INFERRED, 불가능 조건 아님) | 3-c + B 계약 유지 |
| 참고 제약 (INFERRED) | A + S-B |
| 참고 제약 (INFERRED) | B + 3-a/3-b |

## 5. 다음 단계

```text
HQ의 ④ 결정 (양식 7c6b92d5에 기입하거나 전달)
→ CUE가 조합 점검 (배제 조건에 걸리면 확정 전에 먼저 보고)
→ 결정 기록 확정·커밋
→ FU-007 번역 방식 결정
→ 새 ADR 작성 지시 → C1 Review → HQ 승인 → 구현 Task Order
```
