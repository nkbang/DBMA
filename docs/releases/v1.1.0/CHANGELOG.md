# DBMA v1.1.0 — Changelog

---

## Version History

### v1.1.0 (2026-07-11) — Release Baseline

**Status**: Production Ready

#### Summary

DBMA v1.1.0 represents the culmination of 15 development sprints (Sprint 1 through Sprint 15). It is a **Stable Research Platform** (L3 Maturity Level) designed for Korean theological corpus analysis, retrieval, and semantic research.

This release establishes DBMA as an operational product — not merely a research prototype.

#### What's New

| Component | Sprint Range | Description |
|-----------|-------------|-------------|
| Core Retrieval Engine | Sprint 5-9 | Hybrid BM25 + Vector retrieval pipeline |
| Query Intelligence Layer | Sprint 10-13 | Book detection, reference parsing, theme classification |
| Evaluation Framework | Sprint 14-15 | Fingerprint validation, gold-standard benchmarking |
| Document Identity System | Sprint 12-13 | identity_registry.json for document provenance |
| Interactive Research UI | Sprint 6-15 | Streamlit-based research interface with 5 pages |

#### Engineering Achievements

- 15 development sprints completed
- 100+ audit reports generated across PT-PROGRESS, PT-RELEASE, PT-PRODUCT series
- Zero production defects in core pipeline
- Retrieval accuracy validated against gold-standard benchmark
- Full documentation package created (LOOP 6 deliverable)

---

### v1.0.0 — Development Build (Deprecated)

**Status**: Deprecated (replaced by v1.1.0)

This was the initial development baseline prior to Sprint 15 hardening. It is no longer referenced in documentation.

#### Key Differences from v1.1.0

| Aspect | v1.0.0 | v1.1.0 |
|--------|--------|--------|
| Version nomenclature | Mixed (1.0.0, Sprint X) | Unified (v1.1.0) |
| Entry point | `dbma.py` (deprecated) | `ui/app.py` (current) |
| Documentation | Sparse | Complete release package |
| Evaluation framework | Experimental | Hardened with benchmarks |
| Document identity | Not implemented | Full identity_registry.json |
| Research readiness | Prototype | Stable Research Platform |

---

## Sprint History Summary

### Sprint 1-5: Foundation

- Core architecture design
- ChromaDB integration
- BM25 retrieval engine
- PDF ingestion pipeline
- Initial UI (dbma.py era)

### Sprint 6-9: Retrieval Hardening

- Hybrid retrieval (BM25 + Vector)
- Query intelligence layer
- Metadata extraction
- Corpus processing pipeline
- UI migration to `ui/app.py`

### Sprint 10-13: Intelligence Layer

- Book detection and reference parsing
- Theme classification
- Document identity system
- Identity registry implementation
- Research page development

### Sprint 14-15: Evaluation & Release

- Fingerprint evaluation framework
- Gold standard benchmarking
- Release candidate testing
- Documentation package creation
- v1.1.0 release baseline

---

## Migration Guide (v1.0 → v1.1)

If you have an existing v1.0 installation:

```bash
# 1. Backup your data
tar czf dbma-pre-upgrade.tar.gz \
    chroma_db/ data/제련완성본/ core/identity_registry.json config.yaml

# 2. Install v1.1.0 (follow INSTALL.md)

# 3. No config migration needed — config.yaml is backward compatible
```

---

## Known Issues

| Issue | Priority | Status | Workaround |
|-------|----------|--------|-----------|
| Korean semantic retrieval accuracy | P1 | In roadmap | Use BM25 fallback for Korean keywords |
| Large corpus (>10GB) performance | P2 | Tracked | Reduce chunk_size to 256 |

---

## What's Next

### Planned Future Releases

| Version | Focus | Status |
|---------|-------|--------|
| v1.2.0 | Korean semantic retrieval improvement | Roadmap |
| v2.0.0 | MIE (Mining & Exegetical) Architecture | Vision |

---

*DBMA v1.1.0 is a Stable Research Platform. All previous sprints contributed to this release baseline.*