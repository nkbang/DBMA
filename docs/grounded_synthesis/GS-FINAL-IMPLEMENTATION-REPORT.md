# GROUNDED SYNTHESIS — FINAL IMPLEMENTATION REPORT

**Phase**: P12 (Final Implementation Report — 감사 전용, 신규 기능 없음)
**Auditor**: NAE Forensic Auditor (C1)
**Date**: 2026-09-28
**Baseline commit**: `1c0117a7` (docs(p0-5): 24건 재실행 002 — Grounded Synthesis 이전 마지막 커밋)
**HEAD commit**: `06e5a47b` (docs(grounded-synthesis): Phase 11 — Production Safety Audit)
**Branch**: `feat/peb-v0.1` (origin/feat/peb-v0.1)

---

## 1. Phase History

| Phase | Commit Hash | Description | CUE 판정 | HQ 승인일 |
|-------|-------------|-------------|----------|-----------|
| P1 | `2dd40d2e` | Evidence Data Model + Corpus Identity Adapter | 완료 (r3) | — |
| P2 | `db677ac6` | EvidencePool and retrieval boundary integration | 완료 | — |
| P3+3A | `14fccb54` | Multi-Query Evidence Assembly + Manifest | 완료 (r3) | — |
| P4 | `9eae5167` | SynthesisInput Boundary | 완료 | — |
| P5 | `20bf6ddd` | Claim-Evidence Binding | 완료 | — |
| P6 | `2e3eaeea` | Grounded Answer Assembly | 완료 | — |
| P7 | `f9f4a55f` | Citation/Provenance Validation | 완료 (r2) | — |
| P8 | `e5eecd5f` | Negative/Failure-path Validation | 완료 (r3) | — |
| P9 | `5738c709` | Full Grounded Synthesis Integration Test | 완료 (r3) | — |
| P10 | `0d265afc` | Regression/Architecture Integrity Audit | 완료 | — |
| P11 | `06e5a47b` | Production Safety Audit | 완료 (r2) | — |
| P12 | — | Final Implementation Report (이 문서) | — | — |

---

## 2. Final Architecture

```
User Query Set
    ↓
RetrievalEngine.retrieve() / HybridQueryProcessor.process()  (기존, 무변경)
    ↓
list[RankedCandidate]  (vector/bm25/theological/passage/final score)
    ↓
RankedCandidateEvidenceAdapter (core/evidence_adapters/tsu_adapter.py:210)
    ↓
list[Evidence]  (core/evidence_model.py:51, frozen dataclass)
    ↓
EvidencePool (core/evidence_pool.py:39, duplicate overwrite policy)
    ↓
AssemblyManifest (core/evidence_assembly.py:67, query↔evidence_id 양방향 매핑)
    ↓
SynthesisInput (core/grounded_synthesis_input.py:37, frozen dataclass)
    ↓
Claim[] (core/grounded_claims.py:38, bind_claims() at core/grounded_claims.py:57)
    ↓
GroundedAnswer (core/grounded_answer.py:37, status: grounded|insufficient_evidence|conflicting_evidence)
    ↓
CitationCheckReport (core/grounded_citation.py:71, span_found_in_text 기준: core/grounded_citation.py:43-56)
```

기존 DBMA/NAE 파이프라인 (RetrievalEngine → HybridRetriever → CandidateGenerator → Qdrant/Tantivy) 은
`core/retrieval.py`, `core/hybrid_candidate_pipeline.py`, `core/candidate_generator.py`가
`1c0117a7..HEAD` 동안 **0줄 변경**으로 유지된다(P10 §2.3, P11 항목 6).

---

## 3. Retrieval Boundary (§13-Q1 답)

**Q1: 기존 RetrievalEngine이 계속 유일한 retrieval authority인가?**

**답: 예.** Grounded Synthesis는 retrieval을 실행하지도, 호출하지도 않는다.

근거:
- `core/evidence_assembly.py` docstring (line 16-30): "Phase 3은 retrieval을 실행하지 않는다.
  QueryProcessor/HybridQueryProcessor/RetrievalEngine/HybridRetriever를 import하거나 호출하지 않는다."
- `core/evidence_pool.py` docstring (line 20-24): "No retrieval execution"
- P10 회귀 테스트: `tests/test_evidence_pool.py::test_no_retrieval_import_in_evidence_pool` (line 570) —
  grep으로 `core/evidence_pool.py`에 retrieval 관련 import가 없음을 확인
- P10 회귀 테스트: `tests/test_evidence_pool.py::test_evidence_pool_does_not_call_retrieve` (line 587) —
  mock으로 retrieve() 호출이 발생하지 않음을 확인
- P11 항목 6: `git diff 1c0117a7..HEAD core/retrieval.py` = 0줄 변경
- P11 항목 8: retrieval 단계에 ollama 호출 없음 (grep으로 import 확인)

P9 통합 테스트 `tests/test_grounded_synthesis_integration.py::test_full_pipeline_grounded` (line 94)에서
RetrievalEngine은 black-box authority로 호출만 하며, GS 코드는 RankedCandidate 타입을 읽기 전용으로 참조한다.

---

## 4. Evidence Boundary (§13-Q2 답)

**Q2: LLM이 EvidencePool을 넘어 사실을 생성할 수 있는 구조가 없는가?**

**답: 없다.** EvidencePool은 오직 RankedCandidateEvidenceAdapter를 통해서만 채워지며,
RankedCandidate는 기존 RetrievalEngine의 출력이다.

근거:
- `core/evidence_model.py` docstring (line 17-19): "fake provenance 생성 금지, existing metadata 손실 금지,
  retrieval ranking/text 변경 금지"
- `core/evidence_adapters/tsu_adapter.py::RankedCandidateEvidenceAdapter` (line 210):
  RankedCandidate → Evidence 변환은 adapter 패턴으로, 입력이 RankedCandidate뿐
- `core/evidence_pool.py` docstring (line 20-24): "No score calculation, No re-ranking,
  No Evidence mutation, No retrieval execution"
- `core/grounded_synthesis_input.py` docstring (line 19): "ADR-036 B9 금지 import 없음"
- P8 테스트: `tests/test_grounded_failure_paths.py::test_stub_does_not_expand_interpretation` (line 473) —
  stub이 확대 해석하지 않음을 확인
- P11 항목 7: `requests/httpx/urllib/socket` import 없음 (외부 검색 불가)

---

## 5. Multi-Query Assembly (§13-Q3, Q4 답)

**Q3: 여러 질의의 evidence가 하나의 pool로 조립되면서 provenance가 손상되지 않는가?**

**답: 손상되지 않는다.** AssemblyManifest(P3A)가 EvidencePool의 overwrite 정책과 무관하게
질의→evidence_id 연관을 완전히 보존한다.

근거:
- `core/evidence_assembly.py::AssemblyManifest` (line 67-80):
  "질의 -> evidence_id 연관을 EvidencePool의 overwrite 정책과 무관하게 보존"
  `by_query_order`: 질의 순서대로 (QuerySpec, [evidence_id, ...])
  `queries_for(evidence_id)`: evidence_id → 이 근거를 찾은 모든 QuerySpec.query (line 83)
- P3A manifest 구성은 EvidencePool 내부 상태(_evidences, _index)에 접근하지 않음 (line 74-75)
- 테스트: `tests/test_evidence_assembly.py::test_manifest_queries_for_duplicate_evidence` (line 514) —
  중복 evidence가 여러 질의에서 발견될 때 manifest가 모두 기록함을 확인
- 테스트: `tests/test_evidence_assembly.py::test_manifest_key_matches_pool_evidence_id_when_tsu_id_missing` (line 631) —
  tsu_id 결측 시 fallback 경로에서도 manifest key가 실제 evidence_id와 일치함을 확인
- P3A 커밋 메시지: "r2: tsu_id 결측 폴백 경로에서 manifest key가 실제 evidence_id와 어긋남 → REWORK,
  r3: _resolve_evidence_id 재사용으로 해소"

**Q4: 동일 Evidence가 여러 질의에서 발견될 때 P2 정책이 유지되는가?**

**답: 유지된다.** P2의 duplicate overwrite 정책(마지막 값 유지)이 그대로 적용된다.

근거:
- `core/evidence_pool.py` docstring (line 42-53): "Duplicate identity policy: When add() encounters an
  evidence_id that already exists, the NEW evidence OVERWRITES the existing one."
- 테스트: `tests/test_evidence_pool.py::test_duplicate_overwrites_value` (line 147) —
  중복 evidence_id가 새 값으로 덮어씌워짐을 확인
- 테스트: `tests/test_evidence_pool.py::test_duplicate_does_not_increase_len` (line 173) —
  중복 추가 시 pool 길이가 증가하지 않음을 확인
- 테스트: `tests/test_evidence_pool.py::test_duplicate_preserves_insertion_position` (line 186) —
  중복 overwrite가 삽입 순서를 변경하지 않음을 확인
- 테스트: `tests/test_evidence_assembly.py::test_duplicate_overwrite_policy` (line 363) —
  multi-query에서 duplicate가 overwrite됨을 확인
- P2 커밋 메시지: "duplicate overwrite policy, 마지막 값 유지"

---

## 6. Grounded Synthesis 요약

### Synthesis Input (P4)
- `core/grounded_synthesis_input.py::SynthesisInput` (line 37): frozen dataclass
- `build_synthesis_input()`: 라운드로빈 절단, 중복 evidence_id 1회만 포함
- 출처 라벨: source_file → document_title → '미상' (가짜 provenance 생성 금지)
- 테스트: `tests/test_grounded_synthesis_input.py` — 16개 테스트 (AC1-AC9)

### Claim Generation (P5)
- `core/grounded_claims.py::Claim` (line 38): frozen dataclass, claim_id/text/evidence_ids/valid
- `bind_claims()` (line 57): evidence_ids ⊆ included_evidence_ids 판정
- 무효 Claim도 valid=False로 표시만 함 (폐기하지 않음, ADR-036 B4)
- 테스트: `tests/test_grounded_claims.py` — 20개 테스트 (AC1-AC6)
- **남은 사항**: claim_{idx:03d} ID가 단일 bind_claims() 호출 내에서만 고유
  (P5 커밋 메시지 명시, 아직 실사용 문제로 이어지지 않음)

### Grounded Answer Assembly (P6)
- `core/grounded_answer.py::GroundedAnswer` (line 37): frozen dataclass
- 상태 판정: no_evidence → conflicting → no_valid_claim → grounded 순서
- **자동 충돌 탐지 부재**: 호출자 명시 플래그(conflicting=True)로만 진입
  (`core/grounded_answer.py` line 19: "자동 충돌 상태 판정(텍스트 비교, 어휘 분석 등) 금지")
- 테스트: `tests/test_grounded_answer.py` — 17개 테스트 (AC1-AC6)

---
---

## 7. Citation / Provenance (§13-Q5 답)

**Q5: 최종 factual claim을 Evidence까지 추적할 수 있는가?**

**답: 구조적으로 추적 가능하지만, span 일치 판정에는 한계가 있다.**

근거:
- `core/grounded_citation.py::check_citation_provenance()` (line 120):
  (1) id_exists: evidence_id in included_evidence_ids
  (2) span_found_in_text: Evidence.text.find(span_text) >= 0
  (3) provenance_traceable: Evidence.has_provenance
- span 판정 기준 (`core/grounded_citation.py` line 43-56):
  "최소 길이: 5자 이상, exact substring match, case-sensitive"
- P7 REWORK: id_exists=False면 하위 검사 없이 자동 False(short-circuit)로 해소
  (pool엔 실재하지만 included_evidence_ids에서 max_evidence 절단으로 제외된 근거 인용 케이스)
- 테스트: `tests/test_grounded_citation.py::test_ac1_short_circuit_when_evidence_in_pool_but_excluded` (line 485)
- 테스트: `tests/test_grounded_citation.py::test_ac2_span_found` (line 165),
  `tests/test_grounded_citation.py::test_ac2_span_not_found` (line 176),
  `tests/test_grounded_citation.py::test_ac4_span_too_short` (line 230)
- P9 실모델 실행 (`GS-P09-REAL-MODEL-RUN-RESULTS.md`):
  A1(로마서 8:1-4) → grounded 도달, claim.evidence_ids에 실제 evidence_id 포함 확인

**한계**: span 일치 판정 기준이 "5자 이상 exact substring"이므로, 한국어 답변과 영어 원문 사이에서는
거의 항상 실패한다. P9 실측에서 확인됨 — G2(조작된 인물) 질의는 insufficient_evidence로 올바르게 종료.

---

## 8. Failure Handling (§13-Q6 답)

**Q6: 근거가 부족할 때 시스템이 추측하지 않고 부족함을 표현하는가?**

**답: 예.** 세 가지 insufficient 경로가 모두 구현되어 있다.

근거:
- `core/grounded_answer.py::assemble_grounded_answer()` (line 53-59):
  1. included_evidence_ids 비어 → "insufficient_evidence", reason="no_evidence"
  2. claims 전부 valid=False → "insufficient_evidence", reason="no_valid_claim"
  3. conflicting=True → "conflicting_evidence" (자동 판정 아님, 호출자 명시 플래그만)
- P6 docstring (line 19): "자동 충돌 상태 판정(텍스트 비교, 어휘 분석 등) 금지"
- P6 테스트: `tests/test_grounded_answer.py::test_ac1_empty_included` (line 63) — 빈 pool → insufficient
- P6 테스트: `tests/test_grounded_answer.py::test_ac2_all_invalid` (line 92) — 전부 invalid → insufficient
- P8 테스트: `tests/test_grounded_failure_paths.py::test_empty_pool_gives_insufficient_status` (line 117)
- P8 테스트: `tests/test_grounded_failure_paths.py::test_no_valid_claims_becomes_insufficient` (line 533)
- P9 실모델: G2(조작된 인물) → insufficient_evidence/no_valid_claim (실측 확인)

P8에서 6개 실패 경로 케이스를 모두 검증:
| Case | 테스트명 | 결과 |
|------|----------|------|
| A: 검색 결과 없음 | `test_empty_pool_gives_insufficient_status` (line 117) | PASS |
| B: 근거 1건뿐, 관련성 낮음 | `test_single_evidence_span_not_found` (line 133) | PASS |
| C: 다중 질의 중 일부만 결과 | `test_partial_query_results_assembly_continues` (line 218) | PASS |
| D: 중복 Evidence | `test_duplicate_evidence_pool_overwrite_policy` (line 301) | PASS |
| E: Evidence 충돌 | `test_conflicting_evidence_both_claims_preserved` (line 353) | PASS |
| F: 근거가 질문과 무관 | `test_irrelevant_evidence_citation_fails_span_check` (line 503) | PASS |

---

## 9. Regression (§13-Q7 답)

**Q7: Grounded Synthesis 추가로 기존 retrieval 결과·인프라가 손상되지 않았는가?**

**답: 손상되지 않았다.** P10 회귀 테스트에서 확인.

핵심 수치 (P10 보고서):
| | Baseline (`1c0117a7`) | HEAD (`5738c709`) |
|---|---|---|
| Passed | 3203 | 3423 (+220 GS 신규 테스트) |
| Failed | 0 | 4 (GS와 무관) |

HEAD 실패 4건 분석 (P10 §2.3):
- 2건: `config.yaml nae_pd.enabled` 로컬 staged 변경 (환경 격차)
- 2건: `NAE/corpus/raw` 하위 파일 부재 (환경 격차)
- **GS와 무관한 테스트 4건** — 기존 파이프라인 무변동 확인

P10 핵심 확인:
- `core/retrieval.py`: 1c0117a7..HEAD 0줄 변경
- `core/hybrid_candidate_pipeline.py`: 0줄 변경
- `core/candidate_generator.py`: 0줄 변경
- TSU/Qdrant/Tantivy/RetrievalEngine/HybridRetriever/CandidateGenerator 6개 컴포넌트 무수정
- GS 파일의 retrieval import는 전부 읽기 전용 (RankedCandidate 타입 참조)

P11 보고서 링크: `docs/grounded_synthesis/GS-P11-PRODUCTION-SAFETY-REPORT.md`
- TSU mutation=0 (sha256 기준선 일치)
- Tantivy mutation=0 (aggregate sha256 132파일 일치)
- Corpus regeneration=0 (grep으로 호출이력 없음 확인)
- Benchmark mutation=0 (output/bench/ git status 무변경)

---

## 10. Production Safety

P11 보고서: `docs/grounded_synthesis/GS-P11-PRODUCTION-SAFETY-REPORT.md`

9개 항목 전부 "0" 또는 "해당 없음":
1. TSU mutation=0 (sha256 기준선 일치)
2. Qdrant mutation=해당없음 (미실행 — Qdrant 현재/기존 모두 정지)
3. Tantivy mutation=0 (aggregate sha256 132파일 일치)
4. Corpus regeneration=0 (GS 코드/테스트가 merge_nae_corpus.py, process_unprocessed_nae.py를 호출하지 않음)
5. Benchmark mutation=0 (output/bench/ git status 무변경)
6. No new retrieval path=0 (1c0117a7..HEAD 기준 core/retrieval.py 등 0-diff)
7. No hidden retrieval/external search=0 (requests/httpx/urllib/socket import 없음)
8. No LLM retrieval=0 (retrieval 단계에 ollama 호출 없음)
9. No corpus mutation=0 (1·3과 동일 근거)

---
---

## 11. Scope Integrity

### git log --oneline 1c0117a7..HEAD 전체

```
06e5a47b docs(grounded-synthesis): Phase 11 — Production Safety Audit
0d265afc docs(grounded-synthesis): Phase 10 — Regression/Architecture Integrity Audit
5738c709 feat(grounded-synthesis): Phase 9 — Full Grounded Synthesis Integration Test
e5eecd5f test(grounded-synthesis): Phase 8 — Negative/Failure-path Validation
f9f4a55f feat(grounded-synthesis): Phase 7 — Citation/Provenance Validation
2e3eaeea feat(grounded-synthesis): Phase 6 — Grounded Answer Assembly
20bf6ddd feat(grounded-synthesis): Phase 5 — Claim-Evidence Binding
9eae5167 feat(grounded-synthesis): Phase 4 — SynthesisInput Boundary
14fccb54 feat(evidence): Grounded Synthesis Phase 3+3A — Multi-Query Evidence Assembly + Manifest
db677ac6 feat: add EvidencePool and retrieval boundary integration (Phase 2)
2dd40d2e feat(evidence): Grounded Synthesis Phase 1 — Evidence Data Model + Corpus Identity Adapter
```

총 11개 커밋 (P1→P11). P12는 이 문서(산출물)뿐.

### git diff --stat 1c0117a7..HEAD 전체

```
 core/evidence_adapters/__init__.py                 |  17 +-
 core/evidence_adapters/tsu_adapter.py              | 342 ++++++++++
 core/evidence_assembly.py                          | 233 +++++++
 core/evidence_model.py                             | 142 ++++
 core/evidence_pool.py                              | 190 +++++
 core/grounded_answer.py                            | 136 ++++
 core/grounded_citation.py                          | 190 +++++
 core/grounded_claims.py                            | 129 ++++
 core/grounded_synthesis_input.py                   | 151 ++++
 docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md | 159 +++++
 docs/grounded_synthesis/GS-P10-REGRESSION-REPORT.md | 239 +++++++
 docs/grounded_synthesis/GS-P11-PRODUCTION-SAFETY-REPORT.md | 262 +++++++
 scripts/grounded_synthesis_integration_demo.py     | 316 +++++++++
 tests/test_evidence_assembly.py                    | 759 +++++++++++++++++++++
 tests/test_evidence_model.py                       | 645 +++++++++++++++++
 tests/test_evidence_pool.py                        | 634 +++++++++++++++++
 tests/test_grounded_answer.py                      | 355 ++++++++++
 tests/test_grounded_citation.py                    | 513 ++++++++++++++
 tests/test_grounded_claims.py                      | 344 ++++++++++
 tests/test_grounded_failure_paths.py               | 658 ++++++++++++++++++
 tests/test_grounded_synthesis_input.py             | 424 ++++++++++++
 tests/test_grounded_synthesis_integration.py       | 335 ++++++++++
 22 files changed, 7172 insertions(+), 1 deletion(-)
```

**승인 범위 밖 변경 0건 확인**: 모든 파일이 WO 허용 파일 목록에 포함된다.
- core/ 하위: 9개 신규/수정 파일 (모두 GS 관련)
- docs/grounded_synthesis/: 3개 보고서 파일 (P9/P10/P11)
- scripts/: 1개 demo 스크립트
- tests/: 8개 테스트 파일
- 기존 core/retrieval.py, core/hybrid_candidate_pipeline.py, core/candidate_generator.py: 0줄 변경

---
---

## 12. Remaining Limitations

다음 한계는 숨긴 가정 없이 전부 기록한다.

### (a) D2 미통합 상태

Grounded Synthesis(P1-P11)가 생성한 EvidencePool, SynthesisInput, Claim, GroundedAnswer,
CitationCheckReport는 **아직 운영 UI/생성 경로와 연결되지 않았다**.

근거:
- P9 `scripts/grounded_synthesis_integration_demo.py` (line 1): "stub LLM 결정적 통합 테스트"
  와 "실제 QueryProcessor/HybridQueryProcessor + 실제 Ollama 호출 참조 구현"이 별도
- P9 커밋 메시지: "stub LLM만 사용 — 실모델은 P9" (P6/P5도 동일)
- GS 코드가 NAE UI, ingestion pipeline, corpus processing을 import하거나 호출하지 않음
- `core/grounded_synthesis_input.py` docstring (line 19): "ADR-036 B9 금지 import 없음"
- P11 항목 4: "GS 코드/테스트가 merge_nae_corpus.py, process_unprocessed_nae.py를 호출하지 않음"

즉, GS 파이프라인은 독립적으로 검증되었지만, 실제 NAE 사용자-facing 경로에 통합되지 않았다.

### (b) 자동 충돌 탐지 부재

P6 `assemble_grounded_answer()`는 conflicting_evidence 상태를 **자동으로 감지하지 않는다**.
호출자가 명시적으로 `conflicting=True` 플래그를 넘겨야 진입한다.

근거:
- `core/grounded_answer.py` docstring (line 19): "자동 충돌 상태 판정(텍스트 비교, 어휘 분석 등) 금지"
- `core/grounded_answer.py::assemble_grounded_answer()` signature (line 49): `conflicting: bool = False`
- 테스트: `tests/test_grounded_answer.py::test_ac5_conflicting_requires_explicit_flag` (line 218)
- 테스트: `tests/test_grounded_failure_paths.py::test_conflicting_status_flag_not_auto_detected` (line 436)

텍스트 비교, 어휘 분석, 의미적 모순 감지 등 자동 충돌 탐지는 구현되지 않았다.

### (c) span 일치 판정 기준의 한계

P7 `check_citation_provenance()`의 span 판정 기준은:
- 최소 길이: 5자 이상 (`core/grounded_citation.py` line 43)
- exact substring match, case-sensitive (`core/grounded_citation.py` line 47-49)

이 기준은 **한국어 답변과 영어 원문 사이에서 거의 항상 실패한다**.

근거:
- P7 docstring (line 8): "의미적 뒷받침 여부는 다루지 않는다"
- P7 REWORK 기록: "Pool엔 실재하지만 included_evidence_ids에서 max_evidence 절단으로 제외된
  근거를 인용해도 span/provenance가 True로 나오는 결함" — short-circuit로 해소됨
- P9 실모델 실행 (`GS-P09-REAL-MODEL-RUN-RESULTS.md`):
  A1(로마서 8:1-4)은 grounded 도달했지만, 이는 영어 원문이 English 답변에 그대로 포함되었기 때문.
  한국어 번역문이 영어 원문을 exact substring으로 포함하는 경우만 통과.
- 테스트: `tests/test_grounded_citation.py::test_ac2_case_sensitive` (line 187) —
  case-sensitive 판정 확인 (대소문자 불일치 시 실패)

### (d) Claim ID 고유성 범위

P5 `bind_claims()`에서 생성되는 claim_id (`claim_{idx:03d}`)는 **단일 bind_claims() 호출 내에서만 고유**하다.
여러 synthesis 결과를 합칠 때 전역 고유성을 보장하지 않는다.

근거:
- P5 커밋 메시지: "남은 사항(비차단, P6 전달 필요): claim_{idx:03d} ID가 단일 bind_claims()
  호출 내에서만 고유 — 여러 synthesis 결과를 합칠 때 전역 고유성 별도 설계 필요"
- `core/grounded_claims.py::Claim` (line 41): `claim_id: str` — 타입만 지정, 고유성 범위 명시 없음

### (e) EvidencePool duplicate overwrite 정책의 정보 손실

동일 evidence_id가 여러 질의에서 발견될 때 P2 overwrite 정책(마지막 값 유지)이 적용되므로,
이전에 삽입된 버전의 metadata/score가 손실된다.

근거:
- `core/evidence_pool.py` docstring (line 46-53): overwrite 정책 명시
- AssemblyManifest(P3A)가 query↔evidence_id 연관을 보존하지만, overwrite로 사라진 evidence 버전 자체는 복원 불가

### (f) SynthesisInput max_evidence 절단에 따른 provenance 단절

P4 `build_synthesis_input()`의 max_evidence 절단으로 excluded된 evidence_id를
P5 Claim이 인용하면 P7 citation check에서 id_exists=False가 되지만,
EvidencePool에는 실재하므로 span_found_in_text=True가 나올 수 있다.

근거:
- P7 REWORK 기록: "id_exists=False면 하위 검사 없이 자동 False(short-circuit)"로 해소됨
- 하지만 이 short-circuit는 id_exists가 False인 경우에만 적용 — id_exists=True지만
  max_evidence 절단으로 excluded된 경우의 처리는 명시되지 않음

### (g) P9 실모델 실행의 GPU 의존성

P9 `scripts/grounded_synthesis_integration_demo.py`는 실제 Ollama 모델 호출을 포함하므로
GPU 환경이 필요하다. pytest 테스트 스위트에 합산되지 않는다.

근거:
- P9 커밋 메시지: "scripts/grounded_synthesis_integration_demo.py: 실제 QueryProcessor/
  HybridQueryProcessor + 실제 Ollama(DEFAULT_GEN_MODEL) 호출 참조 구현 (pytest 미실행, GPU 의존)"
- `GS-P09-REAL-MODEL-RUN-RESULTS.md` (line 7): "이 결과는 자동 테스트 PASS 수치에 합산되지 않음"

### (h) TSU dataset git 미추적

TSU dataset(204,262건)이 git 추적 파일이 아니므로, baseline worktree에서 실제 실행 비교가 불가능하다.
P10은 `core/retrieval.py` 0-diff로 대체 입증했다.

근거:
- P10 보고서: "TSU dataset이 git 미추적 파일이라 baseline worktree에서 실제 실행 비교가 불가능했음을
  명시하고, core/retrieval.py 0-diff로 대체 입증"

---
---

## 13. Evidence Summary

### Phase별 테스트 수

| Phase | 테스트 파일 | 테스트 수 | 커밋 |
|-------|-------------|-----------|------|
| P1 | `tests/test_evidence_model.py` | 51 | `2dd40d2e` |
| P2 | `tests/test_evidence_pool.py` | 33 | `db677ac6` |
| P3+3A | `tests/test_evidence_assembly.py` | 20 | `14fccb54` |
| P4 | `tests/test_grounded_synthesis_input.py` | 16 | `9eae5167` |
| P5 | `tests/test_grounded_claims.py` | 20 | `20bf6ddd` |
| P6 | `tests/test_grounded_answer.py` | 17 | `2e3eaeea` |
| P7 | `tests/test_grounded_citation.py` | 27 | `f9f4a55f` |
| P8 | `tests/test_grounded_failure_paths.py` | 18 | `e5eecd5f` |
| P9 | `tests/test_grounded_synthesis_integration.py` | 7 | `5738c709` |
| P10 | 회귀 테스트 (전체) | 3423 passed / 4 failed | `0d265afc` |
| P11 | 안전 감사 (9항목) | 9/9 항목 확인 | `06e5a47b` |
| **누계** | | **220 GS 신규 + 3203 기존 = 3423** | |

### 실모델 실행 결과 링크

- `docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md`
- Query G2 (조작된 인물): `insufficient_evidence` / `no_valid_claim` — 정상
- Query A1 (로마서 8:1-4): `grounded` — 정상
- Query B1: `grounded` — 정상

---

## 14. Recommendation

CUE READ-ONLY FINAL VALIDATION REQUESTED
