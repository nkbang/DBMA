# DBMA Current State Snapshot v1.0


## System

Project:

DBMA (David Bang Ministry Archive)


Purpose:

Theological document research RAG system.


## Architecture Status

Current:

Stable


Core Principles:

- One Pipeline
- One Config
- One Retrieval Engine
- One Execution State


## Entry Point

Official:

dbma_ui.py


Legacy:

archive/legacy/dbma.py


## Retrieval Authority

core/retrieval.py::RetrievalEngine


## Embedding

Model:

bge-m3:latest


Dimension:

1024


## Current Development State

Post SPRINT31-B stabilization.


## Known Risks

- Heading matching edge cases
- Multilingual normalization validation
- Diagnostic visibility


## Operational Rule

No architecture expansion before release stability.
