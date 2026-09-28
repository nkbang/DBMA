# PHASE 05 WORK ORDER REPORT

## 1. Files changed

```
 M config.yaml
 M core/candidate_generator.py
 M core/hybrid_candidate_pipeline.py
 A  scripts/merge_nae_corpus.py
 A  scripts/process_unprocessed_nae.py
 A  scripts/test_default_corpus_query.py
?? core/grounded_claims.py
?? docs/grounded_synthesis/
?? tests/test_grounded_claims.py
```

**GS 관련 신규 파일 (2건):**
- `core/grounded_claims.py` (신규, 128줄)
- `tests/test_grounded_claims.py` (신규, 353줄)

**기존 staged 6건은 열람·수정·stage/unstage 모두 하지 않음.**

## 2. Existing Architecture Verification

읽은 파일 및 확인한 인터페이스:

| 파일 | 확인한 인터페이스 |
|---|---|
| `core/grounded_synthesis_input.py` | `SynthesisInput`: `query_specs`, `included_evidence_ids`, `excluded_evidence_ids`, `truncated`, `prompt_text`. frozen dataclass. |
| `core/evidence_model.py` | `Evidence`: `evidence_id`, `text`, `source_file`, `document_title` 등. frozen dataclass. |
| `core/evidence_pool.py` | `EvidencePool.get()`, `all()` 등. |
| `core/evidence_assembly.py` | `AssemblyManifest.by_query_order`, `QuerySpec`. |

모든 인터페이스는 읽기 전용으로 확인 — 수정 없음.

## 3. Design

### 공개 API 시그니처 (ADR-036 B4, B8 정본)

```python
@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    evidence_ids: list[str]
    valid: bool  # evidence_ids ⊆ synthesis_input.included_evidence_ids


class ClaimExtractor(Protocol):
    def extract(self, answer_text: str, synthesis_input: SynthesisInput) -> list[Claim]: ...


def bind_claims(
    raw_claims: list[tuple[str, list[str]]],  # (claim_text, cited_evidence_ids)
    synthesis_input: SynthesisInput,
) -> list[Claim]:
    """cited_evidence_ids ⊆ included_evidence_ids 여부로 valid를 결정한다.
    유효하지 않은 evidence_id를 포함해도 Claim을 폐기하지 않는다 — valid=False로
    표시만 한다(정보 손실 금지, ADR-036 B4).
    """
```

### StubClaimExtractor

```python
class StubClaimExtractor:
    def __init__(self, claims_map: dict[str, list[tuple[str, list[str]]]] | None = None) -> None:
        ...
    def extract(self, answer_text: str, synthesis_input: SynthesisInput) -> list[Claim]:
        """answer_text에서 미리 정한 claim 목록을 추출하고 결속한다."""
```

## 4. Implementation notes

- **valid 판정 로직**: `evidence_ids`가 비어있으면 False, 아니면 `all(eid in included_set for eid in evidence_ids)`.
- **claim_id 자동 할당**: `claim_{idx:03d}` 형식 (claim_000, claim_001, ...).
- **Claim 폐기 금지**: valid=False인 Claim도 리스트에 그대로 유지 (ADR-036 B4).
- **claim_guard.py 분리**: docstring에서 "위험 탐지 모듈(ClaimGuard)"로 간접 참조만 하고 import는 절대 하지 않음. grep 검증(AC5) 통과.
- **prompt_text 접근 0회**: bind_claims가 SynthesisInput의 ID 필드만 사용. grep 검증(AC6) 통과.

## 5. Tests

**명령:**
```bash
cd ~/DBMA && source ~/envs/dbma311/bin/activate && PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_grounded_claims.py -v --tb=short
```

**출력 마지막 줄:**
```
============================== 20 passed in 0.10s ==============================
```

**테스트명 목록 (20건):**
1. `TestAC1_ValidBinding::test_ac1_all_eids_included`
2. `TestAC1_ValidBinding::test_ac1_single_eid`
3. `TestAC2_InvalidBinding::test_ac2_one_eid_not_included`
4. `TestAC2_InvalidBinding::test_ac2_all_eids_not_included`
5. `TestAC2_InvalidBinding::test_ac2_excluded_eid`
6. `TestAC3_NoEvidence::test_ac3_empty_evidence_ids`
7. `TestAC4_Determinism::test_ac4_three_runs_identical`
8. `TestAC4_Determinism::test_ac4_stub_deterministic_no_network`
9. `TestAC5_NoClaimGuardImport::test_ac5_grep_no_claim_guard`
10. `TestAC6_ResponsibilityBoundary::test_ac6_bind_claims_uses_only_ids`
11. `TestAC6_ResponsibilityBoundary::test_ac6_grep_no_prompt_text_code_access`
12. `TestClaimStructure::test_claim_is_frozen_dataclass`
13. `TestClaimStructure::test_claim_all_fields_present`
14. `TestBindClaimsEdgeCases::test_empty_raw_claims`
15. `TestBindClaimsEdgeCases::test_multiple_claims_mixed_validity`
16. `TestBindClaimsEdgeCases::test_claim_ids_preserved`
17. `TestStubClaimExtractor::test_extract_no_match`
18. `TestStubClaimExtractor::test_extract_partial_match`
19. `TestStubClaimExtractor::test_extract_multiple_patterns`
20. `TestStubClaimExtractor::test_extract_invalid_eid`

## 6. AC 대조표

| AC-id | 충족 여부 | 근거: 테스트명 또는 출력 |
|---|---|---|
| AC1 | 충족 | `test_ac1_all_eids_included`, `test_ac1_single_eid` — valid=True 정확히 검증 |
| AC2 | 충족 | `test_ac2_one_eid_not_included`, `test_ac2_all_eids_not_included`, `test_ac2_excluded_eid` — valid=False + Claim 폐기 없음 |
| AC3 | 충족 | `test_ac3_empty_evidence_ids` — evidence_ids=[] → valid=False |
| AC4 | 충족 | `test_ac4_three_runs_identical` — 3회 반복 결과 동일. `test_ac4_stub_deterministic_no_network` — 구조 검증 |
| AC5 | 충족 | `test_ac5_grep_no_claim_guard` — grep returncode==1 (import 문 부재) |
| AC6 | 충족 | `test_ac6_bind_claims_uses_only_ids` — prompt_text 변경해도 동일 결과. `test_ac6_grep_no_prompt_text_code_access` — grep returncode==1 |

## 7. Production safety

- **R5 (기존 코드 무수정)**: `core/claim_guard.py`, `core/generation.py`, P1~P4 산출물 모두 미접함. git status에서 `??` (untracked)로 신규 파일만 표시됨.
- **R6 (금지 import)**: AC5 테스트 + 수동 grep으로 확인. import 목록: `logging`, `dataclasses`, `typing.Protocol`, `core.grounded_synthesis_input` — 모두 허용. claim_guard.py import 0건.
- **R7 (파일 쓰기 금지)**: 이 모듈에서 `open()`, `write_text()` 호출 0건. 순수 함수만 구현.
- **bind_claims 책임 경계**: AC6 테스트로 prompt_text/Evidence.text 접근 0임을 구조적으로 검증.

## 8. Remaining issues

1. **StubClaimExtractor의 패턴 매칭 방식**: 현재는 단순 부분 문자열 매칭. P9에서 실제 LLM 기반 구현으로 교체될 때 이 인터페이스 호환성 확인 필요.
2. **G0 staged 변경 보류**: HQ 결정 전까지 6건의 non-GS staged 변경은 untouched. GS 커밋 시 경로 지정 커밋 필요.
3. **Claim ID 충돌**: 현재 `claim_{idx:03d}`는 bind_claims 호출 내 순서만 반영. 여러 bind_claims 호출 간 ID 충돌 가능성 (운영에서는 UUID 등 고유 ID 필요).

## 9. Phase recommendation

CUE READ-ONLY REVALIDATION REQUESTED
