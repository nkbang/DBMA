# DBMA Repository Index v1.0


## Purpose

This document provides C1 with a high-level map of the DBMA repository.

This is not a code reference.
It describes responsibilities and architectural relationships.


---

# Project Root

Location:

~/DBMA


---

# Entry Point


## dbma_ui.py

Role:

Official DBMA application launcher.


Flow:

dbma_ui.py

↓

ui/app.py

↓

DBMA application services


---

# Core Layer


Location:

core/


Responsibility:

DBMA processing and intelligence core.


Important modules:


## retrieval.py

Authority:

RetrievalEngine


Responsibility:

- Query processing
- Retrieval
- Ranking


Rule:

All retrieval decisions belong here.


---

## processing.py

Responsibility:

Document processing orchestration.


---

## embedder.py

Responsibility:

Embedding generation.


Current model:

bge-m3:latest


---

## chunking_optimizer.py

Responsibility:

Semantic chunk optimization.


Important:

Chunk quality directly affects retrieval quality.


---

## text_normalizer.py

Responsibility:

Text normalization.


Important:

Multilingual text consistency depends on this layer.


---

# Data Layer


Location:

data/


Responsibility:

Source documents and processed corpus.


Structure:


RAW

↓

Processing

↓

Structured Corpus


---

# Vector Layer


Related:

Vector database


Responsibility:

Store and retrieve document embeddings.


Important checks:

- Dimension consistency
- Index consistency


---

# Test Layer


Location:

tests/


Responsibility:

Regression protection.


Important categories:

- Retrieval tests
- Pipeline tests
- Embedding tests
- Document processing tests


---

# Documentation Layer


Location:

docs/


Responsibility:

System knowledge and operational history.


Important:

Architecture decisions must be traceable.


---

# Agent Relationship


Human HQ:

Final authority.


C1:

Planning and governance.


CUE:

Implementation and execution.


---

# Incident Investigation Priority


When an issue occurs:


1. Identify symptom

2. Check recent changes

3. Identify affected layer

4. Validate evidence

5. Recommend minimum-risk action


Never assume:

Symptom location = Root cause.


---

# Architecture Protection


Protected principles:


One Pipeline

One Config

One Retrieval Engine

One Execution State


