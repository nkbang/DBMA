# C1 Task Order 028 — 완료 보고서 (Notion 커넥터 기반 작업, EvidenceUnit 연결, 픽스처만)

**상태**: 완료
**완료일**: 2026-07-29
**우선순위**: P1

---

## §1. 구현 내용

### 1.1 `core/evidence_unit.py` — CorpusType.NOTION 추가

기존 값/필드는 변경하지 않고 `CorpusType` enum에 `NOTION = "notion"`만 추가.

```python
class CorpusType(str, Enum):
    SCRIPTURE = "scripture"
    LOGOS = "logos"
    PERSONAL_LIBRARY = "personal_library"
    OBSIDIAN = "obsidian"
    SERMON = "sermon"
    RESEARCH = "research"
    NOTION = "notion"   # 신규 (Task Order 028)
```

### 1.2 `core/evidence_adapters/notion_fixture_adapter.py` — 신규 모듈

`EvidenceSourceAdapter` 상속, JSON 픽스처 → `EvidenceUnit(corpus_type=NOTION)` 변환.

- 페이지 하나에 블록 여러 개면 `EvidenceUnit`도 여러 개 생성
- `evidence_id` 형식: `f"notion:{page_id}:{block_id}"`
- `provenance.original_uri`에 페이지 `url` 값 저장 (실제로 열지 않음)
- `annotations.tags`에 `properties.tags`에서 가져옴
- `quality.extraction_status`는 항상 `"pass"` 고정 (OCR 개념 없음)
- `extractor_name = "notion_fixture"`

### 1.3 `tests/fixtures/notion_fixture.json` — 신규 픽스처

2개 Notion 페이지 × 각 3개 블록 = 총 6개 블록 포함.

```json
[
  {
    "page_id": "abc123def456",
    "title": "창세기 24장 연구",
    "url": "https://notion.so/abc123def456",
    "properties": {"tags": ["prayer", "providence"], "status": "research"},
    "blocks": [
      {"block_id": "b1", "type": "paragraph", "text": "본문 관찰: 이삭이 결혼 이야기를 통해 하나님의 주권이 어떻게 드러나는지 살펴본다.", "block_index": 0},
      {"block_id": "b2", "type": "heading_2", "text": "기도의 중요성", "block_index": 1},
      {"block_id": "b3", "type": "paragraph", "text": "엘리야르는 하나님의 인도하심을 믿고 기도했다.", "block_index": 2}
    ]
  },
  {
    "page_id": "ghi789jkl012",
    "title": "창세기 24장 설교 노트",
    "url": "https://notion.so/ghi789jkl012",
    "properties": {"tags": ["sermon", "genesis"], "status": "draft"},
    "blocks": [
      {"block_id": "b4", "type": "paragraph", "text": "설교 주제: 하나님의 인도하심과 인간의 응답", "block_index": 0},
      {"block_id": "b5", "type": "bullet_list_item", "text": "첫째, 하나님의 주권적인 준비", "block_index": 1},
      {"block_id": "b6", "type": "bullet_list_item", "text": "둘째, 인간의 믿음과 순종", "block_index": 2}
    ]
  }
]
```

### 1.4 `tests/test_notion_fixture_adapter.py` — 신규 테스트

15개 테스트 케이스:
- `test_load_evidence_returns_list` — 리스트 반환 확인
- `test_load_evidence_six_items` — 6개 EvidenceUnit 생성 확인
- `test_all_corpus_type_is_notion` — 모두 NOTION 타입 확인
- `test_first_page_first_block_conversion` — 첫 항목 정확 변환 확인
- `test_first_page_second_block_is_heading` — heading_2 타입 확인
- `test_first_page_tags_applied_to_all_blocks` — tags 전파 확인
- `test_second_page_tags` — 두 번째 페이지 tags 정확 매핑 확인
- `test_evidence_id_format` — evidence_id 형식 확인
- `test_original_uri_stored_as_string` — original_uri 문자열 저장 확인
- `test_extractor_name_is_fixture` — extractor_name 확인
- `test_extraction_status_always_pass` — extraction_status 항상 pass 확인
- `test_empty_fixture_file` — 빈 배열 처리 확인
- `test_single_page_single_block_fixture` — 단일 항목 처리 확인
- `test_page_with_no_blocks` — 블록 없는 페이지 처리 확인
- `test_no_actual_notion_connection` — 실제 연결 없음 확인

---

## §2. 미접촉 파일 확인

`core/retrieval.py`, `core/parallel_retriever.py`, `core/generation.py`, `ui/pages/chat.py` 는 전혀 접촉하지 않음.

새로 만든 파일(import 체인)에서 이 파일들을 참조하는 import문이 없음:

```bash
$ grep -n "import.*retrieval\|import.*parallel_retriever\|import.*generation\|import.*chat" \
    core/evidence_adapters/notion_fixture_adapter.py \
    core/evidence_unit.py \
    tests/test_notion_fixture_adapter.py
(결과 없음 — 무접촉 확인)
```

---

## §3. 실제 Notion API 호출 코드 없음 확인

```bash
$ grep -r "api\.notion\.com" core/ tests/ scripts/ --include="*.py"
(결과 없음)

$ grep -r "NOTION_TOKEN" core/ tests/ scripts/ --include="*.py"
(결과 없음)

$ grep -r "notion_client" core/ tests/ scripts/ --include="*.py"
tests/test_notion_fixture_adapter.py:        requests, httpx, notion_client 접근이 없어야 한다.
```

`notion_client`은 테스트 파일의 주석에만 존재하고 실제 import 나 코드 사용 없음.

**결론**: 실제 Notion API 호출 코드, 토큰 처리, 외부 라이브러리 의존성 전혀 없음.

---

## §4. 테스트 실행 결과

```
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/David/envs/dbma311/bin/python
cachedir: .pytest_cache
rootdir: /Users/David/DBMA
configfile: pyproject.toml
plugins: anyio-4.14.0, cov-7.1.0, Faker-40.23.0, langsmith-0.9.1

collecting ... collected 15 items

tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_load_evidence_returns_list PASSED [  6%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_load_evidence_six_items PASSED [ 13%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_all_corpus_type_is_notion PASSED [ 20%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_first_page_first_block_conversion PASSED [ 26%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_first_page_second_block_is_heading PASSED [ 33%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_first_page_tags_applied_to_all_blocks PASSED [ 40%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_second_page_tags PASSED [ 46%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_evidence_id_format PASSED [ 53%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_original_uri_stored_as_string PASSED [ 60%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_extractor_name_is_fixture PASSED [ 66%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_extraction_status_always_pass PASSED [ 73%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_empty_fixture_file PASSED [ 80%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_single_page_single_block_fixture PASSED [ 86%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_page_with_no_blocks PASSED [ 93%]
tests/test_notion_fixture_adapter.py::TestNotionFixtureAdapter::test_no_actual_notion_connection PASSED [100%]

============================== 15 passed in 0.04s ==============================
```

**15개 테스트 전체 통과 (0.04초)**

---

## §5. 실제 Notion 연동을 위한 사용자 결정 사항

Notion Integration Token 발급 및 워크스페이스 연결을 시작하기 전에 사용자가 결정해야 할 사항:

1. **Integration Token 발급**: Notion Integrations 대시보드에서 토큰 생성
2. **워크스페이스 범위**: 어떤 Notion 페이지/데이터베이스에 접근할지 범위 지정
3. **페이지 매핑**: Notion 페이지 구조 → EvidenceUnit 매핑 정책 (블록 단위 vs 페이지 단위)
4. **속성 스키마**: Notion 데이터베이스 속성(tags, status 등) → EvidenceUnit 필드 매핑
5. **증분 동기화**: 기존 픽스처 기반에서 실제 API 연동으로 전환 시 증분 업데이트 전략

---

## §6. 생성된 파일 목록

| 파일 | 설명 |
|------|------|
| `core/evidence_unit.py` | CorpusType.NOTION 추가 (기존 값/필드 변경 없음) |
| `core/evidence_adapters/notion_fixture_adapter.py` | Notion JSON 픽스처 → EvidenceUnit 변환 어댑터 |
| `tests/fixtures/notion_fixture.json` | 테스트용 Notion 픽스처 (2페이지, 6블록) |
| `tests/test_notion_fixture_adapter.py` | NotionFixtureAdapter 단위 테스트 (15개 케이스) |

**미접촉 파일**: `core/retrieval.py`, `core/parallel_retriever.py`, `core/generation.py`, `ui/pages/chat.py` — 전부 무변경