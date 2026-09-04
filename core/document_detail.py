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