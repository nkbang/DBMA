# DBMA Production Engineering Rules

## 1. Project Identity

Project:

DBMA (David Bang Ministry Archive)

Current Phase:

Production Engineering / Release Stabilization

Development Boundary:

[2026-07-26 정정] "Sprint 15가 마지막"이라는 아래 경계는 이미 지난
사실이다 — 실제로는 SPRINT27~33까지 아키텍처급 변경(Research Workspace
Layer, Boundary Score 모델, Hierarchical Chunk Builder 등, ADR-004~008)이
사용자 승인 하에 계속 진행됐다. "Sprint 15 이후 아키텍처 확장 금지"를
현재 유효한 제약으로 취급하지 마라. 현재 진행 상태의 유일한 권위 소스는
docs/STATE.md이다 — 작업 전 반드시 그 파일을 먼저 확인하라. 아래
숫자(Sprint 13/14/15)는 참고용 이력으로만 남겨둔다.

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

## 7. Git Commit Policy

* NEVER run `git add` or `git commit` unless the user's Task Order
  explicitly asks for a commit in that same request.
* A request to investigate, report, fix, or implement does NOT imply
  permission to commit — implementing and committing are separate
  approvals.
* Read-only/investigation tasks (status reports, audits, greps) must
  leave `git status` unchanged. Do not stage or commit anything as a
  side effect of "cleaning up" while investigating.
* If you believe a commit is warranted but the Task Order didn't ask
  for one, say so in your report ("이 변경은 커밋이 필요해 보입니다")
  and wait for explicit approval — do not commit preemptively.
* Never use `git checkout --`, `git reset --hard`, `git restore`, or
  any other command that discards working-tree changes unless the
  user explicitly asked for that revert. If asked to "start over" or
  something looks wrong, ask first — a prior session's uncommitted
  work may be in that working tree.

---

## 8. Documentation Policy

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

## 9. Validation Requirements

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

## 10. DBMA Pipeline Integrity

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

## 11. Benchmark Rules

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

## 12. Regression Rules

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

## 13. Sprint Control

[2026-07-26 정정] 이 섹션의 "Sprint 13 → 14 → 15" 계획은 낡았다(파일
최종 수정 2026-07-10, 실제로는 SPRINT33-D까지 진행됨). Sprint 번호를
여기 다시 하드코딩하지 않는다 — 매번 새로 낡아지는 문제가 반복되므로,
**현재 진행 중인 스프린트/체크포인트는 항상 docs/STATE.md를 읽어서
확인**한다. 이 파일은 "이 프로젝트가 언젠가 유지보수 전용으로
동결된다"는 원칙(아래 Final objectives)만 유지하고, 구체적 스프린트
번호는 더 이상 여기서 관리하지 않는다.

동결 시 최종 목표(원칙은 유효, 시점은 docs/STATE.md 참고):

* stable retrieval
* validated corpus
* reliable benchmark
* production readiness

---

## 14. Current Priority Order

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

## 15. Response Format for Engineering Tasks

When completing tasks, report only:

1. Modified production files
2. Tests executed
3. Validation statistics
4. Benchmark impact
5. Remaining blockers

Avoid unnecessary summaries.

---

## 16. Final Engineering Principle

DBMA is no longer a prototype.

Treat it as a production engineering system.

Every change must be:

* measurable
* reproducible
* reversible
* justified by evidence
