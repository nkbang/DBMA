# 설교문 작성 워크플로 — Phase 1 설계 검토 문서

| 항목 | 내용 |
|---|---|
| 작성자 | DBMA Principal Research Engineer (시스템 아키텍트) |
| 문서 버전 | 1.0 |
| 작성일 | 2026-07-20 |
| 상태 | 설계 검토 — 구현 전 CUE 확인 필요 |
| 대상 | CUE (Core Engineering Unit) |

---

## §1. 배경

DBMA RAG Chat은 현재 단발 질문-답변 구조입니다. 향후 "설교문 작성" 기능을 추가해야 하며, 이 기능은 다음과 같은 다단계 워크플로입니다:

```
본문(성경 구절) + 주제 입력
        ↓
넓은 범위 자료 검색 (RetrievalEngine)
        ↓
설교 개요 1차 생성 (서론 / 대지 / 결론) — GenerationService
        ↓
사용자 검토·수정 (UI 상호작용)
        ↓
승인된 개요 → 대지별 확장 생성 (GenerationService)
```

이 설계 검토 문서는 기존 아키텍처(`core/retrieval.py`, `core/generation.py`, `ui/pages/chat.py`, `ui/pages/research.py`, `ui/state/query_processor.py`, `ADR-001`)를 참조하여 5가지 핵심 질문에 답변합니다.

---

## §2. 산출물

이 문서가 마크다운 파일 하나뿐입니다. `.py` 파일 생성·수정이 없습니다.

---

## §3. 설계 검토 — 5개 질문

### Q1. 검색 전략: `retrieve()` 여러 번 호출 vs `k_output`/`candidate_k` 확장

**권장안:**  
`QueryProcessor.process(k=candidate_k)`로 단일 호출 시 후보군을 넓게 가져온 후, UI/워크플로 로직에서 2단계 필터링을 적용하는 방식을 권장합니다.

**이유:**

1. **ADR-001 (One Retrieval Engine) 원칙 준수**: `retrieve()`를 여러 번 호출하는 것은 동일한 엔진에 대해 "병렬 검색 경로"를 암묵적으로 창출합니다. ADR-001은 신규 검색 경로를 만들지 않는다고 명시합니다.
2. **파이프라인 단순성**: 단일 호출은 스코어링·랭킹 파이프라인을 한 번만 실행하므로 예측 가능성이 높습니다.
3. **컨텍스트 일관성**: 여러 호출 시 각 호출마다 다른 스코어링 결과가 나올 수 있으며, 이 결과를 조립하는 로직이 복잡해집니다.

**텍스트 다이어그램 — 권장 흐름:**

```
사용자 입력 (성경구절 + 주제)
        ↓
QueryProcessor.process(k=50)          ← candidate_k 확장
        ↓
RetrievalEngine.hybrid_scoring()      ← BM25 + vector + theological
        ↓
RetrievalEngine.ranking()             ← 단일 랭킹
        ↓
ResponsePackage.top_k_results[50]     ← 넓은 후보군
        ↓
[워크플로 로직] 도메인별 필터링        ← 예: "문체 참고" vs "본문 근거"
        ↓
개요 생성용 컨텍스트 블록 조립
```

**트레이드오프:**

| 기준 | candidate_k 확장 (권장) | 여러 번 호출 |
|---|---|---|
| ADR-001 준수 | ✓ 원칙 유지 | ✗ 병렬 경로 창출 위험 |
| 도메인별 타겟팅 | △ 넓은 후보군에서 필터링 필요 | ✓ 도메인별 쿼리 최적화 가능 |
| 구현 복잡도 | 낮음 (단일 파이프라인) | 높음 (다중 쿼리 조립 로직) |
| 성능 오버헤드 | 단일 호출 (50개 스코어링) | 다중 호출 (3×17개 = 51개 스코어링) |
| 예측 가능성 | 높음 (단일 랭킹) | 낮음 (다중 랭킹 조립) |

**결론:**  
이 문서는 "설계 검토" 단계이므로, candidate_k 확장이 원칙 위반 리스크가 현저히 낮습니다. 구현 시에는 `candidate_k` 값을 측정 가능하게 하고 (예: baseline benchmark), 필요시 점진적 확장을 검토합니다.

---

### Q2. 개요→확장 2단계 워크플로의 세션 상태 모델링

**권장안:**  
신규 페이지 `ui/pages/sermon_draft.py`에서 `st.session_state["sermon_draft_state"]` 딕셔너리로 상태를 모델링합니다. 기존 `chat_messages` 패턴과 호환됩니다.

**상태 구조 (의사코드):**

```
sermon_draft_state (dict)
├── status: str                      # "input" | "outline_generated" | "reviewing" | "approved" | "expanding"
├── input:
│   ├── scripture_refs: list[dict]   # ScriptureReference.to_dict() 결과
│   └── theme: str                   # 설교 주제
├── outline:
│   ├── structure: dict              # {sermon_id, title, subtitle, introduction, main_points[], conclusion}
│   ├── source_candidates: list[dict]# 개요 생성에 사용된 RankedCandidate.to_dict()
│   └── user_edits: list[dict]       # {point_index, field, original, edited, timestamp}
├── expansion:
│   ├── approved_points: list[int]   # 승인된 대지 인덱스
│   ├── expanded_chunks: dict        # point_index → 확장된 내용 문자열
│   └── draft_complete: bool
└── metadata:
    ├── created_at: str               # ISO 8601
    └── updated_at: str               # ISO 8601
```

**텍스트 다이어그램 — 상태 전이:**

```
[input]
   │ 사용자: 성경구절 + 주제 입력
   ▼
[outline_generated] ← RetrievalEngine.retrieve(k=wide) → GenerationService.generate_outline()
   │ 사용자: 개요 검토·수정 (user_edits 반영)
   ▼
[reviewing]
   │ 사용자: "승인" 버튼 클릭
   ▼
[approved]
   │ 사용자: 대지 선택 → "확성" 버튼
   ▼
[expanding] ← GenerationService.expand_point() × N
   │
   ▼
[draft_complete]
```

**이유:**

1. **기존 패턴 호환**: `chat.py`의 `chat_messages`, `research.py`의 `research_session_id`와 동일한 `st.session_state` 기반
2. **명확한 상태 전이**: `status` 필드로 워크플로 단계 식별 가능
3. **감사 추적**: `user_edits`로 어떤 수정이 있었는지 추적 가능
4. **확장성**: `expansion` 영역에 대지별 확장 결과 누적

**트레이드오프:**

| 기준 | session_state 딕셔너리 (권장) | 별도 세션 스토어 |
|---|---|---|
| 구현 복잡도 | 낮음 (내장 API) | 높음 (Redis/파일 I/O) |
| Phase 1 적합성 | ✓ 단순성 우선 | △ 과잉 설계 |
| 대용량 데이터 | △ 메모리 상주 제한 | ✓ 외부 스토어 |
| 유지보수 (장기적으로) | ✓ 현재 아키텍처와 일치 | △ 추가 의존성 |

---

### Q3. 본인 과거 설교문(.rtf)을 "문체 참고 예시"로 분리 — TSU 데이터 모델/file_scope 최소 변경 설계

**권장안:**  
TSU 레코드의 `metadata` 필드에 선택적 `sermon_type` 플래그를 추가하고, `file_scope`에 특수 키워드를 도입합니다. Phase 1에서는 구현하지 않고 설계만 확정합니다.

**TSU 메타데이터 변경 (최소):**

```json
{
    "tsu_id": "tsu_00001",
    "content": "...",
    "verse_mapping": { "book_id": "ROM", "chapter": 5, "verse_start": 3 },
    "themes": ["suffering", "faith"],
    "sermon_type": null,          ← 신규 필드 (선택적, 기존 레코드는 null)
    "source_file": "some_sermon.rtf"
}
```

- 값 범위: `null` | `"preacher_work"` (본인 과거 설교문) | `"other"`
- 기존 레거스 레코드는 `null`로 방치 — 하위 호환성 유지

**file_scope 확장 설계 (의사코드):**

```python
# RetrievalEngine.retrieve() 시 file_scope 파라미터 확장:
# 기존: file_scope = ["doc1.rtf", "doc2.rtf"]  ← 파일 이름 기반
# 신규: file_scope에 특수 키워드 추가 가능

if file_scope and "sermon_style_reference" in file_scope:
    # sermon_type == "preacher_work"인 TSU만 필터
    candidates = [
        c for c in candidates
        if c.metadata.get("sermon_type") == "preacher_work"
    ]
```

**텍스트 다이어그램 — 문체 참고 검색 흐름:**

```
사용자: "문체 참고용 설교문 선택" (별도 UI)
        ↓
[관리 로직] TSU 메타데이터 배칭 업데이트
  sermon_type = "preacher_work"  ← 본인 과거 설교문 식별
        ↓
[워크플로 시점] file_scope = ["sermon_style_reference"]
        ↓
RetrievalEngine.retrieve(k=10, file_scope=["sermon_style_reference"])
        ↓
sermon_type 필터링 (metadata 기반)
        ↓
문체 참고 예시 3-5건 → 프롬프트 컨텍스트에 포함
```

**이유:**

1. **TSU 핵심 필드 무변경**: `content`, `verse_mapping`, `themes` 등 핵심 필드 변경 없음
2. **선택적 메타데이터**: `sermon_type`은 null 허용 — 기존 레코드 영향 없음
3. **file_scope 재사용**: 기존 파라미터에 키워드 확장만으로 필터링 주입

**트레이드오프:**

| 기준 | sermon_type 메타데이터 (권장) | 별도 컬렉션 분리 | 파일 디렉토리 분리 |
|---|---|---|---|
| TSU 모델 변경 | 최소 (1 필드) | 많음 (새 스키마) | 없음 |
| 기존 레코드 영향 | null 방치 | 마이그레이션 필요 | 없음 |
| 검색 시 필터링 | metadata 기반 | 별도 쿼리 | file_scope 기반 |
| Phase 1 구현 비용 | 설계만 | 구현 필요 | 설계+구현 필요 |

---

### Q4. GenerationService를 그대로 재사용 가능한가, 별도 메서드가 필요한가?

**권장안:**  
GenerationService의 **핵심 Ollama 호출 로직은 재사용**하되, 설교문 워크플로 전용 래퍼 서비스(`SermonDraftService`)를 신규 작성합니다. 직접 상속보다는 조합(composition)을 사용합니다.

**생성 계층 구조 (텍스트 다이어그램):**

```
GenerationService (기존 — 변경 없음)
├── generate(response_package) → GenerationResult
├── generate_stream(response_package) → GenerationStream
└── _build_prompt(response) → (prompt, context_used)
    │
    │  ← llm_context_block + question 기반 일반 RAG 프롬프트

SermonDraftService (신규 — Ollama 호출은 GenerationService 위임)
├── __init__: self.generator = GenerationService()
│
├── generate_outline(scripture_refs, theme, source_candidates) → dict
│   │  ← 개요 생성용 별도 프롬프트 템플릿
│   │  ← source_candidates를 컨텍스트로 포함
│   └── 내부: generator.generate() 호출 (prompt는 개요 전용)
│
├── expand_point(outline_point, style_examples) → str
│   │  ← 대지별 확장 생성
│   │  ← 문체 참고 예시 포함 프롬프트
│   └── 내부: generator.generate() 호출 (prompt는 확장 전용)
│
└── refine_outline(outline, user_edits) → dict
    │  ← 사용자 수정 반영 재생성
    └── 내부: generator.generate() 호출 (prompt는 수정 반영 전용)
```

**인터페이스 시그니처 (의사코드):**

```python
# 기존 — 변경 없음
class GenerationService:
    def generate(self, response: ResponsePackage, ...) -> GenerationResult
    def generate_stream(self, response: ResponsePackage, ...) -> GenerationStream

# 신규 — 별도 서비스
class SermonDraftService:
    def __init__(self):
        self.generator = GenerationService()  # 조합 (상속 아님)

    def generate_outline(
        self,
        scripture_refs: list[ScriptureReference],
        theme: str,
        source_candidates: list[RankedCandidate],
    ) -> dict:
        """설교 개요(서론/대지/결론) 1차 생성"""
        ...

    def expand_point(
        self,
        point_index: int,
        outline_content: str,
        style_examples: list[str],
    ) -> str:
        """승인된 대지를 해당 내용으로 확장 생성"""
        ...

    def refine_outline(
        self,
        current_outline: dict,
        user_edits: list[dict],
    ) -> dict:
        """사용자 수정 반영한 개요 재생성"""
        ...
```

**이유:**

1. **프롬프트 템플릿 근본적 차이**: 일반 RAG 답변 (`llm_context_block + question`)과 설교 개요 프롬프트는 구조가 다름
2. **책임 분리**: GenerationService는 "Ollama 호출" 책임, SermonDraftService는 "설교문 도메인 로직" 책임
3. **하위 호환성**: 기존 GenerationService를 건드리지 않음

**트레이드오프:**

| 기준 |GenerationService 재사용 + 래퍼 (권장) | GenerationService 확장 | 완전 신규 서비스 |
|---|---|---|---|
| 기존 코드 영향 | 없음 | 있음 | 없음 |
| Ollama 호출 중복 | 조합으로 공유 | 상속으로 공유 | 중복 구현 |
| 도메인 명확성 | ✓ 명확 분리 | △ 혼합 | ✓ 명확 |
| 유지보수 | 낮음 | 높음 (상속 트리) | 중간 |

---

### Q5. 이 워크플로가 기존 아키텍처의 어떤 전제를 깨뜨릴 위험이 있는가?

**식별된 위반 위험 5가지:**

#### 위험 #1: 단일 쿼리 가정 (중요도: 중)

기존 `QueryProcessor.process()`는 "단일 질문 → 단일 응답" 설계입니다. 설교문 워크플로는 "입력 → 검색 → 생성 → 수정 → 재생성"의 다단계 사이클을 돌며, 각 단계가 동일한 엔진을 반복 호출합니다.

**영향:**  
`ResponsePackage`의 시맨틱스가 "답변 출처"에서 "참고 자료"로 변경됩니다. UI 레이어에서 상태 관리 책임이 이전됩니다.

**완화책:**  
워크플로 로직은 UI 레이어(`sermon_draft.py`)에서 관리하고, 엔진은 stateless API로 제공.

---

#### 위험 #2: stateless 파이프라인 (중요도: 중)

`RetrievalEngine`과 `GenerationService`는 모두 stateless입니다. 인덱싱은 예외이지만, 검색·생성 파이프라인은 상태가 없습니다. 워크플로 상태가 UI 레이어로 완전히 이전됩니다.

**영향:**  
브라우저 리로드 시 워크플로 상태 손실. 현재 `chat_messages` 패턴과 동일하지만, 설교문처럼 중요한 콘텐츠는 세션 외부에 영구화 필요할 수 있습니다.

**완화책:**  
Phase 1에서는 session_state만으로 충분. 이후 단계에서 persistence 설계 검토.

---

#### 위험 #3: 컨텍스트 블록 구조 (중요도: 소)

`ResponsePackage.llm_context_block`은 일반 RAG 답변용 포맷입니다. 설교 개요 생성 시에는 "성경 본문 + 관련 TSU 내용 + 설교 주제" 구조가 필요하며, 현재 포맷과 다릅니다.

**영향:**  
`GenerationService._build_prompt()`가 생성하는 프롬프트가 설교문 도메인에 최적화되지 않음.

**완화책:**  
`SermonDraftService`가 별도 프롬프트 템플릿을 사용하고, `ResponsePackage`를 직접 전달하지 않음.

---

#### 위험 #4: ResponsePackage 시맨틱스 (중요도: 소)

`top_k_results` 필드는 "답변 생성에 사용된 출처"로 해석됩니다. 워크플로에서는 "개요 생성 참고 자료"로 용도가 변경되지만, 데이터 구조는 동일합니다.

**영향:**  
UI에서 `top_k_results`를 "출처"로 표시하는 것이 설교문 컨텍스트에서는 "참고 문헌"으로 해석되어야 함.

**완화책:**  
UI 레이어에서 라벨/해석 변경. 데이터 구조 변경 불필요.

---

#### 위험 #5: One Retrieval Engine (중요도: 중)

Q1에서 다룬 바와 같이, 검색 전략 설계가不当시 병렬 검색 경로 창출 위험이 있습니다. ADR-001은 "신규 검색 경로를 만들지 않는다"고 명시합니다.

**영향:**  
`retrieve()` 다중 호출은 동일한 엔진에 대해 여러 검색 인스턴스를 만드는 효과가 있으며, 이는 원칙 위반입니다.

**완화책:**  
Q1에서 권장한 바와 같이 `candidate_k` 확장 단일 호출만 허용.

---

## §4. 열린 질문 — CUE가 구현 시작 전 확인해야 할 사항

아래 질문들은 불확실한 부분이므로 지어낸 답변 없이 질문으로 남깁니다. 구현 전 CUE의 확인이 필요합니다.

### Q-A1. 설교문 생성에 사용할 LLM 모델은 기존 RAG Chat과 동일해야 하는가, 별도 모델이 필요한가?

- **확인 사항**: `core/config.py`의 `DEFAULT_GEN_MODEL`이 설교문 개요/확성 모두에 적합한가?
- **영향**: 별도 모델이 필요하면 `config.yaml`에 신규 설정 항목 추가 필요. 프롬프트 템플릿도 모델별 최적화 필요.

### Q-A2. "문체 참고 예시"로 사용할 본인 과거 설교문의 양은 얼마나 되는가?

- **확인 사항**: 문체 참고용 TSU 레코드가 몇 건 정도 필요한가 (3건? 5건? 10건?)?
- **영향**: 프롬프트 컨텍스트 길이 제한 (Ollama 모델의 context window)에 직접적 영향. `candidate_k` 값 결정에 필요.

### Q-A3. 사용자 검토·수정 단계에서 동시 편집 충돌 처리가 필요한가?

- **확인 사항**: 단일 브라우저 세션만 지원하는가, 아니면 다중 세션 간 공유/동시 편집이 가능한가?
- **영향**: 세션 상태 모델링이 단순 dict인지, lock/merge 메커니즘이 필요한지 결정.

### Q-A4. TSU 메타데이터에 `sermon_type` 필드 추가 시, 기존 레코드 마이그레이션 책임은 누구에게 있는가?

- **확인 사항**: Phase 1 이후 별도 스프린트에서 배치가 필요한가, 아니면 영구적으로 null 방치하는가?
- **영향**: 데이터 파이프라인 (`scripts/build_tsu_dataset.py` 등) 수정 필요 여부. 운영 절차 변경 필요.

---

## §5. 결론

설교문 작성 워크플로는 기존 아키텍처와 양립 가능합니다. 핵심 원칙:

1. **검색**: `candidate_k` 확장 단일 호출 (ADR-001 준수)
2. **상태**: `st.session_state` 기반 단순 모델 (Phase 1 적합)
3. **TSU 변경**: `sermon_type` 메타데이터 필드 (최소 변경, Phase 1 설계만)
4. **생성**: GenerationService 조합 + SermonDraftService 래퍼
5. **전제 위반**: UI 레이어에서 완화 (엔진 변경 없음)

이 설계 검토 문서는 설교문 작성 기능(Phase 1)의 설계 검토 단계 산출물입니다. 구현은 CUE가 위 열린 질문을 확인한 후 별도로 계획됩니다.

---

*본 문서는 docs/architecture/ 범위에서 작성되었으며, 어떤 코드도 수정하지 않았습니다.*