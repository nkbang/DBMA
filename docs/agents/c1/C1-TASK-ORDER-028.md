# C1 Task Order 028 — v3 Notion 커넥터 기반 작업 (EvidenceUnit 연결, 픽스처만)

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P1
**선행 작업**: Task Order 025(EvidenceUnit 공통 모델, `core/evidence_adapters/`) 완료·검증됨(전체 회귀
1020/1020). 재정의 금지, 그대로 재사용.
**근거 문서**: [docs/architecture/NAE-Unified-Research-Search-Plan-v3.md](../../architecture/NAE-Unified-Research-Search-Plan-v3.md)
**작성일**: 2026-07-30
**⚠️ 범위 제약 (DEVONthink Task Order 025와 동일 원칙)**: Notion은 공식 REST API(Integration Token 방식)가
있어 DEVONthink처럼 접근 방식 자체가 불확실하지는 않다. 그러나 **이번 Task Order에서 실제 Notion API를
호출하는 코드는 작성하지 않는다** — Integration Token 발급/워크스페이스 연결은 사용자가 아직 결정하지
않은 별도 단계다. 이번엔 API 응답 형식을 흉내 낸 JSON 픽스처로만 어댑터를 검증한다. `requests`/`httpx`로
`api.notion.com`에 실제 접속하는 코드, 토큰을 읽는 로직(`os.environ["NOTION_TOKEN"]` 등) 전부 금지.

---

## 1. 배경

v3의 원래 6개 코퍼스(Scripture/Logos/Personal Library/Obsidian/Sermon/Research)에는 Notion이 없었다 —
DEVONthink 철회([[project_devonthink_withdrawn]]) 이후 사용자가 대신 Notion을 개인 지식 코퍼스로
선택했다. `core/evidence_unit.py`의 `CorpusType`에 `NOTION`을 추가해 대응한다.

Notion의 데이터 구조는 Obsidian(파일+frontmatter)과 다르다 — 페이지(page)/블록(block) 트리 구조,
데이터베이스(database) 속성(properties), 페이지 간 relation/mention 링크를 갖는다. 이 구조를
`EvidenceUnit`으로 어떻게 매핑할지가 이번 작업의 핵심 설계 문제다.

---

## 2. 구현 범위

### 2.1 `core/evidence_unit.py` 수정 (필드 추가만, 기존 필드/값 변경 금지)

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

`EvidenceLocation`에 Notion 전용 위치 필드 추가 검토: 기존 `section_path`(heading 경로)를 Notion의
"페이지 제목 > 블록 경로"로 재사용할 수 있는지 먼저 확인하고, 안 맞으면 `notion_block_id: str | None`
정도만 최소 추가 (불필요한 필드 남발 금지 — 실제 픽스처 매핑 과정에서 꼭 필요한 것만 추가할 것).

### 2.2 신규 모듈 — `core/evidence_adapters/notion_fixture_adapter.py`

`core/evidence_adapters/base.py::EvidenceSourceAdapter`(Task Order 025에서 구현됨)를 상속한다.

Notion API의 실제 응답 형식(예: [Notion API Page object](https://developers.notion.com/reference/page) —
`id`, `properties`, `url`, `created_time`, `last_edited_time`, 블록 목록은 별도 `blocks.children.list`
응답)을 흉내 낸 JSON 픽스처를 읽어 `EvidenceUnit(corpus_type=NOTION)`으로 변환한다.

픽스처 예시 형태 (`tests/fixtures/notion_fixture.json`):
```json
[
  {
    "page_id": "abc123...",
    "title": "창세기 24장 연구",
    "url": "https://notion.so/abc123",
    "created_time": "2026-07-20T10:00:00.000Z",
    "last_edited_time": "2026-07-25T09:00:00.000Z",
    "properties": {"tags": ["prayer", "providence"], "status": "research"},
    "blocks": [
      {"block_id": "b1", "type": "paragraph", "text": "본문 관찰...", "block_index": 0}
    ]
  }
]
```

- `EvidenceUnit.evidence_id`는 `f"notion:{page_id}:{block_id}"` 형식으로 블록 단위 생성 (Notion 페이지
  하나가 여러 EvidenceUnit으로 나뉠 수 있음 — 실제 청킹 전략은 이번 범위 밖, 블록 하나 = EvidenceUnit
  하나로 단순화).
- `provenance.original_uri`는 페이지 `url` 값을 문자열로 저장만 (실제로 열지 않음).
- `annotations.tags`는 `properties.tags`에서 가져온다 (Notion 속성 스키마가 데이터베이스마다 다르다는
  점은 알아두되, 이번 픽스처는 `tags`가 문자열 리스트로 고정된 단순 형태로 가정).
- `quality.extraction_status`는 항상 `"pass"`로 고정 (OCR 개념이 없으므로 DEVONthink 어댑터처럼 품질
  점수 기반 분기 불필요).

### 2.3 이번 범위에서 제외

- 실제 Notion API 호출 (`api.notion.com`), Integration Token 처리 — §범위 제약 참고.
- 페이지 트리/중첩 블록의 재귀적 파싱 — 픽스처는 평면 블록 리스트로 단순화, 실제 Notion 블록 트리(토글,
  중첩 리스트 등) 대응은 실제 연동 시점에.
- 데이터베이스 속성 스키마 일반화 — 실제 워크스페이스 구조를 보기 전엔 추측하지 않는다.
- `ParallelRetriever`/검색 파이프라인 연결 — v3 Phase 4 이후.

---

## 3. 검증 계획

1. **단위 테스트** (`tests/test_notion_fixture_adapter.py` 신규):
   - 픽스처 JSON → `EvidenceUnit(corpus_type=NOTION)` 정확 변환
   - 페이지 하나에 블록 여러 개면 `EvidenceUnit`도 여러 개 생성되는지
   - `properties.tags`가 `annotations.tags`로 정확히 매핑되는지
   - `original_uri`에 `url` 값이 그대로 저장되는지 (열기 시도 없음)
2. `core/evidence_unit.py`의 `CorpusType.NOTION` 추가로 인한 기존 테스트(`tests/test_evidence_unit.py`)
   회귀 없음 확인.
3. 전체 회귀 스위트 재실행 — 기존 통과 개수 유지 확인 (pytest 출력 그대로 복사, 어림잡아 세지 말 것).

---

## 4. 보고 형식

1. `core/evidence_unit.py`(diff), `core/evidence_adapters/notion_fixture_adapter.py`,
   `tests/fixtures/notion_fixture.json`, `tests/test_notion_fixture_adapter.py` diff
2. `core/retrieval.py`/`core/parallel_retriever.py`/`core/generation.py`/`ui/pages/chat.py` — 전부
   미접촉이어야 함 (`git diff` 빈 diff 확인)
3. 실제 Notion API 호출 코드가 없음을 grep으로 자체 확인한 결과 (`api.notion.com`, `NOTION_TOKEN`,
   `notion_client` 등 검색해서 안 나온다는 것을 보고서에 명시)
4. 테스트 실행 결과 — pytest 출력 그대로 복사
5. 실제 Notion 연동(Integration Token 발급, 워크스페이스 연결 범위)을 시작하기 전에 사용자가 결정해야
   할 사항 정리

---

## 5. 다음 조치

사용자가 Notion Integration Token 발급 및 연동 워크스페이스 범위를 정하면, CUE가 실제 연동 Task Order를
발급한다. 그 전까지 v3 Notion 코퍼스는 이 픽스처 기반 인프라 상태로 대기.
