# DISCLOSURE — ADR-024 §D 무수정 원칙과의 충돌

## 변경 사항: `client.search()` → `client.query_points()`

### 변경 전 (ADR-024 원안)
```python
response = client.search(
    collection_name=...,
    query_vector=query_vector,
    limit=top_k,
)
```

### 변경 후 (현재 코드)
```python
response = client.query_points(
    collection_name=collection_name,
    query=query_vector,
    limit=top_k,
    timeout=30,
    with_payload=True,
)
```

### 변경 불가한 이유

qdrant-client 1.18.0에서 `QdrantClient.search()` 메서드가 완전히 제거됨:

```python
>>> from qdrant_client import QdrantClient
>>> hasattr(QdrantClient, 'search')
False
>>> hasattr(QdrantClient, 'query_points')
True
```

`search()`를 호출하면 `AttributeError`가 발생하므로, **실제 동작을 위해서는
필수 변경**임. 이는 ADR-024 §D(무수정)의 범위를 벗어난 수정이지만,
qdrant-client의 breaking change에 의한 필수 대응임.

### 영향 범위

- `NAE/retrieval_adapter.py::search()` 함수 내부만 변경
- API 시그니처는 호환 (동일한 입력 → 동일한 출력)
- DBMA core/retrieval.py, corpus, production data 모두 무변경

### 검증

```
qdrant-client version: 1.18.0
QdrantClient.search exists: False
QdrantClient.query_points exists: True
```

---

## 변경 사항: `_HARD_TIMEOUT_S` → `_HARD_TIMEOUT_MS` + 실제 deadline 체크

### 변경 전 (버그)
```python
_HARD_TIMEOUT_S = 3_000  # hard timeout (seconds) — 3000초!
deadline = time.monotonic() + _HARD_TIMEOUT_S  # 계산만 하고 체크 안 함
```

**문제**: 
1. `_HARD_TIMEOUT_S`가 초 단위라 3000초(50분) — ADR-024 §G의 3초와 다름
2. `deadline` 변수가 계산만 되고 **전혀 체크되지 않음** — hard timeout이 완전히 비활성화

### 변경 후 (수정됨)
```python
_HARD_TIMEOUT_MS = 3_000  # hard timeout (milliseconds)
deadline = time.monotonic() + _HARD_TIMEOUT_MS / 1_000  # ms → s 변환

# embedding 전후 체크
_check_deadline(deadline)
vector = ollama.embeddings(...)
_check_deadline(deadline)

# search 전후 체크
_check_deadline(deadline)
hits = search(vector, ...)
_check_deadline(deadline)
```

**`_check_deadline()` 구현**:
```python
def _check_deadline(deadline: float) -> None:
    remaining_ms = (deadline - time.monotonic()) * 1_000
    if remaining_ms <= 0:
        raise TimeoutError(
            f"[bridge_query] hard timeout exceeded ({-remaining_ms:.0f}ms overdue)"
        )
```

### 검증 결과

```python
# 3.1초 지연 mock으로 테스트
>>> bridge_query('test', top_k=5)
TimeoutError: [bridge_query] hard timeout exceeded (104ms overdue)
→ fail-closed로 [] 반환
PASS
```

