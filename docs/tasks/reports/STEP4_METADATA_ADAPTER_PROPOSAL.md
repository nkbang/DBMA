# STEP4 Minimal Adapter Proposal

작성일: 2026-07-31
목적: NAE metadata를 ingestion→TSU 경로에 흘려보내기 위한 최소 변경 설계. **설계 제안이며 코드 수정은 하지 않음.**

## 필요한 파일 (4곳, STEP4_PROCESSING_METADATA_FLOW.md §결론과 동일)

1. `core/document_context.py` — `DocumentContext` dataclass
2. `core/processing.py` — Point A(539행) `DocumentContext(...)` 생성부
3. `core/identity_registry.py` — `register_document()` (112~148행)
4. `core/tsu_builder.py` — `build_tsu_records()` (340행 이후 record 구성부)

## 각 파일 예상 변경 규모

### 1. `core/document_context.py`
```python
# Structural metadata 섹션(52~58행 부근)에 추가
nae_theological_position: Optional[str] = None
nae_denomination_context: Optional[str] = None
nae_content_genre: list[str] = field(default_factory=list)
nae_copyright_status: Optional[str] = None
```
- `to_metadata_dict()`(126행)에 위 4개 키 포함 — 기존 dict 변환 로직 패턴 그대로 확장
- 예상 규모: **약 8~10줄** (필드 선언 4줄 + to_metadata_dict 반영 4줄 + 주석)

### 2. `core/processing.py`
```python
# Point A(539행) DocumentContext(...) 생성 시 인자 추가
_document_context = DocumentContext(
    ...,
    nae_theological_position=nae_meta.get("theological_position") if nae_meta else None,
    nae_denomination_context=nae_meta.get("denomination_context") if nae_meta else None,
    nae_content_genre=nae_meta.get("content_genre", []) if nae_meta else [],
    nae_copyright_status=nae_meta.get("copyright_status") if nae_meta else None,
)
```
- 전제: `nae_meta`라는 사전 등록 정보(예: STEP4_PILOT_SOURCE_ENTRY.md 같은 파일을 소스 파일명 기준으로 lookup)가 `process_one_file()`에 어떻게든 전달되어야 함 — **이 lookup 메커니즘 자체가 아직 미설계**. title/author처럼 파일 자체에서 자동 추출 불가능하므로, 별도 입력 경로(예: `file_info`에 `nae_meta` 키 추가, 또는 `source_file` 기준 별도 룩업 테이블 로드) 설계가 선행되어야 함.
- 예상 규모: **약 6줄 + 미확정 lookup 로직(규모 산정 불가)**

### 3. `core/identity_registry.py`
```python
# "Optional fields" 섹션(130행 부근)에 추가
"nae_theological_position": metadata.get("nae_theological_position"),
"nae_denomination_context": metadata.get("nae_denomination_context"),
"nae_content_genre": metadata.get("nae_content_genre", []),
"nae_copyright_status": metadata.get("nae_copyright_status"),
```
- 예상 규모: **약 4~5줄**, 기존 `"book": metadata.get("book")` 등과 완전히 동일한 패턴

### 4. `core/tsu_builder.py`
```python
# source_provenance 블록(422~437행) 이후에 추가
record["nae_metadata"] = {
    "theological_position": doc.get("nae_theological_position"),
    "denomination_context": doc.get("nae_denomination_context"),
    "content_genre": doc.get("nae_content_genre", []),
    "copyright_status": doc.get("nae_copyright_status"),
}
```
- 예상 규모: **약 6~8줄**, 기존 `content_quality`/`structure` 블록과 동일 패턴

## 총 예상 변경 규모

- 확정 가능한 부분: 4개 파일 합산 **약 25~30줄**
- 미확정 부분: `core/processing.py`의 "NAE 사전 등록 정보를 어디서 lookup할 것인가" — 이는 규모를 특정할 수 없는 별도 설계 결정(간단하면 5줄, 복잡하면 별도 모듈 필요)

## 기존 기능 영향

- **없음(예상)**. 4곳 모두 additive-only 패턴(기존 필드 변경/삭제 없음, 신규 필드만 추가, 기본값 `None`/`[]`)을 따름 — SPRINT28-B(content_quality)/SPRINT29-C(structure)/ADR-009(baptist_theme 등)가 이미 3차례 검증한 안전한 확장 방식과 동일.
- `core/retrieval.py`는 변경 대상에서 제외 — 새 필드를 읽지 않으므로 검색 동작 불변.
- 기존 문서(NAE가 아닌 일반 DBMA 문서)는 `nae_meta`가 없으므로 4개 필드 모두 `None`/`[]`로 채워짐 — 기존 데이터셋에 대해 no-op.

## Rollback 가능성

- **높음**. 4개 변경 모두 신규 필드 추가이며 기존 필드를 참조하는 코드 경로를 전혀 건드리지 않음.
- Rollback 방법: 4개 파일의 diff를 되돌리기만 하면 됨 — 데이터 마이그레이션 불필요(신규 필드가 없어져도 기존 레코드는 이미 additive이므로 하위 호환 깨지지 않음).
- 단, 이미 생성된 `identity_registry.json`/`tsu_dataset.jsonl`에 `nae_*` 키가 기록된 후 코드를 되돌리면, 해당 키는 "코드가 모르는 잉여 필드"로 파일에 남지만 기존 읽기 로직(`doc.get(...)`)은 존재하지 않는 키를 요청하지 않으므로 **파싱 오류나 동작 이상을 일으키지 않음**.

## 결론

- 코드 변경 자체는 국소적이고 rollback 안전하나, **`core/processing.py`의 NAE 메타데이터 lookup 메커니즘 설계가 선행되어야** 실제 구현에 착수 가능
- 이번 문서는 제안만 제공하며 코드 수정은 수행하지 않음
