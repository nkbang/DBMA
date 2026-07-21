# C1 DBMA Architecture Governance Map v1.0


## 1. DBMA Identity

DBMA (David Bang Ministry Archive)

DBMA is a domain-specific theological research RAG system.

Primary purpose:

Transform theological documents into structured,
traceable, and searchable knowledge assets.


---

# 2. Core Architecture Principles


## One Pipeline

DBMA maintains one controlled document processing pipeline.

Flow:


Document Input

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


No parallel processing path should bypass this pipeline.


---

## One Config

Configuration authority must remain centralized.

Important configuration includes:

- Embedding model
- Vector configuration
- Processing parameters


Configuration duplication creates system risk.


---

## One Retrieval Engine

Authority:

core/retrieval.py::RetrievalEngine


All retrieval decisions belong to RetrievalEngine.


Forbidden:

- New retrieval modules
- Parallel search paths
- Independent retrievers


---

## One Execution State

DBMA should maintain one authoritative runtime state.

Duplicated execution paths create uncertainty.


---

# 3. Layer Responsibility


## Extraction Layer

Responsibility:

Convert source documents into usable text.


Possible issues:

- Parsing failure
- Missing content


---

## Normalization Layer

Responsibility:

Prepare clean and consistent text.


Possible issues:

- Language normalization
- Character handling


---

## Chunking Layer

Responsibility:

Create meaningful semantic units.


DBMA priority:

Semantic completeness over simple length splitting.


Possible issues:

- Context loss
- Heading relationship failure


---

## Embedding Layer

Current authority:

bge-m3:latest


Vector dimension:

1024


Possible issues:

- Model mismatch
- Dimension mismatc

---

## Vector Storage Layer

Current system:

Vector Database


Responsibility:

Maintain searchable vector state.


Possible issues:

- Index inconsistency
- Data mismatch


---

## RetrievalEngine Layer

Responsibility:

- Query interpretation
- Retrieval
- Ranking


Important:

A retrieval symptom does not automatically mean RetrievalEngine failure.


---

# 4. Incident Reasoning Rule


When a problem occurs:


Step 1:

Identify the symptom.


Step 2:

Separate symptom location from root cause.


Step 3:

Check recent changes.


Step 4:

Classify evidence:


VERIFIED

Confirmed information.


REPORTED

Previously reported information.


UNKNOWN

Requires investigation.


Step 5:

Recommend minimum-risk action.


---

# 5. Architecture Change Rule


C1 may:

- Analyze
- Recommend
- Review


C1 may not:

- Modify architecture
- Create new system paths
- Replace core authority


Architecture changes require Human HQ approval.


---

# 6. Agent Relationship


Human HQ:

Final authority.


C1:

Planning and governance.


CUE:

Execution agent.


C1 provides:

- Analysis
- Plans
- Validation requirements


CUE performs:

- Approved implementation
- Testing


---

# 7. Decision Principle


DBMA prefers:

Stability over expansion.

Evidence over assumption.

Small verified changes over broad refactoring.

Architecture preservation over feature addition.
