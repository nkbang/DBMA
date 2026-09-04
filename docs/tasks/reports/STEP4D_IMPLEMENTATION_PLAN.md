# STEP4-D Implementation Plan

작성일: 2026-07-31
근거: NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md / NAE_METADATA_INPUT_STRATEGY.md(Option B) 확정 설계

## 변경 파일

| 파일 | 종류 | 규모 |
|---|---|---|
| `scripts/ingest_nae_source.py` | 신규 | `scripts/ingest_logos_export.py` 구조 복제, NAE manifest 전용 |
| `core/tsu_builder.py` | 수정 | `nae_metadata` additive 블록 구성, ~8줄 |

`data/nae/sources/baptist/` 등 inbox 경로는 STEP1/STEP2에서 이미 생성됨 — 별도 디렉토리 생성 불필요. `core/config.py`에 `DEFAULT_NAE_*` 상수를 추가하지 않고, 스크립트 내부 기본값(`data/nae/sources`, `data/nae/processed`)으로 한정 — 이번 STEP4-D 승인 범위(신규 스크립트 + tsu_builder.py)를 벗어나지 않기 위함.

## 변경 이유

- `scripts/ingest_nae_source.py`: NAE manifest(NAE_SOURCE_REGISTRY_SCHEMA_v1.md 형식) 기반으로 원문을 읽어 청킹·registry 등록하고, `theological_position`/`content_genre`/`denomination_context`/`copyright_status`를 registry에 additive로 주입. `scripts/ingest_logos_export.py`가 이미 검증한 패턴(register_document() 무수정, 반환 dict `.update()`)을 그대로 재사용.
- `core/tsu_builder.py`: registry에 주입된 `nae_*` 필드를 읽어 TSU record에 `nae_metadata` 블록으로 전달 — 이 필드가 없으면 이 블록 자체가 생성되지 않도록(기존 `source_provenance`가 `source_tier is None`일 때 `None`을 넣는 것과 동일 원칙) 하여 기존 코퍼스에 영향 없음을 보장.

## Rollback 방법

1. `scripts/ingest_nae_source.py` 파일 삭제 (신규 파일이므로 삭제만으로 완전 원복)
2. `core/tsu_builder.py`의 `nae_metadata` 관련 추가분만 `git diff`로 되돌림 (다른 필드 미변경이므로 diff가 국소적)
3. 이미 이 스크립트로 registry에 `nae_*` 키가 기록된 상태에서 롤백하더라도, 기존 `register_document()`/`build_tsu_records()` 읽기 로직은 이 키를 요구하지 않으므로 파싱 오류 없음 — 데이터 마이그레이션 불필요

## Test 방법

1. **기존 테스트 회귀**: `pytest tests/test_tsu_structure.py tests/test_tsu_manifest.py tests/test_build_tsu_dataset_chapter.py tests/test_build_tsu_dataset_book_id.py tests/test_build_tsu_dataset_verse_mapping.py` — `core/tsu_builder.py` 수정 후 기존 통과 상태 유지 확인
2. **단일 문서 dry-run**: `python -m scripts.ingest_nae_source --manifest <pilot manifest> --dry-run` — 파일 쓰기 없이 문서 식별/청킹 확인
3. **실제 청킹 + registry 등록**(승인 범위 내, 소규모 1건): 임시 output 디렉토리(스크래치패드)를 사용해 실제 파이프라인 코드가 정상 동작하는지 확인 — 운영 `output/`을 건드리지 않음
4. **TSU dry-run**: `python -m scripts.build_tsu_dataset --output-dir <임시 디렉토리> --dry-run` — 생성된 TSU record에 `nae_metadata` 블록이 정확히 포함되는지 확인

상세 실행 결과는 STEP4D_TEST_REPORT.md에 기록.
