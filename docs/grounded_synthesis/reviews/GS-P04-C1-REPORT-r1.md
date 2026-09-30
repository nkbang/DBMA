# PHASE 04 WORK ORDER REPORT

## 1. Files changed

```
 M config.yaml
 M core/candidate_generator.py
 M core/hybrid_candidate_pipeline.py
 A  scripts/merge_nae_corpus.py
 A  scripts/process_unprocessed_nae.py
 A  scripts/test_default_corpus_query.py
?? core/grounded_synthesis_input.py
?? docs/grounded_synthesis/
?? tests/test_grounded_synthesis_input.py
```

**GS 관련 신규 파일 (2건):**
- `core/grounded_synthesis_input.py` (신규, 150줄)
- `tests/test_grounded_synthesis_input.py` (신규, 424줄)

**기존 staged 6건은 열람·수정·stage/unstage 모두 하지 않음.**

## 2. Existing Architecture Verification

읽은 파일 및 확인한 인터페이스:

| 파일 | 확인 내용 |
|---|---|
| `core/evidence_model.py` | `Evidence` dataclass: `evidence_id`, `text`, `source_file`, `document_title`, `chunk_id`, score 필드들. frozen=True. |
| `core/evidence_pool.py` | `EvidencePool`: `add()`, `get()`, `all()`, `__len__`, `__contains__`. `all()`은 삽입 순서 보존. |
| `core/evidence_assembly.py` | `AssemblyManifest`: `by_query_order: list[tuple[QuerySpec, list[str]]]`, `evidence_to_queries: dict[str, list[str]]`. `QuerySpec`: `query`, `role`, `order`. |

모든 인터페이스는 읽기 전용으로 확인 — 수정 없음.

## 3. Design

### 공개 API 시그니처 (ADR-036 B8 정본)

```python
@dataclass(frozen=True)
class SynthesisInput:
    query_specs: list[QuerySpec]          # P3 QuerySpec 재사용
    included_evidence_ids: list[str]      # 순서 = 프롬프트에 들어간 순서
    excluded_evidence_ids: list[str]      # 예산 초과로 뺀 것들
    truncated: bool                       # excluded가 있으면 True
    prompt_text: str                      # 실제로 LLM에 전달될 텍스트


def build_synthesis_input(
    pool: EvidencePool,
    manifest: AssemblyManifest,
    max_evidence: int,
) -> SynthesisInput:
    """절단 규칙: 질의 순서(manifest.by_query_order) → 각 질의 내부 원 순위 순서로
    라운드로빈하며 evidence_id를 채운다. 이미 included에 들어간 evidence_id는
    건너뛴다(중복 방지, 순서는 최초 등장 기준). max_evidence에 도달하면 멈추고
    나머지는 전부 excluded_evidence_ids에 담는다. 점수를 읽거나 비교하지 않는다.

    prompt_text는 included_evidence_ids 순서대로 EvidencePool.get(id).text를
    이어붙여 만든다. 각 항목 앞에 "[출처: {source_file 또는 document_title 또는
    '미상'}]"을 붙인다 (가짜 출처를 만들지 않음).
    """
```

## 4. Implementation notes

- **라운드로빈 알고리즘**: `remaining` 리스트로 각 질의의 남은 evidence_id를 추적. 각 round에서 모든 질의를 순회하며 하나씩 pop. 이미 seen인 eid는 skip (중복 제거).
- **excluded 처리**: included에 포함되지 않고 remaining에 남아있는 모든 eid를 excluded로 기록.
- **prompt_text**: `[출처: {source_file 또는 document_title 또는 '미상'}]\n{text]` 형식. pool.get()이 None을 반환하면 "(증거 ID {eid} — text 없음)"으로 처리.
- **점수 접근 0회**: grep 검증(AC8) 통과. `.final_score`, `.retrieval_score`, `sorted(`, `sort(` 모두 부재.
- **금지 import 0건**: grep 검증(AC9) 통과. ollama, qdrant_client, tantivy, retrieval 클래스 등 모두 부재.

## 5. Tests

**명령:**
```bash
cd ~/DBMA && source ~/envs/dbma311/bin/activate && PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_grounded_synthesis_input.py -v --tb=short
```

**출력 마지막 줄:**
```
============================== 16 passed in 0.08s ==============================
```

**테스트명 목록 (16건):**
1. `TestAC1_IncludedExcludedCompleteness::test_ac1_all_evidence_accounted_for`
2. `TestAC2_NoTruncation::test_ac2_pool_smaller_than_max`
3. `TestAC2_NoTruncation::test_ac2_pool_equal_to_max`
4. `TestAC3_Truncation::test_ac3_pool_larger_than_max`
5. `TestAC4_RoundRobinOrder::test_ac4_roundrobin_sequence`
6. `TestAC5_DuplicateEvidenceId::test_ac5_same_eid_across_queries`
7. `TestAC6_PromptTextContent::test_ac6_included_text_present`
8. `TestAC6_PromptTextContent::test_ac6_excluded_text_absent`
9. `TestAC7_MissingSourceLabel::test_ac7_none_source_file`
10. `TestAC8_NoScoreAccess::test_ac8_grep_no_score_access`
11. `TestAC9_NoForbiddenImports::test_ac9_grep_no_forbidden_imports`
12. `TestSynthesisInputStructure::test_synthesis_input_is_frozen_dataclass`
13. `TestSynthesisInputStructure::test_synthesis_input_all_fields_present`
14. `TestBuildSynthesisInputEdgeCases::test_empty_pool`
15. `TestBuildSynthesisInputEdgeCases::test_invalid_max_evidence`
16. `TestBuildSynthesisInputEdgeCases::test_query_specs_preserved`

## 6. AC 대조표

| AC-id | 충족 여부 | 근거: 테스트명 또는 출력 |
|---|---|---|
| AC1 | 충족 | `test_ac1_all_evidence_accounted_for` — pool의 전체 집합과 included+excluded가 정확히 일치 |
| AC2 | 충족 | `test_ac2_pool_smaller_than_max`, `test_ac2_pool_equal_to_max` — truncated=False, excluded=[] |
| AC3 | 충족 | `test_ac3_pool_larger_than_max` — truncated=True, len(included)==max_evidence |
| AC4 | 충족 | `test_ac4_roundrobin_sequence` — [e1, e4, e2] 순서 정확히 검증 |
| AC5 | 충족 | `test_ac5_same_eid_across_queries` — 중복 eid는 1회만 등장 |
| AC6 | 충족 | `test_ac6_included_text_present`, `test_ac6_excluded_text_absent` — 텍스트 포함/미포함 검증 |
| AC7 | 충족 | `test_ac7_none_source_file` — "[출처: 미상]" 확인 |
| AC8 | 충족 | `test_ac8_grep_no_score_access` — grep returncode==1 (매칭 없음) |
| AC9 | 충족 | `test_ac9_grep_no_forbidden_imports` — grep returncode==1 (매칭 없음) |

## 7. Production safety

- **R5 (기존 코드 무수정)**: `core/evidence_model.py`, `core/evidence_pool.py`, `core/evidence_assembly.py`, `core/retrieval.py`, `core/generation.py` 모두 미접함. git status에서 `??` (untracked)로 신규 파일만 표시됨.
- **R6 (금지 import)**: AC9 테스트 + 수동 grep으로 확인. import 목록: `logging`, `dataclasses`, `typing`, `core.evidence_assembly`, `core.evidence_model`, `core.evidence_pool` — 모두 허용.
- **R7 (파일 쓰기 금지)**: 이 모듈에서 `open()`, `write_text()` 호출 0건. 순수 함수만 구현.

## 8. Remaining issues

1. **라운드 로빈의 관련성 한계**: ADR-036 Consequences에서 지적된 대로, 라운드 로빈은 관련성 높은 근거가 빠질 수 있다. 이는 P9 실측으로 재검토 대상.
2. **pool에 없는 evidence_id 처리**: manifest에 있지만 pool에 없는 경우 "(증거 ID {eid} — text 없음)"으로 처리. 실제 운영에서 이 케이스가 얼마나 발생할지 미검증.
3. **G0 staged 변경 보류**: HQ 결정 전까지 6건의 non-GS staged 변경은 untouched. GS 커밋 시 경로 지정 커밋 필요.

## 9. Phase recommendation

CUE READ-ONLY REVALIDATION REQUESTED
