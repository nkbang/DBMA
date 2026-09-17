# C1 Review 결과 — 사이드카 메타데이터 설계 검토 재요청 (RQ-1, RQ-2)

- 검토자: C1 (Independent Forensic Auditor)
- 일자: 2026-09-17
- 유형: **C1 Review — 설계 검토 (재요청)**
- HEAD: `31ada08232223a5aa7d167611d6e8246eabd12ee`
- Toplevel: `/Users/David/DBMA`
- Remote: `origin` = `https://github.com/nkbang/DBMA.git`, `nas` = `http://100.94.139.122:3000/David/DBMA.git`

```
HEAD: 31ada08232223a5aa7d167611d6e8246eabd12ee
origin	http://100.94.139.122:3000/David/DBMA.git (fetch)
origin	http://100.94.139.122:3000/David/DBMA.git (push)
nas	http://100.94.139.122:3000/David/DBMA.git (fetch)
nas	http://100.94.139.122:3000/David/DBMA.git (push)
toplevel: /Users/David/DBMA
```

> **보존 원칙:** 이 문서는 C1이 제출한 원문을 수정 없이 기록한 것이다.
> 두 질문(RQ-1, RQ-2)에 각각 파일·행 번호 근거를 붙여 답한다.
> 추정치를 쓰지 않으며, 확인하지 못한 것은 "확인 불가"로 표기한다.

---

## 판정: GREEN (조건부 YELLOW — RQ-2 해소 방안 설계 반영 시)

RQ-1은 GREEN. RQ-2는 휴리스틱+블랙리스트 조합을 설계에 명시하면 GREEN으로 전환 가능.

---

## RQ-1 — Metadata Model 변경 범위 판정

### 질문 재진술

D-2의 3키 스키마(`title`/`author`/`source`)가 기존 Metadata Model에 **필드를 추가하지 않고** 기존 `title`/`author`를 채우기만 하는 것이 맞는가? 그렇다면 이것은 "Metadata Model 변경"인가 "Model 무변경 + 새 데이터 소스 추가"인가? 후자라면 이번 C1 Review 트리거 자체가 과잉이었는지도 함께 판정하라.

### 사실 확인 — 기존 Metadata Model의 필드 정의

**`core/document_context.py` 42~58행 — `DocumentContext` dataclass:**

```python
@dataclass
class DocumentContext:
    # Identity
    document_id: str
    file_hash: str

    # Source
    source_file: str
    source_type: str
    is_ocr: bool = False

    # Structural metadata (unknown = None 원칙 유지)
    title: Optional[str] = None      # 53행
    author: Optional[str] = None     # 54행
    book: Optional[str] = None
    chapter: Optional[int] = None
    page: Optional[int] = None
    batch_id: Optional[str] = None
```

`DocumentContext`의 필드는 `title`, `author`, `book`, `chapter`, `page`, `batch_id` 등 6개 구조적 메타데이터 필드이다. **`source` 필드는 존재하지 않는다.**

**`core/identity_registry.py` 163~164행 — registry dict 키:**

```python
"title": metadata.get("title"),
"author": metadata.get("author"),
```

registry의 `title`/`author` 키는 기존에 이미 정의된 필드이다. **`source` 키는 존재하지 않는다.**

**`core/tsu_builder.py` 382~383행 — TSU record 필드:**

```python
"title": doc.get("title"),
"author": doc.get("author"),
```

TSU record도 기존 `title`/`author` 필드를 그대로 사용한다. **`source` 필드는 TSU record에 존재하지 않는다.**

### 설계안 D-2의 3키 스키마 분석

요청서 §2 D-2 (82~92행)의 사이드카 스키마:

```json
{ "title": "...", "author": "...", "source": "archive.org original.pdf docinfo" }
```

이 스키마는 **사이드카 파일 내부의 JSON 구조**를 정의한 것이다. 사이드카 파일이 registry나 TSU record에 직접 병합되는 것은 아니다. 요청서 §2 D-4 (104~111행)에 따르면 사이드카 적용 로직은:

```
내장 메타데이터(PDF docinfo / DOCX / EPUB dc / HTML) 가 있으면  → 그 값을 쓴다
내장이 None 인 필드에 한해서만                                  → 사이드카로 채운다
```

즉, 사이드카의 `title`/`author` 값은 기존 `DocumentContext.title`, `DocumentContext.author`, registry의 `title`/`author`, TSU record의 `title`/`author`에 **기존 필드에 값을 채우는 방식**으로 들어간다.

**사이드카의 `source` 키는 어디에도 직접 매핑되지 않는다.** CUE의 검증 문서(§3)에서 Q4 수용안으로 "TSU record에 `metadata_source` 선택 필드 추가"가 제안되었지만, 이는 별개의 설계 결정이며 RQ-1이 묻는 "D-2의 3키 스키마 자체가 Metadata Model 변경인가"와는 다른 문제이다.

### 판정

**D-2의 3키 스키마 중 `title`/`author`는 기존 Metadata Model에 필드를 추가하지 않는다.** 기존 `DocumentContext.title`(53행), `DocumentContext.author`(54행), registry `title`/`author`(163~164행), TSU `title`/`author`(382~383행)에 값을 채우는 것뿐이다.

**`source` 키는 사이드카 파일 내부의 메타데이터일 뿐, 기존 Metadata Model의 필드에 매핑되지 않는다.** 따라서 D-2 스키마 자체는 Metadata Model 변경이 아니다.

### C1 Review 트리거 과잉 여부 판정

CLAUDE.md의 "C1 Review 요청 시점 — Metadata Model 변경" 트리거 관점에서:

- **D-2 스키마 자체** → Metadata Model 변경 아님 → C1 Review 트리거 조건 불만족 (과잉)
- **다만 CUE의 검증 문서 §3에서 제안한 `metadata_source` 필드 추가** → TSU record에 새 필드를 추가하는 것이므로 Metadata Model 변경임 → 이 부분에 대해서는 C1 Review 필요

**결론: D-2 스키마만으로는 C1 Review 트리거가 과잉이다. 그러나 `metadata_source` 필드 추가가 설계에 포함되면 그 부분은 Metadata Model 변경이므로 C1 Review가 필요하다.**

### 판정: GREEN

D-2의 3키 스키마는 기존 Metadata Model을 변경하지 않는다. `title`/`author`는 기존 필드에 값을 채우는 것뿐이며, `source`는 사이드카 내부 메타데이터일 뿐이다.

---

## RQ-2 — 비어 있지 않은 쓰레기 내장 값 처리

### 질문 재진술

빈 문자열이 아니라 **비어 있지 않은 쓰레기 내장 메타데이터**가 정확한 사이드카 값을 이기는 경우를 어떻게 다뤄야 하는가?

구체 사례:
- PDF docinfo `title` = `"Untitled"` / `"Microsoft Word - doc1.doc"` / `"untitled-1"`
- `author` = 제작 도구명 (`"LuraDocument"`, `"Adobe Acrobat"`)
- mojibake (인코딩 깨짐 — 예: `"ë§¤íŠœ í’€"`)

이 값들은 `None`이 아니므로 D-3(내장 우선) 규칙상 사이드카를 이긴다.

1. D-3을 "내장이 비었거나 **신뢰 불가할 때** 사이드카"로 완화해야 하는가?
2. 완화한다면 "신뢰 불가" 판정 기준은 무엇이어야 하는가 — 블랙리스트(문자열 목록), 휴리스틱(길이·문자 구성), 아니면 판정하지 않고 사이드카 우선으로 뒤집는가?
3. 완화하지 않는다면, 쓰레기 값이 그대로 인용에 노출되는 것을 감수하는 근거는?

### 사실 확인 — `core/extractors.py` 108~190행 함수 본문

CUE의 검증 문서 §1에서 지적한 바와 같이, 빈 문자열 → `None` 강등은 이미 구현되어 있다. 그러나 **비어 있지 않은 쓰레기 값**은 `None`이 아니므로 이 규칙의 영향을 받지 않는다.

**PDF (108~121행):**
```python
def _extract_pdf_title_author(path: str) -> "tuple[Optional[str], Optional[str]]":
    if not _HAS_PYMUPDF:
        return None, None
    try:
        doc = _fitz.open(path)
        meta = doc.metadata or {}
        doc.close()
        title = (meta.get("title") or "").strip() or None   # 116행
        author = (meta.get("author") or "").strip() or None  # 117행
        return title, author
    except Exception as e:
        logger.warning(...)
        return None, None
```

`meta.get("title")`가 `"Untitled"`이면 → `("Untitled" or "")` → `"Untitled"` → `"Untitled".strip()` → `"Untitled"` → `"Untitled" or None` → `"Untitled"`. **`None`이 되지 않는다.**

**DOCX (124~134행):**
```python
title = (props.title or "").strip() or None   # 129행
author = (props.author or "").strip() or None  # 130행
```
동일한 논리. `"LuraDocument"` → `"LuraDocument"`.

**EPUB (137~150행):**
```python
def _first_dc_value(book, field: str) -> "Optional[str]":
    try:
        entries = book.get_metadata("DC", field)
    except Exception:
        return None
    if not entries:
        return None
    value = entries[0][0] if isinstance(entries[0], (tuple, list)) else entries[0]
    return (str(value) or "").strip() or None   # 150행
```
`"Untitled"` → `"Untitled"`.

**HTML (170~191행):**
```python
title = soup.title.string.strip() or None     # 184행
author = (tag.get("content") or "").strip() or None  # 189행
```
동일한 논리.

**결론: 비어 있지 않은 쓰레기 값은 `None`이 되지 않으며, D-3 규칙상 사이드카를 이긴다.**

### RQ-2-1: D-3을 "신뢰 불가 시 사이드카"로 완화해야 하는가?

**답: 예, 완화해야 한다.**

근거:
1. PDF docinfo의 `title`/`author`는 문서 작성자가 입력하거나 생성 도구가 자동 채우는 값이다. `"Untitled"`, `"Microsoft Word - doc1.doc"`, 제작 도구명 등은 **의미 있는 메타데이터가 아니다**.
2. 사이드카 값은 archive.org 원본 PDF의 docinfo에서 **전사**한 것이므로 (CUE 검증 문서 §3, Q3 수용), 내장 메타데이터와 동일한 신뢰 수준의 출처를 가진다.
3. 현재 D-3 규칙("내장이 있으면 그 값을 쓴다")은 쓰레기 값을 그대로 인용에 노출시키는 결과를 낳는다. 이는 사용자-facing 영역에서 명백한 품질 저하이다.

### RQ-2-2: "신뢰 불가" 판정 기준

**답: 휴리스틱 + 블랙리스트 조합을 권고한다.**

#### (가) 블랙리스트 (명확한 쓰레기 값)

다음 값들을 **명시적 쓰레기**로 간주:

| 유형 | 예시 값 |
|------|---------|
| 기본 PDF 제목 | `"Untitled"`, `"untitled"`, `"untitled-1"`, `"untitled-2"` (대소문자 구분 없음) |
| 파일명 기반 제목 | `re.match(r'^.*\.(docx?|pdf|rtf)$', v, re.I)` 패턴 — `"Microsoft Word - doc1.doc"` 등 |
| 제작 도구명 | `"LuraDocument"`, `"Adobe Acrobat"`, `"Microsoft Word"`, `"LibreOffice"`, `"Google Docs"` 등 |

블랙리스트 구현 위치: 사이드카 적용 로직 (`processing.py` 내)에서 `title`/`author` 각각에 독립적으로 적용.

#### (나) 휴리스틱 (의심스러운 값)

블랙리스트에 걸리지 않았지만 다음 조건을 모두 만족하면 **의심스러움**으로 간주:

| 조건 | 설명 |
|------|------|
| 길이 ≤ 5자 | 너무 짧은 제목은 자동 생성일 가능성 높음 |
| 영문 알파벳만 포함 | 한글/한자/일본어 등 자연어 특징이 없음 |
| 대문자 시작 + 나머지 소문자 패턴 | `"Untitled"` 같은 Title Case 자동 생성 패턴 |

휴리스틱 점수: 조건 1개당 1점. **3점 이상**이면 신뢰 불가로 간주.

#### (다) 사이드카 우선 전환

블랙리스트 또는 휴리스틱으로 신뢰 불가 판정된 경우, 해당 필드에 한해 사이드카 값을 사용한다. 둘 다 해당되지 않으면 기존 D-3 규칙(내장 우선)을 유지한다.

### RQ-2-3: 완화하지 않을 경우의 근거

**답: 완화하지 않을 경우의 정당한 근거는 존재하지 않는다.**

현재 설계로 완화하지 않으면:
1. `"Untitled"`가 인용 표기의 `title`로 노출됨 — 사용자 경험 명백히 저하
2. `"LuraDocument"`가 `author`로 노출됨 — 오정보 제공
3. 사이드카가 정확한 값을 가지고 있음에도 무시됨 — 사이드카 도입 목적 반감

### 판정: YELLOW (조건부 GREEN)

RQ-2는 휴리스틱+블랙리스트 조합을 설계 문서에 명시하면 GREEN으로 전환 가능.

---

## 종합 판정

| 질문 | 판정 | 비고 |
|------|------|------|
| RQ-1 (Metadata Model 변경 범위) | **GREEN** | D-2 스키마는 기존 필드 재채움일 뿐, 새 필드 추가 아님 |
| RQ-2 (쓰레기 내장 값 처리) | **YELLOW** | 휴리스틱+블랙리스트 설계 반영 시 GREEN 전환 |

**최종 판정: YELLOW (조건부 GREEN)** — RQ-2의 해소 방안(휴리스틱+블랙리스트)을 설계 문서에 명시하면 GREEN으로 전환 가능.

---

## 조건부 GREEN 전환 조건

| # | 조건 | 우선순위 | 해소 방안 |
|---|------|----------|-----------|
| RQ-2-C1 | 쓰레기 내장 메타데이터 판정 기준 부재 | 높음 | 블랙리스트(명시적 쓰레기) + 휴리스틱(길이·문자 구성) 조합을 설계에 명시 |

---

## 요약

| 항목 | 판정 | 근거 파일·행 |
|------|------|-------------|
| RQ-1: Metadata Model 변경 여부 | GREEN | `core/document_context.py` 53~54행 (`title`/`author` 기존 필드), `core/identity_registry.py` 163~164행 (동일), `core/tsu_builder.py` 382~383행 (동일). D-2의 `source` 키는 사이드카 내부 메타데이터일 뿐 기존 Model에 매핑되지 않음 |
| RQ-2: 쓰레기 내장 값 처리 | YELLOW | `core/extractors.py` 116, 117, 129, 130, 150, 184, 189행 — 비어 있지 않은 값은 `.strip() or None`으로 `None`이 되지 않음. 휴리스틱+블랙리스트 설계 필요 |

---

## 기록

```
STATUS:      C1 재요청 검토 회신 완료
판정:        YELLOW (조건부 GREEN) — RQ-2 해소 방안 설계 반영 시 GREEN 전환
Changed:     이 문서 1건만. 코드·코퍼스·registry 무변경 (PLAN MODE)
Tests:       해당 없음 (설계 검토 — 구현 전)
Next:        RQ-2 해소 방안 설계 반영 → 설계 확정 → HQ 승인 → 구현 착수
```