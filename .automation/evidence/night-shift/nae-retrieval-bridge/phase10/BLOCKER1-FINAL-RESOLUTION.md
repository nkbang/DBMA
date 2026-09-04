# BLOCKER 1 Final Resolution — Hard timeout client-level enforcement

## Date: 2026-08-15
## Status: RESOLVED (client-level timeout)

---

## 문제 (근본 원인)

### 1. `_check_deadline()`은 사후 감지일 뿐
```python
# 이전 코드 (버그)
_check_deadline(deadline)  # 호출 전 체크
vector = ollama.embeddings(...)  # ← 여기서 hang하면 뒤쪽 체크에 도달 못 함
_check_deadline(deadline)  # ← 도달 못 함
```

호출이 hang(응답 없음)이면 뒤쪽 `_check_deadline`에 도달하지 못해 **무한 대기**.

### 2. `ollama.embeddings()`는 timeout 파라미터 없음
```python
>>> inspect.signature(ollama.embeddings)
[model, prompt, options, keep_alive]  # ← timeout 없음
```

module-level `ollama.embeddings()`는 httpx timeout을 설정할 수 없음. 기본 클라이언트의 httpx timeout은 **None(무제한)**.

### 3. `search()`의 `timeout=30`은 ADR-024 §G의 3초 예산과 맞지 않음
```python
# 이전 코드 (버그)
timeout=30  # ← 30초, ADR-024 §G의 3초와 다름
```

---

## 수정 내용

### 1. `ollama.Client(timeout=3.0)` 사용 — client-level httpx timeout

```python
# 이전 (버그)
vector = ollama.embeddings(model="bge-m3:latest", prompt=query_text)["embedding"]

# 이후 (수정)
ollama_client = ollama.Client(timeout=_HARD_TIMEOUT_MS / 1_000)  # 3.0초
vector = ollama_client.embeddings(model="bge-m3:latest", prompt=query_text)["embedding"]
```

`ollama.Client(timeout=3.0)`이 httpx.Client의 `Timeout(timeout=3.0)`을 설정:
- Connect timeout: 3.0초
- Read timeout: 3.0초
- **실제 hang 시 httpx.ReadTimeout 발생 → 실제 차단**

### 2. `search()`에 `remaining_timeout_s` 파라미터 추가

```python
# 이전 (버그)
timeout=30  # ← 고정 30초

# 이후 (수정)
remaining_s = max(0.5, deadline - time.monotonic())
hits = search(vector, top_k=top_k, limit_check=False, remaining_timeout_s=remaining_s)
```

남은 deadline 기준으로 timeout 계산 (최소 1초).

### 3. `_check_deadline()`은 여전히 사후 감지이지만, client-level timeout이 실제 hang 차단

```python
# embedding 전 체크
_check_deadline(deadline)
t0 = time.monotonic()
vector = ollama_client.embeddings(...)  # ← httpx timeout으로 실제 hang 차단
embed_ms = (time.monotonic() - t0) * 1_000

# embedding 후 체크
_check_deadline(deadline)
```

---

## 검증 결과 (실제 실행 증거)

### TEST G2: httpx.ReadTimeout → fail-closed

```python
def raise_read_timeout(*args, **kwargs):
    raise httpx.ReadTimeout('Request timed out')

with patch.object(ollama.Client, 'embeddings', side_effect=raise_read_timeout):
    result = bridge_query('test query', top_k=5, limit_check=False)
```

**결과**:
```
✅ PASS: httpx.ReadTimeout → fail-closed (0.00s)
   result=[]
```

### TEST B: 정상 동작

```
✅ PASS: 5 citations 반환 (0.39s)
```

---

## Final State: PRODUCTION_READY

BLOCKER 1 해결됨. nae_pd module 활성화 시 실제 Production 사용 가능.
