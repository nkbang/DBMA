
# NAE Corpus Factory 전환 — 종합 보고서 (CUE Audit용)

- prepared_at: 2026-08-16T22:05:00Z
- prepared_by: C1 (Independent Forensic Auditor)
- baseline_source: PHASE0-VOL01-BASELINE.md
- 이 문서는 NAE Corpus Factory 전환의 종합 설계 보고서다.

---

## Executive Summary

**Mission**: Book-단위 순차 처리에서 Pipeline-단위 동시 처리로 전환

**Baseline**: Fuller Vol.1 (5452 candidates, 16.04h, 340/h, GPU ~99%)

**핵심 병목**:
1. GPU (llama-server -np 1, model 53GB 상주)
2. LLM inference time (candidate당 10.59s 중 ~95%+)
3. 단일 worker pipeline (동시 처리 불가)

**개선 기회**:
A. LLM 호출 전 deterministic filtering (33.2% is_claim=false 제거) → 처리시간 25-30% 감소
B. 독립 queue worker로 pipeline 분리 → 여러 source 동시 처리
C. GPU 병렬화 실험 (CUE 승인 후, §13)

---

## Phase별 설계 요약

### Phase 0: Vol.1 Baseline Capture (완료)

- captured_at: 2026-08-16T11:46:50Z
- 파일: PHASE0-VOL01-BASELINE.md
- Vol.1 Production Run 완료 상태 캡처 (5452 candidates 모두 처리)

### Phase 1: Bottleneck Analysis (완료)

- analyzed_at: 2026-08-16T21:30:00Z
- 파일: phase1-bottleneck-analysis/PHASE1-BOTTLENECK-ANALYSIS.md
- Vol.1 baseline evidence 기반 10개 질문 답변 완료

### Phase 2: Candidate Filtering 설계 (완료)

- designed_at: 2026-08-16T21:35:00Z
- 파일: phase2-candidate-filtering/PHASE2-CANDIDATE-FILTERING.md
- LLM 호출 전 deterministic preprocessing 설계
- 예상 효과: LLM 호출 33.2% 감소 → 처리시간 25-30% 감소

### Phase 3: TSU Extraction Pipeline 분리 (완료)

- designed_at: 2026-08-16T21:40:00Z
- 파일: phase3-pipeline-separation/PHASE3-PIPELINE-SEPARATION.md
- 독립 queue worker로 pipeline 분리 설계
- 여러 source가 파이프라인의 서로 다른 단계에서 동시에 전진

### Phase 4: Confidence-based Review (완료)

- designed_at: 2026-08-16T21:45:00Z
- 파일: phase4-confidence-review/PHASE4-CONFIDENCE-REVIEW.md
- confidence score 기반 review routing 설계
- HIGH/MEDIUM/LOW routing 로직

### Phase 5: Embedding & Promotion Gate (완료)

- designed_at: 2026-08-16T21:50:00Z
- 파일: phase5-embedding-promotion/PHASE5-EMBEDDING-PROMOTION.md
- TSU → Embedding → Qdrant → Promotion Gate 설계
- 기존 embedder.py, indexer.py와 연동

### Phase 6: Corpus Factory Orchestration (완료)

- designed_at: 2026-08-16T21:55:00Z
- 파일: phase6-orchestration/PHASE6-ORCHESTRATION.md
- 여러 source 동시 전진 orchestration 설계
- Dashboard 연계 확장

### Phase 7: Implementation Plan (완료)

- designed_at: 2026-08-16T22:00:00Z
- 파일: phase7-implementation/PHASE7-IMPLEMENTATION-PLAN.md
- 구현 우선순위 및 검증 계획
- CUE Audit 요청

---

## ADR-022 준수 확인

| 항목 | 준수 | 비고 |
|---|---|---|
| 자동 재시도 금지 | YES | exception_queue.json 수동 처리만 허용 |
| 자동 승격 금지 | YES | Human Review gate 통과 필수 |
| production boundary | YES | core/retrieval.py 등 무단 변경 없음 |
| NAE corpus isolation | YES | NAE/corpus/tsu/ 내에서만 작업 |
| TSU schema governance | YES | 기존 TSU schema 변경 없음 |

## Recall 손실 가능성 확인

| Phase | Recall 영향 | 검증 방법 |
|---|---|---|
| Phase 2: Normalization | 없음 | 공백/제어문자 제거만 |
| Phase 2: Duplicate detection | 낮음 | exact match만 (0.29% 미미) |
| Phase 2: Obvious filtering | 낮음 (가능성) | benchmark 필수 검증 |
| Phase 4: Confidence routing | 없음 | routing만, filtering 아님 |

## Governance violation 확인

- DBMA Core 무단 변경: 없음
- NAE corpus isolation 위반: 없음
- ADR 변경 미승인: 없음 (모든 설계는 CUE 승인 후 구현)
- production boundary 위반: 없음

---

## CUE Audit 요청 사항

1. **Phase 2 Candidate Filtering**: Recall 손실 가능성 있는 filtering이 없는지
2. **Phase 3 Pipeline 분리**: ADR-022 §8 준수 여부
3. **Phase 4 Confidence-based Review**: confidence ≠ theological truthiness 명확성
4. **Phase 5 Embedding & Promotion Gate**: Human Review gate 필수성
5. **Phase 6 Orchestration**: 여러 source 동시 전진 가능성
6. **전체 설계**: ADR-022 준수, production boundary 준수, governance violation 없음

**승인 후 Phase 7 구현 시작**.
