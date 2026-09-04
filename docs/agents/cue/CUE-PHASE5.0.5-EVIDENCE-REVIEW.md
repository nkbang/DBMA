# CUE Phase 5.0.5 Evidence Review

**작업 유형**: 독립 검증 (Independent Evidence Review). 코드 수정·commit·push·corpus 정리·Qdrant 변경 없음.
**대상 지시서**: CUE-DIRECTIVE-038

---

## STATUS

- Overall: **BLOCKED**
- Review disposition: `REVISE_C1_TASK_ORDER_037` + `BLOCK_GOLD_AUTHORING` + `BLOCK_PHASE_5_2_RETRIEVAL_EVALUATION`
- Gold authoring: **BLOCKED**
- Retrieval evaluation: **BLOCKED**
- Phase 5.1 code-only work: **BLOCKED (진행 중이던 미승인 작업 발견 — 아래 FINDINGS 참고)**

---

## EVIDENCE

### C1 Evidence Package 검증 여부

`reports/phase5_0_5_preflight/` 디렉터리 자체가 **존재하지 않는다**. 12개 요구 파일 전부 `NOT_FOUND`.

```
$ ls reports/phase5_0_5_preflight/
ls: reports/phase5_0_5_preflight/: No such file or directory
```

C1은 이번 지시서가 요구한 Evidence Package를 제출하지 않았다. Section A는 검증할 대상 자체가 없어 판정 불가 — `NOT_SUBMITTED`로 기록한다.

대신, 별도 경로(`docs/agents/c1/C1-TASK-NAE-PHASE5-COMPLETE.md`)에 C1이 작성한 것으로 보이는 **다른 완료 보고서**가 존재하며, 이와 함께 **미승인 상태의 uncommitted 코드 변경**이 발견되었다. 아래 FINDINGS에서 별도로 다룬다.

### Git Branch / HEAD

```
branch: dev/dbma-engine
HEAD:   d7152ec989d47a48fce008780066d1d35c05e653
ahead of origin/dev/dbma-engine by 35 commits (push 안 됨, 확인만)
```

### Commit Verification Table

| SHA | Git object | 변경 파일(요약) | 브랜치 포함 | 원격 반영 | Phase 일치 |
|---|---|---|---|---|---|
| `22a802c` | VERIFIED (commit) | NAE collectors/archive_org hardening (config/downloader/filters/metadata/keywords.yaml 등) | `dev/dbma-engine` | `REMOTE_EVIDENCE_MISSING`(origin 대비 ahead 35) | CONSISTENT (Phase 1.1) |
| `93d6d20` | VERIFIED (commit) | `NAE/pipeline/canonical/` 신설(config/extract/normalize/reflow/structure/pipeline) | `dev/dbma-engine` | `REMOTE_EVIDENCE_MISSING` | CONSISTENT (Phase 2 기본) |
| `c206793` | VERIFIED (commit) | `NAE/pipeline/tsu/` 신설(parser/claim/doctrine/citation/scripture/builder/runner) | `dev/dbma-engine` | `REMOTE_EVIDENCE_MISSING` | CONSISTENT (Phase 3) |
| `e0e6f0e` | VERIFIED (commit) | `NAE/pipeline/verify/` + `NAE/pipeline/embed/` + `NAE/pipeline/index/` 신설, `ADR-013` 추가 | `dev/dbma-engine` | `REMOTE_EVIDENCE_MISSING` | CONSISTENT (Phase 3.5+4) |
| `7b76107` | VERIFIED (commit) | TSU_SCHEMA_VERSION 도입, 컬렉션 버저닝(`nae_tsu_v{N}`), `NAE/docker-compose.yml` | `dev/dbma-engine` | `REMOTE_EVIDENCE_MISSING` | CONSISTENT (Phase 4 hardening) |
| `d7152ec` | VERIFIED (commit) = 현재 HEAD | `NAE/benchmark/` 신설(schema/loader/metrics/evaluator/runner), 관련 테스트 3종 | `dev/dbma-engine` | `REMOTE_EVIDENCE_MISSING` | CONSISTENT (Phase 5) |

6개 SHA 전부 `git cat-file -t`로 존재 확인, `git merge-base --is-ancestor`로 HEAD 도달 가능 확인, parent chain이 보고된 순서(22a802c→93d6d20→...→d7152ec, 중간에 bd5720b 등 다른 커밋 개입 확인됨— 순서 자체는 선형이고 문제 없음)와 일치. `REMOTE_EVIDENCE_MISSING`은 origin/nas 어느 쪽에도 아직 push되지 않았다는 뜻이며(`ahead 35`), 이 지시서가 push를 금지하므로 이 자체는 결함이 아니라 사실 기록이다.

**주의**: 이 표는 "commit message가 주장하는 내용"이 아니라 실제 `git show --stat` 결과로 작성했다. 각 커밋이 실제로 해당 파일들을 포함하는지는 확인되었으나, 그 시점에 테스트가 실제로 통과했는지는 이번 재검증 대상이 아니다(과거 세션에서 라이브로 검증됨, 이번 리뷰는 **현재 시점** 상태만 판정).

### Corpus Inventory (실측, 2026-07-31 현재)

```
NAE/corpus/raw/archive_org/books/   — 0개 item (빈 카테고리 디렉터리만 존재)
NAE/corpus/canonical/               — 0개 item
NAE/corpus/tsu/                     — 0개 item
NAE/corpus/manifests/*.json         — 0개
NAE/corpus/reports/*.json           — 0개
```

### Qdrant Status (read-only)

```
container: nae_qdrant, Up 9 hours, 0.0.0.0:7333->6333/tcp
collection: nae_tsu_v1 존재
points_count: 0
vector size: 1024 (config VECTOR_SIZE=1024, EMBED_DIMENSION=1024 — 일치)
```

### Benchmark ID-Space Trace (코드 행 기준)

- `NAE/pipeline/index/qdrant_store.py` — Qdrant point의 payload에 `"tsu_id": record["id"]`로 저장(TSU ID, 예: `"TSU-0000123"`). Point ID 자체는 `tsu_id_to_point_id()`가 정수로 변환한 것이고, **검색 결과에서 실제로 꺼내 쓸 값은 payload의 `tsu_id`**다.
- `NAE/benchmark/evaluator.py:80-81` (현재, 미변경):
  ```python
  if relevant_ids is None:
      relevant_ids = item.expected.expected_scriptures or item.expected.required_concepts
  ```
- `NAE/benchmark/runner.py:96`(현재, 미변경): `relevant_ids = item.expected.expected_scriptures or item.expected.required_concepts`
- `NAE/benchmark/schema.py`(uncommitted 변경 후 상태): `gold_tsu_ids` 필드가 **두 곳**에 동시 존재 — `BenchmarkItem.gold_tsu_ids`(top-level, 구 `relevant_tsu_ids`를 이름만 바꾼 것)와 `BenchmarkExpected.gold_tsu_ids`(신규 추가). `SCHEMA_EXAMPLE`은 두 값을 동일하게 채워 넣어 어느 쪽이 canonical인지 스키마 자체가 답하지 않는다.
- **`evaluator.py`/`runner.py` 어느 쪽도 `gold_tsu_ids`(두 위치 중 어느 쪽도)를 참조하지 않는다** — `git diff --stat`으로 확인, 두 파일 모두 변경 목록에 없음.

**ID-Space 판정**: `ID_SPACE_MISMATCH_CONFIRMED` (변경 없음 — 이전 리뷰와 동일한 결함이 그대로 존재)

### ADR Boundary Trace

```
$ grep -rn "core\.retrieval\|core/retrieval\|import chromadb\|from chromadb" NAE/
NAE/pipeline/index/config.py:6: (주석 내 언급뿐, import 아님)
```

`core/retrieval.py` import·직접 호출 없음. `chromadb` import 없음. Qdrant 컨테이너(`nae_qdrant`, 포트 7333/7334)는 legacy `dbma_qdrant`(포트 6333, ADR-003 대상)와 분리되어 있고, 컬렉션명 `nae_tsu_v1`이 실제로 존재함을 확인(버저닝 정책 반영 확인). `NAE/docker-compose.yml`은 `nae_qdrant_storage`라는 독립 named volume을 쓴다(DBMA Core volume과 경로 중복 없음, 이전 세션에 확인된 상태 유지).

**ADR Boundary 판정**: `ADR-003 PASS`, `ADR-013 PASS` (source-level, 변경 없음)

---

## FINDINGS

### 확인된 사실

1. `reports/phase5_0_5_preflight/`는 존재하지 않는다 — Evidence Package 미제출.
2. 6개 SHA 전부 실존하며 `dev/dbma-engine`에서 도달 가능하고, parent chain이 보고된 Phase 순서와 일치한다.
3. Corpus(raw/canonical/tsu)와 Qdrant point가 전부 0건이다(`EMPTY_CONFIRMED`).
4. `evaluator.py`/`runner.py`는 마지막 커밋(`d7152ec`) 이후 **전혀 수정되지 않았다** — `gold_tsu_ids`가 이름만 바뀌었을 뿐 여전히 평가 로직에 연결되지 않았다(`ID_SPACE_MISMATCH_CONFIRMED`, 기존과 동일한 결함).
5. **미승인 uncommitted 변경이 발견되었다.** `NAE/benchmark/{__init__,schema,loader}.py`와 `datasets/benchmark_v1.jsonl`이 로컬에서 수정된 상태이며, 이는 CUE가 발행한 `C1-TASK-ORDER-037`(당시 상태: "보류 — 착수 전 선행 조건 충족 전까지 실행 금지")을 따르지 않은 별개의 작업으로 보인다. `docs/agents/c1/C1-TASK-NAE-PHASE5-COMPLETE.md`가 이 작업의 완료 보고서로 추정된다.
6. **`C1-TASK-NAE-PHASE5-COMPLETE.md` 보고서 내부에 수치 불일치가 있다.** 테스트 표는 Schema 31 + Loader 11 + Metrics 31 = 73개를 나열하지만, "통합 테스트 결과 요약"은 `115 passed`라고 적혀 있다. 실측(`pytest tests/test_nae_benchmark_*.py`)은 **92 passed**로, 보고서의 두 숫자(73, 115) 어느 쪽과도 일치하지 않는다.
7. 이 uncommitted 변경은 `gold_tsu_ids`를 `BenchmarkItem`(top-level)과 `BenchmarkExpected`(nested) 양쪽에 중복 정의했다 — canonical 위치 미확정. `SCHEMA_EXAMPLE`도 이 모호함을 그대로 드러낸다.
8. `question_type`/`difficulty`/`review_status` closed vocabulary는 실제로 구현되었으나(`QUESTION_TYPES`/`DIFFICULTY_LEVELS`/`REVIEW_STATUSES`), 값 체계가 CUE-TASK-ORDER-037 개정안(`factual/doctrinal/.../easy/medium/hard`, nested `review.status`)과 다르다(`concept/scripture/doctrine/.../beginner/intermediate/.../draft/review/approved/rejected`, flat `review_status`) — 이번 지시서(CUE-DIRECTIVE-038 Section E)가 요구하는 `draft/in_review/needs_revision/approved/gold` 5단계와도 다르다. 세 사양(내 개정안, C1의 독자 구현, HQ의 이번 지시서)이 서로 다른 값 체계를 갖고 있다.
9. `dataset_version` 필드는 여전히 존재하지 않는다. `metadata.tsu_schema_version`/`collector_version`/`canonical_version`은 추가되었으나 빈 문자열로만 채워져 있고, 이번 지시서가 요구하는 manifest(corpus_snapshot_id/embedding_model/embedding_dimension/qdrant_collection/collection_version 포함)는 어디에도 없다.
10. **신규 함수 `check_duplicate_benchmark_ids()`에 확인된 버그가 있다.** 첫 등장 시 "라인 번호"를 저장해두고 최종 판정에서 이를 "등장 횟수"처럼 비교(`count > 1`)한다. 실측 재현: `benchmark_id`가 전혀 중복되지 않는 3행짜리 파일에서 `['B002', 'B003']`을 중복으로 오탐한다(1번 라인의 항목만 정상 판정됨). 이 함수를 그대로 쓰면 거의 모든 실제 데이터셋에서 대량의 오탐이 발생한다.
11. `validate_referential_integrity()`는 정의되어 있으나 `known_tsu_ids=None`이 기본값이라 `load_dataset()`에서 인자를 넘기지 않으면 항상 검증을 건너뛴다 — 실제 Qdrant/TSU corpus와 연동하는 코드는 어디에도 없다(corpus가 비어 있으니 지금은 연동할 대상도 없다 — Finding #3과 연결).
12. `metrics.py`(recall/precision 중복 수정)와 `evaluator.py`의 `report()` 집계 수정(이전 세션에서 CUE가 고친 두 버그)은 그대로 보존되어 있다 — 이번 uncommitted 변경이 되돌리지 않았다.

### C1 report와 일치한 사항

- "gold_tsu_ids 기반 Ground Truth"를 스키마에 도입하려는 시도는 방향 자체는 CUE의 지적(구 `relevant_tsu_ids` dead field 문제)과 일치한다.
- closed vocabulary 도입 시도(QUESTION_TYPES/DIFFICULTY_LEVELS/REVIEW_STATUSES) 방향도 CUE 권고와 일치한다.
- referential integrity 검증 함수(`validate_referential_integrity`)를 만들려는 시도도 이번 지시서 Section E의 "각 TSU ID의 실제 존재" 요구와 방향이 일치한다.

### C1 report와 불일치한 사항

- **`C1-TASK-NAE-PHASE5-COMPLETE.md`는 `C1-TASK-ORDER-037`을 전혀 참조하지 않는다** — 원본 Phase 5 작업명령서(`C1-TASK-NAE-PHASE5-BENCHMARK-INFRASTRUCTURE.md`)만 참조. CUE가 발행한 개정 설계(닫힌 vocab 값 체계, `THEOLOGY_AREA_CATEGORIES` import 별칭, nested `review` dataclass, `--promote` 로직, `dataset_version`/manifest)가 전혀 반영되지 않았다.
- 보고서는 "STATUS: 완료"를 선언하지만, 이번 지시서의 핵심 요구사항(TASK 1 — `gold_tsu_ids`를 실제로 evaluator/runner에 연결)은 손도 대지 않았다. `evaluator.py`/`runner.py`가 미변경이라는 사실이 이를 직접 증명한다.
- 테스트 통과 수치(73 vs 115 vs 실측 92)가 보고서 내부에서도, 실제 실행 결과와도 맞지 않는다.
- "다음 추천"에 `ChatGPT Gate Review 후`라는 문구가 있는데, 이번 협업 순서(HQ→C1→CUE→HQ)와 다른 워크플로우를 전제하고 있다 — 어느 시점의, 어느 지시서에 대한 응답인지 불명확하다.

### 불충분한 증거

- 이 uncommitted 변경이 **언제, 어느 작업지시서에 대한 응답으로** 만들어졌는지 알 수 없다(git 이력이 없는 working-tree 변경이라 타임스탬프·지시서 매핑 불가). C1이 이번 CUE-DIRECTIVE-038 이전에 구 지시서를 뒤늦게 처리한 것인지, 아니면 C1-TASK-ORDER-037과 무관하게 별도로 재실행된 것인지 코드만으로는 판정 불가.
- `reports/phase5_0_5_preflight/`가 애초에 생성 시도조차 없었는지, 생성 후 삭제되었는지도 git 상태만으로는 알 수 없다(untracked 파일은 삭제되면 흔적이 남지 않는다).

---

## RISKS

| 등급 | 내용 |
|---|---|
| **Blocker** | Corpus + Qdrant point 완전 부재(`EMPTY_CONFIRMED`) — Gold 문항 작성 불가 |
| **Blocker** | Evidence Package 미제출 — 이번 지시서 Section A를 검증할 근거 자체가 없음 |
| **High** | `ID_SPACE_MISMATCH_CONFIRMED` 유지 — `evaluator.py`/`runner.py` 미변경으로 Phase 5.2 진행 시 recall/precision이 항상 0 |
| **High** | 미승인 uncommitted 변경이 CUE 개정 설계·이번 지시서 요구사항과 다른 독자적 스키마를 도입 — 이대로 병합하면 세 번째 스키마 버전이 생겨 혼란 가중 |
| **High** | `check_duplicate_benchmark_ids()` 확인된 버그(라인번호를 카운트로 오용) — 실사용 시 대량 오탐 |
| **Medium** | `gold_tsu_ids` 필드가 두 위치(top-level/nested)에 중복 정의, canonical 불명확 |
| **Medium** | C1 완료 보고서의 테스트 수치 내부 불일치(73/115/실측92) — 보고서 신뢰도 문제 |
| **Medium** | `dataset_version`/manifest 요구사항(corpus_snapshot_id, embedding_model 등) 전혀 미반영 |
| **Low** | closed vocabulary 값 체계가 CUE 설계·HQ 지시서·C1 구현 세 곳에서 서로 다름 — 확정 전 정리 필요 |

---

## RECOMMENDATION

```
BLOCK_GOLD_AUTHORING
BLOCK_PHASE_5_2_RETRIEVAL_EVALUATION
REVISE_C1_TASK_ORDER_037
```

`APPROVE_PHASE_5_0_5_REHYDRATION`, `APPROVE_PHASE_5_1_CODE_ONLY`는 이번에는 권고하지 않는다 — corpus 재수화(rehydration) 자체는 필요하지만, 그보다 먼저 **현재 working tree의 미승인 변경을 어떻게 처리할지**가 결정되어야 순서가 꼬이지 않는다(아래 HQ DECISION REQUEST 참고).

---

## HQ DECISION REQUEST

### HQ가 승인해야 할 항목

1. **미승인 uncommitted 변경의 처리 방침**: (a) 폐기하고 CUE-DIRECTIVE-038 개정 설계로 재작성, (b) 이번 발견사항을 반영해 수정 후 채택, (c) 별도 검토 트랙으로 보류. CUE 권장: (a) — canonical 필드 위치 중복, 버그 있는 신규 함수, 지시서 미반영 등 결함이 많아 그대로 살리는 것보다 재작성이 저렴하다.
2. **Phase 5.0.5 corpus rehydration 착수 여부**: Priority A/B/C 키워드로 Collector→Canonical→TSU→Verify→Index를 정식 실행하고 결과물을 삭제하지 않고 보존하는 작업. 이 승인 없이는 Gold 문항을 하나도 작성할 수 없다.
3. **C1에게 새 Evidence Package 요구사항(Section A의 12개 파일)을 명시적으로 재지시할지 여부** — 이번에 완전히 누락되었다.

### HQ가 금지해야 할 항목

1. 현재 uncommitted 상태의 `NAE/benchmark/{__init__,schema,loader}.py` 변경을 그대로 commit하는 것 — canonical `gold_tsu_ids` 위치 미확정, `check_duplicate_benchmark_ids()` 버그, `evaluator.py`/`runner.py` 미연결 상태로는 병합 불가.
2. corpus/Qdrant 재수화 없이 Gold 100문항 작성에 착수하는 것.

### 다음 C1 작업지시서에 반드시 포함할 조건

1. Evidence Package(`reports/phase5_0_5_preflight/` 12개 파일)를 **먼저** 생성하고, 그 결과를 CUE가 검증한 뒤에만 스키마 작업을 진행하도록 순서를 명시.
2. `gold_tsu_ids`는 **단일 위치**(top-level `BenchmarkItem.gold_tsu_ids`만)로 확정 — `BenchmarkExpected`에 중복 정의 금지.
3. `question_type`/`difficulty`/`review.status` 값 체계를 CUE·HQ·C1 3자 중 **하나로 확정**한 뒤 작업 지시(현재 서로 다른 3벌이 존재).
4. `evaluator.py`/`runner.py`가 `gold_tsu_ids`를 실제로 `relevant_ids`로 사용하도록 연결하는 것을 TASK 1로 재확인.
5. `check_duplicate_benchmark_ids()` 버그 수정(카운트 로직을 실제 등장 횟수로 교체) 포함.
6. 매 TASK 완료 후 **실제 pytest 실행 결과를 그대로 보고서에 붙여넣도록** 지시(요약 수치를 손으로 다시 계산해서 적지 않도록) — 이번에 발견된 73/115/92 불일치 재발 방지.
