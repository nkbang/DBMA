# NAE Source Registry Schema v1

작성일: 2026-07-31
목적: NAE 자료를 위한 Source Registry 항목 표준(등록 시 채울 필드 정의). `data/nae/metadata/`에 저장될 소스 1건당 레코드 형식.
NAE_SOURCE_SCHEMA_v1.md(원래 10필드)와 NAE_METADATA_POLICY_v1.md(theological_position/content_genre 등 정책)를 통합·구체화한 실무 등록 스키마.

## 필드 정의

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `source_id` | string | Y | 고유 식별자. 형식: `{denomination}-{content_genre}-{sequence}` 예: `baptist-confession-001` (NAE_SOURCE_SCHEMA_v1.md 계승) |
| `title` | string | Y | 원문 제목 |
| `author` | string | N | 저자/저술 단체. 무명/집단 저작은 명시적 단체명 또는 `unknown` |
| `year` | int | N | 최초 출판/저술 연도 |
| `publisher` | string | N | 출판사/발행 단체 (신규 — 이전 스키마에 없던 필드, 판본 추적용) |
| `copyright_status` | enum | Y | `public_domain` / `licensed` / `unknown` |
| `provenance` | object | Y | 출처 근거 블록 — 하위 필드: `source_url`(원문 출처 URL, null 허용), `acquisition_status`(`not_acquired`/`acquired`/`verified`), `acquisition_date` |
| `content_genre` | array[enum] | Y | NAE_METADATA_POLICY_v1.md §5 기준 8개 값 중 복수 선택 가능 |
| `theological_position` | enum | N | NAE_SOURCE_SCHEMA_v1.md 제안 enum(미확정) 중 1개. document-level, 미정 시 null |
| `denomination_context` | string | N | optional 서술형, NAE_METADATA_POLICY_v1.md §4 |
| `local_path` | string | N | 로컬 저장 경로 (예: `data/nae/sources/baptist/nhc_1833.txt`) — **원문 미확보 시 null**, 등록 즉시 채우지 않음 |

## 등록 상태 값 (provenance.acquisition_status)

- `not_acquired`: 명세만 존재, 원문 없음 (candidate 단계)
- `acquired`: 원문 파일 확보, 아직 registry(`identity_registry.json`) 미반영
- `verified`: 원문 확보 + Public Domain/저작권 상태 확인 완료 + ingest 준비 완료

## 기존 DBMA registry(`core/identity_registry.py`)와의 관계

- 이 스키마는 `data/nae/metadata/`용 **NAE 전용 사전 등록 레코드**이며, `core/identity_registry.py::register_document()`가 관리하는 `identity_registry.json`과는 별도 파일/네임스페이스.
- `core/identity_registry.py`의 문서 레코드는 `title`/`author`/`language`/`source_type`(파일 포맷) 등을 이미 갖고 있음(관측: 112~176행) — 실제 ingest 시점에 이 스키마의 `title`/`author`/`local_path`(→`source_file`) 값이 그쪽으로 흘러들어가는 것이 자연스러운 경로.
- `content_genre`/`theological_position`/`denomination_context`/`copyright_status`는 기존 identity_registry에 대응 필드가 없음 — STEP4_CODE_IMPACT_REVIEW.md에서 확장 위치 검토.

## 비고

- 이 스키마는 등록 **형식**만 정의하며, 실제 레코드 작성(Pilot 대상 1건)은 STEP4_PILOT_SOURCE_ENTRY.md에서 별도 수행
