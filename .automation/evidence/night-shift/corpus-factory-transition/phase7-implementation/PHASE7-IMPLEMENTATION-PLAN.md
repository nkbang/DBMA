
# Phase 7 — Implementation Plan

- designed_at: 2026-08-16T22:00:00Z
- baseline_source: PHASE0-VOL01-BASELINE.md, PHASE1-BOTTLENECK-ANALYSIS.md
- 이 문서는 Phases 1-6 설계의 구현 계획이다.

## 구현 우선순위

### Priority 1: Phase 2 — Candidate Filtering (가장 큰 효과)

**예상 효과**: LLM 호출 33.2% 감소 → 처리시간 25-30% 감소

**구현 파일**:
```
NAE/pipeline/tsu/filtering/
    ├── __init__.py
    ├── normalizer.py      (Normalization)
    ├── duplicate_detector.py (Duplicate detection)
    ├── theological_filter.py (Obvious non-theological filtering)
    └── classifier.py      (Candidate classification)
```

**구현 단계**:
1. Normalization 구현 (Recall 영향 없음 — 우선 구현)
2. Duplicate detection 구현 (미미한 효과 — 후순위)
3. Obvious non-theological filtering 구현 (Recall 검증 필수 — 중순위)
4. Candidate classification 구현 (LLM 호출 전 예측 — 고순위)

**검증 계획**:
- Vol.1에서 deterministic filtering 적용 후 is_claim 결과 비교
- Recall 검증: filtering으로 제거된 candidate 중 신학적 claim이 없는지 확인
- Precision 검증: LLM 호출 전 제거된 candidate가 실제로 non-theological인지 확인

### Priority 2: Phase 3 — TSU Extraction Pipeline 분리

**예상 효과**: 여러 source 동시 처리 가능 → throughput 증가

**구현 파일**:
```
NAE/pipeline/tsu/worker/
    ├── queue_worker.py    (독립 queue worker)
    └── config.py          (worker config)
```

**구현 단계**:
1. batch 처리 → single-candidate processing으로 변경
2. 각 candidate 독립 실패 격리 확인
3. ERROR_QUEUE 검증 (ADR-022 §8 준수)

### Priority 3: Phase 4 — Confidence-based Review

**예상 효과**: Human Review 효율화 → human 시간 절약

**구현 파일**:
```
NAE/pipeline/tsu/review/
    ├── __init__.py
    ├── routing.py         (confidence-based routing)
    └── gate.py            (Human Review gate)
```

**구현 단계**:
1. confidence classification 검증 (기존 worker.py::_classify_confidence())
2. review routing 로직 설계 (신규)
3. Human Review gate 구현 (신규)

### Priority 4: Phase 5 — Embedding & Promotion Gate

**예상 효과**: TSU → Embedding → Qdrant 자동화 → retrieval 가능

**구현 파일**:
```
NAE/pipeline/tsu/embedder/
    ├── __init__.py
    ├── queue.py           (EmbeddingQueue)
    ├── worker.py          (embed_candidate())
    └── config.py          (embedding config)

NAE/pipeline/tsu/promotion/
    ├── __init__.py
    ├── gate.py            (Promotion Gate)
    └── validation.py      (Retrieval Validation)
```

**구현 단계**:
1. Embedding Queue 설계 (신규)
2. Promotion Gate 설계 (신규)
3. Retrieval Validation 설계 (신규)

### Priority 5: Phase 6 — Corpus Factory Orchestration

**예상 효과**: 여러 source 동시 처리 → factory 형태 완성

**구현 파일**:
```
NAE/pipeline/tsu/orchestrator/
    ├── __init__.py
    ├── registry.py        (Source Registry)
    ├── orchestrator.py    (CorpusFactoryOrchestrator)
    └── config.py          (orchestrator config)
```

**구현 단계**:
1. Source Registry 설계 (신규)
2. Orchestrator 설계 (신규)
3. Dashboard 확장 (기존 dashboard 확장)

## CUE Audit 요청

모든 Phase 설계 완료. CUE의 독립 검증을 요청한다.

**검증 항목**:
1. 각 Phase 설계가 ADR-022를 준수하는지
2. Recall 손실 가능성이 없는지
3. Production boundary 위반이 없는지
4. Governance violation이 없는지

**승인 후 구현 시작**.
