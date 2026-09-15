# 메타데이터 추출 결함 수정 Build Report 001

**작성일:** 2026-09-15
**대상:** `core/extractors.py::extract_text_from_file()`
**결과:** STATUS = 성공

---

## 1. 문제

registry·TSU의 `title`/`author`가 항상 `null`로 남아 인용 표기가 불가능했다
(`docs/DBMA_BASELINE_CORPUS_LOAD_REPORT_001.md` §5.1).

## 2. 근본 원인

`extract_text_from_file()`의 확장자 디스패치에서 **PDF와 DOCX에만** 메타데이터
추출 호출이 있었고 **EPUB·HTML 경로에는 그 호출이 아예 없었다.**

```python
elif ext == ".epub":
    text = extract_text_from_epub(path)      # title/author 추출 없음 → None 확정
elif ext in (".html", ".htm"):
    text = extract_text_from_html(path)      # 동일
```

상류가 `None`을 주므로 하류는 전부 정상 동작해도 결과가 비었다:

```
extract_text_from_file()  title=None ← 결함 지점
  → processing.py:466     extracted_title = raw_result.get("title")
  → DocumentContext.title = None
  → identity_registry.py:163  "title": metadata.get("title")  → null
  → tsu_builder.py:382        "title": doc.get("title")       → null
```

`tsu_builder`·`identity_registry`는 전달만 하고 있었다 — 수정 대상이 아니었다.

**증거:** 매튜 풀 EPUB은 `dc:title="매튜 풀 청교도 성경주석 14 : 마태복음"`,
`dc:creator="매튜 풀"`을 실제로 담고 있으나 파이프라인이 둘 다 버렸다.

## 3. 수정

`core/extractors.py`에 추출 함수 2개 추가 후 디스패치에 연결:

| 함수 | 읽는 값 |
|---|---|
| `_extract_epub_title_author()` | `dc:title` / `dc:creator` |
| `_extract_html_title_author()` | `<title>` / `<meta name="author">` |

보조 함수 `_first_dc_value()`가 ebooklib의 `[(값, 속성), ...]` 형태를 안전하게 처리한다.

**설계 원칙 유지 (SPRINT17-Phase5-C2 M2-a)** — 파일 자신의 내장 메타데이터만
읽는다. 파일명·본문 heading에서 추론하지 않는다. HTML도 `<h1>`이 아니라
문서가 선언한 `<title>`만 신뢰한다. 메타데이터가 없으면 `None`을 유지한다.

**txt/md/rtf는 수정 대상이 아니다** — 내장 메타데이터라는 것이 존재하지 않는
형식이므로 `None`이 정상이며, 결함이 아니다. docstring에 명시했다.

실패 시 예외를 올리지 않고 `(None, None)`으로 강등해 문서 처리 전체가 중단되지
않게 했다(기존 PDF/DOCX 경로와 동일한 방침).

## 4. 검증

### 단위·회귀 테스트

`tests/test_extractors_epub_html_metadata.py` 신규 8건 — 전부 PASS.

- EPUB 내장 title/author 추출
- **디스패치 통과 확인** (누락됐던 바로 그 지점)
- 메타데이터 없는 EPUB → 파일명 추론하지 않고 `None`
- 깨진 EPUB → 예외 없이 `(None, None)`
- HTML `<title>`/`<meta author>` 추출, `<h1>` 무시
- txt/md는 여전히 `None`

### 파이프라인 전 구간 (실데이터)

매튜 풀 EPUB을 스크래치 출력 디렉터리로 처리 — **프로덕션 코퍼스 무변경**.

| 필드 | 수정 전 | 수정 후 |
|---|---|---|
| `title` | `null` | `매튜 풀 청교도 성경주석 14 : 마태복음` |
| `author` | `null` | `매튜 풀` |
| `doc_type` | `기타` | **`주석`** |

**부수 효과 — `doc_type` 오분류도 함께 해소되었다.** `guess_doc_type()`이
`extracted_title`을 입력으로 받기 때문에, title이 비어 있던 것이 오분류의
원인 중 하나였다(`BASELINE_CORPUS_LOAD_REPORT_001` §5.2의 일부가 같은 결함).

### 회귀

```
pytest -k "extract or processing or metadata or registry or tsu_builder or doc_type"
→ 466 passed, 2 failed
```

실패 2건은 **수정 전에도 동일하게 실패**함을 `git stash` 대조로 확인 —
본 변경과 무관하다. 원인은 `NAE/corpus/raw/`가 `.gitignore` 대상이라
`Spurgeon_TreasuryOfDavid_Vol1/hocr.html` 등 일부 원본이 이 머신에 부재한 것
(`tests/test_m2_source_registry_governance.py`).

---

## 5. 남은 범위 — 현재 기본 코퍼스

현재 적재된 스펄전 4종은 `.txt`(archive.org OCR 텍스트)라 내장 메타데이터가
없어 **여전히 title/author가 비어 있다.** 본 수정의 결함 범위 밖이다.

다만 같은 자료의 **원본 PDF에는 실제 메타데이터가 있다**:

| 자료 | PDF `title` | PDF `author` |
|---|---|---|
| MTP Vol01 | The Metropolitan Tabernacle Pulpit | Charles Haddon Spurgeon |
| Lectures | Lectures to my students : being addresses… | Spurgeon, C. H. (Charles Haddon), 1834-1892 |
| Till He Come | Till he come : communion meditations and addresses | Spurgeon, C. H. (Charles Haddon), 1834-1892 |

선택지:

- **(A) 원본 PDF에서 재적재** — 실제 메타데이터 확보. 다만 44MB 스캔본이라
  처리 시간이 늘고, 추출 텍스트 품질이 archive.org OCR보다 나을지는 실측 필요.
- **(B) 사이드카 메타데이터 지원 추가** (`<파일명>.meta.json`) — 텍스트 품질을
  유지하면서 메타데이터를 붙일 수 있으나, **새 메타데이터 소스 도입이므로
  CLAUDE.md §C1 Review 시점("Metadata Model 변경")에 해당** — 선행 승인 필요.
- **(C) 현행 유지** — 기본 코퍼스는 출처가 파일명으로 식별되는 수준에서 보류.

HQ 결정 사항이며 본 작업 범위에 포함하지 않았다.

---

## 6. 기록

```
STATUS:      성공
Changed:     core/extractors.py (+2 추출 함수, 디스패치 2줄, docstring)
             tests/test_extractors_epub_html_metadata.py (신규 8건)
Tests:       8 passed
Regression:  466 passed / 2 failed (사전 존재, git stash 대조 확인)
Architecture: ADR-001 무위반 — 검색 경로·Retrieval Engine 무변경
             Metadata Model 무변경 — 기존 정의 필드를 채우기만 함
Git:         commit + push (dev/dbma-engine)
Next:        §5 선택지 HQ 결정
```
