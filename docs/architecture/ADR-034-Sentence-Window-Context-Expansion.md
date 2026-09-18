---
title: "ADR-034: Sentence-Window Context Expansion (Retrieval-Time Neighbor Stitching)"
category: architecture
sprint: (신규, 2026-09-17 착수)
based_on:
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md
  - docs/architecture/ADR-008-Semantic-Chunking-Production-Path.md
created: 2026-09-17
status: Proposed (설계 승인 — 사용자 지시 "작업을 진행하라", 2026-09-18 —
  단, Retrieval Engine 변경 항목이라 CLAUDE.md CUE Operating Policy상
  C1 독립 리뷰 통과 전까지 core/retrieval.py 코드 변경은 착수하지 않는다)
scope_modified: docs/architecture/ 신규 문서만 (코드 미수정) — 이번 갱신도 문서만
---

# ADR-034: Sentence-Window Context Expansion

| | |
|---|---|
| Status | Proposed (설계 승인, C1 Review 대기) |
| Date | 2026-09-17 (갱신 2026-09-18) |
| Deciders | HQ (설계 승인 완료, 2026-09-18) / CUE (조사·설계) / C1 (독립 리뷰 — 대기) |
| Supersedes | — |
| Superseded by | — |
| Amends | 없음 |

---

## Context

사용자가 "청킹 overlap을 늘려 결과물 정밀도를 높이는 업계 표준 방법"을
질문했고, CUE는 세 가지 선택지를 제시했다:

1. 고정 비율 오버랩 확대 — 이미 프로덕션(`chunking_optimizer.py`)에 구현됨.
2. **Sentence-Window / Parent-Child 청킹** — 저장은 작은 단위로 하되,
   검색된 청크의 앞뒤 이웃 청크를 생성(LLM) 시점에만 붙여 문맥을 보강.
3. Late Chunking / Contextual Retrieval — 임베딩·청킹 파이프라인 자체를
   바꿔야 하는 더 큰 개입.

사용자가 2번 업그레이드를 지시했다. 그러나 2번은 `core/retrieval.py`를
건드리는 작업이며, `core/retrieval.py::RetrievalEngine`은 ADR-001이
지정한 유일한 Retrieval Engine Authority이자 CLAUDE.md CUE Operating
Policy의 "반드시 지켜야 하는 사항(명령 없이는 절대 변경 금지)" 목록에
명시된 보호 대상이다. 같은 문서의 "예외 — 항상 승인 요청" 목록에도
"Retrieval Engine 변경"이 별도로 명시되어 있다. 따라서 실제 구현
착수 전에 이 ADR로 설계를 문서화하고 HQ 승인을 먼저 받는다(ADR-008이
따른 것과 동일한 절차 — "게이트/설계 완료 ≠ 실행 승인").

### 사전 조사 결과 (코드 미수정, 조사만)

- `core/tsu_builder.py:build_tsu_records()`가 각 TSU 레코드에
  `document_id`, `chunk_id`(= `generate_chunk_id(document_id, idx)`,
  `idx`는 문서 내 0-base 순번)를 이미 부여하고 있음을 확인했다. TSU
  레코드는 문서별로 `idx` 순서대로 `records` 리스트에 append되므로,
  **TSU 스키마나 청킹/빌드 파이프라인을 전혀 바꾸지 않고도**
  `document_id`별로 순서를 복원해 "직전/직후 청크"를 찾을 수 있다 —
  이 설계는 "TSU Pipeline 변경 금지" 원칙(CLAUDE.md)에 저촉되지 않는다.
- `core/retrieval.py:1391 RetrievalEngine`의 `retrieve()`(하이브리드
  랭킹 파이프라인: 메타데이터 필터 → BM25 → 벡터/TF-IDF → 신학 스코어링
  → 랭킹 → 중복제거 → Top-K)는 **건드리지 않는다** — 랭킹 로직과 점수는
  현재와 동일하게 유지.
- 실제 컨텍스트 텍스트가 LLM에 넘어가는 지점은 `core/retrieval.py:2078
  ContextAssembler.assemble()` 하나뿐이며, `candidate.content`를 그대로
  문자열에 꽂아 넣는 구조다. **이 지점 하나만 확장**하면 랭킹/점수/
  인용(Citation)/스코어링 코드는 전부 무영향으로 유지된다.

---

## Decision (제안 — 이 ADR은 확정하지 않음)

### 제안: `ContextAssembler.assemble()`에서만 이웃 청크를 이어붙인다

1. `RetrievalEngine` 로드 시 `document_id → [chunk_id, ...]` (idx 순서)
   맵을 1회 구축(TSU 로드 부수 산출물, 추가 파일 I/O 없음).
2. `ContextAssembler.assemble()`이 각 `RankedCandidate`에 대해 위 맵으로
   직전 1개·직후 1개 이웃 청크의 `content`를 조회해, LLM 컨텍스트
   블록에서만 `[이전 문맥] ... [검색된 청크] ... [이후 문맥] ...` 형태로
   이어붙인다. 창 크기(N=1, 확장 가능)는 `core/config.py`에 새 설정값
   (`CONTEXT_WINDOW_NEIGHBORS`, 기본 1)으로 노출한다.
3. **랭킹·점수·인용은 절대 영향받지 않는다** — `RankedCandidate.content`,
   `Citation.content_excerpt`는 원래 청크 그대로 유지, 이웃 텍스트는
   `llm_context_block` 조립에만 쓰이는 지역 변수.
4. 문서 경계(이웃이 다른 document_id이거나 존재하지 않는 첫/마지막
   청크)에서는 조용히 생략 — 에러/폴백 문구 없음("모르면 비워둔다"
   원칙, ADR-008/§4 provisional 규칙과 동일 톤).
5. 문서에 걸쳐 인접한 두 후보가 이미 Top-K에 함께 뽑힌 경우 중복
   텍스트가 두 번 나타날 수 있음 — 조립 시점에 이미 블록에 포함된
   `chunk_id`는 이웃으로 재조회하지 않도록 간단한 dedup만 추가(랭킹
   로직 변경 아님).

### 명시적으로 제안하지 않는 것

- `retrieve()`의 랭킹/스코어링/후보 생성 로직 변경 — 전혀 손대지 않음.
- TSU 스키마 변경, `tsu_builder.py` 재실행/재인덱싱 — 필요 없음(기존
  `document_id`/`chunk_id`만으로 충분).
- Late Chunking, Contextual Retrieval(제안 3) — 이번 ADR 범위 밖.
- 즉시 프로덕션 반영 — ADR-008 선례와 동일하게, 이 ADR은 설계와
  실측 계획만 확정하고 실제 `core/retrieval.py` 코드 변경은 별도
  명시적 승인 후 착수한다.

---

## 검증 계획 (승인 시 착수)

1. 회귀: 기존 `tests/test_query_enhancements_full_regression.py`,
   `tests/test_book_alias_resolution.py` 등 RetrievalEngine 계약
   테스트 전량 PASS 유지(랭킹 무변경이므로 통과 예상, 실측으로 확인).
2. 신규 단위테스트: 이웃 청크 조회 함수(문서 경계/첫·끝 청크/단일
   청크 문서 edge case), 컨텍스트 블록 조립 결과에 이웃 텍스트가
   포함되는지, dedup 동작.
3. 품질 측정: `docs/architecture/DBMA-SEQ-*` 계열 groundedness/정밀도
   골든셋으로 Before/After 비교(가능하면 [[project_theological_response_quality_audit]]
   P0-5 채점 인프라 재사용).

## Consequences

### 확정되는 것 — 없음(제안만)
### 확정되지 않는 것(전부 HQ 승인 대상)
- 실제 `core/retrieval.py`/`core/config.py` 코드 변경 착수 여부.
- 이웃 창 크기(N) 기본값.
- Citation에 이웃 문맥을 노출할지 여부(현재 제안은 비노출 — LLM 컨텍스트만 확장).

### 리스크
- Top-K 후보가 서로 인접한 청크로 몰려 있으면(같은 문서 밀집 검색)
  컨텍스트 블록 길이가 늘어나 프롬프트 토큰 예산에 영향 — dedup으로
  일부 완화되나 완전 제거는 아님. 실측 후 창 크기 조정 필요할 수 있음.
- `document_id`/`chunk_id` 맵 구축은 TSU 로드 시 O(N) 1회 비용 —
  53k~ TSU 규모에서도 무시 가능한 수준으로 예상(실측 필요).

---

## Next Steps

1. ~~이 ADR(Proposed) 설계 검토·승인~~ — **완료 (2026-09-18, 사용자 지시
   "작업을 진행하라")**.
2. **C1 Review 요청 — 진행 중 (`docs/agents/c1/C1-TASK-ORDER-061-ADR034-DESIGN-REVIEW.md`)**.
   신규 Architecture 변경(Retrieval Engine을 건드리는 설계)이라 CLAUDE.md
   CUE 정책상 구현 착수 전 필수.
3. C1 APPROVE 이후 구현 → 단위테스트 → 회귀 → Build Report → Git Commit/Push.
   (CUE 표준 순서).
