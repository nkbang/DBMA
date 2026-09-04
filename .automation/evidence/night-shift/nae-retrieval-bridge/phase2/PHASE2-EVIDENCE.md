# Phase 2 — ADR Boundary Check Evidence

## 1. ADR-001: Retrieval Engine Authority (core/retrieval.py::RetrievalEngine)

**Source:** `docs/architecture/ADR-001-Retrieval-Engine-Authority.md`

### Key Facts (실제 문서 인용):

> **Decision:** `core/retrieval.py::RetrievalEngine`(및 그 위의 `QueryProcessor` 계약)을 DBMA의 유일한 Retrieval Engine Authority로 지정한다.
>
> - 향후 신규 검색/RAG 기능은 `core/retrieval.py` 계약 위에서만 구현한다 — 새로운 병행 검색 경로를 만들지 않는다.

**SPRINT20-H-3 Correction:**
> ~~**벡터 백엔드 일관성**: `RetrievalEngine`은 Qdrant만 사용한다.**~~ — **[SPRINT20-H-3에서 사실과 다름이 확인됨, 하단 Correction 참고]** `RetrievalEngine`은 Qdrant를 전혀 쿼리하지 않으며, 영구 vector store를 사용하지 않는다.

**Phase 2 Verdict:**
- ADR-001은 "새로운 병행 검색 경로 금지"를 규정
- **하지만** module-gated adapter는 병행 경로가 아님 — `nae_pd` module이 explicitly enabled될 때만 동작
- `NAE/retrieval_adapter.py`가 이미 이 exception pattern으로 존재

---

## 2. ADR-003: Legacy Vector Store Strategy

**Source:** `docs/architecture/ADR-003-Legacy-Vector-Store-Strategy.md`

### Key Facts (실제 문서 인용):

> **Consequences:**
> - No production dependency may be added to Chroma/Qdrant without new ADR approval.
> - `RetrievalEngine`은 Qdrant와 Chroma 어느 쪽도 쿼리하지 않는다 — 영구 vector store 미사용

**Scope 제외 항목 (ADR-003 §Scope Exclusions):**
> ADR-003의 제약은 Production RetrievalEngine의 production 검색 경로에 적용된다. NAE/ 하위 subsystem은 별도 ADR(ADR-013)으로 관리.

**Phase 2 Verdict:**
- ADR-003은 "Production 경로에 Chroma/Qdrant 의존성 추가 금지"
- **NAE Qdrant는 Production 경로에 연결되지 않음** — 이 investigation은 read-only probe만 수행
- ADR-024에서 production integration을 결정할 때만 ADR-003 개정 필요

---

## 3. ADR-013: NAE Vector Store (Independent Qdrant Instance)

**Source:** `docs/architecture/ADR-013-NAE-Vector-Store.md`

### Key Facts (실제 문서 인용):

> **Scope 제약:**
> - `nae_qdrant`/`nae_tsu_v*` 컬렉션은 `NAE/` 하위 파이프라인에서만 사용한다.
> - `core/retrieval.py::RetrievalEngine`의 검색 경로에는 연결하지 않는다 — ADR-003의 migration policy를 그대로 준수한다.

> **Consequences:**
> - 향후 NAE corpus를 `RetrievalEngine`의 production 경로에 통합하려면(예: Theology RAG Alpha 단계) **이 ADR을 개정하는 신규 ADR이 필요하다.**

**Phase 2 Verdict:**
- ADR-013은 NAE Qdrant를 NAE/ 하위에서만 사용하도록 제한
- **integration은 신규 ADR(ADR-024)에서 결정** — 이 investigation은 feasibility만 확인
- ADR-013 위반 아님 (read-only probe는 integration이 아님)

---

## 4. ADR-017: NAE ID Governance Standard

**Source:** `docs/architecture/ADR-017-NAE-ID-Governance-Standard.md`

### Key Facts (실제 문서 인용):

> **3.1 Canonical ID Rule:**
> ```
> author_id  = "{surname}_{given_name}[_{middle_initial}]"
> work_id    = "{author_id}_{title_slug}"
> edition_id = "{work_id}_{publication_year}[_{place_slug}]"
> volume_id  = "{edition_id}_v{NN}"
> source_id  = "{volume_id 또는 edition_id}_{scan_suffix}"
> ```
> 전부 lowercase, snake_case, ASCII, deterministic.

> **3.2 Collision Policy:**
> - `legacy_id` 필드로 구 ID를 보존한다.

**Phase 2 Verdict:**
- ADR-017은 ID 표기 규칙 정의
- NAE TSU payload에 `canonical_id`/`legacy_id` 포함 여부 → Phase 7에서 확인
- ADR-017 위반 아님 (ID Governance는 separate concern)

---

## 5. Existing retrieval_adapter.py as ADR-003 Exception

**Source:** `NAE/retrieval_adapter.py` (34 lines, module `NAE-OPTIONAL-MODULE-PACKAGING-001`)

### Key Facts (실제 코드):

```python
# NAE/retrieval_adapter.py
def search(query_vector: list[float], *, top_k: int = 10, limit_check: bool = True):
    if limit_check and not module_registry.is_enabled("nae_pd"):
        raise NaePdModuleDisabledError(...)
    # ... NAE Qdrant query
```

**사실:**
- `NAE/retrieval_adapter.py`는 **이미 ADR-003 exception pattern으로 존재**
- `module_registry.is_enabled("nae_pd")`로 gating — 명시적 활성화 필요
- RetrievalEngine이 import하지 않음 (독립 모듈)

---

## 6. Hard Stop Condition Check

| 조건 | 결과 | 근거 |
|---|---|---|
| Production RetrievalEngine 수정 필요? | ❌ 아님 | injection point 확인됨 (§1 Phase 1) |
| Production Qdrant mutation 필요? | ❌ 아님 | read-only probe만 수행 |
| ADR-001 위반? | ❌ 아님 | module-gated adapter는 병행 경로 아님 |
| ADR-003 위반? | ❌ 아님 | production 경로 연결 아님 (ADR-024에서 결정) |
| ADR-013 위반? | ❌ 아님 | read-only probe는 integration 아님 |
| ADR-017 위반? | ❌ 아님 | ID Governance separate concern |
| DBMA Core architecture change? | ❌ 아님 | module boundary로 분리 가능 |
| NAE schema change? | ❌ 아님 | payload 이미 rich |

**Phase 2 — PASS**
