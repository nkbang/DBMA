# NAE TSU Review Workflow Design 001

**Project:** NAE-TSU-REVIEW-WORKFLOW-DESIGN-001
**작성일:** 2026-08-07
**성격:** Design Only — `core/retrieval.py`, `builder.py`, Crosswalk
schema, Manifest, Registry, RAW, Canonical, Vector DB, `indexer.py`
포함 코드 전부 무수정.

---

## Phase 1 — Current State Audit

### 1. TSU schema 구조

`NAE/pipeline/tsu/claim.py::ClaimResult`(builder.py가 그대로
`tsu.json` 레코드에 반영):

```python
@dataclass
class ClaimResult:
    is_claim: bool = False
    claim: str | None = None
    doctrine: str | None = None
    scriptures: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    confidence: float | None = None
    extraction_method: str = "llm"
    review_status: str = "unverified"
    model: str = ""
    error: str | None = None
```

Review 관련 필드는 `review_status` **하나뿐**이다 — reviewer, 검토
일시, 검토 근거를 담을 필드가 스키마에 없다.

### 2. review_status 저장 위치

`tsu.json`(`NAE/corpus/tsu/{identifier}/tsu.json`)의 **레코드별
필드**로 저장된다 — 별도 Review 전용 파일이나 저장소는 없다.
`NAE-TSU-REVIEW-GATE-WIRING-IMPLEMENTATION-001`이 이 필드를
읽어(Gate) `verified`만 통과시키도록 `indexer.py`를 배선했지만,
`verified`로 **바꾸는** 절차는 아직 어디에도 없다(사람이 파일을
직접 편집하는 것 외에는 방법이 없는 상태).

### 3. TSU metadata lifecycle

현재 lifecycle은 사실상 1단계다: `builder.build_tsu_for_identifier()`
가 레코드를 생성하는 순간 `review_status="unverified"`로 고정되고,
그 이후 아무 코드도 이 값을 바꾸지 않는다. `NAE_TSU_REVIEW_GATE_
IMPLEMENTATION_REPORT_001.md`가 정의한 4-상태 모델(`generated`/
`reviewed`/`verified`/`rejected`)은 **Gate 판정 로직에는 이미
반영**되어 있으나, 실제 TSU 레코드에는 아직 `"unverified"`라는
5번째 값만 존재한다는 점에 주의(§종합 미해결 항목).

### 4. 기존 `tsu_verified.json` 역할(개념 구분 재확인)

`NAE/pipeline/verify/duplicate.py`(Phase 3.5)가 생성하는
`tsu_verified.json`은 **근접 중복(near-duplicate) 탐지 결과물**이다
— `score`/`duplicate_of` 필드를 추가할 뿐, `review_status` 값을
바꾸지 않는다. `indexer.py::load_records_with_gate_summary()`가
이미 이 둘을 분리해서 다룬다(파일 소스는 `tsu_verified.json`이든
`tsu.json`이든, `review_status` Gate는 항상 별도로 적용).

```
tsu_verified.json = "생성/중복탐지 아티팩트"(자동, 사람 개입 없음)
review_status="verified" = "사람의 신학적 검토 승인"(이번 설계 대상)
```

**이 문서는 이 둘을 동일 개념으로 절대 취급하지 않는다.**

---

## Phase 2 — Review Lifecycle Design

### 상태 전이

```
generated
    │
    ▼ (사람이 검토를 시작)
reviewed
    │
    ├──▶ verified   (검토 결과: 승인)
    │
    └──▶ rejected   (검토 결과: 폐기 — reviewed를 거치지 않고
                      generated에서 곧바로 rejected도 가능, 아래 참고)
```

`generated → rejected`(reviewed를 건너뛰는 경로)도 허용한다 — 예를
들어 claim 자체가 명백히 무의미하거나 추출 오류인 경우, "검토
시작"과 "거부 결정"이 사실상 한 행위로 합쳐질 수 있다. 반대로
`verified → 다른 상태로 역행`은 이번 설계에서 다루지 않는다(재검토가
필요하면 새 TSU 레코드를 만드는 것을 원칙으로 — Migration Engine
Audit Log/Crosswalk Record의 "append-only, 되돌리지 않는다" 관례와
동일 정신).

### 검토자(Reviewer)가 확인하는 것

| 항목 | 확인 내용 |
|---|---|
| Theological Accuracy(신학적 정확성) | claim이 원문 문맥에서 실제로 그렇게 주장하고 있는지, LLM이 없는 내용을 지어내지 않았는지 |
| TSU Claim Completeness(주장의 완결성) | claim이 독립적으로 이해 가능한 문장인지(원문 문맥을 모르는 사람이 읽어도 의미가 통하는지) |
| Source Grounding(원문 근거) | `source_text` 필드가 실제로 그 claim의 근거가 되는지, `page`/`paragraph`/`sentence` 위치가 정확한지 |

이 3가지는 `claim.py` docstring이 이미 명시한 한계("confidence is
model self-reported and uncalibrated")를 사람이 메우는 지점이다 —
LLM의 자기 신뢰도 점수는 신뢰할 수 없으므로, 이 3가지를 사람이
직접 판단해야 `verified`로 승격 가능하다.

### 필수 Metadata(신규 필드, 스키마 확장 — 이번 문서는 설계만)

```yaml
reviewer: string          # 검토자 식별자(NAE-MANUAL-CROSSWALK-POPULATION-IMPLEMENTATION-001의 "Reviewer: Human"과 동일 표기 관례 재사용 후보)
review_date: string        # ISO 8601, 검토 완료 시각
review_notes: string       # 검토자가 남기는 서술(왜 승인/거부했는지)
review_decision: string    # "approved" | "rejected"
```

이 4개 필드는 `ClaimResult`/`tsu.json` 레코드 schema의 **확장**으로
제안한다 — 기존 필드(`id`/`claim`/`doctrine`/`scriptures`/
`citations`/`confidence`/`extraction_method`/`review_status`/`model`)
는 전혀 바꾸지 않는다(Crosswalk Schema 001이 확립한 "additive만,
기존 필드 불변" 원칙과 동일하게 적용).

---

## Phase 3 — Promotion Interface Design(설계만, 구현 없음)

```python
def promote_tsu_to_verified(
    tsu_record: dict,
    *,
    reviewer: str,
    review_date: str,
    review_decision: str,
    review_notes: str | None = None,
) -> dict:
    """설계 초안 — 이번 Task에서 코드로 구현하지 않는다.

    반환: review_status가 갱신된 새 TSU 레코드(원본을 in-place로
    수정하지 않고 새 dict를 반환하는 순수 함수로 설계 — Crosswalk
    Record의 frozen 원칙과 동일 정신, 다음 구현 단계에서 그대로
    반영 권고).
    """
```

### 필수 전제조건(전부 만족해야 승격, 하나라도 없으면 실패)

```
reviewer 존재(빈 문자열 아님)
AND
review_date 존재(빈 문자열 아님, ISO 8601 형식)
AND
review_decision == "approved"
```

### 실패 처리

```
reviewer 없음           -> 승격 거부(자동 verified 금지)
review_date 없음        -> 승격 거부
review_decision != "approved" -> 승격 거부(예: "rejected"면 review_status="rejected"로만 전이, verified 아님)
```

**"자동 verified 금지"를 코드 레벨로 강제하는 방법(설계 제안)**:
`promote_tsu_to_verified()`는 위 3개 전제조건이 전부 충족되지 않으면
`review_status`를 절대 `"verified"`로 설정하지 않고 예외를 던지거나
(Crosswalk의 `SchemaError` 패턴 재사용 후보) 실패를 나타내는 반환값을
준다 — Mapping Policy Rule 3("추측 매핑 금지")과 동일한 정신을
TSU Review에도 적용: **근거(reviewer/review_date/decision) 없이
승격되는 경로를 코드 구조적으로 없앤다.**

---

## Phase 4 — `tsu_verified.json` Naming Review

### 문제

`tsu_verified.json`(Phase 3.5 중복탐지 산출물)이라는 파일명이
`review_status == "verified"`(이번 설계의 사람 검토 승인)와 이름이
겹쳐, 향후 유지보수자가 "이 파일이 있으면 사람이 검토를 끝낸
것"이라고 오해할 위험이 있다 — 실제로는 이 파일의 존재 여부와
`review_status` 값은 완전히 독립적이다(Phase 1 §4 재확인).

### Option A — 유지 + 문서화

- 장점: 파일 rename에 따르는 하위 호환성 문제(기존 산출물 이름
  변경, `indexer.py`의 두 경로 참조 로직 수정 등) 없음
- 단점: 이름 자체의 오해 소지는 계속 남음 — 문서화만으로는 코드를
  처음 보는 사람이 여전히 헷갈릴 수 있음

### Option B — 명칭 변경

후보: `tsu_validated.json`, `tsu_checked.json`, `tsu_dedup.json`(가장
명확 — "중복 제거 처리됨"이라는 뜻을 이름에 직접 담음)

- 장점: 이름 자체가 "review_status와 무관한 중복탐지 산출물"임을
  분명히 함
- 단점: `NAE/pipeline/index/indexer.py::load_records_with_gate_summary()`
  의 `verified_path` 변수/파일 경로, `NAE/pipeline/verify/duplicate.py`
  가 쓰는 출력 파일명, 관련 테스트(`tests/test_indexer_review_gate_
  wiring.py`의 `filename="tsu_verified.json"` 사용처) 전부 변경
  필요 — 실행 코드 변경이 수반되므로 이번 **Design Only** Task
  범위를 벗어남

### 권고안

**`tsu_dedup.json`으로 명칭 변경(Option B)을 권고**하되, **이번
Task에서는 실행하지 않는다**(Task 지시 "실제 rename 금지"). 근거:
`tsu_validated.json`/`tsu_checked.json`도 여전히 "검증/확인됨"이라는
뉘앙스가 남아 `review_status`와 다시 혼동될 수 있는 반면,
`tsu_dedup.json`은 "무엇을 했는지"(중복 제거)를 이름에 직접 명시해
`review_status`의 "무엇이 되었는지"(검토 상태)와 어휘 자체가
겹치지 않는다. 실제 rename은 별도 승인된 구현 작업(코드 변경 —
`indexer.py`/`duplicate.py`/관련 테스트 동시 수정 필요)으로 진행할
것을 제안한다.

---

## Phase 5 — Architecture Boundary

```
$ git status --short core/retrieval.py NAE/pipeline/tsu/builder.py \
    scripts/crosswalk/schema.py resources/theological_sources/ \
    NAE/corpus/raw NAE/corpus/canonical docs/architecture/
(core/retrieval.py, builder.py, Crosswalk schema, Manifest, Registry,
RAW, Canonical — 전부 이번 Task에서 무접촉. NAE/pipeline/index/
indexer.py의 기존 M 표시는 직전 승인된 NAE-TSU-REVIEW-GATE-WIRING-
IMPLEMENTATION-001의 변경분이며, 이번 Design 작업이 추가로 건드리지
않음 — git diff 재확인 결과 이번 세션에서 그 파일을 열람만 했고
쓰기는 없었음.)
```

Vector DB(Qdrant) 코드 — 이번 문서는 Promotion Interface를
"설계"만 했을 뿐 `indexer.py`나 Qdrant 관련 파일 어디에도 실제
연결하지 않았다.

**PASS — 코드 변경 0건(이번 Task 전체).**

---

## 완료 보고

```
STATUS: COMPLETE (design only, no code changes)

FILES CREATED:
docs/NAE_TSU_REVIEW_WORKFLOW_DESIGN_001.md

FILES MODIFIED:
(없음)

CURRENT LIFECYCLE:
review_status는 "unverified" 고정값 1개만 실사용 — generated/reviewed/verified/rejected 4-상태 모델은 Gate 판정 로직(review_gate.py)에는 이미 반영되어 있으나, 실제 승격 절차(누가 언제 무엇을 근거로 바꾸는가)는 이번 문서에서 최초로 설계됨

PROMOTION RULE:
promote_tsu_to_verified(reviewer, review_date, review_decision, review_notes) — reviewer AND review_date AND review_decision=="approved" 전부 충족해야만 verified로 전이, 하나라도 없으면 자동 승격 금지(설계만, 미구현)

NAMING REVIEW:
tsu_verified.json(Phase 3.5 중복탐지) vs review_status="verified"(사람 검토) 이름 충돌 확인. 권고안: tsu_dedup.json으로 명칭 변경(Option B) — 단 이번 Task에서 실제 rename 미수행, 별도 구현 작업으로 이관

ARCHITECTURE IMPACT:
없음 — core/retrieval.py, builder.py, Crosswalk schema, Manifest, Registry, RAW, Canonical, Vector DB, indexer.py 전부 이번 Task에서 코드 변경 0건

BLOCKER:
0

WARNING:
1 (review_status에 4-상태 모델 값이 아직 하나도 실제로 쓰이지 않음 — 이 설계를 실제 구현하지 않으면 지금 생성된 TSU 4건은 영원히 "unverified" 상태로 남아 Embedding 대상이 될 수 없음)

NEXT STEP:
C1 Review Workflow Design 검토 요청 → 승인 시 (1) tsu.json 스키마에 4개 필드(reviewer/review_date/review_notes/review_decision) 추가 + promote_tsu_to_verified() 구현, (2) tsu_verified.json → tsu_dedup.json rename(선택, 별도 승인) — 두 구현 작업 모두 이번 문서 범위 밖

GIT:
NOT PERFORMED
```
