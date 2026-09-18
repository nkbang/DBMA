# C1 Task Order 061 — ADR-034 설계 검토 보고서 (독립 검증)

- 발주: CUE · 일자: 2026-09-17
- 검토 일자: 2026-09-17
- 검토 모델: `qwen3.6:35b-DBMAcode` (C1 Forensic Auditor)
- 모드: PLAN MODE (검증 분석), ACT MODE (보고서 작성)
- 판정: **APPROVE**

---

## 1. 검토 대상

ADR-034 "Sentence-Window Context Expansion" 설계 문서:
`docs/architecture/ADR-034-Sentence-Window-Context-Expansion.md` (worktree 버전, 메인 저장소 미존재)

핵심 주장:
> `core/retrieval.py:2078 ContextAssembler.assemble()`에서만 이웃 청크를 이어붙이면
> 랭킹/스코어링/Citation을 건드리지 않으며, TSU 스키마 변경 없이 가능하다.

---

## 2. 검증 결과 — 주장별 사실 확인

### 주장 1: "TSU 레코드에 `document_id`와 `chunk_id`가 이미 부여되어 있으며,
`idx` 순서대로 저장되므로 TSU 스키마 변경 없이 직전/직후 청크를 찾을 수 있다"

**검증: 맞음 (APPROVE)**

근거:
- `core/tsu_builder.py:371-372`: TSU 레코드에 `"document_id": document_id, "chunk_id": chunk_id`가 이미 포함됨
- `core/tsu_builder.py:319`: `for idx, chunk_id in enumerate(chunk_ids):` — idx 순서대로 records 리스트에 append
- 실제 데이터 확인 (`output/bench/tsu_dataset.jsonl`):
  ```json
  {"tsu_id": "TSU-ACT-ada6a56f8ea13582f61e8d52b74e62c2_chunk_00000",
   "document_id": "ada6a56f8ea13582f61e8d52b74e62c2",
   "chunk_id": "ada6a56f8ea13582f61e8d52b74e62c2_chunk_00000",
   ...}
  {"tsu_id": "TSU-ACT-ada6a56f8ea13582f61e8d52b74e62c2_chunk_00001",
   "document_id": "ada6a56f8ea13582f61e8d52b74e62c2",
   "chunk_id": "ada6a56f8ea13582f61e8d52b74e62c2_chunk_00001",
   ...}
  ```
- `RetrievalEngine.__init__` (line 1414)에서 `self._load_corpus()`가 `self.tsus: list[dict]`에 전량 로드 — 추가 파일 I/O 없음

**결론**: TSU 스키마 변경 불필요. `document_id → [chunk_id, ...]` 맵은 TSU 로드 시 부수 산출물로 O(N) 1회 구축 가능.

---

### 주장 2: "`ContextAssembler.assemble()`이 LLM 컨텍스트 전달의 유일한 지점이다"

**검증: 맞음 (APPROVE)**

근거:
- `core/retrieval.py:2298`: `QueryProcessor.process()` 내에서 `self.context_assembler.assemble(candidates[:k], parsed_query)` 호출
- `assemble()` 반환값 `(llm_context_block, scripture_contexts)`가 `ResponseFormatter.format()`으로 전달 (line 2304-2307)
- `candidate.content` 사용 지점 전수 grep:
  - line 2016: `_deduplicate()` — MD5 해시용 읽기 전용
  - line 2093: `assemble()` — 컨텍스트 블록 조립 (우리가 확장할 지점)
  - line 2184: `CitationBuilder.build_citations()` — `content_excerpt=candidate.content[:200]` 읽기 전용
  - line 2230: `ResponseFormatter._summarize_theology()` — `candidate.content.lower()` 읽기 전용
- `assemble()` 외에는 `candidate.content`를 LLM 컨텍스트로 전달하는 경로 없음

**결론**: `assemble()`이 유일한 지점. 이 지점만 확장하면 다른 곳 무영향.

---

### 주장 3: "랭킹·점수·인용은 절대 영향받지 않는다"

**검증: 맞음 (APPROVE)**

근거:
- **랭킹**: `RetrievalEngine.retrieve()` (line 1391~1950)는 ranking pipeline — 변경 안 함. `assemble()`은 ranking 완료 후 별도 단계 (line 2298)
- **점수**: `RankedCandidate.final_score` 등 모든 스코어 필드는 `candidate.content`와 무관. `assemble()`에서 score 읽기만 함 (line 2094), 수정 안 함
- **인용 (Citation)**: `CitationBuilder.build_citations()` (line 2158~2192)는 `candidate.content[:200]`를 `content_excerpt`로 사용 — 읽기 전용. `assemble()` 호출 (line 2298)보다 **이후**에 호출 (line 2301)
- **pipeline 순서**: retrieve() → assemble() → build_citations() → format() — assemble()은 중간 단계,前後의 데이터 흐름을 변경하지 않음

**결론**: 랭킹/스코어링/Citation 코드 경로와 데이터 모두 무영향.

---

### 주장 4: "`candidate.metadata`에 `document_id`와 `chunk_id`가 포함된다"

**검증: 맞음 (APPROVE)**

근거:
- `core/retrieval.py:1926`: `RankedCandidate(..., metadata=tsu, ...)` — tsu는 full TSU dict
- TSU dict에 `document_id` (line 371), `chunk_id` (line 372) 포함됨 (tsu_builder.py)
- 실제 데이터에서 확인: `candidate.metadata["document_id"]` → `"ada6a56f8ea13582f61e8d52b74e62c2"`,
  `candidate.metadata["chunk_id"]` → `"ada6a56f8ea13582f61e8d52b74e62c2_chunk_00000"`

**결론**: neighbor lookup에 필요한 필드가 모두 metadata에 존재.

---

### 주장 5: "RetrievalEngine.retrieve()의 랭킹/스코어링 로직을 건드리지 않는다"

**검증: 맞음 (APPROVE)**

근거:
- ADR 설계에서 명시적으로 "제안하지 않는 것" 섹션에 `retrieve()` 변경 없음 명시 (ADR line 92-93)
- `RetrievalEngine.__init__`에 `document_id → [chunk_id, ...]` 맵 추가는 로드 시 1회 구축 (추가 I/O 없음)
- retrieve() pipeline (STEP 1~7) 전체 변경 안 함

**결론**: Retrieval Engine 핵심 로직 무변경.

---

## 3. 리스크 분석

### 리스크 1: Top-K 후보가 같은 문서에 밀집되면 컨텍스트 블록 길이 증가

**등급**: 낮음 (ADR에서 이미 dedup으로 완화 계획)
**근거**: ADR line 85-88에서 "이미 블록에 포함된 chunk_id는 이웃으로 재조회하지 않도록 dedup" 명시. 실제 데이터에서 같은 문서 밀집도는 `_apply_document_diversity()` (line 1952~1980)로 이미 제한됨.

### 리스크 2: `document_id → [chunk_id, ...]` 맵 구축 비용

**등급**: 낮음
**근거**: TSU 로드 시 `self.tsus`가 이미 메모리에 있음. O(N) 순회만으로 맵 구축 — 84,766건 TSU 기준 수 ms 수준으로 예상. 실제 측정은 필요하지만 "무시 가능한 수준"이라는 주장과 일치.

### 리스크 3: chunk_id 문자열 파싱 vs 맵 기반 neighbor lookup

**등급**: 낮음 (설계상 명확)
**근거**: ADR은 `document_id → [chunk_id, ...]` 맵을 제안 — chunk_id 문자열 파싱 불필요. 맵 기반 접근이 더 안전하고 명확함.

---

## 4. 판정: APPROVE

### 근거 요약

| 주장 | 검증 결과 | 근거 |
|------|----------|------|
| TSU 스키마 변경 없이 가능 | 맞음 | `document_id`/`chunk_id`가 기존 TSU에 포함, 실제 데이터 확인 |
| assemble()이 유일한 LLM 컨텍스트 전달 지점 | 맞음 | 전수 grep 확인, 그 외 호출 없음 |
| 랭킹/스코어링/Citation 무영향 | 맞음 | pipeline 순서 확인, candidate.content 읽기 전용 사용 확인 |
| metadata에 필요한 필드 포함 | 맞음 | RankedCandidate(metadata=tsu)에서 tsu가 full dict |
| retrieve() 무변경 | 맞음 | ADR 설계에서 명시적 제외, 맵 구축은 init 시 1회 |

### 조건부 권고 (설계 승인 시)

1. **실측 필수**: `document_id → [chunk_id, ...]` 맵 구축 시간과 Top-K 밀집 시 컨텍스트 블록 길이 증가량을 실제 데이터로 측정
2. **N=1 기본값**: 이웃 창 크기 기본값은 1로 두고, 실측 후 조정 (ADR과 일치)
3. **Citation 비노출**: 이웃 문맥을 Citation에 노출하지 않는 현재 제안 유지 (LLM 컨텍스트만 확장)

---

## 5. 검증 방법론

- `core/retrieval.py` line-by-line 읽기 (line 95~140, 1387~1450, 1890~1970, 1952~2022, 2060~2124, 2155~2230, 2260~2310)
- `core/tsu_builder.py` line-by-line 읽기 (line 275~400)
- `RankedCandidate.content` 사용 지점 전수 grep: `grep -n "candidate\.content\|c\.content" core/retrieval.py` → 4곳 모두 확인
- `assemble()` 호출 지점 grep: `grep -n "\.assemble(" core/retrieval.py` → line 2298 단 한 곳 확인
- 실제 TSU 데이터 확인: `output/bench/tsu_dataset.jsonl` 첫 2건 읽기
- pipeline 순서 확인: `QueryProcessor.process()` (line 2268~2310)

---

## 6. 결론

CUE의 "최소 침습 설계" 주장은 **모든 면에서 사실임**.

- TSU 스키마 변경 불필요: 기존 `document_id`/`chunk_id`로 충분
- 랭킹/스코어링/Citation 무영향: `assemble()`은 ranking 완료 후 별도 단계, `candidate.content`는 읽기 전용
- Retrieval Engine 핵심 로직 무변경: init 시 맵 구축만 추가
- `assemble()`이 유일한 LLM 컨텍스트 전달 지점: 전수 확인 완료

**설계 승인: APPROVE** — 구현 착수 가능.
