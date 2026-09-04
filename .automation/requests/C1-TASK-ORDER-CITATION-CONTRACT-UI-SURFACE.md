# C1 Task Order — Citation Contract UI Surface (Research + Chat)

| | |
|---|---|
| Issued by | CUE |
| Issued | 2026-08-17 |
| Executor | C1 |
| Verifier | CUE |
| Approver (final) | Rev. Bang |
| Status | GREEN — C1 실행 승인(CUE 검토 CONDITIONAL GREEN → 함수명 정정 완료 → GREEN, Rev. Bang 착수 승인 2026-08-17) |
| Basis | G4 Independent Verification (Gate 1, End-User Package), 2026-08-17 — 판정: GAP |

---

## 0. Purpose (scope-limited)

`core/retrieval.py::QueryProcessor.process()`는 매 쿼리마다 `CitationBuilder.build_citations()`를
호출해 `ResponsePackage.citations: list[Citation]`을 이미 채운다(`retrieval.py:1985`). 이 값은
`author`/`source_title`/`evidence_confidence`/`language`/`source_type`을 담고 있지만,
`ui/pages/research.py`(네이티브 DBMA 결과)와 `ui/pages/chat.py` 어디도 이를 읽지 않는다 —
둘 다 `RankedCandidate.metadata`의 부분집합(`source_file`, `document_id`, `tsu_id`,
`verse_mapping`, 점수)만 표시한다.

**목표**: 이미 계산되어 있는 `response.citations`의 값(author/source_title/evidence_confidence)을
Research 네이티브 카드와 Chat 출처 expander에 **추가로** 표시한다.

This Task Order does **not**:
- modify `core/retrieval.py`, `CitationBuilder`, `Citation`, `RankedCandidate`, `QueryProcessor` (contract 자체는 이미 완결 — 재구현 금지)
- remove or replace any currently displayed field (bm25/vector/theological score, `explanation`, `verse_mapping` 등은 Citation에 없는 정보이므로 유지)
- change NAE bridge section(`_render_nae_section`, ADR-024) — 이미 Citation을 쓰고 있어 범위 밖
- introduce a new ADR — 이 작업은 UI 렌더링 필드 추가일 뿐, `RetrievalEngine`/Metadata Model/ID Governance를 건드리지 않는다(CLAUDE.md C1 Review 트리거 기준 미해당)

---

## 1. Prior Facts (CUE가 이미 확정 — 재조사 금지)

- `response.top_k_results[i]`와 `response.citations[i]`는 **동일 인덱스로 1:1 대응**한다
  (근거: `QueryProcessor.process()`, `retrieval.py:1977-1990` — `candidates[:k]`가
  `citations = build_citations(candidates[:k])`와 `response_formatter.format(..., candidates[:k], ..., citations, ...)`
  양쪽에 동일 슬라이스로 전달됨). 별도 매칭 로직 불필요, index로 zip하면 된다.
- `Citation` 필드(`core/retrieval.py:1810-1829`): `citation_id, tsu_id, scripture_reference,
  source_title, source_author, document_id, content_excerpt, evidence_confidence,
  retrieval_score, source_file, language, source_type`.
- `chat.py`가 `RankedCandidate`만 쓰는 이유는 "Citation을 배제하기로 한 결정"이 아니라
  구현 당시(SPRINT17-Phase5-M1b-2) "Research가 이미 쓰던 방식을 그대로 따른다"는 스코프
  메모였다(`chat.py:7-9`) — Research도 애초부터 네이티브 결과에는 Citation을 쓴 적이 없었다.
- 기존 테스트(`tests/test_response_package_citations.py`,
  `tests/test_generation_service_citations.py`)는 **배관(plumbing) 회귀**만 검증한다 — UI
  렌더링 테스트는 없다. 본 작업은 여기에 UI 레벨 테스트를 추가한다(§3 Phase 3).

---

## 2. Role Separation

**C1 (executor)**: Phase 1–4 구현·테스트, 회귀 확인, evidence 작성.
**CUE (verifier)**: 완료 후 §5 acceptance criteria 대조, 회귀 무영향 재확인, 최종 판정.
**Rev. Bang (approver)**: 최종 승인(이미 위 대화에서 이 UI 변경 방향 자체는 승인됨 — 완료 보고 시 재확인만).

---

## 3. Phases

**Phase 1 — Research 네이티브 카드에 author/source_title/evidence_confidence 추가**
- 대상: `ui/pages/research.py::_execute_research_query()`(또는 `_format_candidate()`), `_render_search_results_as_cards()`.
- `_execute_research_query()`가 반환하는 `response`(`ResponsePackage`)에서 `response.citations`를 함께
  `_format_candidate(candidate, citation, parsed_query)` 형태로 전달(index로 zip).
- `_format_candidate()` 반환 dict에 `author`, `source_title`, `evidence_confidence` 키 추가(citation이 None이거나 필드가 없으면 표시 생략 — 값 없음을 빈 문자열/'-'로 채우지 않는다, 실제로 없는 정보를 있는 것처럼 보이면 안 됨).
- `_render_search_results_as_cards()`에서 이 값이 있을 때만 캡션 라인 추가(예: `저자: {author}`). 기존 title/snippet/score 표시는 그대로 유지.

**Phase 2 — Chat 출처 expander에 author/source_title/evidence_confidence 추가**
- 대상: `ui/pages/chat.py::_handle_user_message()`, `_render_source()`, `_render_clickable_source()`.
- `_handle_user_message()`에서 `response.citations`를 `response.top_k_results`와 함께
  `chat_messages`에 저장(직렬화 대상 — `_serialize_messages`/`_deserialize_messages`가
  `Citation`도 `to_dict()`/재구성 가능해야 함. `Citation`에 `to_dict()`가 없으면
  `dataclasses.asdict()`로 처리 — `RankedCandidate`와 다른 방식이어도 무방, 기존
  `_serialize_messages`의 `hasattr(s, "to_dict")` 분기 그대로 재사용 가능한지 먼저 확인).
- `_render_source()`/`_render_clickable_source()`가 대응하는 `Citation`을 받아 author/title/
  confidence를 캡션으로 추가 표시. 기존 `신뢰도: {score:.4f}` 캡션(final_score 기반)은 유지 —
  `evidence_confidence`는 다른 의미이므로 별도 라벨로 구분해서 표시할 것(예: "저자: …" /
  "출처: …(book by author)" / "근거 신뢰도(citation): 0.NN" vs 기존 "신뢰도: 0.NNNN"(final_score)
  — 두 숫자를 같은 라벨로 섞어서 사용자가 혼동하지 않게 한다).

**Phase 3 — 테스트**
- `_format_candidate`가 citation 필드를 올바르게 병합하는지 단위 테스트 추가(citation 있음/None
  두 케이스).
- Chat의 직렬화/역직렬화 round-trip에 `Citation`이 포함된 경우 테스트 추가(`_serialize_messages`
  → `_deserialize_messages` → 원본과 author/source_title 값 일치 확인).
- 기존 회귀: `tests/test_response_package_citations.py`,
  `tests/test_generation_service_citations.py`, `tests/test_book_alias_resolution.py`,
  `tests/test_query_enhancements_full_regression.py` 전부 PASS 유지(무수정 대상이므로).

**Phase 4 — Evidence package**
- `git diff core/retrieval.py` — 빈 결과(무수정) 캡처.
- 변경 파일: `ui/pages/research.py`, `ui/pages/chat.py`, 신규/수정 테스트 파일만.
- 실제 질의 1회 스크린샷 또는 텍스트 출력으로 author/source_title이 실제로 화면에 표시됨을
  캡처(예: streamlit 헤드리스 실행 로그 또는 `st.session_state` 덤프가 아니라 실제 렌더 결과).

---

## 4. Hard Stop Conditions

즉시 중단하고 CUE에 보고(Rev. Bang에게 직접 보고 금지):
1. `core/retrieval.py`(`Citation`, `CitationBuilder`, `RankedCandidate`, `QueryProcessor`, `ResponsePackage`) 수정이 필요해 보이는 경우
2. `response.citations`와 `response.top_k_results`의 인덱스 대응이 실제로 깨지는 경우(§1 전제가 틀렸다는 뜻 — 재설계 필요, 이 Task Order 범위 밖)
3. NAE bridge 섹션(`_render_nae_section`, ADR-024)을 건드려야 할 상황이 생기는 경우
4. 기존 회귀 테스트가 깨지는 경우
5. `evidence_confidence`/`source_author` 등 값이 실제로는 대부분 `None`이라 UI에 표시할 값이
   거의 없다는 사실이 확인되는 경우(이 경우 "GAP이 아니라 데이터 부족"이라는 재분류가 필요하므로
   구현 강행하지 말고 CUE에 실측 보고)

**Never touch**: RAW 데이터, `core/retrieval.py` 전체, ADR-001/003/013/024, NAE corpus,
Production Registry.

---

## 5. Acceptance Criteria (구현 완료 판정)

1. `git diff core/retrieval.py` — 빈 결과
2. `response.citations[i]` ↔ `response.top_k_results[i]` 인덱스 대응이 실제 실행으로 확인됨(같은 `tsu_id`인지 assert)
3. Research 네이티브 카드에 author/source_title(존재하는 경우만) 표시 — 실제 실행 스크린샷/출력
4. Chat 출처 expander에 author/source_title(존재하는 경우만) 표시, 기존 `신뢰도` 캡션과 `evidence_confidence` 캡션이 구분되어 표시됨
5. Chat 대화 기록 저장→복원(새로고침 시나리오) 후에도 author/source_title 값이 유지됨(직렬화 회귀 테스트)
6. Phase 3의 신규 테스트 + 기존 4개 회귀 파일 전부 PASS
7. NAE bridge 섹션(`nae_pd` 모듈) 코드 무변경 확인(`git diff` 대상 파일 목록에 없음)

---

## 6. Output format expected from C1 per phase

`PHASE N — <PASS|INCOMPLETE|BLOCKED> — <1-line summary> — evidence: <path or command+output>`

---

## 7. CUE Pre-Review Gate

- [ ] `core/retrieval.py` 수정 필요? → No — `response.citations`는 이미 계산되어 존재, 소비만 추가.
- [ ] ADR-001(RetrievalEngine 유일 authority) 위반? → No — 검색 로직 무변경, UI 표시 필드 추가일 뿐.
- [ ] ADR-024(NAE bridge) 영향? → No — NAE 섹션은 이미 Citation 사용 중, 범위에서 명시적으로 제외.
- [ ] 신규 ADR 필요? → No — Metadata Model/ID Governance/Validator/Migration 변경 없음, CLAUDE.md C1 Review 트리거 미해당.
- [ ] Production mutation 필요? → No — 읽기 전용 UI 렌더링 추가.

**CUE Pre-Review verdict: PASS — Task Order may be issued to C1.**
