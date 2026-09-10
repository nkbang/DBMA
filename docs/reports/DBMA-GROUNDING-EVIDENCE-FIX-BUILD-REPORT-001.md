# Build Report — 근거 강제 지시문 + 근거 본문 절단 제거

| | |
|---|---|
| 날짜 | 2026-09-10 |
| 브랜치 | `claude/theological-pastoral-response-quality-89b049` |
| Base | `32f59c9` |
| 근거 | 신학·목회 답변 품질 감사(본 세션) 우선순위 1·2번, Rev. Bang 지시 |

## 문제

1. **근거 미강제.** `GenerationService._build_prompt()`가 만드는 프롬프트는
   `문맥:\n{context}\n\n질문:\n{q}`가 전부였고, 모델 SYSTEM 프롬프트에도
   근거 제한 지시가 없었다. 로컬 전용 스택(Ollama/Qdrant)으로 외부 호출을
   물리적으로 차단해 놓고도, 모델 내장 지식이 검색 근거와 무구분으로 섞였다.
2. **근거 본문 절단.** `bridge_query()`가 `RankedCandidate.content`에
   `content_excerpt`(=`source_text[:200]`)를 넣었다. 이 값은
   `ContextAssembler.assemble()`을 지나 `llm_context_block`이 되므로, 모델이
   문장 중간에서 잘린 조각을 근거로 받았다. Fuller Vol01 3,643건 실측
   `source_text` 평균 204자 — 200자 상한이 실제로 물렸다.

## 변경

| 파일 | 내용 |
|---|---|
| `core/generation.py` | `_GROUNDING_DIRECTIVE` / `_GROUNDING_DIRECTIVE_NO_CONTEXT` 추가, `_build_prompt()`가 자료 블록과 질문 사이에 삽입. 라벨 `문맥:` → `자료:`(지시문 §1이 "위 자료"를 가리킴) |
| `NAE/retrieval_adapter.py` | 매핑 dict에 `source_text`(전문) 필드 추가, `RankedCandidate.content`가 이를 사용. `content_excerpt` 200자는 그대로 유지 |
| `resources/models/Modelfile.theology-bot-v2` | 신규 — 실행 중인 `my-theology-bot-v2:latest`의 SYSTEM/PARAMETER를 원문 그대로 저장소에 기록(변경 아님, 기록) |
| `tests/test_generation_conversation_history.py` | 프롬프트 전문 리터럴 비교 → 순서/구성요소 검증으로 전환 + `TestGroundingDirective` 3건 추가 |
| `tests/test_nae_bridge_full_source_text.py` | 신규 4건 — 발췌 200자 유지와 본문 무절단을 함께 검증 |

## ADR 정합성

- **ADR-024 (Approved)** §C 필드 매핑표는 `content_excerpt = content[:200]`을
  **Citation 필드**로 정의한다. `RankedCandidate.content`는 그 표에 없다 —
  둘을 같은 값으로 쓰던 것은 계약이 아니라 계약 밖 구현 편법이었다.
  `content_excerpt` 200자는 손대지 않았으므로 **Architecture Freeze Rule
  위반 없음, ADR Amendment 불요**.
- ADR-001(Retrieval Engine Authority): `core/retrieval.py` 무수정.
- 미해결로 남긴 것(별도 승인 필요): 교단 프로파일 계층(ADR-009),
  한국어 QueryParser, 청크 단위 정책(ADR-007/008 Proposed).

## 검증

```
tests/test_nae_bridge_full_source_text.py + test_generation_conversation_history.py
  → 12 passed
pytest -k "generation or nae_retrieval or bridge or citation or claim_guard"
  → 184 passed, 2548 deselected
```

venv: `~/envs/dbma311`.

## 남은 위험

- 근거 전문이 문맥에 들어가면서 프롬프트 길이가 늘어난다. 모델 `num_ctx`는
  32768이고 기본 top_k에서는 여유가 있으나, top_k를 크게 올리면 초과 가능 —
  실사용 관찰 필요.
- 지시문 준수 여부 자체는 아직 측정하지 않았다. `core/evaluation/rag_judge.py`의
  groundedness 판정은 현재 설교 초안 경로에만 연결돼 있다.
