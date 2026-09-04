# DBMA-SIL Theology Engine Design — Baptist Doctrine Filter + TSU Extension

작성: CUE (2026-07-21)
근거: 사용자 제공 외부 자료 2건(`~/Downloads/현업용 설교 제작 툴
아이디어.md`, `~/Downloads/설교엔진디자인.md`, 둘 다 ChatGPT 대화록)의
아이디어를 실제 코드베이스와 대조 검증 후 재구성.
범위: **신학 엔진(doctrine filter) + TSU 확장만.** 독립형 데스크톱 배포,
계정/라이선스, 클라우드 백엔드(Supabase/R2/Sentry 등)는 사용자 지시로
이번 설계 범위에서 제외 — 별도 사업 결정 대상으로 보류.
상태: 설계 제안, 코드 미작성. 사용자 승인 후 구현 착수.

전신: `C1-TASK-ORDER-005`(DBMA-SIL Phase 0)는 이 설계로 대체되어 중단됨.

---

## 1. 외부 자료 검증 — 무엇이 맞고 무엇이 틀렸는가

두 ChatGPT 문서는 유용한 아이디어(Multi-Agent 리뷰, TSU 신학 메타데이터,
Doctrine Filter 개념)를 제공했지만, DBMA의 **실제 코드를 보지 않고**
작성되어 구조 서술이 부정확하다. 반영 전 대조 검증한 결과:

| 외부 문서 주장 | 실제 코드 (VERIFIED) |
|---|---|
| `core/chunking.py` | 실제로는 `core/chunking_optimizer.py` |
| 설교 기능이 아직 없음(처음부터 설계) | `core/generation.py::SermonDraftService`가 **이미 구현되어 있음**(개요 생성 `generate_outline()`, 대지 확장 `expand_point()`, `ui/pages/sermon_draft.py` UI까지 사이드바 등록·연결 완료) |
| TSU에 신학 메타데이터 없음, 전부 새로 추가해야 함 | TSU 레코드에 `"themes": []` 필드가 **이미 존재**하나(`core/tsu_builder.py:336`) 어디서도 채워지지 않는 죽은 필드 — 새로 추가할 게 아니라 **이미 있는 확장 지점을 활용**하면 됨 |
| Retrieval에 신학 signal이 전혀 없음, 새로 설계해야 함 | `core/query_enhancements.py::EnhancedQueryParser`가 이미 쿼리에서 `themes`(faith/grace/salvation, 믿음/은혜 등)와 `intent`(`"theological"` 포함 6종)를 감지해 `ParsedQuery`에 담고 있음(`core/retrieval.py:78` `ParsedQuery.themes` 필드) — **이미 존재하는 신학 테마 감지 계층 위에 얹으면 됨**, 새 retrieval 모듈 불필요 |
| ADR-006을 SIL 번호로 제안 | ADR-006은 이미 예약됨(`ADR-007` 문서 명시) — **ADR-009**부터 |

**결론**: 외부 문서의 "처음부터 설계"라는 전제 자체가 틀렸다. DBMA는
이미 (a) 설교 생성 서비스, (b) 미사용 TSU 확장 지점, (c) 쿼리 신학
테마 감지기를 갖고 있다 — 이번 설계는 **신규 구축이 아니라 기존
3개 조각을 연결**하는 작업이다.

---

## 2. 원칙 (외부 문서에서 채택 — 타당함)

- **AI가 설교를 창작하지 않는다.** `SermonDraftService`는 이미 이
  원칙을 따르고 있음(검색 근거 없이 생성 안 함, `_format_sermon_context()`가
  인용 가능한 자료만 프롬프트에 넣음). 그대로 유지.
- **최종 신학적 판단은 목회자(사용자)에게 있다.** Doctrine Filter는
  자동 차단이 아니라 **경고/제안**만 한다 — 이미 `sermon_draft.py`의
  "2단계: 개요 검토"가 사람 검토를 요구하는 구조이므로 자연스럽게
  들어맞음.
- **One Retrieval Engine 유지.** `core/retrieval.py::RetrievalEngine`을
  변경하거나 별도 검색 경로를 만들지 않는다(ADR-001). 아래 설계는
  전부 이 경로 밖(TSU 데이터, 후처리 검증)에서 이루어진다.

## 3. 명시적으로 채택하지 않는 것

- Multi-Agent(Exegete/Theologian/Homiletician/Pastor 4단계 파이프라인) —
  DBMA의 "작은 단위로 수정, 바로 검증" 원칙과 맞지 않는 과설계로 판단.
  대신 §5에서 **기존 2단계 흐름(개요→확장)에 검증 1단계만 추가**하는
  최소안을 제안.
- 독립형 데스크톱 배포/계정/라이선스/클라우드 백엔드 — 사용자 지시로
  범위 제외.
- TSU 스키마의 근본 재설계 — 기존 additive-only 원칙(`core/tsu_builder.py`
  주석에 이미 명시된 패턴, SPRINT28-B/29-C 사례)을 그대로 따른다.

---

## 4. TSU 확장 설계

### 4.1 기존 `themes` 필드 재활용 여부 — 재활용하지 않음(신규 필드 권장)

`themes`는 이미 죽은 필드지만, 이름이 범용적이라 다른 의미(주제어 일반)로
오해될 소지가 있다. 신학적 의미가 분명한 **새 필드**를 additive로
추가하는 편이 명확성 면에서 낫다 — 기존 `themes` 필드는 손대지 않고
그대로 둔다(존재 이유가 불명확하니 별도 조사 없이 재해석하지 않는다,
UNKNOWN 처리).

### 4.2 신규 필드 제안 (all additive-only, 기존 레코드 영향 없음)

```json
{
  "theological_claim": null,
  "doctrine_category": [],
  "baptist_theme": []
}
```

- `theological_claim` (str | null): 해당 TSU 콘텐츠가 담고 있는 신학적
  주장 한 문장 요약. 예: "그리스도는 죄인에게 참된 안식을 주신다."
- `doctrine_category` (list[str]): 표준 조직신학 범주. 초기 어휘(외부
  문서 §3 Doctrine Database를 축약): `["Scripture", "Trinity",
  "Christology", "Anthropology", "Soteriology", "Ecclesiology",
  "Eschatology"]` — 폐쇄형 어휘로 시작해 필요시 확장.
- `baptist_theme` (list[str]): SBC/침례교 강조점. 초기 어휘: `["Grace",
  "Faith", "BelieversBaptism", "LocalChurch", "Mission"]`.

### 4.3 채우는 방식 — 두 가지 옵션 (승인 필요)

| 옵션 | 방식 | 장점 | 단점 |
|---|---|---|---|
| A. TSU 빌드 시 일괄 태깅 | `core/tsu_builder.py`에서 레코드 생성 시 LLM으로 분류 | 한 번에 전체 커버리지 확보 | 전체 corpus 재빌드 필요, 비용/시간 큼, 신학적 오분류 시 파급 범위 넓음 |
| B. 설교 워크플로 시점에 온디맨드 태깅 (권장) | `SermonDraftService`가 검색된 candidate에 대해서만 그때그때 분류 | 실제 사용되는 자료만 처리 — 비용 최소, 파급 범위 좁음 | TSU 레코드 자체에는 영구 저장 안 됨(캐시 레이어 별도 필요 시 후속 설계) |

**권장: B (온디맨드)** — MVP 단계에서는 전체 corpus 태깅 비용을 정당화할
증거가 없다. 실사용 패턴을 보고 나서 A로 확장할지 재검토.

---

## 5. Doctrine Filter 설계 (`core/sermon/doctrine_filter.py`, 신규)

### 5.1 위치와 통합 지점

`SermonDraftService.generate_outline()`이 `SermonOutline`을 반환한
**직후**, `sermon_draft.py`의 "2단계: 개요 검토" 렌더링 **이전**에
검증 1회 실행. 기존 흐름을 바꾸지 않고 그 사이에 끼워 넣는다:

```
generate_outline() → SermonOutline
        ↓
[신규] doctrine_filter.check(outline, context_block) → DoctrineReport
        ↓
_render_outline_step()에 DoctrineReport를 경고 배너로 함께 표시
```

### 5.2 인터페이스 (의사코드, 구현 아님)

```python
@dataclass
class DoctrineReport:
    passed: bool
    warnings: list[str]      # 사람이 읽는 경고 문구
    flagged_categories: list[str]  # 어떤 교리 범주에서 문제 소지가 있었는지
    confidence: str           # "low" | "medium" | "high" — 자동 판정 신뢰도 명시

def check(outline: SermonOutline, context_block: str) -> DoctrineReport:
    ...
```

### 5.3 검증 방식 — 규칙 기반이 아니라 LLM 기반, 단 "차단"이 아니라 "경고"

외부 문서(§3)가 제안한 `check_doctrine(sermon, doctrine=[...])` 형태의
점수화(Biblical Fidelity 95% 등)는 **채택하지 않는다** — 이런 정밀한
백분율 점수는 실제로는 근거 없는 확신을 준다(오늘 세션에서 반복
확인된 "그럴듯한 숫자를 지어내는" 실패 패턴과 같은 위험). 대신:

- LLM에게 "이 개요에서 [초기 어휘 목록]과 명백히 배치되는 부분이
  있는가?"만 묻고, **없으면 아무것도 표시하지 않는다**(과잉 경고 방지).
- 있으면 어느 대지에서, 어떤 이유로 문제 소지가 있는지 자연어 경고
  1~2문장만 표시 — 점수화하지 않는다.
- `confidence: "low"`인 경우(모델이 스스로 불확실하다고 표시) 경고를
  숨기지 않고 "확실하지 않음"이라고 명시한 채 보여준다(어제 세션에서
  확인된 UNKNOWN 명시 원칙과 동일).

### 5.4 왜 별도 LLM 호출 1회를 추가하는가

`SermonDraftService`가 이미 겪은 품질 문제(§`core/generation.py:215-227`
주석, "본문을 얕게 풀어쓴 것" 수준 산출 이슈, 3차 시도까지 해결)를
고려하면, doctrine check를 outline 생성과 같은 호출에 욱여넣으면
(멀티태스크 프롬프트) 두 품질 모두 떨어질 위험이 있다. 별도 호출로
분리하는 편이 outline 생성 프롬프트의 기존 안정성을 해치지 않는다.

---

## 6. Retrieval 통합 — 신규 모듈 없이 기존 계층 재사용

외부 문서(§8, "Hybrid Ranking: Semantic 40% + Scripture 30% +
Theological 20% + Previous sermon 10%")는 **RetrievalEngine 자체의
가중치 변경**을 전제하는데, 이는 ADR-001 위반(One Retrieval Engine —
신규 검색 경로/가중치 체계 추가 금지, 변경하려면 ADR 필요) 소지가 크다.

대안(ADR 불필요, 권장):

- `SermonDraftService`가 `QueryProcessor.process()` 호출 시 이미
  `k=_CANDIDATE_K`(20, `ui/pages/sermon_draft.py:25`)로 더 넓게
  검색하고 있다 — 이 결과(`RankedCandidate` 리스트) 안에서 **후처리로만**
  재정렬하면 RetrievalEngine 자체는 무변경.
- `core/query_enhancements.py::EnhancedQueryParser`가 이미 뽑아주는
  `ParsedQuery.themes`/`intent`를 `SermonDraftService`가 후처리
  정렬 키로만 사용 — 신규 신학 signal 추출 로직 자체가 필요 없다.

---

## 7. MVP 범위 (Phase 1, 이번 승인 대상)

```
core/sermon/                      ← 신규 디렉터리
├── __init__.py
└── doctrine_filter.py            ← §5, LLM 기반 경고 1개 함수

core/tsu_builder.py               ← §4.2 필드 3개 추가(additive-only)
                                     (§4.3 옵션 B라면 실제로는 이 파일
                                     불변 — 온디맨드라 TSU 빌드 시점
                                     태깅 안 함. 옵션 A를 택할 때만 여기 수정)

core/generation.py                ← SermonDraftService에 doctrine
                                     check 호출 1줄 추가(기존 메서드
                                     시그니처 불변)

ui/pages/sermon_draft.py          ← 개요 검토 단계에 경고 배너 표시
                                     추가(기존 흐름 불변)

docs/architecture/ADR-009-SIL-Theology-Engine.md   ← 신규
```

**MVP 밖(Phase 2+)**: `evaluation.py`(설교 품질 정량 분석), TSU 옵션 A
(전체 corpus 일괄 태깅), Multi-Agent 확장.

---

## 8. Open Questions (사용자 확인 필요)

1. §4.3 옵션 A/B 중 선택 — 이번 설계는 B(온디맨드)를 권장하지만 최종
   승인 필요.
2. `doctrine_category`/`baptist_theme` 초기 어휘(§4.2)가 신학적으로
   적절한지 — 이건 C1/CUE가 판단할 영역이 아니라 사용자(목회자)의
   신학적 검토가 필요.
3. Doctrine Filter가 "경고를 표시할 신뢰도 임계값"을 얼마로 할지 —
   초기값 제안 없음(실사용 데이터 없이 숫자를 정하면 §5.3에서 경계한
   "근거 없는 확신"과 같은 실수를 반복하게 됨).
4. ADR-009 초안 작성 시점 — 이 설계 문서 승인 후 바로 작성할지, MVP
   구현 후 실측 근거를 담아 작성할지.

---

## 9. 다음 단계

이 문서는 승인 대상이며 코드가 아니다. 승인 시:
1. `ADR-009-SIL-Theology-Engine.md` 작성(이 설계를 공식 결정으로 전환).
2. TDD 게이팅 방식(오늘 청킹 버그 수정과 동일 패턴)으로 `doctrine_filter.py`
   구현 — 실패 테스트 선작성 후 구현.
3. 각 단계는 기존 원칙대로 최소 diff + 전체 회귀 검증 후 커밋.
