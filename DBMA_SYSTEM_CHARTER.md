# DBMA System Charter v1.0


## 1. System Identity

Name:
David Bang Ministry Archive (DBMA)

Purpose:
A theological knowledge intelligence platform
that transforms ministry resources,
books, sermons, commentaries, and research materials
into structured searchable knowledge assets.


## 2. Core Architecture Principles

### One Pipeline

All documents must pass through one controlled processing pipeline.

Flow:

Source Document
    ↓
Extraction
    ↓
Normalization
    ↓
Chunking
    ↓
Embedding
    ↓
Vector Storage
    ↓
RetrievalEngine
    ↓
Research Interface


### One Config

Configuration authority must remain centralized.

No duplicated configuration sources.

Configuration drift is considered a system risk.


### One Retrieval Engine

RetrievalEngine is the only retrieval authority.

Forbidden:

- secondary retrieval modules
- parallel search paths
- duplicated ranking logic


### One Execution State

DBMA must maintain consistent execution state.

No conflicting pipeline states.


## 3. Core Components


Extraction:
Document text acquisition.


Normalization:
Language and text consistency processing.


Chunking:
Semantic unit preparation.


Embedding:

Standard Model:

bge-m3:latest

Dimension:

1024


Vector Storage:

TSU dataset (output/bench/tsu_dataset.jsonl) + in-memory similarity
retrieval (cosine, TF-IDF fallback) — production authority.
Qdrant/Chroma는 legacy corpus history로만 보존되며 검색 경로에서
쿼리되지 않는다 (ADR-001 Correction, ADR-003 확정).


Retrieval:

core/retrieval.py::RetrievalEngine


## 4. Agent Governance


Human HQ:

Final authority.


C1:

Planning and Governance.

Responsibilities:

- system analysis
- architecture review
- risk assessment
- sprint planning


Forbidden:

- code modification
- git operation
- deployment
- autonomous architecture change


CUE:

Implementation Agent.

Responsibilities:

- execute approved tasks
- modify approved files
- run validation


## 5. Change Control

Any architecture modification requires:

1. Problem definition
2. Impact analysis
3. Alternative analysis
4. Human approval


## 6. Evidence Classification


Every analysis must separate:

VERIFIED:
Directly confirmed facts.

REPORTED:
Previously reported information.

UNKNOWN:
Requires verification.


## 7. Decision Principle

Never identify the last visible component
as the root cause without evidence.

Always trace:

Symptom
 ↓
Layer
 ↓
Cause
 ↓
Impact
 ↓
Safe Action