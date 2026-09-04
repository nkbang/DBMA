---
title: "ADR-028: NAE Smith Reference Layer (Background Knowledge Integration)"
category: architecture
based_on:
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md
  - docs/architecture/ADR-013-NAE-Vector-Store.md
  - docs/architecture/ADR-024-NAE-Production-Retrieval-Bridge.md
  - NAE/reference_retrieval_adapter.py
created: 2026-08-25
scope_modified: NAE/reference_retrieval_adapter.py, ui/pages/chat.py, ui/pages/sermon_draft.py, core/generation.py (context injection only)
---

# ADR-028: NAE Smith Reference Layer (Background Knowledge Integration)

| | |
|---|---|
| Status | Accepted |
| Date | 2026-08-25 |
| Deciders | Rev. Bang / HQ |
| Approved | 2026-08-29 |
| Approver | Rev. Bang / HQ |
| Supersedes | — |
| Superseded by | — |

---

## 1. Product Requirement (Product Intent)

Smith Bible Dictionary Vol.1+ integration의 **제품적 목적**은 다음과 같이 명확히 정의된다:

> **"NAE의 질문답변과 설교연구를 필요할 때 조용히 보완하는 background knowledge layer"**

이는 다음을 의미한다:
- Smith 결과를 사용자에게 별도 citation badge/card로 표시하지 않음
- UI에 `[Smith Dict]` 등의 시각적 구분 요소 없음
- 내부 provenance(source_id, volume, page_start/end)만 보존 — LLM 프롬프트와 로깅에서만 활용
- user-facing 영역에서 Smith가 TSU 또는 성경 본문과 혼동되지 않도록 prompt engineering으로 hierarchy 강제

---

## 2. Activation Policy

**권고: conditional (heuristic-based, no LLM classifier)**

| 방식 | 장단점 | 적합도 |
|---|---|---|
| always-on | 매 쿼리마다 reference search 실행 → latency 증가 (~50-100ms 추가), 불필요한 컨텍스트 주입 위험 | 낮음 |
| conditional | 최소 heuristic으로 필터링 → overhead 최소화 | **높음** |
| user-triggered | UI 버튼 필요 → UX 저하, 사전 참조의 "silent background" 목적과 충돌 | 낮음 |

**구현 heuristic (3단계 파이프라인):**

```
1. QueryParser._detect_books_standalone() 결과에 인명/지명 패턴이 있으면 → search_reference 호출
2. ParsedQuery.themes[]에 "wisdom"/"covenant"/"redemption" 등 사전적 정의가 필요한 신학 용어가 있으면 → search_reference 호출
3. ParsedQuery.keywords[] 중 2글자 이상 영단어가 있고, 그것이 성경 용어/역사 용어 패턴과 일치하면 → search_reference 호출
```

구체적 구현 위치: `ui/pages/chat.py`의 retrieval 전 단계에서 `NAE/reference_retrieval_adapter.search_reference()`를 **조건부**로 호출. `core/retrieval.QueryParser`에 새로운 heuristic detector를 추가하는 것은 피한다 (QueryParser는 scripture/book detection만 담당해야 함).

---

## 3. Authority Hierarchy

```
1순위: Scripture / primary biblical text (user가 명시적으로 요청한 본문)
2순위: TSU theological corpus (RetrievalEngine hybrid search 결과)
3순위: Smith reference corpus (background knowledge, citation-only)
```

**prompt boundary 규칙:**
- Smith reference context는 `<reference>` 태그로 감싸고, TSU context (`<context>`)와 명확히 분리
- LLM 프롬프트에 명시적 지시: "Smith Dictionary entries는 참고 자료일 뿐, 성경 본문 또는 TSU theological corpus보다 우선하지 않는다"

**중요:** Smith가 TSU 또는 성경 본문의 해석을 **대체하거나 덮어쓰지 않도록** prompt injection 시 다음을 명시:
```
"참고: 아래 사전 항목은 보조 자료입니다. 주요 근거는 [context id=...] 섹션의 신학 문헌을 우선하십시오."
```

---

## 4. Integration Boundary — Context Injection Strategy

### 4.1 API 분석 결과 (실제 코드 기반)

**`core/generation.py::GenerationService._build_prompt()` (L219-236):**
```python
def _build_prompt(response: ResponsePackage, conversation_history: str = "") -> tuple[str, bool]:
    context = response.llm_context_block or ""
    history_block = f"이전 대화:\n{conversation_history}\n\n" if conversation_history.strip() else ""
    if context.strip():
        return f"{history_block}문맥:\n{context}\n\n질문:\n{response.question}", True
    return f"{history_block}질문:\n{response.question}", False
```

**`core/generation.py::SermonDraftService.expand_point()` (L537-604):**
```python
def expand_point(self, point_text, scripture_and_theme, candidates, ...):
    context_block = _format_sermon_context(candidates)
    # ... base_prompt에 context_block 주입
```

**`core/retrieval.py::ResponsePackage` (L1750-1784):**
```python
@dataclass
class ResponsePackage:
    question: str
    llm_context_block: str  # TSU context만 포함
    citations: list[Citation]
    # ...
```

### 4.2 최소 침습적 Injection 전략

**권고: UI 계층에서 `response.llm_context_block`을 수정하여 병렬 주입**

| 계층 | 적합도 | 이유 |
|---|---|---|
| QueryProcessor | 낮음 | ADR-001 authority 침범, retrieval pipeline 혼선 |
| reference adapter | 높음 | 이미 독립 모듈, 게이트 없음 |
| GenerationService._build_prompt() | **최적** | context_block을 직접 수정 — core API 변경 없음 |
| SermonDraftService.expand_point() | **최적** | _format_sermon_context() 결과에 병렬 주입 |
| Chat UI | **최적** | user query를 최초로 받는 곳, conditional 호출 결정 위치 |

**구현 위치:**
```python
# ui/pages/chat.py — retrieval 후, generation 전
from NAE.reference_retrieval_adapter import search_reference

# heuristic 판단 후
if _should_search_reference(parsed_query):
    ref_context = search_reference(query, top_k=3)
else:
    ref_context = []

# response.llm_context_block에 Smith reference 병렬 주입 (core/retrieval.py 수정 없음)
if ref_context:
    smith_block = _format_reference_context(ref_context)
    response.llm_context_block += f"\n\n<reference>\n{smith_block}\n</reference>"
```

**핵심 원칙:** `core/retrieval.py`, `core/generation.py`의 **시그니처를 변경하지 않는다**. `response.llm_context_block`은 이미 mutable string이므로 UI 계층에서 직접 수정 가능.

---

## 5. Prompt Integration Strategy

**구조:**
```
<tsu_context>
[context id="tsu_001" score="0.8234"]
... TSU results ...
</tsu_context>

<reference>
[Smith Dict] Aaron — Egyptian origin, etc.
</reference>

질문: {user_query}
```

**구분 방법:**
- TSU context: `<context id="..." score="...">` (기존 구조 유지)
- Smith reference: `<reference>[Smith Dict]</reference>` (신규 태그)
- LLM 프롬프트에 명시적 지시: "TSU theological corpus가 primary evidence, Smith Dictionary는 supplementary reference"

**reference 지배 방지:**
```
"Smith Dictionary entries는 참고용입니다. 주요 주장은 [context id=...] 섹션의 신학 문헌에 근거하십시오."
```

**provenance 유지:**
- `NAE/reference_retrieval_adapter.py`의 return dict에 `source_id`, `volume`, `page_start/end` 포함 — 내부 provenance 보존
- 내부적으로는 `content_type: "reference_dictionary"` 필드로 TSU와 구분

---

## 6. Failure Isolation

**권고: fail-closed (빈 리스트 반환, 예외 전파 없음)**

현재 `NAE/reference_retrieval_adapter.py::search_reference()`는 이미 fail-closed 구현이다 (§59-60, §72-74):
```python
except Exception as e:  # noqa: BLE001
    logger.error("[search_reference] embedding failed: %s", e)
    return []
```

**추가 방어:**
1. **timeout 추가**: `NAE/retrieval_adapter.py`의 `_HARD_TIMEOUT_MS = 3_000` 패턴을 참고하여 `search_reference()`에 timeout 적용
2. **UI 계층에서 try-exwrap**:
   ```python
   try:
       ref_context = search_reference(query, top_k=3)
   except Exception:
       ref_context = []  # TSU retrieval은 계속 실행
   ```
3. **latency 모니터링**: reference search가 1초 초과 시 warn logging + skip (다음 쿼리부터 fallback)

**기존 TSU retrieval, Chat, Sermon Draft, Generation이 정상 작동해야 함:**
- reference search 실패 → `ref_context = []` → prompt에 `<reference>` 섹션 생략 → TSU context만 사용 → 정상 동작
- **절대** `core/retrieval.py`, `core/generation.py`의 시그니처를 수정하지 않음

---

## 7. Volume Expansion Strategy

**권고: 동일 `nae_ref_v1` collection 확장 (volume별 payload 필드)**

| 방식 | 장단점 | 적합도 |
|---|---|---|
| 동일 collection, volume 필드 구분 | 단일 인덱스, cross-volume search 가능, 관리 단순 | **높음** |
| volume별 collection 분리 | isolation 명확, query 시 collection 지정 필요, 관리 복잡 | 낮음 |
| 별도 versioning (nae_ref_v2) | 스키마 변경 시 필요, 현재는 불필요 | 낮음 |

**구현:**
- `nae_ref_v1`에 Vol02~04 chunk를 동일 스키마로 upsert
- payload에 `volume: "Vol.02"`, `volume_number: 2` 필드 추가
- query 시 `with_payload=True`로 volume 정보 포함 반환

**예외:** Smith Vol05+가 완전히 다른 스키마(예: multi-language, image caption)를 요구하면 별도 collection 검토.

---

## 8. Risks

| 위험 | 심각도 | 완화책 |
|---|---|---|
| reference search latency가 generation 전체 latency에 영향 | 중 | timeout (3초) + warn threshold (1.5초) + fail-closed |
| Smith reference가 TSU 결과를 압도하는 prompt 구성 | 높음 | prompt 내 명시적 hierarchy 지시 + `<reference>` 태그 분리 |
| Vol02+ ingestion 시 schema drift | 중 | `NAE/pipeline/reference/config.py`에 schema version 관리 + ingest 시 validation |
| conditional heuristic의 false positive/negative | 낮음 | heuristic는 UI 계층에서만 — 수정 시 core 영향 없음 |

---

## 9. Implementation Sequence

**Phase B-1: Adapter hardening (우선순위 1)**
1. `NAE/reference_retrieval_adapter.py`에 timeout 추가 (ADR-024 패턴 참고)
2. logging 레벨 조정 (error → warning for Qdrant timeout)

**Phase B-2: UI integration (우선순위 2)**
3. `ui/pages/chat.py`에 conditional reference search 통합
4. `_should_search_reference()` heuristic 구현 (인명/지명/신학 용어 패턴)
5. `ref_context`를 `GenerationService._build_prompt()`에 병렬 주입

**Phase B-3: Sermon Draft integration (우선순위 3)**
6. `ui/pages/sermon_draft.py`에 동일 pattern 적용
7. `SermonDraftService.generate_outline()`에 `reference_context` 파라미터 추가

**Phase B-4: Prompt engineering (우선순위 4)**
8. generation prompt에 authority hierarchy 지시 추가
9. `<reference>` 태그 구조 정의 + citation provenance 유지

**Phase B-5: Testing & ADR (우선순위 5)**
10. End-to-end smoke test ("Aaron", "Exodus", "Pharisee" 등)
11. ADR-028 작성 + promotion
12. Docs/STATE.md 업데이트

---

## 10. Product Requirement Reiteration (Critical)

**이 ADR의 핵심 제품 요구사항을 다시 명시한다:**

> Smith Bible Dictionary는 **background knowledge layer**이다.
> 
> - 사용자에게 별도 citation badge/card를 표시하지 않는다.
> - UI에 `[Smith Dict]` 등의 시각적 구분 요소를 추가하지 않는다.
> - 내부 provenance만 보존 — LLM 프롬프트와 로깅에서만 활용.
> - user-facing 영역에서 Smith가 TSU 또는 성경 본문과 혼동되지 않도록 prompt engineering으로 hierarchy 강제.

---

## 11. Validation

```bash
# 1. reference_retrieval_adapter.py import check
python -c "from NAE.reference_retrieval_adapter import search_reference; print('OK')"

# 2. Qdrant collection 확인
curl http://localhost:7333/collections | grep nae_ref

# 3. Vol01 ingestion 확인
grep -c "smith_bible_dictionary" ~/DBMA/output/nae_ingest_manifest.jsonl

# 4. Vol02-04 ingestion 후 확인
grep -c "smith_bible_dictionary" ~/DBMA/output/nae_ingest_manifest.jsonl
```

---

## 12. Future Expansion

- Smith Vol05+ ingestion (다국어, image caption 등 별도 스키마 검토)
- conditional heuristic 정확도 개선 (LLM classifier 도입 검토)
- reference search latency 최적화 (embedding cache TTL 조정)
- ADR-028 promotion 후 STATE.md 업데이트
