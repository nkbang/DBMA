---
title: DBMA Documentation Index
category: documentation
phase: Phase 4
status: completed
created: 2026-07-11
---

# DBMA Documentation Index

**Generated:** 2026-07-11  
**Purpose:** Master index of all DBMA documentation  
**Status:** COMPLETED

---

## Quick Start

1. [README.md](./README.md) — Documentation overview and navigation guide
2. [ARCHITECTURE.md](./ARCHITECTURE.md) — System architecture
3. [PIPELINE.md](./PIPELINE.md) — Processing pipeline flow
4. [STATE.md](./STATE.md) — Current project state
5. This file (INDEX.md) — Full document inventory

---

## Core Documentation

| Document | Location | Category | Purpose |
|----------|----------|----------|---------|
| ARCHITECTURE.md | [docs/ARCHITECTURE.md](./ARCHITECTURE.md) | architecture | System architecture overview |
| PIPELINE.md | [docs/PIPELINE.md](./PIPELINE.md) | pipeline | Processing pipeline flow |
| STATE.md | [docs/STATE.md](./STATE.md) | state | Current project state and progress |
| TODO.md | [docs/TODO.md](./TODO.md) | planning | Task list and priorities |
| CHANGELOG.md | [docs/CHANGELOG.md](./CHANGELOG.md) | history | Project change log |
| DBMA_MAP.md | [docs/DBMA_MAP.md](./DBMA_MAP.md) | architecture | Module connection map |
| METADATA_CONTRACT_v1.md | [docs/METADATA_CONTRACT_v1.md](./METADATA_CONTRACT_v1.md) | specification | Metadata v1 contract |
| UI_GUIDE.md | [docs/UI_GUIDE.md](./UI_GUIDE.md) | ui | User interface guide |
| RELEASE_NOTES_v1.1.0.md | [docs/RELEASE_NOTES_v1.1.0.md](./RELEASE_NOTES_v1.1.0.md) | release | Release v1.1.0 notes |

---

## Architecture Documents

| Document | Location | Category | Sprint |
|----------|----------|----------|--------|
| [DBMA Engineering Knowledge Map](./architecture/DBMA-Engineering-Knowledge-Map.md) | docs/architecture/ | architecture | All phases |

---

## Sprint History

| Sprint | Location | Status |
|--------|----------|--------|
| Sprint 5 Engineering Validation | [output/SPRINT5_ENGINEERING_VALIDATION/](../output/SPRINT5_ENGINEERING_VALIDATION/) | Complete |
| Sprint 10-12 Execution Plans | output/SPRINT5_ENGINEERING_VALIDATION/SPRINT10_*.md | Complete |
| Sprint 13-15 Validation | [output/bench/](../output/bench/) | Complete |

---

## Engineering History (Archived)

All engineering audit documents are archived in `output/engineering-history/` with phase-based organization.

### Phase Documents

| Phase | Document | Path |
|-------|----------|------|
| 00 | Project Census | [phase-00/](../output/engineering-history/phase-00/) |
| 02 | Architecture Evolution | [phase-02/](../output/engineering-history/phase-02/) |
| 04 | Engineering Decisions | [phase-04/](../output/engineering-history/phase-04/) |
| 05 | AI/Prompt Evolution | [phase-05/](../output/engineering-history/phase-05/) |
| 06 | UI/UX Evolution | [phase-06/](../output/engineering-history/phase-06/) |
| 07 | Data/Storage Evolution | [phase-07/](../output/engineering-history/phase-07/) |
| 08 | Refactoring History | [phase-08/](../output/engineering-history/phase-08/) |
| 09 | Technical Debt | [phase-09/](../output/engineering-history/phase-09/) |
| 10 | Feature History | [phase-10/](../output/engineering-history/phase-10/) |
| 11 | Documentation Audit | [phase-11/](../output/engineering-history/phase-11/) |
| 12 | Engineering Metrics | [phase-12/](../output/engineering-history/phase-12/) |
| 13 | Risk Assessment | [phase-13/](../output/engineering-history/phase-13/) |
| 14 | Master History | [phase-14/](../output/engineering-history/phase-14/) |

### Engineering History Index

- README: [output/engineering-history/README.md](../output/engineering-history/README.md)
- INDEX: [output/engineering-history/INDEX.md](../output/engineering-history/INDEX.md)
- Migration Report: [output/engineering-history/Engineering_History_Migration_Report.md](../output/engineering-history/Engineering_History_Migration_Report.md)

---

## Validation & Benchmark Reports

### Processing Validation (PT_PROCESSING_*)

| Series | Count | Category |
|--------|-------|----------|
| PT_PROCESSING_001-013 | ~80 docs | Processing pipeline validation |

Located in: [output/PT_PROCESSING_*.md](../output/)

### Research Validation (PT_RESEARCH_*)

| Series | Count | Category |
|--------|-------|----------|
| PT_RESEARCH_001-007 | ~50 docs | Research engine validation |

Located in: [output/PT_RESEARCH_*.md](../output/)

### Metadata Validation (PT_METADATA_*)

| Series | Count | Category |
|--------|-------|----------|
| PT_METADATA_000-002 | ~20 docs | Metadata integrity validation |

Located in: [output/PT_METADATA_*.md](../output/)

### Corpus Analysis (PT_CORPUS_*)

| Series | Count | Category |
|--------|-------|----------|
| PT_CORPUS_001 | ~8 docs | Corpus inventory and coverage |

Located in: [output/PT_CORPUS_*.md](../output/)

### Evaluation Reports (PT_EVALUATION_*)

| Series | Count | Category |
|--------|-------|----------|
| PT_EVALUATION_001-002 | ~20 docs | Benchmark evaluation metrics |

Located in: [output/PT_EVALUATION_*.md](../output/)

### Human Review (PT_HUMAN_*)

| Series | Count | Category |
|--------|-------|----------|
| PT_HUMAN_009-011 | ~15 docs | Human review decisions |

Located in: [output/PT_HUMAN_*.md](../output/)

### Search Validation (PT_SEARCH_*)

| Series | Count | Category |
|--------|-------|----------|
| PT_SEARCH_* | ~6 docs | Search system validation |

Located in: [output/PT_SEARCH_*.md](../output/)

---

## Release & Feature Documentation

| Document | Location | Phase |
|----------|----------|-------|
| DBMA v1.1.0 Release Candidate | [output/DBMA_v1.1.0_RELEASE_CANDIDATE_REPORT.md](../output/) | Release |
| Release Freeze Review | [output/RELEASE_FREEZE_REVIEW_v1.1.0.md](../output/) | Release |
| FAT Plan v1.1.0 | [output/FAT_PLAN_v1.1.0.md](../output/) | Feature |
| FAT Readiness Report | [output/FAT_READINESS_REPORT_v1.1.0.md](../output/) | Feature |
| FAT Human Summary | [output/FAT-HUMAN-SUMMARY_V1.1.0.md](../output/) | Feature |

---

## Documentation Management

### Audit Reports

| Document | Location | Phase |
|----------|----------|-------|
| Documentation Audit Report | [docs/reports/documentation-audit-report.md](./reports/documentation-audit-report.md) | Phase 1 |

### Documentation Rules

| Rule File | Location | Purpose |
|-----------|----------|---------|
| DBMA Engineering Rules | [.clinerules/dbma-engineering.md](../.clinerules/dbma-engineering.md) | Sprint control, validation rules |

---

## Document Categories Reference

```
docs/
├── README.md                    ← Documentation overview (START HERE)
├── INDEX.md                     ← This file (master index)
├── ARCHITECTURE.md              ← System architecture
├── PIPELINE.md                  ← Processing pipeline
├── STATE.md                     ← Current project state
├── TODO.md                      ← Task list
├── CHANGELOG.md                 ← Change log
├── DBMA_MAP.md                  ← Module connection map
├── METADATA_CONTRACT_v1.md      ← Metadata specification
├── UI_GUIDE.md                  ← UI guide
├── RELEASE_NOTES_v1.1.0.md      ← Release notes
├── architecture/                ← Architecture documents
│   └── DBMA-Engineering-Knowledge-Map.md
└── reports/                     ← Audit and upgrade reports
    └── documentation-audit-report.md
```

---

## Cross-Reference Map

### Architecture Chain
```
docs/README.md → docs/ARCHITECTURE.md → output/engineering-history/phase-02/02_Architecture_Evolution.md
```

### Engineering History Chain
```
output/engineering-history/README.md → output/engineering-history/INDEX.md → phase-*/NN_Document.md
output/engineering-history/phase-14/14_DBMA_Engineering_History.md (master synthesis)
```

### Pipeline Chain
```
docs/PIPELINE.md → docs/STATE.md → output/PT_PROCESSING_*/
```

### Release Chain
```
docs/RELEASE_NOTES_v1.1.0.md → output/DBMA_v1.1.0_RELEASE_CANDIDATE_REPORT.md → output/SPRINT5_ENGINEERING_VALIDATION/RC1_RELEASE_NOTES.md
```

---

## Document Naming Convention

| Pattern | Meaning | Example |
|---------|---------|---------|
| `NN_DescriptioN.md` | Sequential report | `02_Architecture_Evolution.md` |
| `PT_SERIES_NUMBER_Purpose.md` | Processing/Test series | `PT_PROCESSING_013_CORPUS_INVENTORY.md` |
| `_v#`.md | Versioned document | `METADATA_CONTRACT_v1.md` |
| `_REPORT.md` | Report documents | `DBMA_v1.1.0_RELEASE_CANDIDATE_REPORT.md` |
| `_PLAN.md` | Planning documents | `FAT_PLAN_v1.1.0.md` |

---

**Index Status:** COMPLETED  
**Last Updated:** 2026-07-11  
**Next Update:** Upon creation of new category documents