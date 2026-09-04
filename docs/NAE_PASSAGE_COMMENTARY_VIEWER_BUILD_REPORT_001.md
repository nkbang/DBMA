# NAE Passage Commentary Viewer — Build Report 001

**Project:** ADR-031 / NAE-PASSAGE-COMMENTARY-VIEWER-001
**Date:** 2026-09-04
**Nature:** 신규 기능 + 신규 데이터 계층(사용자 제공 성경 본문 JSON). Retrieval
Engine / Embedding / TSU Pipeline / 기존 ADR **무접촉**.
**ADR:** ADR-031 **Proposed** (승격 전 — C1 리뷰 + 사용자 승인 대기)

---

## 1. STATUS: 구현 완료 · 테스트 PASS · 회귀 PASS

"연구하기(설교 연구)" 화면에 **"본문 해설"** 탭을 추가했다. 성경뷰어에서 책/장/절을
지정하면, 그 본문과 정합하는 내서재 주석 자료를 근거로 한국어 해설을 생성하고
본문에 각주 번호(①②③) + 하단 참고 자료 서지 목록 + "원문 보기"(문서 상세 패널)를
붙인다. 내서재에 정합 자료가 없으면 안내만 표시하고 생성하지 않는다.

핵심 설계(ADR-028 답습):
- `core/retrieval.py` · `core/generation.py` **공개 시그니처 무변경**.
- 검색 = 기존 `QueryProcessor.process()` 재사용(세션 공유 인스턴스).
- 구절↔청크 정합 = 기존 `core/retrieval.py::compute_passage_match_score()` 재사용
  (`>= 0.5` book 일치 미만이면 `no_material`).
- 생성 = `process()` 가 돌려준 `ResponsePackage` 를 본문 해설용으로 그 자리에서
  수정 후 `GenerationService.generate_stream()` 스트리밍.

---

## 2. Changed Files

### 신규
| 파일 | 역할 |
|---|---|
| `core/bible_text.py` | 사용자 제공 성경 본문 JSON 로더(fail-closed). `BibleText` 조회 API. |
| `core/passage_commentary.py` | 검색→정합 필터→프롬프트/각주 조립→(비스트리밍) 생성. Streamlit 무의존. |
| `core/citation_format.py` | 각주 서지 한 줄 포맷 공용화(`format_footnote_line`, `extract_citation_year`). |
| `ui/components/passage_viewer.py` | 책→장→절 뷰어. 절 본문 표시. `ScriptureReference` 반환. |
| `ui/pages/_passage_commentary_tab.py` | 탭 오케스트레이션: 스트리밍 렌더, `[n]`→배지, 각주 목록, 원문 보기 2단 패널. |
| `docs/architecture/ADR-031-NAE-Passage-Commentary-Viewer.md` | 아키텍처 결정(Proposed). |
| `docs/NAE_BIBLE_TEXT_JSON_SPEC.md` | 성경 JSON 규격 + book_id 표. |
| `tests/test_bible_text.py` (25) · `tests/test_passage_commentary.py` (14) · `tests/test_citation_format.py` (13) | 단위 테스트. |

### 수정 (동작 보존 / 순수 추가)
| 파일 | 변경 |
|---|---|
| `core/config.py` | `BIBLE_TEXT_PATH` 추가(순수 추가). |
| `config.yaml` | `directories.bible_text_path` 한 줄. |
| `ui/pages/sermon_research.py` | 본문을 `st.tabs(["설교 연구","본문 해설"])` 로 분리. 기존 허브 로직은 `_render_hub_tab()` 로 그대로 이동(조기 종료 포함). |
| `ui/pages/research.py` | `_build_footnote_citation` 의 "최초 인용" 본문 조립을 `format_footnote_line()` 호출로 교체. **출력 문자열 동일**(parity 테스트로 고정). `_extract_citation_year` 는 공용 함수 재수출. |

### 런타임 데이터 (커밋 안 됨 — `.gitignore: data/`)
- `data/bible/reference.json` — 스키마 예시용 **PLACEHOLDER**(실제 번역본 아님).
  사용자가 자신의 성경 JSON 으로 교체한다.

---

## 3. Tests (실측)

```
dbma_env/bin/python -m pytest tests/test_bible_text.py tests/test_citation_format.py \
  tests/test_passage_commentary.py -q
→ 39 passed
```

- `test_bible_text`: 정상 로드 / 절 범위 / 카운트 / book_id 정규화 / 정경 순서 /
  fail-closed(파일 없음·깨진 JSON·스키마 불일치·빈 books) / 미가용 인스턴스 안전.
- `test_passage_commentary`: 정합 후보만 통과 / `no_material` 시 생성기 미호출 /
  검색 실패 격리 / 프롬프트에 본문표기·`[1]` 마커·"추측" 가드 포함 / 배지 치환 범위 /
  레지스트리 서지 보강 / gen_failed 매핑.
- `test_citation_format`: `format_footnote_line` 이 기존 research.py 출력과 대표 입력
  전부 문자열 일치.

### End-to-end (Streamlit AppTest, `dbma_env`)
- 탭 마운트: 검색/생성 미발동, 안내 캡션만. 예외 없음.
- 뷰어에서 본문 변경(요한복음 3:16): autorun → 실제 코퍼스 검색 → 정합 요한복음
  주석 8청크 → (가짜 생성기) 해설에 `[1][2]`→`①②`, 각주 8줄
  `① *5. 요한복음1.pdf* (주석, 2026), 신랑과그의친구.` 렌더.
- "원문 보기" 클릭 → 2단 레이아웃 + 문서 상세 패널 + "닫기". 예외 없음.
- 코퍼스에 없는 본문(잠언 8:10): "내서재에 … 자료가 없습니다" 안내만, 생성 없음.

---

## 4. Regression (실측)

```
dbma_env/bin/python -m pytest <관련 27개 파일: bible*/chat*/citation*/footnote*/
  generation*/nae_tsu_citation_scripture/registry*/research*/response_package_citations/
  retrieval_book_coverage/retrieval_missing_dataset/scripture*/sermon_research_hub/
  shared_query_processor …> -q
→ 290 passed, 0 failed
```

또한 `-k` 넓은 키워드 필터로 590 통과 / 1 실패:
`tests/test_p41_toggle_and_telemetry.py::test_toggle_changes_instance_identity`.
→ **이 실패는 사전 존재하는 테스트 격리 결함**이다. 해당 파일을 자연 순서로 단독
실행하면 13/13 PASS 이고, 신규 테스트와 함께(정·역순) 실행해도 52/52 PASS.
`_FakeLegacyProcessor._instances` / `_FakeHybridProcessor._instances` 가 서로 독립
카운터라서, 교차-수트 수집 순서가 바뀌면 첫 인스턴스 id 가 둘 다 1 이 되어
`assert 1 != 1` 로 깨진다. 이번 변경과 무관하며(해당 경로 무접촉), 관련 없는 파일이라
수정하지 않았다.

전체 코어 임포트(`ui.app` 포함) 정상.

---

## 5. Architecture / ADR

- Architecture Rule PASS: Retrieval Engine·Embedding·TSU Pipeline·기존 ADR·Production
  Registry 무접촉. 새 검색 경로/엔진 인스턴스 없음(ADR-001 준수).
- ADR Conflict 없음.
- ADR-031 은 **Proposed**. CUE 정책상 "새 Architecture Layer 추가"이므로
  **C1 독립 리뷰 + 사용자 승인** 후에만 Approved 승격. 승격 전까지 다른 구현의
  근거로 쓰지 않는다.

---

## 6. Git

- Commit: 완료 (feature 브랜치 `dev/dbma-engine`). 대상: 본 리포트의 신규/수정 파일만.
  사전 존재하던 무관 untracked 파일(`docs/agents/cue/*`, `.automation/*`)은 제외.
- Push: `origin dev/dbma-engine` (force/history-rewrite 아님).

---

## 7. Next

1. **C1 독립 리뷰 요청** (ADR-031 신규 Architecture Layer).
2. 사용자: 실제 성경 본문 JSON 을 `data/bible/reference.json` 에 배치
   (`docs/NAE_BIBLE_TEXT_JSON_SPEC.md`). PLACEHOLDER 교체.
3. 사용자 승인 시 ADR-031 Proposed → Approved 승격, STATE.md 갱신.
4. (v2) 본문 선택 후 자유 추가 질문(follow-up), "AI에게 질문"/"설교 준비" 연동.
5. `_ALIGN_FLOOR`(0.5) 임계값 실사용 튜닝.
