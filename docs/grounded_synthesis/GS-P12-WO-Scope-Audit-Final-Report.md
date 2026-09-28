# WORK ORDER — Phase 12: Scope / Architecture Audit + Final Implementation Report

- 선행 게이트: P11 GREEN·HQ 승인
- 대상: C1
- 공통 규칙·STOP 조건: `docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md`
- 이 Phase가 여정의 마지막 C1 산출물이다. C1은 여기서도 최종 GREEN을 선언하지 않는다.

## 목표

1. HQ 원문 §13의 7개 질문에 C1이 근거와 함께 답한다(판정은 CUE·HQ 몫).
2. HQ 원문 §18 양식의 최종 구현 보고서를 작성한다.

## 허용 파일

- 신규: `docs/grounded_synthesis/GS-FINAL-IMPLEMENTATION-REPORT.md`
- 코드 변경 없음

## §13 질문 — C1이 근거(파일:줄, 테스트명, 커밋)와 함께 답할 것

1. Retrieval authority: 기존 RetrievalEngine이 계속 유일한 retrieval authority인가?
2. Evidence boundary: LLM이 EvidencePool을 넘어 사실을 생성할 수 있는 구조가 없는가?
3. Multi-query integrity: 여러 질의의 evidence가 하나의 pool로 조립되면서 provenance가 손상되지 않는가? (P3A manifest 근거로 답할 것)
4. Deduplication integrity: 동일 Evidence가 여러 질의에서 발견될 때 P2 정책이 유지되는가?
5. Claim grounding: 최종 factual claim을 Evidence까지 추적할 수 있는가? (P7 CitationCheckResult 근거)
6. Insufficient evidence: 근거가 부족할 때 시스템이 추측하지 않고 부족함을 표현하는가? (P6/P8 근거)
7. Existing system integrity: Grounded Synthesis 추가로 기존 retrieval 결과·인프라가 손상되지 않았는가? (P10 근거)

## 최종 보고서 양식 (HQ 원문 §18 그대로, 필드 보강)

```
GROUNDED SYNTHESIS — FINAL IMPLEMENTATION REPORT

1. Phase History           (P1~P12 각각: 커밋 해시, CUE 판정, HQ 승인일)
2. Final Architecture      (전체 파이프라인 다이어그램 — 텍스트 화살표로)
3. Retrieval Boundary      (§13-Q1 답)
4. Evidence Boundary       (§13-Q2 답)
5. Multi-Query Assembly    (§13-Q3, Q4 답)
6. Grounded Synthesis      (synthesis input / claim generation / evidence binding 요약)
7. Citation / Provenance   (§13-Q5 답)
8. Failure Handling        (P8 6개 케이스 결과 요약)
9. Regression              (P10 보고서 링크 + 핵심 수치)
10. Production Safety      (P11 보고서 링크 + 핵심 수치)
11. Scope Integrity        (전체 여정 동안 변경된 파일 전체 목록, 승인 범위 밖 변경 0건 확인)
12. Remaining Limitations  (숨긴 가정 없이 전부 — 특히 D2 미통합 상태, 자동 충돌 탐지 부재,
                            span 일치 판정 기준의 한계 등 각 WO에서 이미 기록된 것 총정리)
13. Evidence Summary       (Phase별 테스트 수, 커밋 해시, 실모델 실행 결과 링크)
14. Recommendation         → 반드시: "CUE READ-ONLY FINAL VALIDATION REQUESTED"
```

## Acceptance Criteria

- AC1: §13 질문 7개 전부에 파일:줄 또는 테스트명 근거가 붙어 있음(추상적 서술 금지)
- AC2: "Scope Integrity" 섹션이 P1 시작 커밋부터 현재까지 `git log --oneline`
  전체와 `git diff --stat` 전체를 원문으로 포함
- AC3: 마지막 줄이 정확히 `CUE READ-ONLY FINAL VALIDATION REQUESTED`이고
  GREEN/APPROVED 등 판정 용어가 문서 어디에도 없음

## 보고

`docs/grounded_synthesis/GS-FINAL-IMPLEMENTATION-REPORT.md` 완성 후 CUE에게 전달.
