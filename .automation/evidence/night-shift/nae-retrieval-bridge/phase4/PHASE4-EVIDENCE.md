# Phase 4 — Existing Adapter Inspection Evidence

## 1. `NAE/retrieval_adapter.py` (34 lines) — 실제 구현

**Source:** `NAE/retrieval_adapter.py`

```python
"""NAE optional retrieval adapter (NAE-OPTIONAL-MODULE-PACKAGING-001).

`core/retrieval.py::RetrievalEngine`(ADR-001 유일 정본, "One Pipeline,
One Config, One Retrieval Engine, One Execution State")을 수정하지 않는다
— `RetrievalEngine`은 이 모듈을 import하지 않고, 이 모듈도 `RetrievalEngine`
을 import하지 않는다. 이 파일은 `nae_pd` module이 enabled일 때만 **호출하는
쪽**(예: 향후 UI 탭, 별도 스크립트)이 명시적으로 불러 쓰는 독립 adapter다.

DBMA Core retrieval 경로에 자동으로 끼워 넣지 않는다 — "명시적 module
boundary를 통해서만 접근"(지시서 §6) 원칙.
"""
from __future__ import annotations
from typing import Any
from core import module_registry

class NaePdModuleDisabledError(RuntimeError):
    pass

def search(query_vector: list[float], *, top_k: int = 10, limit_check: bool = True) -> list[dict[str, Any]]:
    """`nae_pd` module이 비활성화 상태면 예외를 던진다 — DBMA Core
    retrieval 경로가 실수로 이 함수를 호출해도 NAE corpus/index에
    접근하지 않는다."""
    if limit_check and not module_registry.is_enabled("nae_pd"):
        raise NaePdModuleDisabledError("nae_pd module is disabled — enable via `scripts/dbma_module.py enable nae_pd` first")

    from NAE.pipeline.index import qdrant_store, config as index_config
    client = qdrant_store.get_client()
    hits = client.search(collection_name=index_config.COLLECTION_NAME, query_vector=query_vector, limit=top_k)
    return [{"tsu_id": h.payload.get("tsu_id"), "score": h.score, "payload": h.payload} for h in hits]
```

**사실:**
- `NAE/retrieval_adapter.py`는 **이미 존재** (34 lines)
- `RetrievalEngine`이 import하지 않음 (양방향 dependency 없음)
- `module_registry.is_enabled("nae_pd")`로 gating — 명시적 활성화 필요
- `qdrant_store.get_client()` → NAE Qdrant search → payload 반환

---

## 2. `core/module_registry.py` Gating Mechanism

**Source:** `core/module_registry.py:38-40`

```python
def is_enabled(name: str, config_path: Path = CONFIG_PATH) -> bool:
    modules = list_modules(config_path)
    return bool(modules.get(name, {}).get("enabled", False))
```

**사실:**
- `config.yaml`의 `modules.nae_pd.enabled` 값 읽음
- **기본값: False** (disabled)
- 활성화: `scripts/dbma_module.py enable nae_pd` 또는 `config.yaml` 직접 수정

---

## 3. `NAE/pipeline/index/qdrant_store.py` — Client Factory

**Source:** `NAE/pipeline/index/qdrant_store.py:17-18`

```python
def get_client(url: str = config.QDRANT_URL) -> QdrantClient:
    return QdrantClient(url=url)
```

**사실:**
- `config.QDRANT_URL`은 NAE Qdrant URL (localhost:7333)
- `qdrant-client`는 NAE 전용 의존성 (DBMA Core에 없음)
- Production Qdrant (port 6333)와 무관

---

## 4. ADR-003 Exception Status

**Task Order §1 Prior Facts:**
> `NAE/retrieval_adapter.py` already exists (34 lines, module `NAE-OPTIONAL-MODULE-PACKAGING-001`).
> It is an explicit, one-directional adapter stub: `RetrievalEngine` does not import it,
> it does not import `RetrievalEngine`. It gates on `core/module_registry.py`
> (`is_enabled("nae_pd")`) and calls `NAE.pipeline.index.qdrant_store.get_client()`
> to search `nae_tsu_v1`. **C1 must treat this file as the existing injection point
> candidate and start Phase 5 from it — do not assume no adapter exists.**

**사실:**
- `retrieval_adapter.py`는 **ADR-003 exception으로 명시됨** (Task Order §1)
- module-gated pattern은 ADR-001 "새로운 병행 검색 경로 금지"와 충돌하지 않음
  (명시적 module boundary로 분리)

---

## 5. Hard Stop Condition Check

| 조건 | 결과 | 근거 |
|---|---|---|
| Production RetrievalEngine 수정 필요? | ❌ 아님 | adapter 이미 존재, module-gated |
| Production Qdrant mutation 필요? | ❌ 아님 | read-only search만 호출 |
| ADR-001/003/013 위반? | ❌ 아님 | Task Order §1에서 exception 명시 |
| DBMA Core architecture change? | ❌ 아님 | adapter path 이미 설계됨 |
| NAE schema change? | ❌ 아님 | qdrant_store.py의 build_point()가 rich payload 생성 |

**Phase 4 — PASS**
