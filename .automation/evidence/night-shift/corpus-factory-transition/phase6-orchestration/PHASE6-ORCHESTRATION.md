
# Phase 6 — Corpus Factory Orchestration

- designed_at: 2026-08-16T21:55:00Z
- baseline_source: PHASE0-VOL01-BASELINE.md, PHASE1-BOTTLENECK-ANALYSIS.md
- 이 문서는 여러 source가 파이프라인의 서로 다른 단계에서 동시에 전진하는 orchestration 설계다.

## 목표 형태

```
Vol.1 → Review → Embedding
Vol.2 → TSU
Vol.3 → Candidate Filtering
...
```

**핵심**: 각 source가 파이프라인의 서로 다른 단계에서 동시 전진 가능

## Orchestration Architecture

### Source Registry

```python
# NAE/corpus/source_registry.json
{
    "Fuller_Complete_Works_Vol01": {
        "status": "embedding",
        "stage": "embedding_queue",
        "progress": 0.75,
        "started_at": "2026-08-16T10:00:00Z",
        "completed_at": null
    },
    "Fuller_Complete_Works_Vol02": {
        "status": "tsu_extraction",
        "stage": "ready",
        "progress": 0.0,
        "started_at": null,
        "completed_at": null
    },
    "Fuller_Complete_Works_Vol03": {
        "status": "candidate_filtering",
        "stage": "ready",
        "progress": 0.0,
        "started_at": null,
        "completed_at": null
    }
}
```

### Pipeline Stage Definitions

```python
# NAE/pipeline/tsu/orchestrator.py

PIPELINE_STAGES = [
    "registration",       # RAW → Registration
    "quality_ocr",        # Quality/OCR
    "candidate_filtering",# Candidate Filtering
    "tsu_extraction",     # TSU Extraction
    "confidence_classification",  # Confidence Classification
    "review_queue",       # Review Queue
    "promotion_gate",     # Promotion Gate
    "embedding",          # Embedding
    "qdrant_indexing",    # Qdrant Indexing
    "retrieval_validation",   # Retrieval Validation
]
```

### Orchestrator 로직

```python
class CorpusFactoryOrchestrator:
    """여러 source의 pipeline 동시 전진 orchestration."""
    
    def __init__(self):
        self.source_registry = SourceRegistry()
        self.stage_queues = {stage: Queue() for stage in PIPELINE_STAGES}
    
    def enqueue_source(self, source_id: str, start_stage: str = "registration"):
        """source를 특정 stage에서 시작."""
        self.source_registry.register(source_id, start_stage)
        self.stage_queues[start_stage].enqueue(source_id)
    
    def process_next_stage(self, source_id: str, current_stage: str) -> str:
        """source의 다음 stage로 전진. 완료 시 'completed' 반환."""
        stage_index = PIPELINE_STAGES.index(current_stage)
        next_stage = PIPELINE_STAGES[stage_index + 1] if stage_index + 1 < len(PIPELINE_STAGES) else None
        
        if next_stage is None:
            self.source_registry.complete(source_id)
            return "completed"
        
        # 다음 stage로 이동
        self.stage_queues[current_stage].dequeue(source_id)
        self.stage_queues[next_stage].enqueue(source_id)
        self.source_registry.update_stage(source_id, next_stage)
        
        return next_stage
    
    def get_factory_status(self) -> dict:
        """현재 factory 상태 반환."""
        status = {}
        for source_id, info in self.source_registry.items():
            status[source_id] = {
                "status": info["status"],
                "stage": info["stage"],
                "progress": info["progress"],
                "queue_depth": {stage: len(queue) for stage, queue in self.stage_queues.items()},
            }
        return status
```

## Dashboard 연계 (§18)

### 기존 Dashboard 확장

```
NAE Live Progress Dashboard (.automation/night-shift/dashboard/)
    → Corpus Factory 상태 표시 추가:
        - 현재 source
        - 각 pipeline stage
        - queue depth
        - processing rate
        - completed/failed/review pending/promotion pending/embedding pending/Qdrant indexed/retrieval validated
        - GPU/CPU/memory/disk/process health
```

### Dashboard Schema 확장

```python
# .automation/night-shift/dashboard/schema.py

CORPUS_FACTORY_SCHEMA = {
    "factory_status": {
        "total_sources": int,
        "completed": int,
        "processing": int,
        "failed": int,
        "pending": int,
    },
    "source_details": [
        {
            "source_id": str,
            "status": str,  # completed/processing/failed/pending
            "stage": str,   # pipeline stage name
            "progress": float,  # 0.0-1.0
            "queue_depth": dict,  # stage -> depth
        }
    ],
    "pipeline_stages": {
        stage_name: {
            "depth": int,
            "processing_rate": float,  # candidates/hour
            "avg_latency": float,  # seconds/candidate
        }
    },
    "system_health": {
        "gpu_utilization": float,  # 0.0-1.0
        "cpu_utilization": float,  # 0.0-1.0
        "memory_usage": float,  # GB
        "disk_usage": float,  # GB
        "process_health": dict,  # process_name -> status
    },
}
```

## 구현 우선순위

1. **Source Registry 설계** (신규)
   - source_registry.json 설계
   - register/update/complete/completed_at 로직

2. **Orchestrator 설계** (신규)
   - pipeline stage 정의
   - enqueue/dequeue 로직
   - factory status 조회

3. **Dashboard 확장** (기존 dashboard 확장)
   - Corpus Factory 상태 표시
   - queue depth, processing rate 표시
   - system health 표시

4. **Production Run orchestration** (신규)
   - Vol.2, Vol.3 등 여러 source 동시 처리
   - failure isolation (한 source 실패 시 전체 중단 없음)

## 다음 단계

Phase 6 설계 완료 → CUE audit → Phase 7 (Implementation)
