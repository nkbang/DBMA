# C1 Correction Order 008 — Phase 3: 경로 버그 + placeholder 텍스트 버그

| | |
|---|---|
| Issued by | CUE 독립 검증 (2026-08-16 15:4x CDT) |
| Continues | Correction Order 007 (진행 중인 작업 위에 추가 지적 — 계속 진행하되 아래 2건 함께 고쳐라) |
| 판정 | `enqueue_from_canonical()`의 실제 데이터 추출은 **정확함**(Fuller Vol02
  실제 book/author/page/paragraph 확인됨) — 이 부분은 다시 만들지 마라.
  버그 2건만 고쳐라. |

---

## 버그 1 — `worker/config.py`의 경로 계산 오류

```python
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
```

이 파일은 `NAE/pipeline/tsu/worker/config.py`에 있다. `parents[3]`은
`NAE/`까지만 올라간다(worker→tsu→pipeline→NAE, 4단계인데 3만 셈).
**진짜 프로젝트 루트(`/Users/David/DBMA`)에 도달하려면 `parents[4]`여야
한다.**

**실제 확인된 결과**: `worker_state.json`이 `NAE/corpus/tsu/`가 아니라
`NAE/NAE/corpus/tsu/worker_state.json`에 생성됨 — CUE가 파일시스템에서
직접 확인했다.

### 요구 조치

```python
_PROJECT_ROOT = Path(__file__).resolve().parents[4]  # 4단계: worker→tsu→pipeline→NAE→project root
```

수정 후 **기존에 잘못된 위치(`NAE/NAE/corpus/tsu/`)에 생긴 파일을 올바른
위치(`NAE/corpus/tsu/`)로 옮겨라**(데이터 손실 없이 — 이미 20건의 실제
Fuller Vol02 candidate가 들어있다, 다시 enqueue할 필요 없다). 그 다음
`NAE/NAE/` 디렉터리가 비었으면 삭제해라.

## 버그 2 — `runner.py::_run_worker_mode()`가 여전히 placeholder 텍스트 사용

```python
candidates.append({
    "candidate_id": cid,
    "text": f"candidate_text_for_{cid}",   # <- 이거, 가짜 텍스트
})
```

`enqueue_from_canonical()`이 이미 각 candidate의 `metadata`에
`text_preview`(120자로 잘림)를 저장해두는데, `_run_worker_mode()`는 그걸
전혀 읽지 않고 저 가짜 문자열을 그대로 LLM에 넘긴다. 이러면 `--enqueue`로
채운 실제 Fuller Vol02 내용이 전혀 쓰이지 않고, LLM은 의미 없는 문자열만
받는다.

### 요구 조치

1. `loader.py`의 `metadata`에 `text_preview`(120자 truncate) 대신 **전체
   문장 텍스트**를 저장해라(필드명은 `text`로 통일해도 된다). candidate
   수가 지금 규모(20~수백 건)에서는 state JSON 파일 크기 문제 안 된다 —
   과도하게 걱정하지 마라.
2. `_run_worker_mode()`에서 `entry.metadata["text"]`(또는 새 필드명)를
   읽어서 실제로 넘겨라:
   ```python
   candidates.append({
       "candidate_id": cid,
       "text": entry.metadata.get("text", ""),
   })
   ```
3. 이미 큐에 들어간 20건은 `text_preview`만 있으니, 버그 수정 후 **큐를
   지우고 다시 `--enqueue`부터 실행**해라(이번엔 진짜 전체 텍스트가
   들어가게).

## Work 3 재실행 (버그 수정 후, 이번엔 진짜로)

```bash
python3 -m NAE.pipeline.tsu.runner --enqueue Fuller_Complete_Works_Vol02 --max-candidates 20
python3 -m NAE.pipeline.tsu.runner --worker-mode
```

- `--worker-mode` 실행 로그에서 최소 1개 candidate의 실제 `claim`
  필드(LLM이 추출한 신학적 주장)가 진짜 Fuller Vol02 내용을 반영하는지
  눈으로 확인 가능한 수준으로 evidence에 남겨라(placeholder 문자열 기반
  가짜 claim이 아니라는 걸 증명해라).
- 의도적 실패 유발 → FAILED 유지 확인 → `--retry-failed`로만 복구되는지
  — 이전 지시 그대로.

## Evidence

`worker-mode-execution.log`, `retry-failed-execution.log`를 이번엔
실제로 만들어서 남겨라(이전 evidence 디렉터리 확인 결과 아직 없었다).
