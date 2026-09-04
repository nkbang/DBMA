# NAE Source Pipeline

작성일: 2026-07-31

NAE 검증 원문(침례교 신학 자료 등)이 `resources/theological_sources/`에 등록된 이후 실제 검색 가능한 데이터가 되기까지 거치는 5단계 흐름을 정리한다.

```
RAW
 ↓
CLEAN
 ↓
TSU
 ↓
Embedding
 ↓
Vector DB
```

## RAW

- **정의**: 사람이 신뢰 저장소(CCEL/Wikisource/Internet Archive 등)에서 직접 확보한 원문 그대로의 상태 — 정제/가공 이전.
- **위치**: `resources/theological_sources/{denomination}/{genre}/` 하위, `source_manifest.yaml`(스키마: `resources/theological_sources/source_manifest.schema.yaml`)로 메타데이터와 함께 등록.
- **상태값**: `PREPARED`(메타데이터만 확정, 원문 미확보) → `ACQUIRED`(원문 파일 확보 완료)
- **검증**: `scripts/source_validator.py`가 이 단계에서 metadata 존재/license/source_id 중복/status를 기계적으로 확인. 원문 내용 자체의 정확성(조항 누락 등)은 사람이 별도 검증(참고: `docs/tasks/reports/STEP5_SOURCE_MANUAL_VERIFY.md`).
- **원칙**: 원문을 추정/생성하지 않는다 — 사람이 실제로 확보한 파일만 이 단계에 존재할 수 있다.

## CLEAN

- **정의**: RAW 원문을 ingest 파이프라인에 태울 수 있는 정제된 형태로 변환하는 단계 — 인코딩 통일(UTF-8), 불필요한 서식 제거, 조항/구조 경계 보존.
- **실행 모듈**: `scripts/ingest_nae_source.py`(신규, STEP4-D 구현) — 원문을 읽어 청킹하고 `core/identity_registry.py::register_document()`로 등록.
- **상태값**: `VERIFIED`(정제 대상으로 확정, 최소 2개 독립 출처 대조 완료) → `INGESTED`(정제·청킹·registry 등록 완료)
- **산출물**: `identity_registry.json`에 문서 레코드 생성, `nae_theological_position`/`nae_content_genre` 등 NAE 전용 필드가 additive로 기록됨(`docs/tasks/reports/NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md` 설계 기준).
- **원칙**: 기존 DBMA ingest 파이프라인(`core/processing.py`)은 수정하지 않음 — NAE는 별도 스크립트 경로로 격리.

## TSU

- **정의**: registry에 등록된 청크를 TSU(Theological Source Unit) record로 변환 — 검색 가능한 최소 단위.
- **실행 모듈**: `core/tsu_builder.py::build_tsu_records()` (기존 함수, STEP4-D에서 `nae_metadata` additive 블록만 추가됨).
- **산출물**: `output/bench/tsu_dataset.jsonl`에 `tsu_id`/`content`/`nae_metadata`(theological_position/denomination_context/content_genre/copyright_status) 등을 담은 레코드.
- **원칙**: 기존 TSU 필드(`content_quality`/`structure`/`baptist_theme`/`doctrine_category`/`source_provenance` 등)는 변경되지 않음 — NAE 필드는 항상 순수 추가.

## Embedding

- **정의**: TSU record의 `content`를 벡터로 변환하는 단계 — 기본 임베딩 모델 `bge-m3:latest`(CLAUDE.md 기준) 사용.
- **실행 모듈**: 기존 DBMA 임베딩 파이프라인 재사용(NAE 전용 임베딩 로직 신규 도입 없음) — 별도 문서(`docs/architecture/` 하위 관련 설계 문서 참고).
- **원칙**: 이 문서 작성 시점 기준, NAE 자료에 대한 실제 embedding 실행은 아직 수행되지 않았음 — 코드/설계는 준비되어 있으나 실행은 항상 별도 승인 대상.

## Vector DB

- **정의**: 생성된 임베딩을 검색 가능한 인덱스로 저장하는 최종 단계.
- **실행 모듈**: `core/retrieval.py::RetrievalEngine`이 인덱스를 소비 — 이 모듈은 NAE 확장과 무관하게 무수정 상태(추가 필드를 아직 읽지 않음).
- **원칙**: Vector DB 변경(재생성/재인덱싱)은 이번까지의 모든 NAE 관련 Task Order에서 일관되게 금지되어 왔으며, 이 문서 작성 시점에도 실행되지 않았음.

## 단계별 담당 파일 요약

| 단계 | 주요 파일 | 상태 |
|---|---|---|
| RAW | `resources/theological_sources/**/source_manifest.yaml` | 스키마 정의됨, 실제 manifest 데이터는 아직 없음 |
| CLEAN | `scripts/ingest_nae_source.py` | 구현·테스트·커밋 완료 (`d32b716`) |
| TSU | `core/tsu_builder.py` (`nae_metadata` 블록) | 구현·테스트·커밋 완료 (`d32b716`) |
| Embedding | 기존 DBMA 파이프라인 재사용 | NAE向 실행 미착수 |
| Vector DB | `core/retrieval.py` | 무수정, NAE向 실행 미착수 |

## 관련 문서

- `resources/theological_sources/source_manifest.schema.yaml` — RAW 단계 메타데이터 스키마
- `docs/tasks/reports/NAE_METADATA_POLICY_v1.md` — 메타데이터 정책 확정본
- `docs/tasks/reports/NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md` — CLEAN→TSU 어댑터 설계
- `docs/tasks/reports/STEP5_REGISTRY_TRANSITION.md` — RAW 단계 내부 상태 전이(PREPARED→ACQUIRED→VERIFIED→INGESTED)
