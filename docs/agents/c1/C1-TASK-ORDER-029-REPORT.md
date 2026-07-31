# C1 Task Order 029 — 검색 결과 상세보기 Phase 1: document_detail API

**상태**: 완료
**완료일**: 2026-07-29
**우선순위**: P1

---

## 1. 수정 파일 diff

### core/document_detail.py (신규)

```python
"""core/document_detail.py — Document Detail Retrieval Module.

Provides get_document_detail() which loads registry metadata, reads the
corresponding full-text file, and computes match locations for query terms.

Three distinct error cases:
  1. "레지스트리를 찾을 수 없습니다" — registry 파일 자체가 없음
  2. "문서 레코드를 찾을 수 없습니다" — registry에 레코드 없음
  3. "원본 문서 파일을 찾을 수 없습니다 (이동 또는 삭제됨)" — md 파일 없음
  4. "본문을 읽는 중 오류가 발생했습니다" — 읽기 실패 또는 OCR 판정

Usage:
    from core.document_detail import get_document_detail

    detail = get_document_detail(
        source_file="7. 사도행전1_pdf",
        document_id="doc-12345",
        query_terms=["사도", "행전"],
    )
    if detail.error is None:
        print(detail.full_text[:200])
    else:
        print(f"error: {detail.error}")
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from core.config import DEFAULT_OUTPUT_DIR, DEFAULT_REGISTRY_PATH
from core.identity_registry import (
    load_identity_registry,
    find_by_document_id,
    find_by_source_file,
)


@dataclass
class MatchLocation:
    """full_text 내 검색어 일치 위치."""
    char_start: int
    char_end: int


@dataclass
class DocumentDetail:
    """검색 결과 상세 정보."""
    document_id: str
    title: str | None
    document_type: str | None       # registry의 doc_type
    source_path: str                 # 사용자에게 보여줄 경로 문자열 (실행 트리거 아님, 텍스트만)
    author: str | None
    created_at: str | None
    tags: list[str] = field(default_factory=list)
    full_text: str = ""
    match_locations: list[MatchLocation] = field(default_factory=list)
    error: str | None = None         # 아래 네 가지 실패 케이스만 채움, 그 외엔 None


def get_document_detail(
    source_file: str,
    document_id: str,
    query_terms: list[str],
    registry_path: str | None = None,
    output_dir: str | None = None,
) -> DocumentDetail:
    """문서 상세 정보를 로드한다.

    1. registry_path가 없으면 core.config.DEFAULT_REGISTRY_PATH 사용,
       output_dir 없으면 core.config.DEFAULT_OUTPUT_DIR 사용.
    2. load_identity_registry(registry_path)로 로드 (파일 없으면 error="레지스트리를 찾을 수
        없습니다" 넣고 나머지 필드는 빈 값으로 반환 - 예외를 던지지 않음).
    3. document_id가 있으면 find_by_document_id, 없으면 find_by_source_file로 레코드 조회.
        못 찾으면 error="문서 레코드를 찾을 수 없습니다".
    4. 레코드에서 title/author/doc_type/created_at/book/chapter 추출.
    5. {output_dir}/{stem}_{ext}.md 경로 계산 후 존재 확인. 없으면
        error="원본 문서 파일을 찾을 수 없습니다 (이동 또는 삭제됨)" - 메타데이터는 채우되 full_text는 빈 문자열.
    6. 파일 읽고 full_text에 담는다. UnicodeDecodeError 등 읽기 실패 시
        error="본문을 읽는 중 오류가 발생했습니다" (구체적 예외 메시지는 로그에만, 사용자 메시지는 고정 문구).
    7. query_terms 각각에 대해 full_text에서 첫 등장 위치를 찾아 match_locations에 추가
        (str.find() 기반 단순 탐색으로 충분 - 정규식/형태소 분석 불필요, 여러 검색어 중 문서 내
        가장 이른 위치 하나만 필요하면 그것만 남겨도 됨 - 구현 시 판단해서 문서화).
    8. 위 모든 단계에서 error가 하나도 안 채워졌으면 error=None으로 정상 반환.

    OCR 판정: registry의 is_ocr=True인데 full_text가 50자 미만이면 간이 판정.
    완벽한 탐지는 아니므로 이 제한 사항을 docstring에 명시한다.
    """
    # defaults
    if registry_path is None:
        registry_path = DEFAULT_REGISTRY_PATH
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    # Step 0: 기본 DocumentDetail 생성
    detail = DocumentDetail(
        document_id=document_id,
        title=None,
        document_type=None,
        source_path="",
        author=None,
        created_at=None,
        tags=[],
        full_text="",
        match_locations=[],
        error=None,
    )

    # Step 1: registry 로드
    if not os.path.exists(registry_path):
        detail.error = "레지스트리를 찾을 수 없습니다"
        return detail

    registry = load_identity_registry(registry_path)

    # Step 2: 레코드 조회
    record: dict | None = None
    if document_id:
        record = find_by_document_id(registry, document_id)
    if record is None and source_file:
        record = find_by_source_file(registry, source_file)

    if record is None:
        detail.error = "문서 레코드를 찾을 수 없습니다"
        return detail

    # Step 3: 메타데이터 추출
    detail.title = record.get("title")
    detail.author = record.get("author")
    detail.document_type = record.get("doc_type")
    detail.created_at = record.get("created_at")
    detail.source_path = record.get("source_file", "")

    # tags: book/chapter 있으면 최소 태그 채움
    book = record.get("book")
    chapter = record.get("chapter")
    if book is not None and chapter is not None:
        detail.tags.append(f"book:{chapter}")

    # Step 4: 본문 파일 경로 계산
    sf = source_file or ""
    stem = Path(sf).stem
    ext = Path(sf).suffix.lstrip(".") if Path(sf).suffix else "md"
    text_filename = f"{stem}_{ext}.md"
    text_path = os.path.join(str(output_dir), text_filename)

    if not os.path.exists(text_path):
        detail.error = "원본 문서 파일을 찾을 수 없습니다 (이동 또는 삭제됨)"
        return detail

    # Step 5: 본문 읽기
    try:
        with open(text_path, "r", encoding="utf-8") as f:
            detail.full_text = f.read()
    except UnicodeDecodeError:
        detail.error = "본문을 읽는 중 오류가 발생했습니다"
        return detail
    except OSError:
        detail.error = "본문을 읽는 중 오류가 발생했습니다"
        return detail

    # OCR 간이 판정: is_ocr=True이고 full_text가 50자 미만
    is_ocr = record.get("is_ocr", False)
    if is_ocr and len(detail.full_text) < 50:
        detail.error = "본문을 읽는 중 오류가 발생했습니다"
        return detail

    # Step 6: match_locations 계산
    if query_terms and detail.full_text:
        earliest_loc: MatchLocation | None = None
        for term in query_terms:
            idx = detail.full_text.find(term)
            if idx != -1:
                loc = MatchLocation(char_start=idx, char_end=idx + len(term))
                if earliest_loc is None or idx < earliest_loc.char_start:
                    earliest_loc = loc
        if earliest_loc is not None:
            detail.match_locations = [earliest_loc]

    return detail
```

### tests/test_document_detail.py (신규)

```python
"""tests/test_document_detail.py — Unit tests for core/document_detail.py.

7 test cases per C1-TASK-ORDER-029 §3:
  1. 정상 케이스: registry에 레코드 있고 md 파일도 있음
  2. 레지스트리 자체가 없는 경우
  3. 레지스트리엔 있는데 document_id/source_file로 못 찾는 경우
  4. 레코드는 있는데 md 파일이 없는 경우(이동/삭제 시뮬레이션)
  5. is_ocr=True이고 본문이 비정상적으로 짧은 경우
  6. query_terms가 본문에 존재
  7. query_terms가 본문에 없음
"""

import json
import os
import tempfile
import textwrap
from pathlib import Path

import pytest

from core.document_detail import (
    DocumentDetail,
    MatchLocation,
    get_document_detail,
)


# ── Fixtures ────────────────────────────────────────────────

def _make_registry(tmpdir: str, documents: dict | None = None) -> str:
    """임시 registry 파일을 만들고 경로를 반환."""
    reg_dir = os.path.join(tmpdir, "registry")
    os.makedirs(reg_dir, exist_ok=True)
    reg_path = os.path.join(reg_dir, "documents.json")
    data = documents or {"schema_version": "2.0", "documents": {}}
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return reg_path


def _make_text_file(tmpdir: str, source_file: str, content: str) -> str:
    """임시 본문 파일을 만들고 경로를 반환."""
    sf = source_file or ""
    stem = Path(sf).stem
    ext = Path(sf).suffix.lstrip(".") if Path(sf).suffix else "md"
    filename = f"{stem}_{ext}.md"
    path = os.path.join(tmpdir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ── Test 1: 정상 케이스 ─────────────────────────────────────

def test_01_normal_case():
    """정상 케이스: registry에 레코드 있고 md 파일도 있음 → error is None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = _make_registry(tmpdir, documents={
            "schema_version": "2.0",
            "documents": {
                "doc-001": {
                    "document_id": "doc-001",
                    "source_file": "test_doc_pdf",
                    "title": "테스트 문서",
                    "author": "저자명",
                    "doc_type": "sermon",
                    "created_at": "2026-01-01T00:00:00",
                    "book": "시편",
                    "chapter": 23,
                    "page": None,
                    "is_ocr": False,
                }
            },
        })
        _make_text_file(tmpdir, "test_doc_pdf", "다윗이 말하기를 여호와는 나의 목자시니 내가 부족함이 없으리로다")

        detail = get_document_detail(
            source_file="test_doc_pdf",
            document_id="doc-001",
            query_terms=["목자"],
            registry_path=reg_path,
            output_dir=tmpdir,
        )

        assert detail.error is None
        assert detail.document_id == "doc-001"
        assert detail.title == "테스트 문서"
        assert detail.author == "저자명"
        assert detail.document_type == "sermon"
        assert detail.created_at == "2026-01-01T00:00:00"
        assert "book:23" in detail.tags
        assert detail.full_text == "다윗이 말하기를 여호와는 나의 목자시니 내가 부족함이 없으리로다"
        assert len(detail.match_locations) == 1
        # "목자" is at index 17 in "다윗이 말하기를 여호와는 나의 목자시니 내가 부족함이 없으리로다"
        assert detail.match_locations[0].char_start == 17
        assert detail.match_locations[0].char_end == 19


# ── Test 2: 레지스트리 자체가 없는 경우 ─────────────────────

def test_02_registry_not_found():
    """레지스트리 자체가 없는 경우 → error 메시지, 예외 발생 안 함."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_reg = os.path.join(tmpdir, "nonexistent_registry.json")

        detail = get_document_detail(
            source_file="test_doc_pdf",
            document_id="doc-001",
            query_terms=["테스트"],
            registry_path=fake_reg,
            output_dir=tmpdir,
        )

        assert detail.error == "레지스트리를 찾을 수 없습니다"
        assert detail.document_id == "doc-001"
        assert detail.title is None
        assert detail.full_text == ""


# ── Test 3: 레지스트리엔 있는데 document_id/source_file로 못 찾는 경우 ──

def test_03_record_not_found():
    """레지스트리엔 있는데 document_id/source_file로 못 찾는 경우 → error 메시지."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = _make_registry(tmpdir, documents={
            "schema_version": "2.0",
            "documents": {
                "doc-999": {
                    "document_id": "doc-999",
                    "source_file": "other_doc_pdf",
                    "title": "다른 문서",
                    "author": None,
                    "doc_type": None,
                    "created_at": None,
                    "is_ocr": False,
                }
            },
        })
        _make_text_file(tmpdir, "test_doc_pdf", "본문 내용")

        detail = get_document_detail(
            source_file="test_doc_pdf",
            document_id="doc-001",
            query_terms=["테스트"],
            registry_path=reg_path,
            output_dir=tmpdir,
        )

        assert detail.error == "문서 레코드를 찾을 수 없습니다"
        assert detail.document_id == "doc-001"


# ── Test 4: 레코드는 있는데 md 파일이 없는 경우 ─────────────

def test_04_file_not_found():
    """레코드는 있는데 md 파일이 없는 경우 → error 메시지, 메타데이터는 채워짐."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = _make_registry(tmpdir, documents={
            "schema_version": "2.0",
            "documents": {
                "doc-001": {
                    "document_id": "doc-001",
                    "source_file": "test_doc_pdf",
                    "title": "테스트 문서",
                    "author": "저자명",
                    "doc_type": "sermon",
                    "created_at": "2026-01-01T00:00:00",
                    "is_ocr": False,
                }
            },
        })
        # md 파일을 만들지 않음 — 파일 없음 시뮬레이션

        detail = get_document_detail(
            source_file="test_doc_pdf",
            document_id="doc-001",
            query_terms=["테스트"],
            registry_path=reg_path,
            output_dir=tmpdir,
        )

        assert detail.error == "원본 문서 파일을 찾을 수 없습니다 (이동 또는 삭제됨)"
        assert detail.title == "테스트 문서"
        assert detail.author == "저자명"
        assert detail.document_type == "sermon"
        assert detail.full_text == ""


# ── Test 5: is_ocr=True이고 본문이 비정상적으로 짧은 경우 ──

def test_05_ocr_failure():
    """is_ocr=True이고 본문이 50자 미만 → OCR 실패 판정."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = _make_registry(tmpdir, documents={
            "schema_version": "2.0",
            "documents": {
                "doc-ocr-001": {
                    "document_id": "doc-ocr-001",
                    "source_file": "ocr_doc_pdf",
                    "title": "OCR 문서",
                    "author": None,
                    "doc_type": "pdf",
                    "created_at": None,
                    "is_ocr": True,
                }
            },
        })
        # 50자 미만 본문
        _make_text_file(tmpdir, "ocr_doc_pdf", "짧은 텍스트")

        detail = get_document_detail(
            source_file="ocr_doc_pdf",
            document_id="doc-ocr-001",
            query_terms=[],
            registry_path=reg_path,
            output_dir=tmpdir,
        )

        assert detail.error == "본문을 읽는 중 오류가 발생했습니다"


# ── Test 6: query_terms가 본문에 존재 ──────────────────────

def test_06_query_terms_found():
    """query_terms가 본문에 존재 → match_locations에 정확한 char_start/char_end."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = _make_registry(tmpdir, documents={
            "schema_version": "2.0",
            "documents": {
                "doc-001": {
                    "document_id": "doc-001",
                    "source_file": "match_test_pdf",
                    "title": None,
                    "author": None,
                    "doc_type": None,
                    "created_at": None,
                    "is_ocr": False,
                }
            },
        })
        _make_text_file(tmpdir, "match_test_pdf", "첫 번째 문장. 두 번째 문장에 검색어가 들어갑니다.")

        detail = get_document_detail(
            source_file="match_test_pdf",
            document_id="doc-001",
            query_terms=["두 번째", "검색어"],
            registry_path=reg_path,
            output_dir=tmpdir,
        )

        assert detail.error is None
        assert len(detail.match_locations) == 1
        # "두 번째"가 더 이른 위치 (idx=9)
        assert detail.match_locations[0].char_start == 9
        assert detail.match_locations[0].char_end == 13


# ── Test 7: query_terms가 본문에 없음 ─────────────────────

def test_07_query_terms_not_found():
    """query_terms가 본문에 없음 → match_locations 빈 리스트, error는 None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = _make_registry(tmpdir, documents={
            "schema_version": "2.0",
            "documents": {
                "doc-001": {
                    "document_id": "doc-001",
                    "source_file": "nomatch_pdf",
                    "title": None,
                    "author": None,
                    "doc_type": None,
                    "created_at": None,
                    "is_ocr": False,
                }
            },
        })
        _make_text_file(tmpdir, "nomatch_pdf", "이 문서에는 검색어가 없습니다.")

        detail = get_document_detail(
            source_file="nomatch_pdf",
            document_id="doc-001",
            query_terms=["존재하지않는단어"],
            registry_path=reg_path,
            output_dir=tmpdir,
        )

        assert detail.error is None
        assert detail.match_locations == []


# ── Test 8: find_by_document_id / find_by_source_file 재구현 확인 ──

def test_08_no_reimplementation():
    """grep으로 find_by_document_id / find_by_source_file / load_identity_registry가
    import해서 썼는지 확인 (재구현 금지)."""
    source_path = Path(__file__).parent.parent / "core" / "document_detail.py"
    source_text = source_path.read_text(encoding="utf-8")

    # import 문에 반드시 포함되어야 함
    assert "from core.identity_registry import" in source_text
    assert "find_by_document_id" in source_text
    assert "find_by_source_file" in source_text
    assert "load_identity_registry" in source_text

    # 재구현 금지: def find_by_document_id:, def find_by_source_file:, def load_identity_registry: 가
    # 이 파일 내에 함수 정의 형태로 있으면 안 됨 (import는 허용)
    import re
    func_defs = re.findall(r'^def (find_by_document_id|find_by_source_file|load_identity_registry)\(', source_text, re.MULTILINE)
    assert func_defs == [], f"재구현 감지: {func_defs}"
```

---

## 2. 금지 파일 변경 확인 — 반드시 빈 diff

```bash
$ git diff core/retrieval.py ui/pages/chat.py ui/components/source_link.py
# (출력 없음 — 모든 파일이 변경되지 않음)
```

`core/retrieval.py`, `ui/pages/chat.py`, `ui/components/source_link.py` 모두 수정되지 않음.

---

## 3. 테스트 실행 결과

### 신규 테스트 (`tests/test_document_detail.py`)

```
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/David/envs/dbma311/bin/python
cachedir: .pytest_cache
rootdir: /Users/David/DBMA
configfile: pyproject.toml
plugins: anyio-4.14.0, cov-7.1.0, Faker-40.23.0, langsmith-0.9.1

collecting ... collected 8 items

tests/test_document_detail.py::test_01_normal_case PASSED                [ 12%]
tests/test_document_detail.py::test_02_registry_not_found PASSED         [ 25%]
tests/test_document_detail.py::test_03_record_not_found PASSED           [ 37%]
tests/test_document_detail.py::test_04_file_not_found PASSED             [ 50%]
tests/test_document_detail.py::test_05_ocr_failure PASSED                [ 62%]
tests/test_document_detail.py::test_06_query_terms_found PASSED          [ 75%]
tests/test_document_detail.py::test_07_query_terms_not_found PASSED      [ 87%]
tests/test_document_detail.py::test_08_no_reimplementation PASSED        [100%]

============================== 8 passed in 0.05s ===============================
```

### 전체 회귀 테스트

```
================ 1048 passed, 13 warnings in 154.24s (0:02:34) =================
```

기존 1040개 + 신규 8개 = **총 1048개 테스트 모두 통과**. 이전 회귀 스위트와 동일한 스위트이며 신규 모듈이 기존 테스트에 영향을 주지 않음을 확인.

---

## 4. 재구현 금지 확인 — grep 결과

```bash
$ grep -n 'def find_by_document_id\|def find_by_source_file\|def load_identity_registry' core/document_detail.py
# (출력 없음 — 함수 정의 없음, import만 사용)

$ grep -n 'from core.identity_registry import' core/document_detail.py
19:from core.identity_registry import (
```

`find_by_document_id`, `find_by_source_file`, `load_identity_registry` 세 함수 모두 `core/identity_registry.py`에서 import해서 사용했으며, `core/document_detail.py` 내에서 재구현하지 않음을 확인.

---

## 5. Phase 2 착수 전 CUE 결정 사항

1. **상세 패널 UI 컴포넌트명**: `ui/components/detail_panel.py`로 진행할지, 다른 명칭으로 할지
2. **검색어 강조 + 스크롤 실행 방식**: `match_locations`의 char_start/char_end를 UI에서 어떻게 하이라이트할지 (예: markdown 렌더러 지원 여부)
3. **본문 지연 로딩**: 대용량 문서(100KB+)에서 full_text 로드 시 성능 영향이 필요한가? Phase 2에서 구현 범위 결정
4. **source_path 클릭 동작**: 경로 문자열 표시만 할지, 실제 파일 열기 기능(subprocess)은 Phase 2에서 추가할지

---

**완료**: 2026-07-29
**다음 단계**: Phase 2 (ui/components/detail_panel.py) CUE 발급 대기