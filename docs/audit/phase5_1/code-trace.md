# Phase 5.1 Code Trace — Q1/Q2/Q3 (Read-only Forensic)

모든 인용은 현재 working tree(HEAD `d7152ec` + 미커밋 변경 포함, `changed_files.txt` 참고)의
실제 파일 내용을 grep/read로 직접 확인한 결과다. 추측·요약 없이 코드 자체를 인용한다.

---

## Q1 — evaluator가 `gold_tsu_ids`를 읽는가?

**판정: FAIL**

`NAE/benchmark/evaluator.py` 80-81행 (현재 상태, 이전 커밋과 동일 — 미변경):

```python
if relevant_ids is None:
    relevant_ids = item.expected.expected_scriptures or item.expected.required_concepts
```

`item.gold_tsu_ids`(top-level) 또는 `item.expected.gold_tsu_ids`(nested, 미커밋 변경으로 신규 추가됨)
어느 쪽도 이 파일 어디에서도 참조되지 않는다. 다음 grep으로 확인:

```
$ grep -n "gold_tsu_ids" NAE/benchmark/evaluator.py
(결과 없음)
```

실제로 읽는 것은 `expected.expected_scriptures`(성경 구절 문자열, 예: `"로마서 3:25"`) 또는
`expected.required_concepts`(한글 개념어, 예: `"속죄"`)다.

---

## Q2 — runner가 Qdrant 검색 결과를 evaluator에 전달하는가?

**판정: FAIL (연결 자체가 구현되어 있지 않음 — Phase 5.2 미착수 상태)**

`NAE/benchmark/runner.py` 41행:

```python
RetrievalFn = Callable[[str], List[str]]
```

90행:

```python
retrieved_ids = retrieval_fn(qtext)
```

`retrieval_fn`은 외부에서 주입되는 콜러블이며, CLI 기본값은 163-170행의 `_dummy_retrieval`:

```python
def _dummy_retrieval(question_text: str) -> List[str]:
    """더미 검색 함수 — 실제 Qdrant 연결 전까지 사용.
    TODO: 실제 Qdrant retrieval_fn으로 교체.
    """
    return []
```

`NAE/benchmark/runner.py` 전체에서 `qdrant`, `NAE.pipeline.index`, `NAE.pipeline.embed` 문자열은
0건 발견(grep 확인). 즉 runner는 Qdrant를 호출하지 않으며, 호출할 수 있는 함수를 주입받는
인터페이스만 존재한다. "Qdrant 결과를 evaluator에 전달하는가?"라는 질문 자체가 아직 전달할
실제 Qdrant 결과가 없는 상태다.

---

## Q3 — Metric 입력 공간이 동일한가?

**판정: FAIL — 비정상 케이스와 정확히 일치**

- `retrieved_ids`의 형식: `NAE/pipeline/index/qdrant_store.py`의 `build_point()`가 Qdrant
  payload에 저장하는 값은 `"tsu_id": record["id"]`이며 `record["id"]`는 `NAE/pipeline/tsu/builder.py`의
  `_format_tsu_id()`가 생성하는 `"TSU-0000123"` 형식이다. Q2에서 확인했듯 이 값이 실제로
  `retrieved_ids`에 들어오는 코드 경로는 아직 없지만, 향후 연결될 경우의 형식은 TSU-ID다.
- `relevant_ids`(gold)의 형식: Q1에서 확인한 `expected.expected_scriptures`/`required_concepts` —
  `NAE/benchmark/datasets/benchmark_v1.jsonl` 실제 데이터 예시(1번째 줄):
  ```json
  "expected_scriptures": ["히브리서 9:22", "로마서 3:25"]
  ```
  자연어 성경 구절 문자열이지 TSU-ID가 아니다.

```
retrieved_ids 공간:  "TSU-0000123" (TSU-ID)
relevant_ids 공간:   "로마서 3:25" (자연어 성경 구절 문자열)
```

사용자가 제시한 "비정상" 예시(`retrieved_ids`=TSU-ID, `gold`=`"Romans 3:25"`)와 정확히 일치한다.
두 집합의 교집합이 항상 공집합이므로 `metrics.recall_at_k`/`precision_at_k`는 실제 검색
품질과 무관하게 항상 0을 반환한다(코드 로직 자체는 정상 동작 — 입력 공간이 어긋난 것).

---

## 참고: `gold_tsu_ids` 필드의 현재 상태 (커밋되지 않음)

미커밋 변경(`git diff NAE/benchmark/schema.py`, `changed_files.txt` 참고)이 `gold_tsu_ids`
필드를 두 곳에 추가했으나, 위 Q1 확인대로 `evaluator.py`/`runner.py` 어느 쪽도 아직 이 필드를
읽지 않는다 — 필드는 존재하나 평가 파이프라인에 연결되지 않은 상태(dead field)다.

```
$ grep -n "gold_tsu_ids" NAE/benchmark/schema.py
68:    gold_tsu_ids: List[str] = field(default_factory=list)   # BenchmarkExpected (nested)
118:    gold_tsu_ids: List[str] = field(default_factory=list)  # BenchmarkItem (top-level)
141, 166, 214-216, 223-240, 261, 278, 296:  to_dict/from_dict/validate/
    validate_referential_integrity/EXPECTED_REQUIRED/SCHEMA_EXAMPLE 참조
```

두 개의 독립된 필드 정의(68행, 118행)가 동시에 존재 — canonical 위치가 스키마 자체에서
확정되지 않음. `evaluator.py`/`runner.py`에는 `gold_tsu_ids` 문자열이 0건(grep 확인).
