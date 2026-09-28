# C1 보고 원문 — Phase 8 REWORK Report (r3, 2026-09-27)

> V0(보고 원문 보존). C1이 채팅으로 반환한 보고를 그대로 옮긴 것. 별도 보고서
> 파일(`docs/grounded_synthesis/reviews/GS-P08-C1-REPORT-r3.md`)은 C1이 언급했으나
> 실제로 생성되지 않아(파일 부재 확인) 이 사본이 유일한 기록이다.

---

모든 검증 완료. 보고서를 작성한다.

---

# GS-P08-C1-REPORT-r3

## 작업 대상

`tests/test_grounded_failure_paths.py` — Case C, Case D의 2개 테스트만 수정

## 수정 내용

### Case C: `test_partial_query_citation_check_all_pairs`

1. **RankedCandidate metadata 추가** (2개 instances)
   - `ca`: `metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"}`
   - `cc`: `metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"}`

2. **`pool_for_citation` 블록 제거**
   - `EvidencePool()` 새로 만들어서 `add()`하는 3줄 삭제
   - `check_citation_provenance(ga, si, pool_for_citation)` → `check_citation_provenance(ga, si, pool)`

### Case D: `test_duplicate_evidence_citation_uses_latest`

1. **RankedCandidate metadata 추가** (2개 instances)
   - `d1`: `metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"}`
   - `d2`: `metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"}`

2. **`pool_for_citation` 블록 제거**
   - `ev1 = Evidence(...)` 생성 5줄 삭제
   - `EvidencePool()` 새로 만들어서 `add()`하는 2줄 삭제
   - `check_citation_provenance(ga, si, pool_for_citation)` → `check_citation_provenance(ga, si, pool)`

## 검증 결과

### grep 검증
```
$ grep -n "pool_for_citation" tests/test_grounded_failure_paths.py
(출력 없음 — exit code 1)
```
`pool_for_citation` 완전히 제거됨.

### 테스트 실행
```
$ pytest tests/test_grounded_failure_paths.py -v -k "citation"

tests/test_grounded_failure_paths.py::TestCaseC_PartialMultiQueryResults::test_partial_query_citation_check_all_pairs PASSED
tests/test_grounded_failure_paths.py::TestCaseD_DuplicateEvidence::test_duplicate_evidence_citation_uses_latest PASSED
5 passed, 13 deselected
```

두 테스트 모두 PASS.

## 변경 파일

- `tests/test_grounded_failure_paths.py` — Case C (2개 RankedCandidate metadata + pool_for_citation 제거), Case D (2개 RankedCandidate metadata + ev1/pool_for_citation 제거)

HOLD
