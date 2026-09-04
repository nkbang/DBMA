# STEP4 Processing Metadata Flow

작성일: 2026-07-31
조사 방식: 읽기 전용 (`core/processing.py`, `core/document_context.py` 코드 열람), 코드 수정 없음.
목적: Source metadata가 ingestion 과정에서 어디서 생성되어 어떻게 registry/TSU로 전달되는지 실제 경로 추적.

## Input Object

`process_one_file(file_info, converter, splitter, output_dir, chunk_size, chunk_overlap, ...)` (`core/processing.py:411`)

- `file_info`: dict — `path`(원본 파일 경로), `name`(source_name), `ext`, `use_ocr` 등을 담은 단일 파일 입력 객체. 이 함수가 파이프라인의 실질적 진입점.
- `file_info`는 상위 `process_batch()`(923행)가 파일 목록을 순회하며 만들어 넘김 — UI(`ui/pages/library.py` 등)에서 온 업로드 파일 목록이 최종 출처로 추정(이번 조사에서 UI 쪽까지는 확인하지 않음, 범위 밖).

## Metadata 생성 위치

두 단계로 나뉘어 있음:

### Point A — 식별 시점 (539행)

```python
_document_context = DocumentContext(
    document_id=document_id,
    file_hash=file_hash,
    source_file=source_name,
    source_type=ext,
    is_ocr=is_ocr,
    title=extracted_title,   # PDF docinfo / DOCX core_properties에서 추출 (raw_result.get("title"))
    author=extracted_author, # 동일
)
```

- `core/document_context.py::DocumentContext`가 실제 metadata 오브젝트(dataclass). `title`/`author`는 원본 파일 자체의 임베디드 메타데이터에서 추출(사람이 입력하는 경로 아님).
- `book`, `chapter`, `page`, `batch_id`는 이 시점에는 `None`(dataclass 기본값) — SKIP 경로에서만 기존 registry 값으로 채워짐(590~600행).
- **NAE 관련 필드(`content_genre`, `theological_position`, `denomination_context`, `copyright_status`)에 대응하는 입력 경로가 현재 코드에 없음** — `DocumentContext` dataclass(42~113행 관측)에 이런 필드 자체가 정의되어 있지 않음.

### Point C — 등록 직전 (816행)

```python
document_meta = _document_context.to_metadata_dict()
record, is_new = register_document(_registry, document_meta, output_dir)
```

- `DocumentContext.to_metadata_dict()`가 dataclass를 dict로 변환, 이 dict가 registry 전달 형식.

## Registry 전달 위치

- `core/identity_registry.py::register_document(registry, metadata, output_dir)` — `document_meta` dict를 받아 `registry["documents"][doc_id]` 레코드로 저장(STEP4_CODE_IMPACT_REVIEW.md에서 이미 확인한 90~148행)
- 현재 `register_document()`가 `metadata.get(...)`로 꺼내 쓰는 키는 `title`/`author`/`book`/`chapter`/`page`/`language`/`source_type`/`doc_type` 등 — `DocumentContext`가 애초에 갖고 있는 필드와 정확히 일치. NAE 필드는 `DocumentContext`에 없으므로 `to_metadata_dict()` 출력에도 없고, `register_document()`가 꺼낼 수도 없음.

## TSU Builder 전달 경로

- `core/tsu_builder.py::build_tsu_records(registry, output_dir)`가 `registry["documents"]`를 순회하며 `doc.get(...)`으로 값을 읽음(STEP3_TSU_PIPELINE_ANALYSIS.md에서 이미 확인)
- 즉 경로는: `DocumentContext`(생성) → `to_metadata_dict()`(변환) → `register_document()`(저장) → `build_tsu_records()`(읽기) — **총 3개 지점을 전부 통과해야 값이 TSU record까지 도달**

## 결론 — NAE metadata 삽입에 필요한 지점 (조사 결과, 실행 아님)

NAE 필드가 ingestion부터 TSU까지 전달되려면 아래 4곳 모두에 손을 대야 함(어느 한 곳만으로는 흐름이 끊김):

1. `core/document_context.py::DocumentContext` dataclass에 필드 추가 (title/author와 같은 레벨)
2. `core/processing.py` Point A(539행)에서 `DocumentContext(...)` 생성 시 값 주입 — **현재 이 값을 어디서 받아올지가 미해결**: PDF 임베디드 메타데이터에는 `theological_position` 같은 개념이 없으므로, `title`/`author`처럼 자동 추출이 불가능 — 별도 입력 경로(예: STEP4_SOURCE_REGISTRATION.md 같은 사전 등록 파일을 읽어오는 방식) 필요
3. `core/identity_registry.py::register_document()`에서 해당 키 추출 추가
4. `core/tsu_builder.py::build_tsu_records()`에서 `nae_metadata` 블록 구성 추가

STEP4_METADATA_ADAPTER_PROPOSAL.md에서 이 4개 지점의 구체적 변경안을 다룸.
