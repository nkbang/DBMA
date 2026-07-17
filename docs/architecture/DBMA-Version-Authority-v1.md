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
- **Version:** v1.3.0
- **Release Name:** Architecture Consolidation Release
- **Status:** Research Grade / Production Candidate

> 버전 번호: 로컬 태그 이력상 `v1.0.0`, `v1.1.0`, `v1.2.0-query-intelligence`가
> 이미 이 브랜치의 과거 커밋에 부여되어 있어(전부 선형 조상), 이번 Architecture
> Consolidation 릴리스는 그 뒤를 잇는 **v1.3.0**으로 확정한다.

## Version History

- **v0.x — Prototype RAG:** dbma.py monolith, Chroma/Qdrant 중심, 처리·검색·임베딩 혼재.
- **v1.0 — Research Grade Release:** TSU Pipeline, RetrievalEngine, Benchmark/Gold Standard, Regression Framework 구축.
- **v1.1 / v1.2 — 중간 태그 마일스톤:** version strings·Korean alias 확장(v1.1.0), Query Intelligence baseline(v1.2.0-query-intelligence). 브랜치 조상 커밋에 태깅됨.
- **v1.3 — Architecture Consolidation Release (현재):** Processing/Identity/Index Authority 확립, TSU Builder core 이동, RetrievalEngine 단일화, BGE-M3/1024 Embedding Authority 확립, Legacy RAG archive 완료.

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

- 런타임 `APP_VERSION`은 `config.yaml` app.version = `1.3.0`에서 해석된다.
  `core/config.py`의 fallback 기본값 `"0.6.4"`는 yaml이 없을 때만 쓰이며 실제
  런타임에는 도달하지 않는다.
