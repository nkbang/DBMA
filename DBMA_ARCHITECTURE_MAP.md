Human HQ
                       |
                       |
                  Governance Layer
                       |
           +-----------+-----------+
           |                       |
          C1 (Planner)          CUE (Executor)
    Planning Brain         Execution Agent
           |                       |
           +-----------+-----------+
                       |
                  DBMA Core
                       |
    =========================================================

## Core Pipeline (Production Engineering Phase)

```
Source Documents (PDF/TXT/MD/DOCX/EPUB/HTML)
       |
       v
  [Extraction]  core/extractors.py
       |
       v
  [Normalization]  core/text_normalizer.py
       |
       v
  [Chunking]  core/chunking_optimizer.py (optimize_chunks) — PRODUCTION
       |
       |  ※ core/hierarchical_chunk_builder.py(Boundary Score/D5 Metrics
       |    포함)는 ADR-008 D-5 게이트 통과했으나 DORMANT — HQ 승인
       |    대기 중이며 core/processing.py가 아직 호출하지 않음
       v
  [TSU Dataset]  (in-memory, Qdrant/Chroma: legacy-only ADR-003)
       |
       v
  [Metadata Layer]  core/identity_registry.py + heading_constants.py
       |
       v
  [Gold Standard]  tests/gold_queries.json + scripts/*_gold_standard.py
       |
       v
  [RetrievalEngine + Ranking]  core/retrieval.py::retrieve()
       |         final_score = base_score * evidence_confidence *
       |         content_quality_factor (core/retrieval.py:1605 —
       |         별도 core/ranking/ 모듈은 존재하지 않음)
       |         Research Workspace (ADR-004~008)
       |         nDCG/MRR/Precision@K/Recall@K는 scripts/rag_benchmark.py의
       |         오프라인 평가 지표, 실시간 랭킹 입력 아님
       v
  [Benchmark]  scripts/rag_benchmark.py + scripts/run_*_benchmark.py
       |
       v
  [Output]  docs/ + output/ + sermon_corpus/
```

## UI Architecture (Streamlit)

```
dbma_ui.py (entry point)
    |
    +-- ui/tabs.py (tab routing)
    |       |
    |       +-- Processing Tab  (document upload, extraction, chunking)
    |       +-- Search Tab      (retrieval results with clickable source links)
    |       +-- Chat Tab        (RAG conversation with citation badges)
    |       +-- Library Tab     (document detail view with pending source nav)
    |       +-- Research Tab    (research workspace)
    |       +-- Dashboard Tab   (system overview)
    |       +-- Monitor Tab     (system health/performance)
    |       +-- Sermon Draft Tab   (설교문 작성)
    |       +-- Sermon Review Tab  (설교 리뷰)
    |
    +-- ui/components/
    |       +-- source_link.py   (clickable source navigation)
    |       +-- tables.py        (search results table with clickable_source)
    |       +-- sidebar.py       (sidebar navigation)
    |       +-- styles.py        (UI styling)
    |
    +-- ui/pages/
            +-- chat.py          (RAG conversation page)
            +-- research.py      (research workspace page)
            +-- library.py       (document detail page)
            +-- dashboard.py     (system overview page)
            +-- monitor.py       (system health/performance page)
            +-- processing.py    (document ingestion page)
            +-- sermon_draft.py  (설교문 작성 page)
            +-- sermon_review.py (설교 리뷰 page)
```

## Key Components (ADR-004~008 additions)

| Component | File | Purpose |
|-----------|------|---------|
| Research Workspace | `core/research_workspace.py` | Document research context management |
| Hierarchical Chunk Builder | `core/hierarchical_chunk_builder.py` | Multi-level chunking with boundary detection — **DORMANT**, D-5 게이트 통과했으나 HQ 승인 대기, 프로덕션 미사용 |
| Boundary Score Model | `core/semantic_boundary_detector.py` | Semantic boundary scoring (ADR-006) — Hierarchical Chunk Builder 내부에서만 사용, retrieval 경로와 무관 |
| Identity Registry | `core/identity_registry.py` | Document identity and canonical metadata |
| Heading Constants | `core/heading_constants.py` | Bible book/chapter/verse aliases |
| Canonical Constants | `core/canonical_constants.py` | System-wide constant definitions |
| Runtime State | `core/runtime_state.py` | Dynamic pipeline state management |

## Data Flow Summary

```
User Input (UI)
    ↓
Query Enhancement (core/query_enhancements.py)
    ↓
Research Workspace Lookup (core/research_workspace.py)
    ↓
Retrieval (core/retrieval.py) — TSU 데이터셋은 ingestion 시점에
core/chunking_optimizer.py로 이미 청킹 완료된 상태를 조회함
(core/hierarchical_chunk_builder.py는 core/retrieval.py가 import하지
않는 DORMANT 후보 — 검색 경로와 무관)
    ↓
Ranking (core/retrieval.py::retrieve() 내부 final_score 계산 —
Boundary Score/D5 Metrics는 여기 관여하지 않음, dormant 경로 전용)
    ↓
Citation Rendering (ui/components/source_link.py)
    ↓
LLM Response Generation
    ↓
Result Display (Chat/Search UI with clickable source links)
```

## Sprint Status Reference

Current Phase: Production Engineering / Release Stabilization  
Latest Sprint: SPRINT33  
Release: v1.3.0 (tag 07ec084)  
Status: v1.3.0 RC READY  
Last synced: 2026-07-27  
For detailed state: see [`docs/STATE.md`](docs/STATE.md)
