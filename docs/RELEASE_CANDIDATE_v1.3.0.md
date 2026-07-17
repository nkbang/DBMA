---
title: DBMA v1.3.0 Release Candidate
category: release
status: RC (validation 진행)
created: 2026-07-17
baseline_commit: ca23542
head_commit: 4fda8ad (RC freeze; version bump follows)
---

# DBMA v1.3.0 — Architecture Consolidation Release Candidate

## Summary

DBMA를 "RAG + VectorDB 시스템"에서 **TSU 기반 Theological Retrieval System**으로
아키텍처 정체성을 확정하고, Authority 계층을 물리적으로 분리한 릴리스.
SPRINT20-I(Architecture Consolidation)에서 완성.

## Authority (확정)

| Layer | Authority |
|---|---|
| Processing | core/processing.py |
| Identity | core/identity_registry.py |
| Index | core/index_orchestrator.py |
| TSU Generation | core/tsu_builder.py |
| Retrieval | core/retrieval.py (BM25 + BGE-M3 + hybrid + document diversity) |
| Embedding | core/embedder.py (BGE-M3 / Ollama / 1024 dim) |
| Generation | core/generation.py |
| UI Entry | dbma_ui.py → ui/pages/* |
| Legacy | archive/legacy/ + chroma_db + backups (ADR-003 KEEP) |

## Changes (ca23542 → 6fb39c3)

- `be0a776` 임베딩 런타임 hardening(batch-split + oversized/retry guard) + gen-model 정정
- `dc9e4d3` TSU Builder·Index·registry-path authority core 통합
- `ec35092` UI 상태/표시 수정
- `78721b0` Index/Version Authority 문서
- `ce6b05a` legacy 코드 archive
- `e2c9995` retrieval document diversity
- `6fb39c3` ADR-003 Finalization

## RC Checklist

- [x] 전체 테스트 통과 (237 passed, ~/envs/dbma311)
- [x] 공식 UI(ui.app) import 정상
- [x] Legacy 코드 격리 (archive/legacy, 공식 importer 0)
- [x] Retrieval 품질 회귀 없음 (book-level: 전 지표 delta 0)
- [x] Document diversity 개선 (2 Kings 1→3 문서)
- [x] Version 정합 (APP_VERSION = 1.3.0)
- [x] Storage 정책 확정 (ADR-003 Finalization)
- [x] Release validation: chapter-level benchmark(1500q) — **PASS**
- [x] git push (완료, origin/dev/dbma-engine)

### Chapter-level validation: PASS

1500q, cap=2 + P2 embedding fix. vs baseline v2(cap=0):

| Metric | Baseline | v1.3.0 | Δ |
|---|---|---|---|
| P@1 | 0.242 | 0.242 | 0 |
| P@5 | 0.180 | 0.174 | -0.006 |
| MRR | 0.3454 | 0.3453 | -0.0001 |
| nDCG@10 | 0.3853 | 0.3849 | -0.0004 |
| hit@10 | 0.1567 | 0.1565 | -0.0002 |

- avg_latency 311.5ms. 전 지표 baseline과 동등(noise 수준) → 회귀 없음.
- Evidence: `output/bench/chapter_level_result_v1.3.0_cap2.json`.

## Resolved Issues

- **Ollama HTTP 500**: 원인 규명·수정 완료(commit f5f2753). char//4 토큰추정이
  다국어 텍스트 과소평가 → oversized 청크가 Ollama batch(2048) 초과.
  `_APPROX_CHARS_PER_TOKEN` 4→2로 전송 전 차단. chapter-level 재실행 시 500 재발 0.
- Orphan cleanup 완료: `data/rag_index/`, 빈 backup 폴더, `core/md_manager.py`(archive).

## Next

GA 검토 (안정화 기간 후).
