# WORK ORDER — Phase 9: Full Grounded Synthesis Integration Test

- 선행 게이트: P8 GREEN·HQ 승인
- 대상: C1
- 공통 규칙·STOP 조건: `docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md`

## 목표

처음으로 전체 파이프라인을 하나의 흐름으로 실행한다.

```
User Query → Query Set(호출자 제공) → 기존 Retrieval(QueryProcessor/HybridQueryProcessor,
변경 없이 호출) → RankedCandidate[] → Evidence Adapter → EvidencePool(P2/P3) →
AssemblyManifest(P3A) → SynthesisInput(P4) → Claim(P5) → GroundedAnswer(P6) →
CitationCheckResult(P7)
```

RetrievalEngine 자체는 재작성하지 않는다 — black-box authority로 호출만 한다.
이 Phase는 두 갈래로 나뉜다: (a) stub LLM 결정적 통합 테스트, (b) 실제 Ollama 모델
실행 결과 — 별도 섹션으로 분리 보고(GS-00 R8/B7).

## 허용 파일

- 신규: `scripts/grounded_synthesis_integration_demo.py` (실행 스크립트 — 호출자 자격으로
  QueryProcessor/HybridQueryProcessor/ollama 사용 허용, ADR-036 B9 예외)
- 신규: `tests/test_grounded_synthesis_integration.py` (stub LLM만, 네트워크 없음)
- 신규: `docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md` (실모델 실행 결과 기록)
- 무수정: 그 외 전체

## 설계

- `tests/test_grounded_synthesis_integration.py`: 실제 `QueryProcessor`를 인스턴스화하지 않고,
  P1~P8 각 Phase의 산출물을 손으로 만든 `RankedCandidate` 리스트로 연결해서
  전체 파이프라인이 오류 없이 `GroundedAnswer` + `CitationCheckResult[]`까지 도달하는지
  확인한다(순수 함수 합성 테스트, stub LLM).
- `scripts/grounded_synthesis_integration_demo.py`: 실제로 `QueryProcessor.process()` 또는
  `HybridQueryProcessor.process()`를 호출하고, 실제 Ollama(`DEFAULT_GEN_MODEL`)로
  Claim 추출을 수행하는 참조 구현. `python scripts/grounded_synthesis_integration_demo.py
  "<질의>"` 형태로 수동 실행 가능해야 한다. **이 스크립트는 pytest에서 실행되지 않는다**
  (GPU/모델 가용성에 의존하므로).
- `GS-P0_5_GOLD_QUERY_SET`(`docs/NAE_GOLD_QUERY_SET_P0_5_001.md`)에서 최소 3개 질의를
  뽑아 데모 스크립트로 실행하고, 결과를 `GS-P09-REAL-MODEL-RUN-RESULTS.md`에 원문
  그대로(프롬프트, 원 답변, GroundedAnswer.status, CitationCheckResult 요약) 기록한다.
  근거 0건이 정상 응답으로 이미 알려진 질의(G2 "존 스미스 3세" 등, 조작된 인물)를
  최소 1개 포함해서 insufficient_evidence 경로를 실측으로 확인한다.

## Acceptance Criteria

- AC1: stub 통합 테스트가 STOP 조건 없이 `GroundedAnswer.status`까지 도달(성공/부족
  양쪽 케이스 각 1개 이상)
- AC2: 데모 스크립트가 `core/retrieval.py`, `core/hybrid_candidate_pipeline.py`를
  수정 없이 그대로 import해서 사용함(diff 없음을 `git diff --stat`으로 증명)
- AC3: 실행 중 Qdrant/Tantivy/TSU 파일에 쓰기가 발생하지 않음 — 실행 전후
  `docs/grounded_synthesis/reviews/GS-SAFETY-BASELINE-CUE-20260927.json`의 해시와
  비교해서 동일함을 보고서에 기록(재계산 명령과 출력 포함)
- AC4: 최소 3개 질의의 실모델 실행 결과가 `GS-P09-REAL-MODEL-RUN-RESULTS.md`에
  기록되고, 그중 최소 1개는 근거 부족(insufficient_evidence) 경로
- AC5: 실모델 실행 결과가 자동 테스트 PASS 수치에 합산되지 않음(별도 파일, 별도 섹션)

## STOP 트리거

- 실행 중 위 해시가 변하면 즉시 실행을 멈추고 `STOP CONDITION TRIGGERED`(#10/#11/#12 해당)로 보고

## 보고

`GS-00-JOURNEY-INDEX.md` §7 양식 + AC3의 해시 비교 결과.
