
# Phase 3 — TSU Extraction Pipeline 분리

- designed_at: 2026-08-16T21:40:00Z
- baseline_source: PHASE0-VOL01-BASELINE.md, PHASE1-BOTTLENECK-ANALYSIS.md
- 이 문서는 독립 queue worker로 pipeline을 분리하는 설계다.

## 현재 아키텍처 (단일 worker)

```
[READY] → [PROCESSING] → [EXTRACTED] → [CONFIDENCE_CLASSIFIED]
   ↑          ↓              ↓                ↓
   └──── process_batch() ────┴────────────────┘
         (sequential, single process)
```

**문제점**:
- 단일 worker가 모든 단계를 순차 처리
- 한 source가 TSU Extraction에 있으면 다른 source는 대기
- 한 source 실패 시 전체 batch 중단 가능성

## 목표 아키텍처 (독립 queue worker)

```
[READY] → [PROCESSING] → [EXTRACTED] → [CONFIDENCE_CLASSIFIED]
   ↑          ↓              ↓                ↓
   │          │              │                │
   ▼          ▼              ▼                ▼
TSU_QUEUE  ERROR_QUEUE  REVIEW_QUEUE  PROMOTION_QUEUE

Vol.1: TSU Extraction 진행 중    Vol.2: READY 대기
Vol.3: Candidate Filtering       Vol.4: Embedding
```

**핵심**: 여러 source가 파이프라인의 서로 다른 단계에서 동시에 전진

## Queue 정의

### 1. TSU_EXTRACTION_QUEUE (기존 worker.py 기반)

```
READY → PROCESSING → EXTRACTED → CONFIDENCE_CLASSIFIED
실패: PROCESSING → FAILED → ERROR_QUEUE
```

**현재 구현**: `NAE/pipeline/tsu/worker/worker.py::process_batch()`
**개선점**: 
- batch 처리 대신 single-candidate processing으로 변경
- 각 candidate 독립 실패 격리 (이미 구현됨 — ADR-022 §6)

### 2. ERROR_QUEUE (기존 TSUExtractionExceptionQueue 기반)

```
FAILED → [Human Review] → READY (retry) or DISCARDED
```

**현재 구현**: `NAE/pipeline/tsu/worker/queue.py::TSUExtractionExceptionQueue`
**ADR-022 §8 준수**: 자동 재시도/자동 승격 금지

### 3. REVIEW_QUEUE (신규 설계)

```
CONFIDENCE_CLASSIFIED → [Confidence-based Routing]
    HIGH → 자동 후속 처리 (Embedding Queue로 이동)
    MEDIUM → Sampling / Targeted Review
    LOW → Human Review
```

**설계 필요**: Phase 4에서 상세 설계

### 4. PROMOTION_QUEUE (신규 설계)

```
[Human Review] → [Promotion Gate] → Embedding Queue
```

**설계 필요**: Phase 5에서 상세 설계

## 구현 우선순위

1. **TSU_EXTRACTION_QUEUE 개선** (기존 worker.py single-candidate processing)
   - batch 처리 → single-candidate processing으로 변경
   - 각 candidate 독립 실패 격리 확인

2. **ERROR_QUEUE 검증** (기존 TSUExtractionExceptionQueue)
   - ADR-022 §8 준수 확인
   - manual retry만 허용

3. **REVIEW_QUEUE 설계** (Phase 4에서 구현)
   - confidence-based routing 로직
   - Human Review gate

4. **PROMOTION_QUEUE 설계** (Phase 5에서 구현)
   - promotion gate 로직
   - embedding queue로 이동

## 병렬화 정책 (§13 준수)

Vol.1 baseline (`llama-server -np 1`, GPU ~99%)을 기준으로 삼는다.

**단순히 1→2→4 worker로 바꾸지 않는다.** 아래를 전부 만족할 때만 concurrency 실험을 "제안"한다:

```
✅ Vol.1 Production 완료
✅ 현재 모델 unload/reload 가능한 시점
✅ 메모리 headroom 확인됨
✅ GPU thermal/power 상태 확인 가능
✅ baseline throughput 확보됨(Phase 0)
✅ production interruption 없이 실험 가능
✅ rollback 가능
```

## 다음 단계

Phase 3 설계 완료 → CUE audit → Phase 4 (Confidence-based Review)
