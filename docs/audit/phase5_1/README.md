# Phase 5.1 Evidence Package (CUE-P0-FINAL-EVIDENCE-CLOSURE)

Read-only forensic review. 코드 수정·reset·restore·commit 없음.

## 파일 구성

| 파일 | 내용 |
|---|---|
| `commit.txt` | HEAD SHA, parent SHA, branch, `git show --stat HEAD` |
| `changed_files.txt` | 커밋된 변경(`HEAD^..HEAD`)과 미커밋 working tree 변경을 분리해 기록 |
| `tests/pytest-output.txt` | `pytest tests/test_nae_benchmark_*.py -v` 전체 출력 (92 passed) |
| `code-trace.md` | Q1/Q2/Q3에 대한 코드 행 단위 근거 |
| `adr-linkage.md` | ADR-003/ADR-013 source-level 준수 확인 |
| `findings.md` | 확인된 사실 / 확인 안 된 주장 / 구조적 결함 / 필요 증거 |

## 요약 판정

```
Q1 (evaluator reads gold_tsu_ids): FAIL
Q2 (runner passes Qdrant results):  FAIL (Qdrant 연결 코드 자체 없음)
Q3 (metric ID-space alignment):     FAIL

ADR-003: VERIFIED (미침범)
ADR-013: VERIFIED (독립 운영 확인)

Tests: 92 passed, 0 failed (tests/pytest-output.txt)
```

## P1 재감사 요청 (제출 형식)

```
Repository:
nkbang/DBMA

Branch:
dev/dbma-engine

Commit:
d7152ec989d47a48fce008780066d1d35c05e653

Evidence:
docs/audit/phase5_1/

Tests:
pytest tests/test_nae_benchmark_*.py -v
→ 92 passed, 0 failed (docs/audit/phase5_1/tests/pytest-output.txt)

ADR:
ADR-003 — VERIFIED (docs/audit/phase5_1/adr-linkage.md)
ADR-013 — VERIFIED (docs/audit/phase5_1/adr-linkage.md)

Benchmark linkage:
evaluator.py — gold_tsu_ids 미참조 (FAIL, docs/audit/phase5_1/code-trace.md Q1)
runner.py    — Qdrant 연결 미구현 (FAIL, docs/audit/phase5_1/code-trace.md Q2)
metrics.py   — 계산 로직 자체는 정상, 단 입력 ID-space 불일치 (FAIL, docs/audit/phase5_1/code-trace.md Q3)

주의: commit d7152ec 이후 working tree에 미커밋 변경이 존재함
(docs/audit/phase5_1/changed_files.txt 참고) — 이 변경은 어느 commit에도
속하지 않으므로 이번 Evidence Package의 commit/diff 근거(commit.txt)에는
포함되지 않았다. 미커밋 변경도 포함해 재감사가 필요하면 별도 명시 요청 바람.
```
