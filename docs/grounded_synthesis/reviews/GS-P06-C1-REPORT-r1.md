# PHASE 06 WORK ORDER REPORT

## 1. Files changed

```
 A core/grounded_answer.py
 A tests/test_grounded_answer.py
```

**GS 관련 신규 파일 (2건):**
- `core/grounded_answer.py` (신규, 136줄)
- `tests/test_grounded_answer.py` (신규, 355줄, 17 테스트)

## 2. Existing Architecture Verification

읽은 파일 및 확인한 인터페이스:

| 파일 | 확인한 인터페이스 |
|---|---|
| `core/grounded_claims.py` | `Claim`: `claim_id`, `text`, `evidence_ids`, `valid`. frozen dataclass. |
| `core/grounded_synthesis_input.py` | `SynthesisInput`: `query_specs`, `included_evidence_ids`, `excluded_evidence_ids`, `truncated`, `prompt_text`. frozen dataclass. |
| `docs/grounded_synthesis/GS-P06-WO-Grounded-Answer.md` | ADR-036 B8 시그니처, 상태 판정 규칙, text 구성 규칙 |

모든 인터페이스는 읽기 전용으로 확인 — 수정 없음.

## 3. Design

### 공개 API 시그니처 (ADR-036 B5, B8 정본)

```python
@dataclass(frozen=True)
class GroundedAnswer:
    status: Literal["grounded", "insufficient_evidence", "conflicting_evidence"]
    claims: list[Claim]
    text: str
    insufficiency_reason: Optional[str]


def assemble_grounded_answer(
    claims: list[Claim],
    synthesis_input: SynthesisInput,
    conflicting: bool = False,
) -> GroundedAnswer:
    """Claim[]을 GroundedAnswer로 조립한다."""
```

### 상태 판정 규칙 (우선순위 고정)

| 우선순위 | 조건 | status | insufficiency_reason |
|---|---|---|---|
| 1 | `included_evidence_ids == []` | `insufficient_evidence` | `no_evidence` |
| 2 | `conflicting=True` | `conflicting_evidence` | `None` |
| 3 | 모든 claim이 `valid=False` | `insufficient_evidence` | `no_valid_claim` |
| 4 | valid=True claim 존재 | `grounded` | `None` |
| 5 | claims가 빈 리스트 | `insufficient_evidence` | `no_claims` |

### text 구성 규칙

- **grounded**: valid claim들의 `text`를 `\n\n`로 이어붙임 (invalid claim text 제외)
- **insufficient**: 고정 문구 `"이 질문은 현재 등록된 자료로는 답할 수 없습니다."`
- **conflicting**: `"자료들이 서로 다른 견해를 제시합니다."` + 각 claim을 `[evidence_ids] text` 형식으로 병기

## 4. Implementation notes

- **상태 우선순위 중요**: `included_evidence_ids == []`를 가장 먼저 검사. 이 순서가 바뀌면 AC1이 깨짐.
- **invalid claim 폐기 금지**: ADR-036 B4에 따라 invalid claim도 `GroundedAnswer.claims`에 그대로 유지. text 구성 시에만 제외.
- **자동 충돌 탐지 금지**: 텍스트 유사도 비교, 어휘 분석 등 자동 판정 로직 없음. 호출자가 `conflicting=True` 플래그를 명시해야 진입.
- **금지 표현 미포함**: insufficient 상태 text가 "일반적으로", "일반적인 신학적 관점에서" 등 금지 표현을 포함하지 않음 (고정 문구 사용).
- **core/generation.py 격리**: import 0회, `_GROUNDING_DIRECTIVE` 접근 0회. grep 검증 통과.
- **stub LLM**: 이 Phase는 LLM 호출 없이 구조체 조립만 수행.

## 5. Tests executed

```bash
python -m pytest tests/test_grounded_answer.py -v --tb=short
```

**결과: 17/17 PASSED (0.11s)**

| 테스트 클래스 | 테스트 수 | 커버리지 |
|---|---|---|
| `TestAC1_NoEvidencePool` | 2 | AC1: 빈 evidence pool → insufficient_evidence |
| `TestAC2_AllInvalidClaims` | 2 | AC2: 모든 claim invalid → insufficient_evidence |
| `TestAC3_GroundedStatus` | 2 | AC3: valid claim 존재 → grounded, invalid text 제외 |
| `TestAC4_NoForbiddenPhrases` | 1 | AC4: insufficient text가 금지 표현 미포함 |
| `TestAC5_NoAutoConflictDetection` | 2 | AC5: grep으로 자동 충돌 탐지 부재 + 명시 플래그만 사용 |
| `TestAC6_NoGenerationCall` | 2 | AC6: grep으로 generation.py import/접근 부재 |
| `TestGroundedAnswerStructure` | 3 | frozen dataclass, 필드 정합성, status 리터럴 |
| `TestAssembleGroundedAnswerEdgeCases` | 3 | 빈 claims, conflicting text 구조, mixed valid claims |

## 6. Validation statistics

| 항목 | 결과 |
|---|---|
| 테스트 통과율 | 17/17 (100%) |
| grep AC5 (자동 충돌 탐지 부재) | PASS |
| grep AC6 (generation.py 격리) | PASS |
| frozen dataclass 검증 | PASS |
| status 리터럴 검증 | PASS |
| insufficient text 금지 표현 | PASS |

## 7. Remaining blockers

- **claim_id 중복 가능성**: `bind_claims`를 여러 번 호출할 때 `claim_{idx:03d}`가 중복될 수 있음 (STOP 조건으로 문서화, 미수정).
- **P9 실모델 연동**: 현재는 stub 구조체 조립만. 실제 LLM 연동은 별도 Phase에서 처리.
