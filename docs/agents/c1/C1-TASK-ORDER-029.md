# C1 Task Order 029 — 검색 결과 상세보기 Phase 1: document_detail API

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P1
**근거 문서**: [docs/architecture/DBMA-Search-Result-Detail-Panel-Plan-v1.md](../../architecture/DBMA-Search-Result-Detail-Panel-Plan-v1.md)
**작성일**: 2026-07-30
**모드 제약**: `core/retrieval.py`, `ui/pages/chat.py`, `ui/components/source_link.py` 절대 미접촉 (Phase 2/3
에서 다룸). 이번엔 신규 모듈 `core/document_detail.py` + 테스트만 작성한다.

---

## 1. 배경 — 실제 데이터 구조 (착수 전 CUE가 직접 확인함)

- 레지스트리 조회는 이미 있는 함수를 그대로 쓴다: `core/identity_registry.py::load_identity_registry(path)`,
  `find_by_source_file(registry, source_file)`, `find_by_document_id(registry, document_id)`.
  **새로 만들지 말 것.**
- 레지스트리 레코드 실제 필드(운영 registry에서 직접 확인, `data/제련완성본/registry/documents.json`):
  `document_id`, `source_file`, `title`(null 가능), `author`(null 가능), `doc_type`, `created_at`,
  `is_ocr`, `book`/`chapter`/`page`(성경 참조, null 가능), `status`.
- 본문 전체는 레지스트리에 없다 — **`{output_dir}/{stem}_{ext}.md`** 경로에 별도 파일로 존재한다
  (CUE가 `data/제련완성본/7. 사도행전1_pdf.md` 실존을 직접 확인함 — output_dir 바로 아래, 하위 폴더 없음).
  `stem`/`ext`는 `source_file`에서 `Path(source_file).stem`/`Path(source_file).suffix.lstrip(".")`로
  얻는다 (Task Order 019의 백필 스크립트와 동일한 명명 규칙 — `scripts/backfill_doc_type.py` 참고해서
  똑같이 맞출 것).
- `output_dir`은 `core/config.py::DEFAULT_OUTPUT_DIR`를 기본값으로 쓰되, 함수 인자로 override 가능하게
  한다(테스트에서 임시 디렉토리를 쓸 수 있어야 함).

---

## 2. 구현 범위

### 2.1 신규 모듈 — `core/document_detail.py`

```python
from dataclasses import dataclass, field

@dataclass
class MatchLocation:
    char_start: int
    char_end: int

@dataclass
class DocumentDetail:
    document_id: str
    title: str | None
    document_type: str | None       # registry의 doc_type
    source_path: str                 # 사용자에게 보여줄 경로 문자열 (실행 트리거 아님, 텍스트만)
    author: str | None
    created_at: str | None
    tags: list[str] = field(default_factory=list)   # 이번 범위: book/chapter 있으면 ["book:CHAPTER"] 형태로만 채움, 정교한 태그 체계는 후속
    full_text: str = ""
    match_locations: list[MatchLocation] = field(default_factory=list)
    error: str | None = None         # 아래 세 가지 실패 케이스만 채움, 그 외엔 None


def get_document_detail(
    source_file: str,
    document_id: str,
    query_terms: list[str],
    registry_path: str | None = None,
    output_dir: str | None = None,
) -> DocumentDetail:
    """
    1. registry_path가 없으면 core.config.DEFAULT_REGISTRY_PATH 사용, output_dir 없으면
       core.config.DEFAULT_OUTPUT_DIR 사용.
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
    """
```

- **본문 누락/파일 이동/OCR 실패, 이 세 가지를 구분해서 error 메시지를 다르게 낼 것** (계획서 §4의
  "본문 누락, 파일 이동, OCR 실패 등 예외 상황에서 원인 안내" 수용 기준). OCR 실패는 레지스트리의
  `is_ocr=True`인데 `full_text`가 비정상적으로 짧거나(예: 50자 미만) 빈 경우로 간이 판정 — 완벽한
  탐지는 아니라는 걸 docstring에 명시.
- **대형 문서 지연 로딩은 이번 범위에서 구현하지 않는다** (계획서 §2.2 결정 사항 그대로).

### 2.2 이번 범위에서 제외

- UI 연동(`ui/pages/chat.py`, `ui/components/detail_panel.py`) — Phase 2/3.
- `subprocess`로 원본 파일 여는 기능 — 사용자가 "경로만 표시"로 결정함(계획서 §5). 이 함수는 경로
  **문자열만** 반환하고 절대 실행하지 않는다.
- `tags` 필드의 정교한 태그 체계 — 이번엔 `book`/`chapter`가 있을 때만 최소한으로 채움.

---

## 3. 검증 계획

**단위 테스트** (`tests/test_document_detail.py` 신규, 임시 디렉토리로 registry/output_dir 격리):

1. 정상 케이스: registry에 레코드 있고 md 파일도 있음 → `DocumentDetail` 전체 필드 정확히 채워짐,
   `error is None`
2. 레지스트리 자체가 없는 경우 → `error`에 해당 메시지, 예외 발생 안 함
3. 레지스트리엔 있는데 document_id/source_file로 못 찾는 경우 → `error` 메시지
4. 레코드는 있는데 md 파일이 없는 경우(이동/삭제 시뮬레이션) → `error`="원본 문서 파일을 찾을 수
   없습니다..." 이고 메타데이터(title/author 등)는 채워짐
5. `is_ocr=True`이고 본문이 비정상적으로 짧은 경우 → OCR 실패로 판정된 error 메시지
6. `query_terms`가 본문에 존재 → `match_locations`에 정확한 char_start/char_end
7. `query_terms`가 본문에 없음 → `match_locations` 빈 리스트, `error`는 None (매치 없음은 에러가 아님)
8. `find_by_document_id`/`find_by_source_file`를 재구현하지 않고 import해서 썼는지 코드 리뷰 관점에서
   확인 (grep으로 자체 검증해 보고서에 남길 것)

기존 회귀 스위트 전체 재실행 — 통과 개수 pytest 출력 그대로 복사.

---

## 4. 보고 형식

1. `core/document_detail.py`, `tests/test_document_detail.py` diff
2. `git diff core/retrieval.py ui/pages/chat.py ui/components/source_link.py` — 반드시 빈 diff
3. 테스트 실행 결과 (pytest 출력 그대로 복사, 어림잡아 세지 말 것 — 이전 여러 Task Order에서 수치
   오보 사례가 반복됐음, 이번엔 반드시 실제 pytest 출력을 그대로 붙여넣을 것)
4. `find_by_document_id`/`find_by_source_file`/`load_identity_registry`를 재구현 안 하고 import해서
   썼는지 grep 결과
5. Phase 2(`ui/components/detail_panel.py`) 착수 전 CUE가 결정해야 할 사항이 있으면 정리

---

## 5. 다음 조치

Phase 1 완료·검증되면 Phase 2(우측 상세 패널 UI, 검색어 강조 + 스크롤 실험)를 CUE가 발급.
