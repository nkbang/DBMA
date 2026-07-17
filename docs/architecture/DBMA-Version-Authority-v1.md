---
title: DBMA Version Authority v1
category: architecture
status: authority (current)
created: 2026-07-17
---

# DBMA Version Authority

버전·상태 표현의 단일 기준 문서. 보고서/작업 계획은 이 정의를 따른다.

## Current

- **Project:** DBMA (David Bang Ministry Archive)
- **Subtitle:** Personal Knowledge Operating System
- **Version:** v1.1.0
- **Release Name:** Architecture Consolidation Release
- **Status:** Research Grade / Production Candidate

## Version History

- **v0.x — Prototype RAG:** dbma.py monolith, Chroma/Qdrant 중심, 처리·검색·임베딩 혼재.
- **v1.0 — Research Grade Release:** TSU Pipeline, RetrievalEngine, Benchmark/Gold Standard, Regression Framework 구축.
- **v1.1 — Architecture Consolidation Release (현재):** Processing/Identity/Index Authority 확립, TSU Builder core 이동, RetrievalEngine 단일화, BGE-M3/1024 Embedding Authority 확립, Legacy RAG 분리 진행.

## Architecture Authority (확정)

| Layer | Authority |
|---|---|
| Processing | `core/processing.py` |
| Identity | `core/identity_registry.py` |
| Index | `core/index_orchestrator.py` |
| TSU Generation | `core/tsu_builder.py` |
| Retrieval | `core/retrieval.py` |
| Embedding | `core/embedder.py` (BGE-M3 / Ollama / 1024 dim) |
| Generation | `core/generation.py` |
| UI Entry | `dbma_ui.py → ui/pages/*` |
| Legacy (archive 대상) | `dbma.py` + Chroma/Qdrant island (`core/search.py`·`ingest.py`·`qdrant_init.py`) |

## v2.0 조건 (아래 완료 전 v2.0 언급 금지)

- Legacy 제거 완료
- 자동 ingestion workflow 완성
- Knowledge Graph / semantic enrichment 추가
- Research agent workflow 구축
- Archive lifecycle manager 구축

## Version Resolution

- 런타임 `APP_VERSION`은 `config.yaml` app.version = `1.1.0`에서 해석된다(확인:
  `core.config.APP_VERSION == "1.1.0"`). `core/config.py`의 fallback 기본값
  `"0.6.4"`는 yaml이 없을 때만 쓰이며 실제 런타임에는 도달하지 않는다.
