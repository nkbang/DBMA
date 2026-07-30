# C1 Task Order 023 — Sprint D: ClaimGuard (위험 주장 탐지 · 절대주장 차단 · 범위 한정 문구)

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P0 (Sprint A/B/C 후속, 검색 신뢰성 파이프라인 v2 마지막 핵심 단계)
**선행 작업**: Task Order 020/021/022 완료·검증됨(39/39 통과). `core/dataset_registry.py`의 `TrustTier`,
`core/parallel_retriever.py`의 `EvidenceCandidate`/`classify_evidence()`를 그대로 재사용한다. 재정의 금지.
**근거 문서**: [docs/architecture/DBMA-Search-Trust-Pipeline-Plan-v2.md](../../architecture/DBMA-Search-Trust-Pipeline-Plan-v2.md) §3 Sprint D
**작성일**: 2026-07-29
**모드 제약**: `core/retrieval.py`, `core/parallel_retriever.py` 절대 미접촉 (읽기 전용 import만).
UI(`ui/`) 연동은 이번 범위 밖 — 순수 로직 모듈만 구현한다.

---

## 1. 배경

Sprint C까지 완료되어 T1(본문 검색)/T2(큐레이션 태그) 두 축의 근거를 `EvidenceCandidate` 리스트로 얻을 수
있다. Sprint D는 이 근거들을 놓고 "이 근거로 이런 문장을 말해도 되는가"를 판정하는 `ClaimGuard`를
구현한다. **이번 Task Order는 판정 로직만 다룬다 — 실제 LLM 응답 생성 파이프라인에 끼워 넣는 것(어디서
호출할지)은 범위 밖이며, 다음 Task Order(Sprint D 통합 또는 UI 연동)에서 CUE가 별도로 설계한다.**

---

## 2. 구현 범위

### 2.1 신규 모듈 — `core/claim_guard.py`

**위험 표현 사전** (지시서 원문 그대로, 한국어 우선):

```python
ABSOLUTE_SUPERLATIVE_TERMS = [
    "최초", "처음", "가장 이른", "유일", "반드시", "전부", "항상", "절대", "명백히",
    "성경 전체에서", "정통 교리", "모든 학자", "학계의 합의",
    "성경이 가르친다", "원어의 정확한 의미는", "역사적으로 확실하다",
]
```

**판정 결과 모델:**

```python
from dataclasses import dataclass, field
from enum import Enum

class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    HIGH = "high"

@dataclass
class ClaimGuardResult:
    risk_level: RiskLevel
    matched_terms: list[str] = field(default_factory=list)
    scope_qualifier_required: bool = False
    absolute_claim_blocked: bool = False
    competing_candidates_found: bool = False
    reason: str = ""                      # 사람이 읽을 판정 사유
    suggested_wording: str | None = None  # §2.3 참고
```

**핵심 클래스:**

```python
class ClaimGuard:
    def __init__(self, parallel_retriever_db_path: str | None = None):
        """parallel_retriever_db_path는 competing-candidate 탐색용
        (bible_tag_annotation 조회) — None이면 경쟁후보 탐색을 건너뛰고
        보수적으로 판정(no_full_corpus_comparison_exists=True로 취급)."""

    def detect_risk(self, claim_text: str) -> tuple[RiskLevel, list[str]]:
        """claim_text에서 ABSOLUTE_SUPERLATIVE_TERMS 매칭 검사.
        1개 이상 매칭 시 HIGH, 매칭 없으면 NONE. (LOW는 이번엔 미사용 —
        향후 확장 대비 enum에만 남겨둠)"""

    def evaluate(
        self,
        claim_text: str,
        evidence: list["EvidenceCandidate"],   # core.parallel_retriever.EvidenceCandidate
        tag_name: str | None = None,
    ) -> ClaimGuardResult:
        """
        규칙 (지시서 원문 그대로, evidence의 trust_tier 분포로 판단):

        1. detect_risk(claim_text)로 위험 표현 탐지.
           매칭 없으면 ClaimGuardResult(risk_level=NONE, ...) 바로 반환 (아래 규칙 불필요).

        2. 위험 표현이 있는 경우:
           a. evidence에 trust_tier == T1인 항목이 하나도 없으면
              → absolute_claim_blocked=True, reason="T1(본문) 근거 없이 절대·최상급 주장 불가"
           b. evidence가 전부 T2 또는 T4뿐이면 (T1/T3 없음)
              → absolute_claim_blocked=True, scope_qualifier_required=True,
                reason="T2/T4 단독 근거로는 절대 주장 불가 — 데이터셋 범위 한정 필요"
           c. tag_name이 주어졌고 parallel_retriever_db_path가 있으면:
              _find_competing_candidates(tag_name)로 동일 태그의 다른 canonical_reference가
              2개 이상 있는지 확인 → 있으면 competing_candidates_found=True.
              없으면(또는 db_path가 None이면) competing_candidates_found=False,
              → 이 경우 absolute_claim_blocked=True,
                reason="전체 코퍼스 비교 불가 — '최초/유일' 주장 차단 (no_full_corpus_comparison_exists)"
           d. a~c 모두 통과(T1 근거 있음 + T2/T4 단독 아님 + 경쟁후보 확인됨)해도
              scope_qualifier_required=True는 유지 (완전한 절대 주장은 허용하지 않음 — 항상
              범위 한정 문구를 요구하는 게 이 시스템의 기본값).

        3. suggested_wording 채우기: §2.3의 템플릿 중 근거 상태에 맞는 것을 선택.
        """

    def _find_competing_candidates(self, tag_name: str) -> int:
        """bible_tag_annotation에서 tag_name으로 조회했을 때 서로 다른
        canonical_reference가 몇 개인지 반환 (SELECT DISTINCT). db_path가
        없으면 0 반환."""
```

### 2.2 이번 범위에서 제외

- OCR 품질 기반 규칙(원문 지시서 규칙 4) — Personal Library Corpus(DEVONthink)가 아직 없으므로 스킵.
  `ClaimGuardResult`에 필드만 남겨두지 말고 아예 구현하지 않는다 (없는 데이터에 대한 규칙을 미리 만들지
  않음 — YAGNI).
- 상충 근거 병렬 표시(원문 지시서 규칙 6) — 현재 데이터로는 "상충"을 판단할 근거가 없음(같은 태그의 서로
  다른 절은 상충이 아니라 복수 후보). 실제 상충 탐지는 T3(주석/논문) 코퍼스가 생긴 뒤에나 의미 있음 —
  후속 Task Order.
- 실제 답변 생성 파이프라인 연동 — §1 참고.

### 2.3 문장 템플릿 (지시서 표 그대로, `suggested_wording` 생성용)

```python
def _scope_statement(dataset_id: str, tag_name: str, canonical_reference: str) -> str:
    return f"해당 데이터셋({dataset_id})의 `{tag_name}` 태그 검색에서 {canonical_reference}가 결과로 나타난다."

def _textual_observation_statement(canonical_reference: str, observation: str) -> str:
    return f"{canonical_reference}는 {observation}."

def _scoped_conclusion_statement(canonical_reference: str, definition_note: str) -> str:
    return f"이 정의({definition_note}) 아래 {canonical_reference}는 가장 이른 사례 중 하나로 볼 수 있다."
```

`evaluate()`는 `absolute_claim_blocked=True`일 때 `_scope_statement` 또는 `_scoped_conclusion_statement`
중 근거 상태에 맞는 것을 `suggested_wording`에 채운다. (구체적으로 어떤 데이터를 넣을지는 evidence 리스트의
첫 항목에서 dataset_id/tag_name/canonical_reference를 뽑아 채우면 됨 — 여러 개면 첫 번째 것 사용, 이후
개선은 후속 작업.)

---

## 3. 검증 계획

1. **단위 테스트** (`tests/test_claim_guard.py` 신규):
   - 위험 표현 없는 claim_text → `RiskLevel.NONE`, 다른 필드 전부 기본값
   - 위험 표현 있음 + T1 근거 없음 → `absolute_claim_blocked=True`
   - 위험 표현 있음 + T2/T4만 있음 → `absolute_claim_blocked=True`, `scope_qualifier_required=True`
   - 위험 표현 있음 + T1 있음 + `db_path=None`(경쟁후보 탐색 불가) → `absolute_claim_blocked=True`
     (no_full_corpus_comparison_exists 케이스)
   - 위험 표현 있음 + T1 있음 + 경쟁후보 2개 이상 존재 → `competing_candidates_found=True`,
     `absolute_claim_blocked` 여부는 §2.1 규칙 2d대로 (여전히 scope_qualifier는 요구하지만 완전 차단은
     아닐 수 있음 — 이 케이스의 정확한 기대값은 규칙 2d 문구를 그대로 구현하고 테스트에서 확인)
   - `detect_risk()`가 사전의 모든 표현 각각에 대해 최소 1개는 매칭되는지 (전체 목록 순회 테스트)
   - `_find_competing_candidates()`가 Sprint B의 `bible_tag_annotation` 스키마와 정확히 맞물려 조회되는지
     (픽스처 DB로 실측)
2. Sprint A/B/C 테스트 회귀 없음 확인 — 39/39 유지.

---

## 4. 보고 형식

1. `core/claim_guard.py`, `tests/test_claim_guard.py` diff
2. `git diff core/retrieval.py core/parallel_retriever.py` — **반드시 빈 diff**
3. 테스트 실행 결과 — **pytest 출력의 정확한 숫자를 그대로 복사** (이전에 오보 사례 있었음, 재차 강조)
4. §2.2에서 제외한 항목 중 다음 단계(응답 생성 파이프라인 연동) 착수 전 CUE가 결정해야 할 사항 정리

---

## 5. 다음 조치

Sprint D 완료·검증되면 v2의 Sprint A~D(핵심 스펙)가 모두 끝난다. CUE가 (a) 실제 응답 생성 경로에
ClaimGuard를 연결하는 통합 Task Order, (b) Sprint E(골드셋 평가) 착수 여부를 사용자와 논의 후 발급.
