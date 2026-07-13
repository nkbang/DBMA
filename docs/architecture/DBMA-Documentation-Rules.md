---
title: DBMA Documentation Management Rules
category: documentation
phase: Phase 6
related_files:
  - docs/INDEX.md
  - docs/README.md
  - .clinerules/dbma-engineering.md
status: active
created: 2026-07-11
---

# DBMA Documentation Management Rules

**Effective:** 2026-07-11  
**Phase:** Phase 6 — Documentation Rules  
**Status:** ACTIVE

---

## 1. Folder Structure (Mandatory)

All Markdown documents MUST be placed in the following structure:

```
docs/
├── README.md                    ← Documentation overview (existing)
├── INDEX.md                     ← Master document index (existing)
├── ARCHITECTURE.md              ← System architecture (existing)
├── PIPELINE.md                  ← Processing pipeline (existing)
├── STATE.md                     ← Project state (existing)
├── TODO.md                      ← Task list (existing)
├── CHANGELOG.md                 ← Change log (existing)
├── DBMA_MAP.md                  ← Module map (existing)
├── METADATA_CONTRACT_v1.md      ← Metadata spec (existing)
├── UI_GUIDE.md                  ← UI guide (existing)
├── RELEASE_NOTES_v1.1.0.md      ← Release notes (existing)
├── architecture/                ← Architecture documents
│   ├── DBMA-Engineering-Knowledge-Map.md
│   └── DBMA-Documentation-Rules.md  ← This file
├── reports/                     ← Audit and upgrade reports
│   └── documentation-audit-report.md
├── sprint-history/              ← Sprint documentation (reserved)
├── adr/                         ← Architecture Decision Records (reserved)
├── engines/                     ← Engine-specific docs (reserved)
├── ui/                          ← UI documentation (reserved)
├── ai-agent/                    ← AI agent documentation (reserved)
├── testing/                     ← Testing documentation (reserved)
├── deployment/                  ← Deployment documentation (reserved)
└── archive/                     ← Legacy/superseded documents (reserved)
```

**Rules:**
- NO new folders may be created under `docs/` without explicit approval
- ALL existing folders in `output/`, `output/engineering-history/`, `output/SPRINT5_ENGINEERING_VALIDATION/`, and `output/bench/` remain as their canonical locations
- New documentation MUST follow this structure

---

## 2. File Naming Convention (Mandatory)

| Pattern | Use Case | Example |
|---------|----------|---------|
| `CATEGORY_SERIES_NUMBER_Purpose.md` | Validation/test reports | `PT_PROCESSING_013_CORPUS_INVENTORY.md` |
| `NN_DescriptioN.md` | Sequential engineering docs | `02_Architecture_Evolution.md` |
| `NAME_vN.md` | Versioned specifications | `METADATA_CONTRACT_v1.md` |
| `NAME_REPORT.md` | Final reports | `DBMA_v1.1.0_RELEASE_CANDIDATE_REPORT.md` |
| `NAME_PLAN.md` | Planning documents | `FAT_PLAN_v1.1.0.md` |

**Rules:**
- Use PascalCase for descriptive parts
- Prepend sequential numbers with zero-padding (00, 01, 02...)
- NO spaces or special characters in filenames
- NO camelCase mixed with underscore naming (pick one style per component)

---

## 3. Metadata Block (Mandatory)

Every new Markdown document MUST include a YAML front matter block:

```yaml
---
title: Document Title
category: architecture|pipeline|testing|release|documentation|ui|adr
phase: Sprint number or "ongoing"
related_files:
  - related_file_1.md
  - related_file_2.md
status: active|completed|deprecated
created: YYYY-MM-DD
---
```

**Required Fields:**
- `title` — Document title (no dashes)
- `category` — One of the allowed categories above
- `phase` — Sprint number or "ongoing"
- `status` — active / completed / deprecated
- `created` — ISO date (YYYY-MM-DD)

**Optional Fields:**
- `related_files` — List of related document paths
- `updated` — Last update date (if different from created)

---

## 4. Document Placement Rules

### Core Architecture & Pipeline Docs → `docs/`

Examples: ARCHITECTURE.md, PIPELINE.md, STATE.md

### Validation/Test Reports → `output/` (existing location preserved)

All PT_* series documents remain in `output/`.
Future similar reports use the same pattern.

### Engineering Audit → `output/engineering-history/` (existing location preserved)

All phase-XX audit documents remain in their canonical locations.

### Sprint Documentation → `output/SPRINT*_ENGINEERING_VALIDATION/` (existing location preserved)

Sprint deliverables remain in their sprint-specific directories.

### Benchmark Results → `output/bench/` (existing location preserved)

Benchmark reports and test data remain in `output/bench/`.

### New Architecture Docs → `docs/architecture/`

Examples: Knowledge maps, architecture evolution, design decisions

### New Audit Reports → `docs/reports/`

Examples: Documentation audits, compliance reports

---

## 5. Prohibited Actions (Hard Constraints)

The following actions are STRICTLY PROHIBITED without explicit user approval:

| Action | Reason |
|--------|--------|
| Modify application source code | Documentation-only task |
| Create new folders under docs/ without approval | Structural integrity |
| Delete existing documentation | Historical record preservation |
| Rename existing documents | Cross-reference stability |
| Move files from canonical locations | Architecture consistency |
| Create root-level .md files | Organization hygiene |
| Duplicate engineering-history content | Storage efficiency |

---

## 6. Document Lifecycle

```
Draft → Review → Active → Archived
  ↓        ↓       ↓        ↓
created  approved  stable   superseded
```

### Status Transitions

| From | To | Condition |
|------|-----|-----------|
| (new) | active | Approved by reviewer |
| active | completed | All objectives met |
| active | deprecated | Superseded by newer version |
| completed | archived | No longer needed for reference |

---

## 7. Index Maintenance

When creating a new document:

1. Add to `docs/INDEX.md` in the appropriate section
2. Update related documents with cross-references
3. Record creation date in metadata block

When archiving a document:

1. Move to `docs/archive/` (or note in INDEX.md)
2. Update source document's status to `deprecated`
3. Note deprecation reason in INDEX.md

---

## 8. Engineering-History Integration

The engineering-history archive is the **canonical** location for phase-based audit documents:

- Files generated → `output/engineering-history/phase-XX/NN_Document.md`
- Index updated → `output/engineering-history/INDEX.md`
- Cross-references maintained → via `docs/INDEX.md` Engineering History section

---

## 9. Sprint Documentation Integration

Sprint deliverables follow this pattern:

```
sprint-XX/
├── README.md                    ← Sprint overview
├── objective-N.md               ← Objective documentation
├── validation-N.md              ← Validation reports
└── report-N.md                  ← Final reports
```

Cross-reference to `docs/INDEX.md` Sprint History section.

---

**Rule Status:** ACTIVE  
**Effective Date:** 2026-07-11  
**Next Review:** Upon Sprint 16 or new category introduction