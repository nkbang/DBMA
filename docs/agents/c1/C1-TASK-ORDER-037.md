# C1 Task Order 037 — NAE Phase 5.1: Gold Benchmark Dataset v1 Infrastructure

**상태**: **보류 — 아래 "0. 착수 전 선행 조건" 충족 전까지 실행 금지**
**우선순위**: P0 (Phase 5.2 Qdrant 연결의 선행 조건 — TASK 1을 먼저 하지 않으면 Phase 5.2에서 모든 질문의 recall/precision이 항상 0.0으로 나옴)
**대상 파일**: `NAE/benchmark/schema.py`, `NAE/benchmark/config.py`(신규), `NAE/benchmark/evaluator.py`, `NAE/benchmark/runner.py`, `NAE/benchmark/datasets/`, 관련 테스트
**참고 파일 (읽기 전용)**: `NAE/pipeline/tsu/config.py`(`DOCTRINE_CATEGORIES` — import로만 재사용), `docs/agents/c1/C1-TASK-NAE-PHASE5-BENCHMARK-INFRASTRUCTURE.md`, `docs/agents/cue/CUE-PHASE5.1-ARCHITECTURE-REVIEW.md`(이번 개정의 근거), `NAE/benchmark/GOLD_BENCHMARK_AUTHORING_GUIDE.md`
**모드 제약**: 이번 작업은 **데이터 구조·도구**만 만든다. 실제 신학적 질문/정답 100문항의 **내용을 C1이 창작하지 않는다** — 0번·아래 3번 참고.

---

## 0. 착수 전 선행 조건 (CUE Architecture Review에서 발견, HQ 승인 대기)

`docs/agents/cue/CUE-PHASE5.1-ARCHITECTURE-REVIEW.md` GROUND TRUTH REVIEW에서 확인:
NAE corpus(raw/canonical/tsu)와 `nae_qdrant` 컬렉션이 **현재 전부 비어 있다**(라이브 스모크테스트 후 매번 정리하는 방식으로 운영해왔기 때문). `gold_tsu_ids`는 실제 Qdrant에 존재하는 TSU ID를 사람이 조회해서 채우는 값이므로, corpus가 비어 있으면 TASK 5(사람의 Gold 문항 작성)를 시작할 수 없다.

**이 Task Order의 TASK 1~4(스키마·도구 구현)는 corpus 상태와 무관하게 지금 진행해도 된다** — 코드 작업이기 때문이다. 다만 완료 후 실제로 100문항 작성에 들어가려면, 그 전에 Collector→Canonical→TSU→Verify→Index 파이프라인을 정식으로 한 번 실행해 결과물을 **삭제하지 않고 보존**해야 한다(이건 C1의 작업이 아니라 CUE/HQ가 운영 단계에서 처리할 사안 — C1은 신경 쓰지 않아도 됨).

---

## 0-1. 역할 분리 (중요)

```
C1  → 데이터 구조(schema)와 도구(tooling) 구현
CUE/HQ → 실제 문항 샘플의 신학적 품질 검토 + corpus 운영
```

C1은 100문항짜리 **완성된 신학 벤치마크 데이터셋을 스스로 생성해서는 안 된다.** 신학적 정답(expected_scriptures, gold_tsu_ids, expected_doctrine 등)은 로컬 LLM이나 휴리스틱으로 만들어낼 수 없는 영역이다 — NAE 전체가 지금까지 "검증 안 된 분류기 위에 다중 처리 경로를 얹지 않는다"는 원칙을 지켜왔다(TSU의 `review_status: unverified`, evidence.py의 `textual_verification: not_available` 등과 동일한 원칙).

C1이 만드는 것: 스키마·검증 도구, 빈 값 placeholder 100개 템플릿 JSONL, review 상태 추적 CLI(promote 포함).
C1이 만들지 않는 것: 실제 질문 문장, 실제 gold_tsu_ids/expected_scriptures/expected_doctrine 값(테스트 픽스처 제외).

---

## 1. 배경

Phase 5 Benchmark Infrastructure는 CUE 기술 검토에서 두 가지 버그(recall 중복 오버플로, `report()` 집계 편향)를 수정한 뒤 승인되었다(커밋 `d7152ec`). Phase 5.1 착수 전 CUE의 Architecture/Ontology/Ground-Truth 설계 검토에서 스키마 확장 방향이 확정되었다 — 아래 TASK 2는 최초 초안 대비 개정된 버전이다.

`BenchmarkItem.relevant_tsu_ids` 필드가 스키마에 존재하지만 `evaluator.py`/`runner.py` 어디에서도 사용되지 않는다. 실제로는 `item.expected.expected_scriptures or item.expected.required_concepts`(성경 구절 문자열/한글 개념어)를 `relevant_ids`로 쓰고 있는데, `retrieved_ids`는 TSU ID(`TSU-0000123` 형식, `NAE/pipeline/index/qdrant_store.py`의 `tsu_id` payload 참고)다. 서로 다른 ID 공간이라 **절대 매칭되지 않는다** — Phase 5.2에서 실제 Qdrant 검색을 연결하면 모든 질문의 recall/precision이 검색 품질과 무관하게 항상 0.0이 된다.

## 2. 작업 범위

### TASK 1 — relevant_tsu_ids → gold_tsu_ids 정정 및 실제 연결 (최우선, P0)

1. `schema.py`의 `BenchmarkItem.relevant_tsu_ids` 필드명을 `gold_tsu_ids`로 변경한다(`to_dict`/`from_dict`도 함께).
2. `evaluator.py`의 `Evaluator.evaluate()`에서 `relevant_ids`의 기본값 결정 로직을 수정한다:
   - `relevant_ids`가 `None`으로 전달되면 `item.gold_tsu_ids`를 사용한다 (기존의 `item.expected.expected_scriptures or item.expected.required_concepts` 폴백은 제거).
   - `item.gold_tsu_ids`가 비어 있으면 지금처럼 `status="skipped"` 처리한다.
3. `runner.py`의 `run_benchmark()`도 동일하게 `item.gold_tsu_ids`를 `relevant_ids`로 사용하도록 수정한다.
4. `expected.expected_scriptures`/`expected.required_concepts`/`expected.expected_doctrine`은 삭제하지 않는다 — 사람이 문항을 검토할 때 참고하는 **설명용 필드**로 남긴다. 코드 주석으로 "지표 계산에는 더 이상 쓰이지 않음"을 명시한다.
5. 기존 `NAE/benchmark/datasets/benchmark_v1.jsonl`(구조 검증용 5개 레코드)도 `gold_tsu_ids` 필드명에 맞춰 갱신한다(값은 빈 배열 유지 — 구조 검증용이며 실제 데이터가 아니다).

### TASK 2 — Schema 확장 (CUE 개정 반영)

**2-1. `NAE/benchmark/config.py`(신규)** — 버전 관리 가능한 닫힌 vocabulary:

```python
from NAE.pipeline.tsu.config import DOCTRINE_CATEGORIES

# Benchmark의 theology_area는 TSU의 doctrine 분류와 반드시 같은 체계를 쓴다
# (CUE ONTOLOGY REVIEW) - 새 리스트를 만들지 말고 이 별칭만 쓸 것.
THEOLOGY_AREA_CATEGORIES = DOCTRINE_CATEGORIES

# 초기 제안값 - 실제 100문항 작성 중 부족하면 갱신 가능
# (NAE/benchmark/GOLD_BENCHMARK_AUTHORING_GUIDE.md §6 참고)
QUESTION_TYPE_CATEGORIES = [
    "factual", "doctrinal", "comparative", "exegetical", "historical", "other",
]

DIFFICULTY_CATEGORIES = ["easy", "medium", "hard"]
```

**2-2. `BenchmarkItem`에 필드 추가:**

- `question_type: str = ""` — `validate()`에서 `QUESTION_TYPE_CATEGORIES`에 속하는지(빈 문자열은 허용, 아직 미분류 상태) 검증한다.
- `difficulty: str = ""` — 동일하게 `DIFFICULTY_CATEGORIES` 검증.
- `theology_area: str = ""` — 동일하게 `THEOLOGY_AREA_CATEGORIES` 검증.
- `review: BenchmarkReview` — 신규 dataclass:
  ```python
  @dataclass
  class BenchmarkReview:
      status: str = "draft"  # "draft" | "in_review" | "needs_revision" | "approved" | "rejected"
      reviewer: str = ""
      reviewed_at: str = ""
      notes: str = ""
  ```

**2-3. `BenchmarkMetadata`에 필드 추가:**

- `dataset_version: str = ""` — 이 레코드가 속한 데이터셋 manifest 버전(아래 TASK 4 참고). 개별 문항이 아니라 파일(배치) 단위 추적용.

`to_dict`/`from_dict`/`validate()`/`SCHEMA_EXAMPLE`을 모두 새 필드에 맞춰 갱신한다. 기존 필드(`benchmark_id`, `question`, `expected`, `retrieval`, `evaluation`, `metadata`, `retrieved_tsu_ids`, `retrieved_scores`, `gold_tsu_ids`)는 유지한다.

### TASK 3 — 100문항 템플릿 생성 도구

`NAE/benchmark/template.py`(신규):

```python
def generate_placeholder_dataset(count: int = 100, output_path: Path = ..., dataset_version: str = "v1") -> None:
    """빈 값 placeholder 레코드 `count`개를 JSONL로 출력한다.

    각 레코드는 benchmark_id(B001, B002, ...)와 metadata.dataset_version만
    채워지고 나머지는 전부 기본값(빈 문자열/빈 리스트) 상태다 — 사람이 채워
    넣을 자리. review.status는 반드시 "draft"로 시작한다.
    """
```

CLI: `python -m NAE.benchmark.template --count 100 --dataset-version v1 --output NAE/benchmark/datasets/gold_v1_draft.jsonl`

**주의**: 생성되는 값은 전부 빈 값이어야 한다. `question.text`, `expected.expected_scriptures` 등에 예시 문구나 그럴듯한 신학 내용을 채워 넣지 말 것.

### TASK 4 — Human Review CLI (promote 로직 추가)

`NAE/benchmark/review.py`(신규):

- `--dataset <path> --summary`: `review.status`별 개수 집계 출력.
- `--dataset <path> --approve <benchmark_id> --reviewer <name>`: `review.status`를 `"approved"`로, `review.reviewer`/`review.reviewed_at`을 채우고 파일에 다시 저장.
- `--reject <benchmark_id> --notes <text>`, `--needs-revision <benchmark_id> --notes <text>`도 동일한 방식.
- 존재하지 않는 `benchmark_id`를 지정하면 에러 메시지와 함께 종료 코드 1(크래시 금지).
- **`--promote --draft <path> --output <gold_path> --manifest <manifest_path>`** (신규 요구사항):
  1. `review.status == "approved"`인 레코드만 필터링.
  2. 필수 필드(`question.text`, `gold_tsu_ids`)가 비어있지 않은지 **재검증** — approve는 됐지만 필드가 비어있는 레코드가 있으면 promote를 중단하고 어느 `benchmark_id`가 문제인지 출력한다(reviewer의 실수를 이중으로 방어).
  3. 통과한 레코드만 `gold_path`(JSONL)로 출력.
  4. `manifest_path`에 다음 형식으로 기록: `{"dataset_version": ..., "schema_version": "1", "question_count": N, "created_at": ..., "promoted_from": "<draft path>", "doctrine_coverage": {"Baptism": 3, "Soteriology": 5, ...}}` (`doctrine_coverage`는 promote된 레코드들의 `theology_area` 값 개수 집계).

### TASK 5 — 테스트

`tests/test_nae_benchmark_schema.py`에 `question_type`/`difficulty`/`theology_area`/`review`/`gold_tsu_ids`/`metadata.dataset_version` 검증 테스트를 추가한다(닫힌 vocabulary 위반 시 `validate()`가 에러를 반환하는지 포함). `tests/test_nae_benchmark_config.py`(THEOLOGY_AREA_CATEGORIES가 `DOCTRINE_CATEGORIES`와 동일 객체/값인지 확인), `tests/test_nae_benchmark_template.py`, `tests/test_nae_benchmark_review.py`(promote의 재검증 로직, 특히 "approved인데 필드가 비어있는 레코드는 promote되지 않는다"는 케이스 필수)를 신규 작성한다. 기존 86개 테스트가 필드명 변경으로 깨지지 않는지 확인하고, 깨진 부분은 새 필드명으로 갱신한다.

## 3. 완료 보고 형식

```
STATUS: PASS / BLOCKED

TASK 1 — gold_tsu_ids 연결:
(변경 전/후 evaluator.py/runner.py 핵심 diff, relevant_ids가 이제 어디서 오는지)

TASK 2 — Schema 확장:
(config.py 신규 리스트 3개, 추가된 필드 목록, THEOLOGY_AREA_CATEGORIES가 DOCTRINE_CATEGORIES를
 import로 참조하는지 - 값 복사 아닌지 - 확인)

TASK 3 — 템플릿 도구:
(생성된 100개 placeholder 레코드 중 1개 샘플 - 전부 빈 값인지 확인 가능하게)

TASK 4 — Review CLI:
(--summary, --approve, --promote 실행 예시와 출력. --promote의 재검증 실패 케이스 시연)

TEST RESULTS:
(pytest 전체 결과, 기존 86개 중 몇 개가 필드명 변경으로 수정되었는지)

KNOWN ISSUES:
(있다면)
```

## 4. 금지 사항

- 실제 신학적 질문 문장, expected_scriptures, gold_tsu_ids 값, expected_doctrine 값을 창작해 채워 넣지 말 것
- `NAE/pipeline/tsu/config.py` 수정 금지 (읽기 전용 — `DOCTRINE_CATEGORIES`만 import해서 재사용, 값 복사 금지)
- `NAE/pipeline/` 하위(canonical/tsu/verify/embed/index) 및 `core/` 하위 파일 수정 금지 — 이번 작업은 `NAE/benchmark/`에 한정
- git commit 금지 (CUE 검토 후 별도 승인)

---

## C1 전달용 지시 문구 (복사해서 그대로 전달 — HQ가 "0. 착수 전 선행 조건"을 확인·승인한 후에만 전달할 것)

```
C1, 다음 작업을 진행해줘.

작업명령서: docs/agents/c1/C1-TASK-ORDER-037.md

TASK 1부터 TASK 5까지 순서대로 진행해. TASK 1이 가장 중요해 — relevant_tsu_ids
필드가 evaluator.py/runner.py에서 전혀 쓰이지 않는 문제부터 고쳐야 나머지
작업이 의미가 있어.

TASK 2의 question_type/difficulty/theology_area는 자유 텍스트가 아니라
NAE/benchmark/config.py에 새로 만드는 닫힌 리스트를 써야 해. theology_area는
특히 중요한데, NAE/pipeline/tsu/config.py의 DOCTRINE_CATEGORIES를 값으로
복사하지 말고 반드시 import해서 별칭(THEOLOGY_AREA_CATEGORIES)으로 참조해 —
나중에 한쪽만 갱신되는 사고를 막기 위해서야.

TASK 4의 --promote 커맨드가 이번에 새로 추가된 요구사항이야. approved인데
필수 필드가 비어있는 레코드는 promote되면 안 돼 — 재검증 로직 꼭 넣어줘.

가장 중요한 제약: 실제 신학 문항 100개의 내용(질문 문장, 성경 구절, TSU ID,
교리 분류)을 네가 만들어내면 안 돼. 스키마와 도구만 만들고, 실제 값은 전부
빈 상태(placeholder)로 남겨.

완료되면 문서에 명시된 "완료 보고 형식"으로 보고하고, git commit은 하지 마.
```
