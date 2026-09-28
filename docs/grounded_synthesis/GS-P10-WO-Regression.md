# WORK ORDER — Phase 10: Regression / Architecture Integrity Audit

- 선행 게이트: P9 GREEN·HQ 승인
- 대상: C1
- 공통 규칙·STOP 조건: `docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md`
- 새 기능을 만들지 않는다 — 감사만 한다

## 목표

Grounded Synthesis(P1~P9) 추가로 기존 DBMA/NAE retrieval architecture가
변하지 않았음을 확인한다.

## 허용 파일

- 신규: `docs/grounded_synthesis/GS-P10-REGRESSION-REPORT.md`
- 코드 변경 없음(이 Phase는 파일 하나만 생성한다)

## 절차

1. **G0 격리 확인**: `git -C /Users/David/DBMA status --porcelain`으로 P3~P9 전체
   변경분이 G0(staged 6건)과 섞이지 않았는지 확인. `git diff --stat <P1 시작 커밋>..HEAD`가
   Grounded Synthesis 파일(core/evidence_*.py, core/grounded_*.py, tests/test_evidence_*.py,
   tests/test_grounded_*.py, scripts/grounded_synthesis_*.py, docs/grounded_synthesis/*,
   docs/architecture/ADR-036*)로만 구성되어 있는지 확인.
2. **전수 회귀**: `~/envs/dbma311/bin/python -m pytest tests/ -q --deselect
   <GPU/네트워크 의존 테스트가 있다면 여기 나열>` 전체 실행. 실패가 있으면
   Grounded Synthesis 도입 전(HEAD~N, P1 시작 전 커밋)에서도 실패하는지 대조해서
   "기존 결함"과 "이번에 생긴 회귀"를 분리한다.
3. **retrieval 출력 동일성**: `docs/NAE_GOLD_QUERY_SET_P0_5_001.md`의 질의 중 5개를
   골라 `QueryProcessor.process()`를 P1 시작 커밋 기준과 현재 HEAD 기준 양쪽에서
   실행하고 `top_k_results`의 `tsu_id` 순서·개수·`final_score`가 동일한지 비교한다.
   (주의: `origin/main`은 P1 이후 retrieval 로직이 8커밋 앞서 있다 — 비교 기준은
   반드시 `feat/peb-v0.1`의 P1 시작 직전 커밋으로 고정한다. main 동기화로 인한
   차이는 이 비교에 섞이지 않는다.)
4. **아키텍처 대상 목록 확인**(HQ 원문 §10): TSU / Qdrant / Tantivy / RetrievalEngine /
   HybridRetriever / CandidateGenerator / Evidence Model / EvidencePool 각각에 대해
   "Grounded Synthesis가 이 컴포넌트의 코드를 수정했는가"를 grep(`git log --oneline
   -- <path>`)으로 확인하고 표로 정리한다.

## Acceptance Criteria

- AC1: G0 변경과 GS 변경이 커밋 경계로 명확히 분리되어 있음(커밋 목록으로 증명)
- AC2: 전수 회귀 실행 결과, GS 도입으로 새로 생긴 실패가 0건(기존 결함과 신규 회귀를
  구분한 표 포함)
- AC3: 5개 질의의 retrieval 출력이 P1 시작 전/현재 HEAD 사이에서 동일
  (다르면 원인이 main 동기화인지 GS 코드인지 diff로 특정)
- AC4: §10 대상 8개 컴포넌트 전부 "수정 없음"으로 확인(하나라도 수정 이력이 있으면
  그 커밋 해시와 diff를 보고서에 명시하고 즉시 STOP)

## 보고

`docs/grounded_synthesis/GS-P10-REGRESSION-REPORT.md`로 직접 작성(별도 Work Order
Report 양식 대신 이 파일 자체가 산출물). 마지막 줄은 여전히
`HOLD` / `CUE READ-ONLY REVALIDATION REQUESTED` / `STOP CONDITION TRIGGERED` 중 하나.
