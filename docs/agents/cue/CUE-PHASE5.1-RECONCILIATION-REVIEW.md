# CUE Phase 5.1 Reconciliation Review

**작업 유형**: 문서 전용 최종화 (Documentation-only finalization). 코드·테스트·데이터 수정 없음. corpus/Qdrant 변경 없음.
**참조**: `docs/audit/phase5_1/`(변경하지 않음, 참조만) — 이 문서는 그 패키지의 결론을 반복 인용하지 않고 독립적으로 재확인한다.

---

## STATUS

```
STATUS: ID_SPACE_MISMATCH_CONFIRMED
Gold Authoring: BLOCKED
Phase 5.2 Retrieval Evaluation: BLOCKED
Phase 5 Benchmark: NOT RETRIEVAL-VALID
Phase 4 Vector Infrastructure: LOCAL ADR COMPLIANCE REPORTED — P1 GITHUB VERIFICATION PENDING
```

---

## 1. `evaluator.py`가 `gold_tsu_ids`를 읽지 않는 코드 행 근거

`NAE/benchmark/evaluator.py:81`:

```python
relevant_ids = item.expected.expected_scriptures or item.expected.required_concepts
```

이 한 줄이 `Evaluator.evaluate()`가 정답(ground truth)을 결정하는 유일한 경로다(호출자가
`relevant_ids`를 명시적으로 넘기지 않는 한). `item.gold_tsu_ids`(top-level) 또는
`item.expected.gold_tsu_ids`(nested, working tree에 미커밋 상태로 존재)는 이 파일 안
어디에서도 등장하지 않는다:

```
$ grep -n "gold_tsu_ids" NAE/benchmark/evaluator.py
(결과 없음)
```

`evaluator.py:102`에서 이 `relevant_ids`가 그대로 지표 계산에 전달된다:

```python
metrics = compute_all_metrics(retrieved_ids, relevant_ids, effective_k)
```

## 2. `runner.py`가 Qdrant/retriever를 호출하지 않고 `_dummy_retrieval()`을 쓰는 코드 행 근거

`NAE/benchmark/runner.py:90`:

```python
retrieved_ids = retrieval_fn(qtext)
```

`retrieval_fn`은 함수 인자로 주입되는 콜러블(`RetrievalFn = Callable[[str], List[str]]`,
41행)이며, CLI 경로(`main()`)에서 사용자가 `--retrieval-fn`을 지정하지 않는 한 다음이
기본값으로 바인딩된다(`runner.py:163-170`):

```python
def _dummy_retrieval(question_text: str) -> List[str]:
    """더미 검색 함수 — 실제 Qdrant 연결 전까지 사용.
    TODO: 실제 Qdrant retrieval_fn으로 교체.
    """
    return []
```

`NAE/benchmark/runner.py` 전체에서 `qdrant`, `NAE.pipeline.index`, `NAE.pipeline.embed`
문자열은 0건이다:

```
$ grep -n "qdrant\|pipeline.index\|pipeline.embed" NAE/benchmark/runner.py
(결과 없음)
```

즉 Qdrant를 "잘못 호출"하는 것이 아니라, 호출하는 코드 자체가 존재하지 않는다.

## 3. `expected_scriptures`/`required_concepts`가 metric 정답 조건으로 쓰이는 코드 행 근거

동일한 패턴이 `runner.py:96`에도 있다:

```python
relevant_ids = item.expected.expected_scriptures or item.expected.required_concepts
```

`evaluator.py:81`(evaluate() 내부 기본값 경로)과 `runner.py:96`(run_benchmark() 내부
직접 호출 경로) 두 곳 모두 동일한 표현식을 독립적으로 갖고 있다 — 공통 함수로 추출되지
않은 중복 코드이며, 향후 하나만 고치고 다른 하나를 놓칠 위험이 이미 구조적으로 존재한다.

## 4. `retrieved_ids`와 정답 값의 ID-space 불일치

```
retrieved_ids 형식:  "TSU-0000123"  (NAE/pipeline/index/qdrant_store.py:build_point()가
                                      payload["tsu_id"]로 저장하는 형식, NAE/pipeline/tsu/
                                      builder.py:_format_tsu_id()가 생성)
relevant_ids 형식:   "로마서 3:25"   (NAE/benchmark/datasets/benchmark_v1.jsonl 1번째 줄의
                                      실제 expected_scriptures 값)
```

`metrics.recall_at_k`/`precision_at_k`/`mean_reciprocal_rank`는 두 리스트의 문자열
교집합(`set` 연산)으로 동작한다(`NAE/benchmark/metrics.py` 확인, 계산 로직 자체는
정상). TSU-ID 문자열과 성경 구절 문자열은 교집합이 항상 공집합이므로, 이 두 공간이
연결되지 않는 한 **어떤 검색 결과가 오더라도 recall/precision/MRR/hit_rate는 전부 0을
반환한다** — 검색 품질과 무관한 상수 0이다.

## 5. `92 passed`의 정확한 명령과 한계

```
$ ~/envs/dbma311/bin/python -m pytest tests/test_nae_benchmark_*.py -v
============================== 92 passed in 0.07s ==============================
```

(전체 출력은 `docs/audit/phase5_1/tests/pytest-output.txt`에 원본 저장됨, 이 문서에서는
재확인 실행 결과만 인용)

**한계**: 이 92개는 전부 **unit test**다 — `schema.py`의 validation 로직, `loader.py`의
JSONL 파싱, `metrics.py`의 순수 함수 계산, `evaluator.py`/`runner.py`의 오케스트레이션을
각각 독립적으로(주로 mock 또는 고정 입력으로) 검증한다. 이 중 어떤 테스트도 다음을
검증하지 않는다:

- 실제 Qdrant에서 반환된 검색 결과로 실행했을 때의 recall/precision
- `gold_tsu_ids`가 실제로 평가에 반영되는지(애초에 반영되지 않으므로 테스트할 대상이
  없음 — 4번 항목 참고)
- 100문항 규모에서의 벤치마크 실행 가능성

**"unit test pass ≠ retrieval-valid benchmark"**: 92 passed는 "코드가 의도한 대로
동작한다"는 것만 증명한다. 그 "의도"(`expected_scriptures`를 정답으로 쓰는 것) 자체가
Phase 5.2의 실제 요구사항(TSU-ID 기반 검색 평가)과 맞지 않으므로, 테스트 통과가 벤치마크의
retrieval-validity를 보장하지 않는다.

## 6. ADR-003/ADR-013 — local evidence와 P1 GitHub 검증 보류 사실

`docs/audit/phase5_1/adr-linkage.md`에서 로컬 저장소 기준으로 다음을 확인했다:

- `core.retrieval`/`chromadb` import 0건(grep, source-level)
- `nae_qdrant`(포트 7333/7334, 볼륨 `nae_qdrant_storage`)가 legacy `dbma_qdrant`(포트 6333,
  볼륨 `dbma_qdrant_storage`)와 완전 분리되어 실행 중
- 컬렉션 `nae_tsu_v1` 실존, BGE-M3 dimension(1024) = Qdrant vector size(1024) 일치

이 확인은 **전부 로컬 파일시스템·로컬 Docker 데몬·로컬 git 저장소**를 대상으로 한 것이다.
`git status`상 `dev/dbma-engine`은 `origin/dev/dbma-engine` 대비 35커밋 ahead이며 아직
push되지 않았다(`docs/audit/phase5_1/commit.txt`에 기록된 상태 기준). 즉 이번 ADR 준수
확인은 **local evidence로서는 VERIFIED**이나, GitHub(P1)이 동일한 커밋 이력·파일 상태를
독립적으로 관측하고 재확인한 사실은 없다 — 로컬 검증과 원격 검증은 별개의 사실이다.

## 7. Uncommitted 변경 파일 목록 — evidence-only commit 제외 명시

다음 파일은 현재 working tree에서 수정된 상태이며, **이번 또는 향후 evidence-only commit에
포함하지 않는다**(HQ-DIRECTIVE-042의 금지 목록과 일치, 이 문서 작성 시점 기준 재확인):

```
NAE/benchmark/__init__.py
NAE/benchmark/datasets/benchmark_v1.jsonl
NAE/benchmark/loader.py
NAE/benchmark/schema.py
scripts/build_tsu_dataset.py
tests/test_nae_benchmark_loader.py
tests/test_nae_benchmark_schema.py
```

이 목록은 실측 재확인(`git status --short`)과 일치하며, 이번 문서 작성 과정에서 위 파일들에
어떠한 수정·삭제·`git add`도 수행하지 않았다.

## 8. C1의 115 → 73 정정과 실제 92 passed의 불일치 — 원인 또는 미해결 상태

`docs/agents/c1/C1-TASK-NAE-PHASE5-COMPLETE.md`는 테스트 표에서 Schema 31 + Loader 11 +
Metrics 31 = **73**개를 개별 나열하지만, 같은 문서의 "통합 테스트 결과 요약" 섹션은
**115 passed**라고 기록한다. 이 두 숫자는 같은 문서 안에서도 서로 다르다.

이번 forensic(`docs/audit/phase5_1/`)과 이 문서의 재확인 실행 결과는 **92 passed**다 —
73과도, 115와도 일치하지 않는 세 번째 값이다.

**원인은 확인되지 않았다** — working tree가 uncommitted 상태이므로(7번 항목 목록) 어느
시점의 파일 스냅샷을 C1이 73/115를 셀 때 사용했는지 재현할 방법이 없다. 가능한 설명
가설은 다음과 같으나, 어느 것도 코드/git 증거로 확정되지 않는다:

- 73은 C1이 손으로 표에 나열한 개수(누락 가능), 115는 실행 로그를 잘못 옮겨 적었거나
  다른 실행(예: `tests/` 전체 실행, 또는 이전 파일 상태)의 결과를 붙여넣었을 가능성
- 92는 현재 working tree 상태(schema.py/loader.py 미커밋 변경 포함)에서 실행한 결과이므로,
  C1이 73/115를 기록한 시점의 파일 상태와 다를 가능성

**미해결 상태로 기록한다** — 이 불일치는 추가 조사(예: C1에게 실행 로그 원본 제출 요구)
없이는 해소되지 않는다.

---

## 최종 판정 재확인 (독립 결론)

이 문서는 `docs/audit/phase5_1/`의 결론을 인용이 아니라 위 1~8번 항목에서 코드/명령을
다시 실행·재인용하여 독립적으로 도출했다. 결론은 동일하다:

```
ID_SPACE_MISMATCH_CONFIRMED — Gold Benchmark 100문항 작성 및 Phase 5.2 Retrieval
Evaluation은 evaluator.py:81, runner.py:96의 relevant_ids 소스가 gold_tsu_ids로
교체되고 runner.py의 retrieval_fn이 실제 Qdrant 호출로 대체되기 전까지 차단 상태를
유지해야 한다.
```
