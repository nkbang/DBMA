# CUE Final Validation — Grounded Synthesis (템플릿, P12 보고 수신 시 채움)

- 대상 문서: `docs/grounded_synthesis/GS-FINAL-IMPLEMENTATION-REPORT.md`
- 절차: `docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md` §5 V0~V9 전체 재적용
  (P12는 별도가 아니라 전체 여정에 대한 마지막 V5 재실행 — P1부터의 테스트를
  전부 다시 돌린다)

## 7문항 최종 판정 (HQ 원문 §15, CUE가 C1 근거를 검증한 뒤 직접 판정)

| # | 질문 | C1 근거(요약) | CUE 검증 방법 | 판정 |
|---|---|---|---|---|
| 1 | Retrieval authority 유지 | | `core/retrieval.py` diff = 0 확인 | |
| 2 | Evidence boundary 유지 | | R6 grep 전체 재실행 | |
| 3 | Multi-query integrity | | P3A manifest 테스트 재실행 + CUE 자체 재현 | |
| 4 | Deduplication integrity | | P2 정책 회귀 테스트 재실행 | |
| 5 | Claim grounding 추적 가능 | | P7 CitationCheckResult 표본 수동 검증 | |
| 6 | Insufficient evidence 정상 표현 | | P8 6케이스 재실행 | |
| 7 | Existing system integrity | | P10 보고서 수치 재계산 | |

## CUE 최종 판정

- [ ] GREEN — HQ 최종 승인 상신
- [ ] HOLD — REWORK WO 필요(사유: )
- [ ] RED — STOP 조건 재발 또는 날조 발견(사유: )

## HQ 보고 (15줄 이내)

(여기 작성)
