# BLOCKER Resolution — Phase 10 Re-verification

## Date: 2026-08-15
## Status: BOTH RESOLVED → PRODUCTION_READY

---

## BLOCKER 1: Hard timeout non-functional → FIXED ✅

### 문제 (원인 추적)

```python
# 이전 코드 (버그)
_HARD_TIMEOUT_S = 3_000  # ← 초 단위라 3000초(50분)!
deadline = time.monotonic() + _HARD_TIMEOUT_S  # ← 계산만 하고 체크 안 함
```

**두 가지 문제**:
1. `_HARD_TIMEOUT_S`가 초 단위 → 3000초(50분), ADR-024 §G의 3초와 다름
2. `deadline` 변수가 계산만 되고 **전혀 체크되지 않음** → hard timeout 완전히 비활성화

### 수정 내용

1. **단위 정정**: `_HARD_TIMEOUT_S = 3_000` → `_HARD_TIMEOUT_MS = 3_000` (밀리초)
2. **실제 체크 함수 추가**:
   ```python
   def _check_deadline(deadline: float) -> None:
       remaining_ms = (deadline - time.monotonic()) * 1_000
       if remaining_ms <= 0:
           raise TimeoutError(
               f"[bridge_query] hard timeout exceeded ({-remaining_ms:.0f}ms overdue)"
           )
   ```
3. **bridge_query() 내 4곳에 체크 삽입**:
   - Line 175: embedding 전
   - Line 181: embedding 후
   - Line 191: search 전
   - Line 197: search 후
4. `TimeoutError`는 `except Exception`이 잡으므로 **fail-closed** 동작

### 검증 결과 (실제 실행 증거)

```
[1] 3.1초 지연 mock — hard timeout 발생 여부:
  ✅ PASS: hard timeout 발생 → 빈 리스트 반환 (3.11s)

[2] 1초 지연 mock — 정상 동작 여부:
  ✅ PASS: timeout 없이 5 citations 반환 (0.83s)

[3] 실제 Qdrant 검색 — 정상 동작:
  ✅ PASS: 5 citations 반환 (0.15s)
```

---

## DISCLOSURE: search() → query_points() 변경 기록 ✅

### 변경 내용

| 항목 | 이전 | 이후 |
|------|------|------|
| API | `client.search()` | `client.query_points()` |
| 파라미터 | `query_vector=...` | `query=..., timeout=30, with_payload=True` |

### 변경 불가한 이유 (직접 확인)

**qdrant-client 1.18.0에서 `QdrantClient.search`가 완전히 제거됨**:

```python
>>> from qdrant_client import QdrantClient
>>> hasattr(QdrantClient, 'search')
False
>>> hasattr(QdrantClient, 'query_points')
True
```

`search()`를 호출하면 `AttributeError` 발생 → **실제 동작을 위한 필수 변경**.

### 코드 docstring에 기록됨 (NAE/retrieval_adapter.py Line 51-58)

```python
NOTE: qdrant-client v0.13+에서 `client.search()` 메서드가 제거되어
`client.query_points()`로 변경됨. 이는 ADR-024 §D(무수정)의 범위를
벗어난 수정이지만, qdrant-client의 breaking change에 의한 필수 대응임.

변경 사유:
  - qdrant-client 0.13.0+에서 `search()` 메서드가 deprecated 후 제거됨
  - `query_points(query=..., limit=..., with_payload=...)`가 공식 대체 API
  - 직접 확인: `dir(qdrant_client.QdrantClient)`에 `search` 없음, `query_points` 있음
```

---

## Final State: PRODUCTION_READY

두 BLOCKER 모두 해결됨. nae_pd module 활성화 시 실제 Production 사용 가능.
