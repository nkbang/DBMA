# DBMA Production Engineering Rules

## 1. Project Identity

Project:

DBMA (David Bang Ministry Archive)

Current Phase:

Production Engineering / Release Stabilization

Development Boundary:

Sprint 15 is the FINAL development sprint.

After Sprint 15:

* Maintenance only
* Bug fixes only
* No architectural expansion
* No speculative features

---

## 2. Execution Environment Rules

## Mandatory Python Environment

All DBMA Python execution MUST use:

```bash
~/envs/dbma311
```

Never use:

```bash
python
python3
pip
pip3
```

from the system environment.

Before executing any Python command:

Run:

```bash
cd ~/DBMA
source ~/envs/dbma311/bin/activate
```

Verify:

```bash
which python
```

Expected:

```
~/envs/dbma311/bin/python
```

Verify:

```bash
python --version
```

Expected:

```
Python 3.11.x
```

If the environment is unavailable:

STOP.

Do not continue execution.

Report the environment failure.

---

## 3. Execution Safety Gate

Before running any command:

Verify:

1. Current directory

Expected:

```
~/DBMA
```

2. Virtual environment

Expected:

```
dbma311
```

3. Target file exists

4. Required dependencies available

5. Git/change status if modifying code

Never execute commands blindly.

Never continue after environment errors without correction.

---

## 4. File Placement Rules

## Production Code

Allowed:

```
core/
```

Examples:

```
core/tsu/
core/retrieval/
core/ranking/
```

## Tests

Allowed:

```
tests/
```

## Utility Scripts

Allowed:

```
scripts/
```

## Reports and Validation Output

Allowed:

```
output/
```

## Forbidden

Do not create:

```
~/DBMA/test_xxx.py
~/DBMA/script_xxx.py
~/DBMA/random_file.py
```

in project root.

Root-level files require explicit approval.

---

## 5. Engineering Development Rules

## Architecture Protection

Do NOT:

* redesign architecture
* replace core pipeline
* introduce unnecessary frameworks
* create duplicate systems
* change TSU schema without approval

Current architecture is frozen.

Focus:

* correctness
* validation
* performance
* reliability

---

## 6. Code Modification Policy

Modify production code ONLY when:

* fixing verified defects
* improving measurable performance
* satisfying acceptance criteria

Do NOT:

* refactor for style only
* rename large components unnecessarily
* create abstraction layers without need

Prefer:

small deterministic changes

over:

large redesigns

---

## 7. Documentation Policy

Documentation is required only when:

* recording engineering decisions
* release evidence
* validation results
* operational procedures

Do NOT create:

* duplicate explanations
* unnecessary markdown files
* speculative architecture documents

Priority:

1. Working code
2. Tests
3. Validation
4. Documentation

---

## 8. Validation Requirements

Every engineering change must verify:

```
Code
 ↓
Test
 ↓
Pipeline
 ↓
Benchmark
 ↓
Regression
```

Required checks:

* no broken imports
* no stale identifiers
* no duplicate TSU IDs
* no orphan references
* deterministic output

---

## 9. DBMA Pipeline Integrity

Maintain this pipeline:

```
Source Documents

↓

Extraction

↓

TSU Dataset

↓

Metadata

↓

Gold Standard

↓

Retrieval

↓

Ranking

↓

Benchmark

↓

Regression
```

Never bypass validation layers.

---

## 10. Benchmark Rules

Benchmark execution must use:

Real TSU dataset.

Real Gold Standard.

Real retrieval pipeline.

Never use:

* synthetic replacement data
* stub retrieval
* fake metrics

Metrics:

* Precision@K
* Recall@K
* MRR
* nDCG
* Hit Rate
* Latency
* Throughput

---

## 11. Regression Rules

Maintain:

* baseline history
* reproducible results
* deterministic comparison

Never overwrite previous baselines.

Create new versions:

Example:

```text
baseline_v1.json
baseline_v2.json
baseline_v3.json
```

---

## 12. Sprint Control

Current:

Sprint 13

Remaining:

Sprint 14
Sprint 15

Sprint 15 completion means:

DBMA development freeze.

Final objectives:

* stable retrieval
* validated corpus
* reliable benchmark
* production readiness

---

## 13. Current Priority Order

Priority 1:

Data integrity

Priority 2:

Retrieval correctness

Priority 3:

Benchmark accuracy

Priority 4:

Performance optimization

Priority 5:

Release stabilization

Do not prioritize UI or additional features.

---

## 14. Response Format for Engineering Tasks

When completing tasks, report only:

1. Modified production files
2. Tests executed
3. Validation statistics
4. Benchmark impact
5. Remaining blockers

Avoid unnecessary summaries.

---

## 15. Final Engineering Principle

DBMA is no longer a prototype.

Treat it as a production engineering system.

Every change must be:

* measurable
* reproducible
* reversible
* justified by evidence
