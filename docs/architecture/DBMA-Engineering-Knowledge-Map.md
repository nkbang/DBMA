---
title: DBMA Engineering Knowledge Map
category: architecture
phase: Phase 5
related_files:
  - docs/ARCHITECTURE.md
  - docs/PIPELINE.md
  - output/engineering-history/phase-14/14_DBMA_Engineering_History.md
  - output/engineering-history/phase-02/02_Architecture_Evolution.md
status: completed
created: 2026-07-11
---

# DBMA Engineering Knowledge Map

**Generated:** 2026-07-11  
**Purpose:** Trace DBMA's evolution through all major architectural phases  
**Status:** COMPLETED

---

## Evolution Timeline

```
DBMA Evolution
═══════════════════════════════════════════════════════

Phase 0: Initial Prototype (pre-sprint 1)
├── Single-file dbma.py entry point
├── Basic RAG pipeline (extract → embed → store → retrieve)
├── No separation of concerns
└── All logic in monolithic module

Phase 1: Document Engine (sprint 1-3)
├── Extraction pipeline established
├── TSU dataset format defined
├── Chunking strategy implemented
└── Metadata schema v1 created

Phase 2: Library Engine (sprint 4-6)
├── Library interface separated from core
├── Collection management introduced
├── Search API layer added
└── Index persistence pattern established

Phase 3: StateStore (sprint 7-9)
├── State management extracted to ui/state/
├── Store pattern for UI state decoupling
├── Persistence layer abstracted
└── Query context tracking introduced

Phase 4: UI Separation (sprint 10-12)
├── ui/ directory structured (theme, components, state, pages)
├── Industrialization of UI design system
├── Dashboard / Library / Research / Processing pages separated
└── Entry point audit completed (ui/app.py ↔ dbma.py ↔ processing.py)

Phase 5: MIE Architecture (sprint 13-14)
├── Metadata Index Engine (MIE) concept formalized
├── Identity registry pattern (core/identity_registry.py)
├── Processing pipeline hardened with decision engine
├── Research query enhancements (book alias, Korean normalization)
└── Benchmark framework established

Phase 6: Production v1.0.0 (sprint 15+)
├── Retrieval validation complete
├── TSU dataset v4 stabilized
├── Gold standard alignment verified
├── Sprint 5 Engineering Validation corpus created
└── Release candidate v1.1.0 defined

═══════════════════════════════════════════════════════
```

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────┐
│                    UI Layer (ui/)                    │
│  dashboard | library | research | processing | monitor│
├─────────────────────────────────────────────────────┤
│                 Query Enhancement Layer              │
│  book_alias | korean_normalization | relevance       │
├─────────────────────────────────────────────────────┤
│                  Retrieval Engine (core/)            │
│  retrieval.py | search.py | query_enhancements.py    │
├─────────────────────────────────────────────────────┤
│                   Processing Pipeline                │
│  processing.py | ingest.py | chunking_optimizer.py   │
├─────────────────────────────────────────────────────┤
│                    Identity Layer                     │
│  document_identity.py | identity_registry.py         │
├─────────────────────────────────────────────────────┤
│                 Extraction & Embedding               │
│  extractors.py | embedder.py | text_splitter.py      │
├─────────────────────────────────────────────────────┤
│                   Storage Layer                      │
│  Qdrant vector DB | TSU dataset (JSONL)              │
└─────────────────────────────────────────────────────┘
```

---

## Key Transition Points

| From | To | Sprint | Driver |
|------|-----|--------|--------|
| Single-file → Document Engine | 1-3 | Extraction stability |
| Document Engine → Library Engine | 4-6 | Multi-document support |
| Library Engine → StateStore | 7-9 | UI state complexity |
| StateStore → UI Separation | 10-12 | Design system requirements |
| UI Separation → MIE Architecture | 13-14 | Research query quality |
| MIE → Production v1.0 | 15+ | Benchmark validation |

---

## Critical Files by Phase

### Phase 0: Prototype
- `dbma.py` — monolithic entry point

### Phase 1-2: Document/Library Engine
- `core/extractors.py` — document extraction
- `core/tsu/` — TSU dataset format
- `core/embedder.py` — embedding pipeline

### Phase 3: StateStore
- `ui/state/store.py` — state management pattern
- `ui/state/__init__.py` — state module interface

### Phase 4: UI Separation
- `ui/app.py` — main entry point
- `ui/pages/` — page modules
- `ui/theme/` — design system
- `ui/components/` — reusable components

### Phase 5: MIE Architecture
- `core/retrieval.py` — retrieval engine
- `core/query_enhancements.py` — query processing
- `core/document_identity.py` — identity management
- `core/identity_registry.py` — identity registry
- `core/processing.py` — processing pipeline

### Phase 6: Production v1.0
- `core/ingest.py` — ingestion pipeline
- `tests/gold_queries.json` — gold standard
- `output/SPRINT5_ENGINEERING_VALIDATION/` — validation corpus

---

## Engineering History References

| Document | Location | Category |
|----------|----------|----------|
| Architecture Evolution | `output/engineering-history/phase-02/02_Architecture_Evolution.md` | phase-02 |
| Engineering Decisions | `output/engineering-history/phase-04/04_Engineering_Decisions.md` | phase-04 |
| AI/Prompt Evolution | `output/engineering-history/phase-05/05_AI_Evolution.md` | phase-05 |
| UI/UX Evolution | `output/engineering-history/phase-06/06_UI_Evolution.md` | phase-06 |
| Data Evolution | `output/engineering-history/phase-07/07_Data_Evolution.md` | phase-07 |
| Refactoring History | `output/engineering-history/phase-08/08_Refactoring_History.md` | phase-08 |
| Technical Debt | `output/engineering-history/phase-09/09_Technical_Debt.md` | phase-09 |
| Feature History | `output/engineering-history/phase-10/10_Feature_History.md` | phase-10 |
| Documentation Audit | `output/engineering-history/phase-11/11_Documentation_Audit.md` | phase-11 |
| Engineering Metrics | `output/engineering-history/phase-12/12_Engineering_Metrics.md` | phase-12 |
| Risk Assessment | `output/engineering-history/phase-13/13_Risk_Assessment.md` | phase-13 |
| Master History | `output/engineering-history/phase-14/14_DBMA_Engineering_History.md` | phase-14 |

---

**Map Status:** COMPLETED  
**Next Reference:** Engineering history Phase 14 for complete timeline details