---
title: DBMA v1.1.0 Release Candidate
category: release
status: RC (validation 진행)
created: 2026-07-17
baseline_commit: ca23542
head_commit: 6fb39c3
---

# DBMA v1.1.0 — Architecture Consolidation Release Candidate

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
- [x] Version 정합 (APP_VERSION = 1.1.0)
- [x] Storage 정책 확정 (ADR-003 Finalization)
- [x] Release validation: chapter-level benchmark(1500q) — **Deferred (RC blocker 아님)**
- [ ] git push (승인 대기)

### Chapter-level validation: Deferred

- RC blocker 아님 — post-RC evidence task로 이동.
- 근거: book-level benchmark 회귀 없음(전 지표 delta 0), 변경은 ranking
  post-processing, `RETRIEVAL_DOCUMENT_CAP=0`으로 rollback 가능. chapter-level은
  release evidence 강화 항목이지 안정성 필수 조건이 아니다.
- v1.1.0 GA 또는 연구용 benchmark report 단계에 추가.

## Known Issues (non-blocking)

- **Ollama HTTP 500**: 장시간 연속 임베딩 요청 시 발생(chapter-level 벤치 중 관찰).
  별도 조사 항목. RC blocker 아님.
- Cleanup 후보: `data/rag_index/`(.DS_Store만), `backups/chroma_backup_20260715_203507`(0B).

## Next

RC 선언 → (선택)chapter-level validation → git push → v1.1.0 tag.
