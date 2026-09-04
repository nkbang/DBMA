# C1 Task Order 022 — Sprint C: ParallelRetriever + trust tier 재랭킹

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P0 (Sprint A/B 후속, 검색 신뢰성 파이프라인 v2)
**선행 작업**: Task Order 020(Sprint A, 검증 완료 30/30 중 20), Task Order 021(Sprint B, 검증 완료 30/30) —
`core/dataset_registry.py`/`core/tag_ingest_validator.py`/`core/dataset_adapters/`의 기존 함수·모델을
그대로 재사용한다. 재정의 금지.
**근거 문서**: [docs/architecture/DBMA-Search-Trust-Pipeline-Plan-v2.md](../../architecture/DBMA-Search-Trust-Pipeline-Plan-v2.md) §3 Sprint C
**작성일**: 2026-07-29
**모드 제약**: **이번이 처음으로 `core/retrieval.py`를 다루는 Task Order다. 단, 기존 `RetrievalEngine.retrieve()`
본문은 한 글자도 수정하지 않는다** — 읽기 전용으로 import/호출만 한다. 새 기능은 반드시 신규 파일
`core/parallel_retriever.py`에 작성. 기존 `retrieve()`의 시그니처·반환 타입·내부 로직 변경은 이번
Task Order 범위 밖이며, 변경이 필요하다고 판단되면 구현하지 말고 보고서에 "변경 필요 사유"만 적을 것.

---

## 1. 배경

Sprint A/B로 데이터셋 레지스트리와 태그 인제스트 인프라가 갖춰졌다. Sprint C는 이를 실제 검색에
연결하는 단계다 — 계획서 원문의 "복수 검색 축 병렬 수행"을, 기존 `RetrievalEngine.retrieve()`(BM25+벡터+
신학점수, T1 근거)를 축 하나로 두고, `bible_tag_annotation`(Sprint B, T2 근거) 조회를 또 다른 축으로 두어
병렬 실행 후 병합하는 방식으로 구현한다.

**범위를 의도적으로 좁힌다**: 지시서 원문은 7개 검색기(canonical/BM25/vector/morphology/curated tag/
commentary/LLM)를 요구하지만, 이번 Task Order는 **2개 축만** 구현한다 — (1) 기존 `RetrievalEngine.retrieve()`
전체를 T1 축으로 그대로 사용, (2) `bible_tag_annotation` 테이블 조회를 T2 축으로 신규 구현. 나머지
축(morphology/commentary/LLM expansion)은 실제 데이터가 없으므로 후속 Task Order로 미룬다.

---

## 2. 구현 범위

### 2.1 신규 모듈 — `core/parallel_retriever.py`

```python
from dataclasses import dataclass
from core.retrieval import RetrievalEngine, ParsedQuery, RankedCandidate
from core.dataset_registry import TrustTier

@dataclass
class EvidenceCandidate:
    """RankedCandidate(T1 축)와 bible_tag_annotation 조회 결과(T2 축)를
    공통 인터페이스로 감싼 것. 기존 RankedCandidate는 변경하지 않는다."""
    canonical_reference: str | None   # T2 축에서만 채워짐 (예: "Gen.24.12")
    evidence_axis: str                # "t1_hybrid_search" | "t2_curated_tag"
    trust_tier: TrustTier
    ranked_candidate: RankedCandidate | None = None   # T1 축일 때만
    dataset_id: str | None = None                     # T2 축일 때만
    tag_namespace: str | None = None
    tag_name: str | None = None
    scope: str | None = None

class ParallelRetriever:
    """RetrievalEngine.retrieve()를 T1 축으로 감싸고, bible_tag_annotation
    조회를 T2 축으로 병렬 실행해 병합·재랭킹한다. RetrievalEngine 본체는
    수정하지 않는다 — 읽기 전용 사용."""

    def __init__(self, retrieval_engine: RetrievalEngine, dataset_registry_db_path: str):
        self.retrieval_engine = retrieval_engine
        self.db_path = dataset_registry_db_path

    def retrieve(
        self,
        parsed_query: ParsedQuery,
        k_output: int = 10,
        embedding_cache=None,
        file_scope=None,
        tag_names: list[str] | None = None,   # 예: ["prayer"] — T2 축에서 찾을 태그. None이면 T2 축 생략
    ) -> list[EvidenceCandidate]:
        """
        1. T1 축: self.retrieval_engine.retrieve(parsed_query, k_output, embedding_cache, file_scope)
           기존 시그니처 그대로 호출 — 반환된 RankedCandidate마다
           EvidenceCandidate(evidence_axis="t1_hybrid_search", trust_tier=T1)로 감싼다.
        2. T2 축: tag_names가 주어지면, core/dataset_registry.py의 조회 함수(SELECT)를 이용해
           bible_tag_annotation에서 tag_name IN tag_names인 행을 canonical_reference 정경 순서로
           정렬해 가져온다. 각 행을 EvidenceCandidate(evidence_axis="t2_curated_tag", trust_tier=T2)로 감싼다.
        3. 두 축의 결과를 리스트로 합쳐 반환 (T1 먼저, T2 다음 — 축 구분이 명확해야 하므로 점수로
           뒤섞어 재정렬하지 않는다. "재랭킹"은 각 축 *내부* 정렬에만 적용, §2.2 참고).
        """
```

### 2.2 Trust tier 가중치 반영 (축 내부 재랭킹만)

- T1 축(`RankedCandidate` 리스트)은 이미 `final_score`로 정렬되어 있음 — 그대로 유지.
- T2 축은 `canonical_reference`의 **정경 순서**(책 순서 → 장 → 절)로 정렬한다. 정경 순서 비교 함수는
  `core/retrieval.py`의 기존 `ScriptureReference`를 **import해서 읽기 전용으로 사용** (새로 구현하지 말 것 —
  이미 있는 파싱/비교 로직 중복 금지).
- `dataset_registry`의 `ranking_weight` 필드는 이번 Task Order에서는 **저장만 하고 정렬에는 아직 반영하지
  않는다** (여러 데이터셋이 섞일 때의 가중치 정책은 Sprint D의 ClaimGuard와 함께 설계하는 게 맞음 — 지금은
  단일 데이터셋 시나리오이므로 조기 최적화하지 않는다).

### 2.3 근거 유형 분류 헬퍼

```python
def classify_evidence(candidates: list[EvidenceCandidate]) -> dict[str, list[EvidenceCandidate]]:
    """evidence_axis 기준으로 그룹화. {"t1_hybrid_search": [...], "t2_curated_tag": [...]} 반환.
    UI(Sprint D 이후)에서 "본문 근거" vs "큐레이션 태그 근거" 배지를 나눠 표시할 때 쓸 최소 유틸."""
```

### 2.4 이번 범위에서 제외

- Morphology/lemma/commentary/LLM 후보확장 검색 축 — 실 데이터 없음, 후속 Task Order.
- 여러 데이터셋 간 `ranking_weight` 교차 정렬 — Sprint D에서 ClaimGuard와 함께.
- UI 반영 — Sprint D 이후.
- `RetrievalEngine.retrieve()` 자체의 리팩터링 — 범위 밖(§ 모드 제약 참고).

---

## 3. 검증 계획

1. **단위 테스트** (`tests/test_parallel_retriever.py` 신규):
   - T2 축 없이(`tag_names=None`) 호출 시 T1 축 결과만 반환되고, 기존 `RetrievalEngine.retrieve()`와
     candidate 개수·내용이 1:1 일치하는지 (즉 T1 축이 기존 동작을 그대로 감싸기만 했는지 확인 — 회귀 검증
     핵심)
   - T2 축 지정 시 `bible_tag_annotation`에서 해당 태그 행만 정확히 조회되는지
   - T2 축 결과가 정경 순서로 정렬되는지 (예: Gen.4.26 < Gen.18.22 < Gen.24.12 순서로 나오는지 픽스처로 확인)
   - `classify_evidence()`가 axis별로 정확히 분리하는지
   - **회귀**: `core/retrieval.py`의 기존 테스트(있다면 `tests/test_retrieval.py` 등)가 그대로 통과하는지
     (파일 미수정이므로 당연히 통과해야 하지만 명시적으로 재실행해 확인)
2. Sprint A/B 테스트(`tests/test_dataset_registry.py`, `tests/test_tag_ingest_validator.py`,
   `tests/test_dataset_adapters.py`) 회귀 없음 확인 — 총 30/30 유지되어야 함.

---

## 4. 보고 형식

1. `core/parallel_retriever.py`, `tests/test_parallel_retriever.py` diff
2. `git diff core/retrieval.py` 결과 — **반드시 빈 diff여야 함**. 한 줄이라도 나오면 그 이유를 보고서
   최상단에 먼저 설명할 것 (허가 없이 수정 금지, CUE가 별도로 재검토함).
3. 테스트 실행 결과 (신규 + 기존 Sprint A/B/기존 retrieval 테스트 합산 pass 수 — **정확한 숫자를 pytest
   출력에서 그대로 복사할 것, 어림잡아 세지 말 것** — 이전 Task Order에서 개수 오보 사례가 있었음)
4. §2.4에서 제외한 항목 중 Sprint D 착수 전 CUE 확인이 필요한 사항 정리

---

## 5. 다음 조치

Sprint C 완료·검증 후 Sprint D(ClaimGuard: 위험 주장 탐지, 절대·최상급 차단 규칙, 범위 한정 문구 자동 생성)
Task Order를 CUE가 발급.
