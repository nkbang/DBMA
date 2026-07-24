# DBMA-SEQ Phase 1 — Design Note

발급: C1 (2026-07-24)
참조: ADR-012, C1-TASK-ORDER-011
성격: **구현 전 설계 메모** — 코드 미포함, CUE 검토용

---

## 1. 목적

`DBMA-SIL`(Sermon Intelligence Layer)이 생성한 설교 개요/확장 결과물의
품질 검증 계층을 설계한다. `DBMA-REQ`(ADR-010, RAG groundedness 평가)와
동일한 패턴을 재사용한다.

```
DBMA-REQ = (question, retrieved_chunks, answer) → groundedness
DBMA-SEQ = (scripture_and_theme, retrieved_candidates, generated_text) → quality_score
```

---

## 2. 기존 코드 분석 결과

### 2.1 `core/evaluation/rag_judge.py` 패턴

```python
# 핵심 시그니처
def judge_groundedness(
    run_id: str,
    query_id: str,
    question: str,
    retrieved_chunks: list[str],        # ← 검색된 청크 텍스트
    retrieved_chunk_ids: list[str],
    answer: str,                         # ← 생성된 답변 텍스트
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> RagEvalScore:

# 프롬프트 구조
_GROUNDEDNESS_PROMPT = """
[질문]
{question}

[검색된 청크]
{chunks_text}

[생성된 답변]
{answer}

groundedness: 답변이 검색된 청크에 실제로 근거했는가 0~5점
JSON: {{"groundedness": <0-5>, "groundedness_rationale": "<한두문장>"}}
"""

# 응답 처리
def _parse_judge_json(raw: str) -> tuple[float, str]:
    # 첫 '{' ~ 마지막 '}' 추출 → JSON 파싱
```

### 2.2 `core/generation.py` — SermonOutline 관련 함수

```python
# 데이터 구조
@dataclass
class SermonOutline:
    title: str
    introduction: str
    points: list[str]        # 대지 목록
    conclusion: str

# SermonDraftService.generate_outline() 시그니처
def generate_outline(
    scripture_and_theme: str,           # ← 본문/주제 (예: "로마서 8:25-28 — 고난과 인내")
    candidates: list[RankedCandidate],   # ← 검색된 자료 청크 리스트
    sermon_format: str = "주제설교",
    gen_model: str = DEFAULT_GEN_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
) -> tuple[SermonOutline, Optional[str]]:

# SermonDraftService.expand_point() 시그니처
def expand_point(
    point_text: str,                    # ← 확장할 대지 텍스트
    scripture_and_theme: str,
    candidates: list[RankedCandidate],   # ← 동일한 검색 자료
    style_examples: str = "",            # ← 어투 참고용 과거 설교문
    sermon_format: str = "주제설교",
    gen_model: str = DEFAULT_GEN_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
) -> tuple[str, Optional[str]]:

# 컨텍스트 포맷 (_format_sermon_context)
# [자료1] 제목 — 저자 (위치)
# 청크 내용
#
# [자료2] ...
```

---

## 3. 설계 — sermon_judge.py에 넘겨야 할 데이터

### 3.1 judge 함수 시그니처 (안)

```python
def judge_sermon_groundedness(
    run_id: str,
    query_id: str,
    
    # === 입력 데이터 ===
    scripture_and_theme: str,            # 본문/주제
    retrieved_candidates: list[RankedCandidate],  # 검색된 자료 (라벨 포함)
    generated_text: str,                 # 생성된 텍스트 (개요 또는 대지)
    text_type: str,                      # "outline" | "expansion"
    
    # === 옵션 ===
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> SermonQualityScore:
```

### 3.2 프롬프트에 포함할 데이터

```
[본문/주제]
{scripture_and_theme}

[검색된 자료]
{retrieved_candidates를 _format_sermon_context()와 동일한 형식으로}
→ [자료1] 제목 — 저자 (위치)
   청크 내용
→ [자료2] ...

[생성된 {text_type}]
{generated_text}

groundedness: 생성된 텍스트가 검색된 자료에 실제로 근거했는가 0~5점
- 5점: 모든 핵심 주장이 자료에서 직접 확인된다
- 0점: 자료와 무관하거나 모순된다

JSON: {{"groundedness": <0-5>, "groundedness_rationale": "<한두문장>"}}
```

### 3.3 dataclass 정의 (안)

```python
@dataclass
class SermonQualityScore:
    run_id: str
    query_id: str
    scripture_and_theme: str
    retrieved_candidate_ids: list[str]
    generated_text: str
    text_type: str           # "outline" | "expansion"
    groundedness: float      # 0.0 ~ 5.0
    groundedness_rationale: str
    judge_model: str
    timestamp: str
```

---

## 4. 골든셋 구조 (사람이 라벨링)

### 4.1 필요 사례 수

5~10개 설교 개요 실제 생성 사례

### 4.2 라벨링 항목

각 사례당:

```json
{
  "query_id": "sermon_001",
  "scripture_and_theme": "로마서 8:28 — 모든 것이 합력하여 선을 이루느니라",
  "retrieved_candidate_ids": ["tsu_abc123", "tsu_def456", ...],
  "sermon_format": "주제설교",
  
  // 개요 라벨
  "outline": {
    "title": "...",
    "introduction": "...",
    "points": ["대지1...", "대지2...", "대지3..."],
    "conclusion": "...",
    "groundedness_label": 4  // 사람이 0~5로 채점
  },
  
  // 대지 확장 라벨 (각 대지별로)
  "expansions": [
    {
      "point_index": 0,
      "expanded_text": "...",
      "groundedness_label": 3
    },
    ...
  ]
}
```

### 4.3 사례 수집 방법 (코드 실행 계획만)

1. `SermonDraftService.generate_outline()`을 실제 본문/주제로 여러 건 호출
2. 반환된 `SermonOutline`을 그대로 골든셋에 저장
3. 사람이 각 대지의 groundedness를 0~5로 채점

---

## 5. rag_judge.py와의 공통화 검토

### 5.1 중복되는 로직

| 로직 | rag_judge.py | sermon_judge.py (안) |
|------|-------------|---------------------|
| JSON 추출 | `_parse_judge_json` | 동일 재사용 |
| Ollama 호출 | `ollama.generate(model, prompt, options)` | 동일 재사용 |
| 실패 처리 | score=0.0 + rationale에 오류메시지 | 동일 방침 |
| 컨텍스트 포맷 | `chunks_text` join | `_format_sermon_context()` 재사용 |

### 5.2 분리 제안

```
core/evaluation/
├── rag_judge.py          # 기존 (RAG 답변 groundedness)
├── sermon_judge.py       # 신규 (설교문 groundedness)
└── _judge_common.py      # 공통 로직 (새설)
    ├── _parse_judge_json()
    ├── _build_ollama_options()
    └── _handle_judge_failure()
```

---

## 6. 구현 전 CUE가 검토할 사항

1. **프롬프트 설계**: 위 안이 검색 자료 기반 근거 판단에 충분한가?
2. **text_type 분리**: outline/expansion을 같은 judge로 처리할지 별도 프롬프트가 필요한가?
3. **공통화 범위**: `_judge_common.py` 분리 필요 여부
4. **골든셋 라벨링**: 담당자·일정 (ADR-010 §Decision-미확정 §1과 동일 절차)

---

## 7. 미결정 사항

| 항목 | 담당 | 상태 |
|------|------|------|
| 골든셋 라벨링 담당 | HQ | 미정 |
| 골든셋 라벨링 일정 | HQ | 미정 |
| judge_model | CUE 검토 후 | DEFAULT_JUDGE_MODEL 임시 |
| Few-shot 예시 뱅크 | Phase 2 | 착수 금지 |
| Eval harness | Phase 2 | 착수 금지 |

---

*이 문서는 코드 구현을 포함하지 않습니다. CUE 검토 후 Phase 1 착수 승인 필요.*