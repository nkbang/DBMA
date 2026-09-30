# GS-P08 WORK ORDER REPORT — REWORK r2 (Case C·D P3A 경로 연결)

## 1. Files changed

```
 M tests/test_grounded_failure_paths.py   (수정: TestCaseC, TestCaseD 재작성 + import 추가)
```

git status 원문:
```
?? docs/grounded_synthesis/
?? tests/test_grounded_failure_paths.py
```

staged 파일 6건(config.yaml, core/candidate_generator.py, core/hybrid_candidate_pipeline.py, scripts/merge_nae_corpus.py, scripts/process_unprocessed_nae.py, scripts/test_default_corpus_query.py)은 **미수정**.

## 2. Existing Architecture Verification

읽은 파일 및 확인한 인터페이스:

| 파일 | 줄 | 확인한 내용 |
|---|---|---|
| `core/evidence_assembly.py` | 1-233 | `QuerySpec`, `AssemblyManifest`, `assemble_evidence_pool_with_manifest()`, `_build_manifest()`, `_extract_evidence_ids()` |
| `core/retrieval.py` | 105-128 | `RankedCandidate` dataclass (tsu_id, content, metadata, vector_score, bm25_score, theological_score, passage_score, final_score, explanation) |
| `core/grounded_synthesis_input.py` | 1-151 | `SynthesisInput`, `build_synthesis_input(pool, manifest, max_evidence)` |
| `core/evidence_model.py` | 1-142 | `Evidence`, `EvidenceProvenance` |
| `core/evidence_pool.py` | 1-190 | `EvidencePool`, `add()`, `get()`, overwrite 정책 |
| `tests/test_grounded_failure_paths.py` | 1-679 | 기존 테스트 구조 (Case A/B/E/F/통합/경계 12개 unchanged) |

## 3. Design — 변경 내용 요약

r1에서 TestCaseC와 TestCaseD가 `EvidencePool()`을 직접 생성하고 `.add()`로 수동 채우던 것을,
P3A 계층(`core.evidence_assembly.assemble_evidence_pool_with_manifest()`)을 **실제로 통과**하는 형태로 재작성했다.

### 추가 import

```python
from core.evidence_assembly import QuerySpec, assemble_evidence_pool_with_manifest
from core.grounded_synthesis_input import build_synthesis_input  # 기존 SynthesisInput + 추가
from core.retrieval import RankedCandidate
```

### Case C 재작성: `TestCaseC_PartialMultiQueryResults`

**이전**: `_make_evidence()` → `EvidencePool()` 수동 생성 → `.add()`로 채움
**이후**: `RankedCandidate` 인스턴스를 `QuerySpec`와 쌍으로 만들어 `assemble_evidence_pool_with_manifest()`에 전달 → 반환된 `pool`, `manifest`에 assertion

핵심 변경:
- `RankedCandidate(tsu_id="e1", content=..., final_score=0.9)` 등으로 P2 출력 형식 모의
- `(QuerySpec(query="A"), [ca]), (QuerySpec(query="B"), []), (QuerySpec(query="C"), [cc])` 입력
- `manifest.by_query_order`에서 B의 빈 결과 `[[]]`가 기록됐는지 확인 (P3A AC3)
- `build_synthesis_input(pool, manifest, max_evidence=10)`으로 P4로 연결

### Case D 재작성: `TestCaseD_DuplicateEvidence`

**이전**: `EvidencePool()` 수동 생성 → `.add(ev1_first)` → `.add(ev1_second)` overwrite 확인
**이후**: 같은 `tsu_id="e1"`을 가진 두 `RankedCandidate`를 서로 다른 질의(A, B)에서 반환하도록 `assemble_evidence_pool_with_manifest()`에 전달 → P2 overwrite 정책이 P3A 경로에서도 적용되는지 확인

핵심 변경:
- `manifest.queries_for("e1") == ["A", "B"]`로 P3A AC1(이전 manifest가 duplicate를 모두 기록) 확인
- `len(pool) == 1` + `pool.get("e1").text == "Second version..."`로 overwrite 정책 확인

## 4. Implementation notes

- 모든 테스트는 stub 데이터만 사용 (RankedCandidate, Evidence, Claim 등 frozen dataclass 직접 생성)
- 네트워크 호출, LLM 호출, GPU 사용 없음
- helper 함수 `_make_evidence()`, `_make_claim()`, `_make_grounded_answer()`, `_make_synthesis_input()`, `_make_pool()`로 테스트 데이터 생성 로직 통합 (unchanged)
- Case C·D 각각 2개 테스트 함수 (총 4개 테스트 재작성)
- Case A/B/E/F/통합/경계 테스트 12개는 **손대지 않음**

## 5. Tests

**실행 명령:**
```bash
cd ~/DBMA && source ~/envs/dbma311/bin/activate && python -m pytest tests/test_grounded_failure_paths.py -v
```

**최종 실행 결과 (원문):**
```
tests/test_grounded_failure_paths.py::TestCaseA_EmptyEvidencePool::test_empty_pool_gives_insufficient_status PASSED
tests/test_grounded_failure_paths.py::TestCaseA_EmptyEvidencePool::test_empty_pool_citation_check_does_not_crash PASSED
tests/test_grounded_failure_paths.py::TestCaseB_SingleLowRelevanceEvidence::test_single_evidence_span_not_found PASSED
tests/test_grounded_failure_paths.py::TestCaseB_SingleLowRelevanceEvidence::test_single_evidence_assembly_no_crash PASSED
tests/test_grounded_failure_paths.py::TestCaseC_PartialMultiQueryResults::test_partial_query_results_assembly_continues PASSED
tests/test_grounded_failure_paths.py::TestCaseC_PartialMultiQueryResults::test_partial_query_citation_check_all_pairs PASSED
tests/test_grounded_failure_paths.py::TestCaseD_DuplicateEvidence::test_duplicate_evidence_pool_overwrite_policy PASSED
tests/test_grounded_failure_paths.py::TestCaseD_DuplicateEvidence::test_duplicate_evidence_citation_uses_latest PASSED
tests/test_grounded_failure_paths.py::TestCaseE_ConflictingEvidence::test_conflicting_evidence_both_claims_preserved PASSED
tests/test_grounded_failure_paths.py::TestCaseE_ConflictingEvidence::test_conflicting_evidence_citation_check_both PASSED
tests/test_grounded_failure_paths.py::TestCaseE_ConflictingEvidence::test_conflicting_status_flag_not_auto_detected PASSED
tests/test_grounded_failure_paths.py::TestCaseF_IrrelevantEvidence::test_stub_does_not_expand_interpretation PASSED
tests/test_grounded_failure_paths.py::TestCaseF_IrrelevantEvidence::test_irrelevant_evidence_citation_fails_span_check PASSED
tests/test_grounded_failure_paths.py::TestCaseF_IrrelevantEvidence::test_no_valid_claims_becomes_insufficient PASSED
tests/test_grounded_failure_paths.py::TestPipelineIntegration::test_full_pipeline_normal_flow PASSED
tests/test_grounded_failure_paths.py::TestEdgeCases::test_span_boundary_five_chars PASSED
tests/test_grounded_failure_paths.py::TestEdgeCases::test_span_four_chars_fails PASSED
tests/test_grounded_failure_paths.py::TestEdgeCases::test_claim_with_empty_evidence_ids_skipped PASSED

18 passed in 0.07s
```

**테스트명 목록:**

| 케이스 | 테스트명 |
|---|---|
| A | `test_empty_pool_gives_insufficient_status` |
| A | `test_empty_pool_citation_check_does_not_crash` |
| B | `test_single_evidence_span_not_found` |
| B | `test_single_evidence_assembly_no_crash` |
| **C** | **`test_partial_query_results_assembly_continues`** ← 재작성 |
| **C** | **`test_partial_query_citation_check_all_pairs`** ← 재작성 |
| **D** | **`test_duplicate_evidence_pool_overwrite_policy`** ← 재작성 |
| **D** | **`test_duplicate_evidence_citation_uses_latest`** ← 재작성 |
| E | `test_conflicting_evidence_both_claims_preserved` |
| E | `test_conflicting_evidence_citation_check_both` |
| E | `test_conflicting_status_flag_not_auto_detected` |
| F | `test_stub_does_not_expand_interpretation` |
| F | `test_irrelevant_evidence_citation_fails_span_check` |
| F | `test_no_valid_claims_becomes_insufficient` |
| 통합 | `test_full_pipeline_normal_flow` |
| 경계 | `test_span_boundary_five_chars` |
| 경계 | `test_span_four_chars_fails` |
| 경계 | `test_claim_with_empty_evidence_ids_skipped` |

## 6. AC 대조표

| AC-id | 충족 여부 | 근거: 테스트명 또는 출력 |
|---|---|---|
| **AC3(재검증)**: Case C·D 테스트가 `assemble_evidence_pool_with_manifest()`를 실제로 호출하고, 그 반환값(pool, manifest)에 assertion을 건다 | **PASS** | Case C: `pool, manifest = assemble_evidence_pool_with_manifest([...])` + `assert len(pool) == 2`, `assert b_entry == [[]]`; Case D: `pool, manifest = assemble_evidence_pool_with_manifest([...])` + `assert len(pool) == 1`, `assert manifest.queries_for("e1") == ["A", "B"]` |
| AC1: 6개 케이스 각각에 테스트 함수 1개 이상, 총 6개 이상 | **PASS** | 각 케이스 2~3개 테스트, 총 18개 (pytest 수집 결과: `18 tests collected`) |
| AC2: 어떤 케이스에서도 예외가 전파되지 않음 | **PASS** | 18개 테스트 전부 PASSED, exception 없음 |
| AC4: 발견된 실패는 코드 수정 없이 Remaining issues에 기록 | **PASS** | 버그 발견 없음. 모든 assertion이 P3A의 실제 동작과 일치 |

## 7. Production safety (R5·R6·R7 준수 확인)

**R5 불변 계약:** core/evidence_model.py, core/evidence_pool.py, core/grounded_*.py, core/evidence_assembly.py **무수정**
```bash
$ git diff --stat core/
# (출력 없음 — 수정 없음)
```

**R6 금지 import·호출:** 테스트 파일에 없음
```bash
$ grep -n "import ollama\|import qdrant\|import tantivy\|import requests\|import httpx\|import urllib\|import subprocess\|import socket" tests/test_grounded_failure_paths.py
# (출력 없음 — 금지 import 없음)
```

**R7 테스트 격리:** 파일 시스템에 tmp_path 외 작성 없음, 운영 데이터 경로 열지 않음

**기존 테스트 회귀 확인:**
```bash
$ python -m pytest tests/test_grounded_citation.py tests/test_grounded_answer.py tests/test_grounded_claims.py tests/test_grounded_synthesis_input.py -v
80 passed in 0.13s
```

## 8. Remaining issues

**버그 발견 없음.** P3A 계층(`assemble_evidence_pool_with_manifest()`)이:
- 빈 결과를 건너뛰고 계속 진행하는지 (Case C)
- duplicate evidence_id에 대해 P2 overwrite 정책(마지막 값 유지)을 적용하는지 (Case D)
- manifest가 모든 query→evidence 연관을 기록하는지 (Case D `queries_for`)

모두 실제 P3A 경로를 통과하는 테스트로 검증됨.

**재작성 이력:**
- Case C: `_make_evidence()` + `EvidencePool().add()` 수동 조립 → `RankedCandidate` + `assemble_evidence_pool_with_manifest()` P3A 경로 연결
- Case D: 동일 — `EvidencePool().add()` 수동 overwrite → `assemble_evidence_pool_with_manifest()`를 통한 duplicate 검증
- 두 케이스 모두 `manifest.queries_for()`, `manifest.by_query_order` 등 P3A manifest API를 직접 검증

## 9. Phase recommendation

CUE READ-ONLY REVALIDATION REQUESTED
