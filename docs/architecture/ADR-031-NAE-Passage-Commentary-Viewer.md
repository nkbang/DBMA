---
title: "ADR-031: NAE Passage Commentary Viewer (성경뷰어 → 내서재 근거 해설)"
category: architecture
based_on:
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md
  - docs/architecture/ADR-028-NAE-Smith-Reference-Layer.md
  - core/retrieval.py (QueryProcessor, compute_passage_match_score, ScriptureReference)
  - core/generation.py (GenerationService)
created: 2026-09-04
scope_modified:
  - core/bible_text.py (신규)
  - core/passage_commentary.py (신규)
  - core/citation_format.py (신규)
  - ui/components/passage_viewer.py (신규)
  - ui/pages/_passage_commentary_tab.py (신규)
  - ui/pages/sermon_research.py (탭 추가)
  - core/config.py (BIBLE_TEXT_PATH)
  - config.yaml (directories.bible_text_path)
  - ui/pages/research.py (각주 포맷 공용화 리팩터, 동작 보존)
---

# ADR-031: NAE Passage Commentary Viewer

| | |
|---|---|
| Status | **Proposed** |
| Date | 2026-09-04 |
| Deciders | Rev. Bang / HQ |
| Approved | — |
| Approver | — |
| Supersedes | — |
| Superseded by | — |

> CUE 정책상 "새 Architecture Layer 추가"에 해당한다. 구현 완료 · 회귀 통과 ·
> C1 독립 리뷰 · 사용자 승인 4개 조건을 모두 만족하기 전까지 Proposed 를
> 유지하며, 다른 구현의 근거로 사용하지 않는다(Evidence Before Promotion Rule).

---

## 1. Product Requirement

"연구하기(설교 연구)" 화면에서 **성경뷰어로 본문을 지정**하면, 그 본문을 이해하는 데
도움이 되는 **해설이 내서재(사용자가 등록한 자료)에 근거해** 생성되고, **본문에 각주
번호(①②③)** 가 붙고 **하단에 참고 자료 서지 목록**이 표시된다.

- 질문을 타이핑하지 않아도 **본문 지정만으로 기본 해설이 생성**된다.
- 내서재에 그 본문과 직접 관련된 주석 자료가 **없으면 안내만 표시하고 생성하지 않는다**
  (근거 없는 생성 금지 — 프로젝트 원칙 "None = unknown, 지어내지 않음").
- 출력 언어는 한국어.

---

## 2. Bible Text Data Layer (신규)

현재 코퍼스에는 성경 전문 텍스트가 없다(주석서·신학서만 TSU 로 임베딩됨). 뷰어가 절
본문을 표시하려면 별도 데이터가 필요하다.

**결정: 사용자가 성경 본문 JSON 을 제공한다.**

- 경로: `config.yaml::directories.bible_text_path` (기본 `data/bible/reference.json`),
  `core/config.py::BIBLE_TEXT_PATH` 로 노출.
- 스키마:
  ```json
  {
    "version": "개역개정",
    "books": {
      "PRO": {"name": "잠언", "chapters": [["1:1 본문", "1:2 본문", ...], ...]}
    }
  }
  ```
  - `books` 키 = book_id — **`core/retrieval.py::BOOK_ID_TO_NAMES` 공간** (아가 = `SOL`).
    `core/sermon/bible_books.py`(아가 = `SOT`)는 표시 전용이며 여기서 쓰지 않는다.
    소문자·영문 약어·한글 별칭도 로더가 정규 book_id 로 변환한다.
  - `chapters` = 장 배열(인덱스 = 장 − 1), 각 장 = 절 문자열 배열(인덱스 = 절 − 1).
  - 66권 전체가 아니어도 된다.
- 로더 `core/bible_text.py::load_bible_text()` 는 **fail-closed**: 파일이 없거나 스키마가
  어긋나면 예외 대신 `BibleText.unavailable(reason)` 을 반환하고, 뷰어는 안내만 표시한다.
- 이 계층은 **TSU / RetrievalEngine / 임베딩과 완전히 분리**된다. `core/retrieval.py` 와
  `core/generation.py` 는 `core/bible_text.py` 를 import 하지 않는다.

---

## 3. Authority Hierarchy & Retrieval

```
1순위: 지정된 성경 본문 (사용자가 뷰어로 선택)
2순위: 내서재 TSU 주석·신학 코퍼스 (RetrievalEngine 결과 중 본문 정합분)
```

- 검색은 **기존 `QueryProcessor.process()` 를 그대로 재사용**한다. 새 검색 경로·엔진
  인스턴스를 만들지 않는다(ADR-001, One Retrieval Engine). 세션 공유
  `ui/state/query_processor.get_shared_query_processor()` 사용.
- 정합 판정은 **기존 `core/retrieval.py::compute_passage_match_score()`** 재사용:
  후보 청크의 `verse_mapping` 이 지정 `ScriptureReference` 와 겹치는 점수를 계산.
  - `>= 0.5` (book_id 일치) 미만만 있으면 → `status = "no_material"` → 생성하지 않음.
  - 통과 후보를 점수 내림차순으로 정렬해 근거로 사용.

---

## 4. Integration Boundary (ADR-028 답습)

**`core/retrieval.py` · `core/generation.py` 의 공개 시그니처를 변경하지 않는다.**

- `retrieve_passage_commentary()` 가 받은 `ResponsePackage`(실제 `process()` 산출물)를
  그 자리에서 본문 해설용으로 수정한다:
  `question` = 지시문, `llm_context_block` = 번호형 `<자료>` 블록 + 한국어 가드 지시,
  `top_k_results` = 정합 후보, `citations` = `CitationBuilder().build_citations(정합후보)`.
- 그 `ResponsePackage` 를 `GenerationService.generate_stream()` 에 넘겨 스트리밍한다.
- 실패 격리: Ollama 실패 → `status = "gen_failed"`, `st.warning` 후 종료(기존 탭·검색
  무영향). 성경 JSON 없음/손상 → 뷰어가 안내만.

프롬프트 가드(핵심):
> "오직 <자료> 에 근거해 한국어로 해설하라. 각 주장 끝에 근거 자료 번호를 [1] 형식으로
> 표기한다. 자료에 없는 내용은 추측하거나 지어내지 않는다."

---

## 5. Render Contract (첨부 그림 대응)

- **본문 인라인 인용**: LLM 이 `[1]`, `[2]` 로 표기 → `render_answer_with_badges()` 가
  `1..N` 범위의 `[n]` 만 `①②③…` 로 치환(범위 밖 대괄호 숫자는 보존).
- **하단 "참고 자료 (내서재)"**: 각 정합 후보 + `Citation` → `FootnoteEntry` →
  `core/citation_format.py::format_footnote_line()` 로 `저자, *제목* (자료유형, 연도), 위치.`
  형태. 레지스트리에 없는 서지 필드(출판사·발행지 등)는 채우지 않는다.
  위치 = `structure.heading_path` 또는 `verse_mapping` 기반 "책 장:절".
- **원문 보기**: `st.button` → `sr_passage_detail_selection` 세션키 → 우측 컬럼에서
  `core/document_detail.get_document_detail()` + `ui/components/detail_panel.render_detail_panel()`
  (2단 레이아웃은 `ui/pages/chat.py::_render_chat_page_with_detail` 패턴).

---

## 6. 배치

`ui/pages/sermon_research.py::render_sermon_research_hub_page` 를 `st.tabs(["설교 연구",
"본문 해설"])` 로 나눈다. 기존 허브(담긴 자료 없으면 조기 종료)는 "설교 연구" 탭
안으로 옮기고, "본문 해설" 탭에서 `render_passage_commentary_tab()` 을 호출한다.
`page.render_header()` / `render_footer()` 는 탭 밖.

---

## 7. Risks

| 위험 | 완화 |
|---|---|
| book_id 공간 불일치(`SOT` vs `SOL`) | 뷰어·JSON·`ScriptureReference` 를 전부 `core.retrieval.BOOK_ID_TO_NAMES` 공간으로 통일. `verse_mapping.book_id` 는 `core/tsu_builder.py` 가 이 공간으로 만든다. |
| 자동 생성이 위젯 조작마다 Ollama 를 호출 | "본문을 바꾸면 자동으로 해설" 체크박스(기본 on) + 명시적 «해설 보기» 버튼. 이미 생성한 본문은 세션 캐시(`sr_passage_result`)로 재사용. |
| 정합 임계값이 너무 느슨/빡빡 | `_ALIGN_FLOOR` 상수(0.5) — 스모크로 조정. |
| 성경 JSON 미제공 | fail-closed — 탭이 안내만, 크래시 없음. |

---

## 8. Validation

```bash
python -m pytest tests/test_bible_text.py tests/test_passage_commentary.py \
  tests/test_citation_format.py -q
python -m pytest tests/test_bible_index.py tests/test_scripture_reference_stabilization.py \
  tests/test_nae_tsu_citation_scripture.py tests/test_bible_books.py -q
```

수동 E2E: `data/bible/reference.json`(잠언 8장 포함) 배치 → `streamlit run dbma_ui.py` →
"연구하기" → "본문 해설" 탭 → 잠언 8:10 선택 → 해설 스트리밍 + ①②③ + 각주 + "원문 보기"
확인. 코퍼스에 없는 본문 선택 → "관련 자료가 없습니다" 안내만.

---

## 9. Future

- 본문 선택 후 자유 추가 질문(follow-up).
- "AI에게 질문" / "설교 준비" 화면 연동.
- 번역본 다중 지원 UI.
