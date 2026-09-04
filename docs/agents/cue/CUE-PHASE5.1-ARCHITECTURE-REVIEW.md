# CUE 작업명령서 결과 — NAE Phase 5.1 Technical Architecture Review & Gold Benchmark Design

**작업 유형**: 설계 및 검토 (구현 아님)
**대상**: NAE Phase 5 Benchmark Infrastructure (커밋 `d7152ec`) + Phase 5.1 착수 전 설계

---

## STATUS

`DESIGN REVIEW COMPLETE — C1-TASK-ORDER-037 개정 필요, 착수 전 선행 조건 1건 발견`

---

## ARCHITECTURE REVIEW (TASK 6)

### 현재 구조

```
NAE/collectors/archive_org/  →  NAE/corpus/raw/
        ↓ (Phase 2)
NAE/pipeline/canonical/      →  NAE/corpus/canonical/
        ↓ (Phase 3)
NAE/pipeline/tsu/            →  NAE/corpus/tsu/
        ↓ (Phase 3.5)
NAE/pipeline/verify/         →  NAE/corpus/tsu/*/tsu_verified.json
        ↓ (Phase 4)
NAE/pipeline/embed/ + NAE/pipeline/index/  →  nae_qdrant (collection nae_tsu_v1)
        ↓ (Phase 5, 아직 없음)
NAE/benchmark/  ←→  ??? (Retriever)  ←→  nae_qdrant
```

### 확인된 것

- `NAE/benchmark/`는 `core/retrieval.py`·Chroma·Qdrant 어디에도 직접 의존하지 않는다(재확인, grep 결과 동일). ADR-013의 격리 원칙 준수.
- `runner.py`의 `RetrievalFn = Callable[[str], List[str]]`은 좋은 설계다 — Phase 5.2에서 실제 검색 함수를 주입해도 `evaluator.py`/`metrics.py`는 손댈 필요가 없다.

### 빠진 것 — Retriever 컴포넌트가 존재하지 않는다

`Benchmark → Retriever → Qdrant → TSU` 흐름에서 "Retriever" 역할을 하는 코드가 현재 NAE 어디에도 없다. `NAE/pipeline/index/qdrant_store.py`는 upsert 전용이고 검색(search) 함수가 없다.

**권장**: Phase 5.2에서 `NAE/pipeline/retrieve/qdrant_retriever.py`를 신설한다(embed/index와 동급의 공유 인프라). 역할: `question_text → NAE.pipeline.embed.client.embed_text() → qdrant_client.search() → payload["tsu_id"] 목록 추출`. `NAE/benchmark/runner.py`는 이 함수를 `retrieval_fn`으로 주입만 하면 된다 — `runner.py` 자체를 수정할 필요 없음(현재 설계가 이미 이 확장을 지원하도록 되어 있다는 뜻이므로 TASK 6 판정은 **PASS**).

**판정**: PASS (Retriever 부재는 Phase 5 범위 밖 — Phase 5.2 선행 조건으로 기록)

---

## SCHEMA REVIEW (TASK 1)

| 필드 | 평가 | 비고 |
|---|---|---|
| `gold_tsu_ids` | MODIFY | 스키마엔 있으나(`relevant_tsu_ids`라는 이름으로) `evaluator.py`/`runner.py`가 실제로 읽지 않음 — TASK 2 참고 |
| `question_type` | MODIFY | C1-TASK-ORDER-037 초안은 "자유 문자열"로 지시했으나, NAE 전체가 `DOCTRINE_CATEGORIES`(TSU) 같은 **닫힌 vocabulary + "Other" 폴백** 패턴을 일관되게 써왔다(license 판정, doctrine 분류 등). question_type도 동일 패턴이 장기적으로 적절하다. 다만 100문항을 실제로 보기 전에는 카테고리를 확정할 수 없으므로, **버전 관리 가능한 리스트**(코드가 아니라 `NAE/benchmark/config.py`의 상수 리스트)로 시작하고 Gold 문항 작성 중 필요시 갱신하는 방식을 권장 |
| `difficulty` | MODIFY | 동일 논리로 닫힌 3단계(`easy`/`medium`/`hard`) 권장 — 이후 난이도별 recall 분석(예: "hard 문항에서만 recall이 낮다")을 하려면 자유 텍스트보다 고정 enum이 유리하다 |
| `dataset_version` | **누락 확인 — 추가 필요** | 현재 `BenchmarkMetadata.created_version`은 문항 단위 필드이고, 데이터셋(파일) 단위 버전이 없다. NAE의 기존 관례(collector_version/canonical_version/tsu_schema_version이 레코드에 실려 재현성을 보장하는 패턴, ADR-013 Phase 3.5/4 하드닝 참고)를 따라야 한다 — 아래 권장안 참고 |
| `review_status` | PASS (설계는 완료, 이름만 조정) | C1-TASK-ORDER-037 초안에 이미 `BenchmarkReview` nested dataclass(`review.status`/`reviewer`/`reviewed_at`/`notes`)로 설계되어 있음 — 기존 스키마의 nested dataclass 패턴(question/expected/retrieval/evaluation/metadata)과 일관성 있음. 플랫 필드보다 이 방식을 유지 권장 |

### dataset_version 설계 권장안

문항(item) 단위가 아니라 **파일(데이터셋) 단위** 메타데이터로 별도 관리한다:

```
NAE/benchmark/datasets/
    gold_v1.jsonl              ← 승인된 문항만 (review.status == "approved")
    gold_v1.manifest.json      ← {dataset_version, schema_version, question_count,
                                   created_at, promoted_from, doctrine_coverage}
```

`BenchmarkMetadata`에는 `dataset_version: str = ""` 필드를 추가해 각 레코드가 "어느 manifest에서 나왔는지"를 자기 참조할 수 있게 한다(TSU 레코드가 `collector_version`/`canonical_version`을 자기 참조하는 것과 동일한 이유 — 파일이 섞이거나 재배포될 때 출처 추적).

**판정**: MODIFY — C1-TASK-ORDER-037 TASK 2를 아래 개정안으로 갱신 필요(본 문서 하단 "TASK ORDER 037 개정 사항" 참고)

---

## GROUND TRUTH REVIEW (TASK 2)

### 확인된 구조적 결함 (기존 발견, 재확인)

`retrieved_ids`(Qdrant `tsu_id` payload, `"TSU-0000123"` 형식)와 현재 `relevant_ids` 소스(`expected_scriptures`/`required_concepts`, 자연어 문자열)가 서로 다른 ID 공간이라 매칭이 원천적으로 불가능하다. C1-TASK-ORDER-037 TASK 1에 이미 수정 지시가 포함되어 있음 — 유지.

### 이번에 새로 확인된 선행 조건 (중대)

**현재 NAE corpus가 비어 있다.** 실측 확인:

```
NAE/corpus/raw/archive_org/books/     — 0개 item (빈 카테고리 디렉터리만 존재)
NAE/corpus/canonical/                 — 0개 item
NAE/corpus/tsu/                       — 0개 item
nae_qdrant collection nae_tsu_v1      — 0 points
```

Phase 1~4 각 단계는 라이브 스모크테스트로 실제 API/Qdrant를 통해 전부 검증되었지만, **매 검증 후 산출물을 정리(cleanup)하는 방식으로 운영**해 왔기 때문에 지금 시점에 남아있는 corpus가 없다.

`gold_tsu_ids`는 실제 Qdrant에 존재하는 TSU ID를 사람이 조회해서 채워야 하는 값이다 — **Qdrant에 아무것도 없으면 Gold Benchmark 문항을 단 하나도 작성할 수 없다.** 이는 TASK 5(Gold Benchmark 작성)의 실질적 선행 조건이다.

**권장**: Phase 5.1 착수 전(또는 병행) 다음 순서로 최소 corpus를 구축·보존해야 한다:

```
1. Priority A/B/C 키워드로 Collector 정식 실행 (스모크테스트가 아닌 실제 축적, --resume 사용)
2. Canonical 정규화 전체 실행
3. TSU Builder 실행 (실제 claim 다수 확보 — 100문항의 기반이 될 만한 양)
4. Verify 실행
5. Index 실행 (nae_qdrant에 영구 적재)
6. 이후에만 사람이 Qdrant를 검색해 gold_tsu_ids를 채울 수 있음
```

이번에는 산출물을 정리하지 않고 **영구 corpus로 유지**해야 한다 — 지금까지의 "검증 후 삭제" 운영 방식은 인프라 검증 단계에서는 맞았지만, Gold Dataset 제작 단계부터는 맞지 않는다.

**판정**: MODIFY — C1-TASK-ORDER-037에 "Phase 5.0.5: 최초 영구 corpus 구축" 선행 단계를 명시적으로 추가해야 한다(HQ 승인 필요 — 아래 RECOMMENDATION 참고).

---

## ONTOLOGY REVIEW (TASK 3)

### DOCTRINE_CATEGORIES 재사용 여부

```python
# NAE/pipeline/tsu/config.py
DOCTRINE_CATEGORIES = [
    "Baptism", "Church Covenant", "Church Discipline", "Lord's Supper",
    "Confession", "Election", "Justification", "Sanctification",
    "Ecclesiology", "Soteriology", "Trinity", "Scripture / Authority",
    "Providence", "Eschatology", "Other",
]
```

**재사용을 권장한다 (새 Ontology 생성 반대).** 근거:

1. TSU의 `doctrine` 필드와 Benchmark의 `theology_area`(또는 유사 필드)가 서로 다른 카테고리 체계를 가지면, "이 문항은 Baptism 영역인데 gold_tsu_ids로 지정한 TSU는 doctrine=Soteriology로 분류되어 있다" 같은 불일치가 발생해도 감지할 방법이 없다. 같은 vocabulary를 쓰면 이 정합성을 자동으로 검증할 수 있다(TASK 5 기준 문서에 "gold_tsu_ids로 선택한 TSU의 doctrine과 문항의 theology_area가 일치해야 한다"는 규칙을 넣을 수 있음).
2. `DOCTRINE_CATEGORIES`는 이미 "닫힌 목록 + Other 강제"라는 NAE의 검증된 설계 원칙(Phase 3 Gate Review에서 승인됨)을 따르고 있다 — 같은 원칙을 다른 곳에서 다시 만들 이유가 없다.

**단, 완전히 동일하게 재사용하지 말고 import로 참조**: `NAE/benchmark/config.py`에서 `from NAE.pipeline.tsu.config import DOCTRINE_CATEGORIES`로 가져와 `THEOLOGY_AREA_CATEGORIES = DOCTRINE_CATEGORIES`로 별칭을 둔다(완전히 같은 리스트를 두 곳에 복사해두면 나중에 한쪽만 갱신되는 사고가 난다 — DRY 원칙).

**판정**: PASS (재사용 승인, import 방식만 명시)

---

## WORKFLOW DESIGN (TASK 4)

```
Draft
  │  (C1의 template.py가 review.status="draft"로 100개 생성,
  │   question/expected/gold_tsu_ids 등은 전부 빈 값)
  ▼
Filled (사람이 채움; review.status는 "draft"→"in_review"로 사람이 직접 전환)
  │  이 단계에서만 gold_tsu_ids/question.text/expected.* 값이 채워진다.
  │  gold_tsu_ids는 반드시 실제 Qdrant 조회 결과여야 한다(GROUND TRUTH REVIEW 참고).
  ▼
In Review (review.status="in_review")
  │  reviewer가 review.py --approve / --reject / --needs-revision 중 하나 실행
  ├──→ needs_revision (notes에 사유 기록) ──→ 다시 "Filled" 단계로
  ├──→ rejected (감사 목적으로 보존, gold set에는 미포함)
  └──→ approved (reviewer/reviewed_at 자동 기록)
  ▼
Approved
  │  review.py --promote 실행 시:
  │    1. review.status=="approved"인 레코드만 필터링
  │    2. gold_tsu_ids/question.text가 비어있지 않은지 재검증(불완전 승인 방지)
  │    3. datasets/gold_v1.jsonl로 출력 + gold_v1.manifest.json 생성/갱신
  ▼
Gold Dataset (datasets/gold_v1.jsonl — 이것만 Phase 5.2 실제 평가에 사용)
```

핵심 설계 포인트:
- **draft 파일과 gold 파일을 분리한다.** 작업 중인 draft(`gold_v1_draft.jsonl`, 모든 상태 포함)와 최종 gold(`gold_v1.jsonl`, approved만)를 같은 파일로 섞으면 "아직 검토 안 된 문항"이 실수로 평가에 섞여 들어갈 위험이 있다.
- **promote 시 재검증**은 review.py에 반드시 구현되어야 한다 — reviewer가 실수로 빈 필드인 채로 approve를 눌러도 promote 단계에서 걸러진다(이중 방어).
- reviewer 1인 체제(현재 CUE/HQ만 존재)이므로 "2인 승인" 같은 절차는 아직 불필요 — 향후 human theologian이 합류하면 `reviewer` 필드가 이미 그 확장을 지원한다.

**판정**: PASS (설계 확정, C1-TASK-ORDER-037 TASK 4에 promote 로직 추가 필요)

---

## CODE REVIEW (TASK 7)

C1의 Phase 5 산출물(`NAE/benchmark/{schema,loader,metrics,evaluator,runner}.py`)은 이전 세션에서 이미 기술 검토를 마쳤다(recall 중복 오버플로 버그, `Evaluator.report()` 첫-결과 편향 버그 — 두 건 모두 수정 후 커밋 `d7152ec`). Phase 5.1용 신규 코드(TASK-ORDER-037)는 아직 C1에게 전달되지 않았으므로 이번 TASK 7은 **새로 검토할 대상이 없음** — 커밋 `d7152ec` 시점 상태 유지로 PASS 재확인.

**판정**: PASS (기존 검토 유효, 재검토 불필요)

---

## GOLD BENCHMARK 작성 기준 (TASK 5)

별도 문서로 작성: [`NAE/benchmark/GOLD_BENCHMARK_AUTHORING_GUIDE.md`](../../../NAE/benchmark/GOLD_BENCHMARK_AUTHORING_GUIDE.md)

---

## ISSUES

| # | 심각도 | 내용 |
|---|---|---|
| 1 | **Blocker** | NAE corpus가 현재 비어 있음(raw/canonical/tsu/Qdrant 전부 0건) — Gold Benchmark 작성 자체가 불가능한 상태. Phase 5.1 착수 전 영구 corpus 구축 필요 |
| 2 | High | `gold_tsu_ids`(구 `relevant_tsu_ids`)가 스키마에만 존재하고 실제 평가 로직에서 미사용 — Phase 5.2에서 모든 지표가 0으로 고정되는 결함 (C1-TASK-ORDER-037 TASK 1에 이미 반영됨, 유지) |
| 3 | Medium | `dataset_version` 필드 부재 — 데이터셋 파일 단위 재현성 추적 불가 |
| 4 | Low | `question_type`/`difficulty`를 자유 문자열로 둘 경우 장기적으로 값이 흩어져 분석이 어려워짐 — 닫힌 vocabulary 권장 |
| 5 | Info | Retriever 컴포넌트가 아직 없음(Phase 5.2 범위, 지금 문제 아님) |

## RECOMMENDATION

1. **Phase 5.1 착수 전에 HQ 승인을 받아 "Phase 5.0.5: 최초 영구 corpus 구축"을 먼저 실행한다.** 이건 코드 작업이 아니라 이미 완성된 파이프라인(Phase 1~4)을 실제 데이터로 정식 실행하고 결과물을 보존하는 운영 작업이다. 소요 시간은 대상 문헌 수에 비례(라이브 테스트 기준 문헌 1권당 수집~색인까지 약 2~3분 + LLM claim 추출 시간).
2. Corpus 구축 후에만 C1-TASK-ORDER-037을 실행한다 — TASK 3(템플릿 생성)의 placeholder는 코드 없이도 만들 수 있지만, TASK 5(사람이 gold_tsu_ids를 채우는 것)는 corpus 없이는 원천적으로 불가능하다.
3. C1-TASK-ORDER-037을 본 리뷰 결과에 맞춰 개정한다(아래 diff 요약) — 개정 후 재승인 요청.

### C1-TASK-ORDER-037 개정 사항 요약

- TASK 2(Schema 확장)에 `dataset_version`(메타데이터) 및 `gold_v1.manifest.json` 산출물 추가
- `question_type`/`difficulty`를 자유 문자열이 아니라 `NAE/benchmark/config.py`의 버전관리 가능한 리스트 상수로 변경(닫힌 vocab + "Other")
- `theology_area`는 `NAE.pipeline.tsu.config.DOCTRINE_CATEGORIES`를 **import 별칭**으로 재사용(복사 금지)
- TASK 4(Review CLI)에 `--promote` 커맨드 추가: approved 레코드만 골라 `gold_v1.jsonl` + manifest로 출력, 필수 필드 재검증 포함
- 선행 조건 섹션에 "Phase 5.0.5 corpus 구축이 먼저 완료되어야 함" 명시
