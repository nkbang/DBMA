# C1 Investigation Order Rules v1.0


## Purpose

This document defines the mandatory investigation sequence
for C1 when analyzing DBMA incidents.

C1 must determine investigation order
based on evidence and system flow.

C1 must not select a component
only because it appears related to the symptom.


---

# Core Rule


Symptom location is not equal to root cause location.


Example:

Search quality degradation


Incorrect:

Search problem
↓
RetrievalEngine modification


Correct:

Search problem
↓
Recent changes
↓
Pipeline inspection
↓
Evidence collection
↓
Root cause identification


---

# Mandatory Investigation Sequence


## Step 1. Confirm Symptom


Define:

- What is failing?
- When did it start?
- Who observed it?
- Is it reproducible?


Do not assign a root cause.


---

## Step 2. Check Recent Changes


Always check first:


- Code changes
- Configuration changes
- Model changes
- Data changes
- Index changes
- Deployment changes


Reason:

New changes have higher investigation priority
than unchanged components.


---

## Step 3. Identify Pipeline Impact


Trace the DBMA flow:


Document

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


Identify possible affected areas.


---

## Step 4. Collect Evidence


For each candidate:


Classify:

VERIFIED

REPORTED

UNKNOWN


Do not convert UNKNOWN into assumptions.


---

## Step 5. Validate with Tests


Use:

- Regression tests
- Benchmark tests
- State comparison
- Logs


Validation comes before modification.


---

## Step 6. Recommend Action


Recommendations must include:


Evidence

↓

Risk

↓

Minimum change

↓

Validation plan


---

# RetrievalEngine Investigation Rule


RetrievalEngine is a protected authority layer.


However:


Importance does not mean priority.


C1 must not state:


"Search issue means RetrievalEngine issue"


without evidence.


---

# Priority Example


Search relevance degradation:


Correct order:


1. Recent deployment changes
2. Configuration comparison
3. Pipeline state verification
4. Embedding/vector consistency check
5. RetrievalEngine behavior validation
6. Code modification proposal


---

# Forbidden Reasoning


Forbidden:


- Component-first diagnosis
- Evidence-free modification
- Architecture expansion
- Parallel retrieval proposal


---

# Decision Standard


C1 follows:


Evidence first.

Order before assumption.

Validation before change.

Architecture before convenience.

