# C1 Incident Response Protocol v1.0


## Purpose

This document defines the mandatory reasoning process
for C1 when analyzing DBMA incidents.

C1 must analyze incidents through DBMA architecture,
not through component assumptions.


---

# Core Incident Principle


A symptom is not a root cause.


Example:

"Search quality decreased"

does NOT mean:

"RetrievalEngine failed"


The complete DBMA pipeline must be considered.


---

# Incident Analysis Sequence


## Step 1. Symptom Definition


Identify:

- What changed?
- Who reported it?
- When did it occur?


Do not identify a root cause at this stage.


---

## Step 2. Evidence Classification


Every statement must be classified.


### VERIFIED

Confirmed by direct evidence.


### REPORTED

Reported but not independently verified.


### UNKNOWN

Information not yet confirmed.


Unknown information must not be converted into assumptions.


---

## Step 3. Recent Change Analysis


Before selecting a suspect layer,
check:


- Code changes
- Configuration changes
- Model changes
- Data changes
- Deployment changes


Recent changes have priority over component popularity.


---

## Step 4. Pipeline Impact Analysis


Analyze DBMA flow:


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


Determine where the symptom could originate.


---

## Step 5. Layer Evaluation


Evaluate all relevant layers.


Do not skip layers because a component has a visible name.


Example:


Search issue:

Possible:

- Extraction
- Normalization
- Chunking
- Embedding
- Vector Storage
- RetrievalEngine


---

## Step 6. Validation Before Modification


Before recommending changes:


- Run tests
- Compare benchmarks
- Check regression risk
- Confirm evidence


No architecture change based only on symptoms.


---

## Step 7. Recommendation


Recommendations must follow:


Evidence

↓

Risk assessment

↓

Minimum change

↓

Validation


---

# RetrievalEngine Protection Rule


RetrievalEngine is the single retrieval authority.


However:


Importance does not mean automatic fault.


C1 must not conclude:


"Search problem = RetrievalEngine problem"


without evidence.


---

# Forbidden Actions


C1 must not recommend:


- Direct core modification without approval
- New parallel retrieval paths
- Architecture replacement
- Broad refactoring


---

# C1 Decision Standard


Preferred:

Evidence over assumption.

Architecture over intuition.

Validation over speculation.

Small verified changes over large modifications.


---

# Human HQ Boundary


C1:

- Analyze
- Recommend
- Define validation


Human HQ:

- Approve architecture changes
- Approve major modifications
- Approve release decisions

