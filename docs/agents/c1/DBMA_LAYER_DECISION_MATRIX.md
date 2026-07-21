# DBMA Layer Decision Matrix v1.0


## Purpose

This document defines how C1 analyzes DBMA incidents.

C1 must reason from architecture flow,
not from component names alone.


---

# Core Rule


A symptom does not identify the root cause.


Example:


Search quality degradation

does NOT mean:

RetrievalEngine failure.


The entire pipeline must be considered.


---

# DBMA Data Flow


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


---

# Layer Investigation Rules


## 1. Extraction Layer


Check when:

- Documents missing
- Text incomplete
- Parsing errors


Questions:

- Was extraction successful?
- Did source content change?


---

## 2. Normalization Layer


Check when:

- Language matching problems
- Special characters fail
- Multilingual search degradation


Questions:

- Was text normalized correctly?
- Were languages preserved?


---

## 3. Chunking Layer


Check when:

- Search finds irrelevant sections
- Context is incomplete
- Semantic relationship is lost


Questions:

- Did chunk boundaries change?
- Was context preserved?


---

## 4. Embedding Layer


Check when:

- Retrieval similarity decreases
- Model changed
- Vector dimension mismatch


Questions:

- Is embedding model consistent?
- Are dimensions correct?


---

## 5. Vector Storage Layer


Check when:

- Index inconsistency suspected
- Missing vectors
- Database corruption


Questions:

- Is vector state valid?
- Does metadata match?


---

## 6. RetrievalEngine Layer


Authority:

core/retrieval.py::RetrievalEngine


Check when:

- Query interpretation fails
- Ranking logic fails
- Retrieval algorithm behavior changes


Important:

RetrievalEngine is protected authority.

Do not modify unless evidence supports the change.


---

# Investigation Priority


For unknown incidents:


Step 1:

Identify symptom.


Step 2:

Check recent changes.


Step 3:

Identify affected pipeline stage.


Step 4:

Collect evidence.


Step 5:

Run validation.


Step 6:

Recommend minimum-risk action.


---

# Forbidden Reasoning


Never conclude:


"Search problem = RetrievalEngine problem"


without evidence.


Never recommend:


- Parallel retrieval system
- Architecture replacement
- Direct core modification


without Human HQ approval.


---

# C1 Decision Principle


Prefer:


Evidence over assumption.

Architecture over intuition.

Validation over speculation.

Small changes over broad changes.

