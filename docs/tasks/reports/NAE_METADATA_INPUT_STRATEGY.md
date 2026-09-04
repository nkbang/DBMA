# NAE Metadata Input Strategy

작성일: 2026-07-31
목적: NAE metadata를 어디서 입력받을지 3개 옵션 비교 평가.

## Option A — DocumentContext parameter extension

`core/document_context.py::DocumentContext` dataclass에 `nae_*` 필드를 직접 추가하고, `core/processing.py`의 UI 업로드 파이프라인(`process_one_file`) 안에서 값을 채우는 방식 (STEP4-B `STEP4_METADATA_ADAPTER_PROPOSAL.md`의 원래 제안).

| 평가 항목 | 내용 |
|---|---|
| 안정성 | 중간 — dataclass 필드 추가 자체는 안전하나, `process_one_file`에 lookup 로직을 끼워 넣어야 하며 이 부분이 UI 업로드 흐름(일반 DBMA 문서)과 NAE 문서 흐름을 한 함수 안에서 분기해야 해서 복잡도 상승 |
| 기존 코드 영향 | 4개 파일(DocumentContext/processing.py/register_document/tsu_builder) 수정 필요 — 영향 범위 가장 넓음 |
| Rollback | 가능하나 4개 파일 diff를 모두 되돌려야 함 |

## Option B — External metadata registry lookup

별도 CLI 스크립트(`scripts/ingest_nae_source.py`, 신규)가 NAE manifest를 읽어 원문을 처리하고, `register_document()` 호출 후 registry dict를 직접 `.update()`하는 방식. **`scripts/ingest_logos_export.py`가 이미 이 패턴으로 운영 중** (NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md에서 확인).

| 평가 항목 | 내용 |
|---|---|
| 안정성 | 높음 — 이미 프로덕션에서 검증된 패턴(Logos ingest)을 복제. `core/tsu_builder.py`가 `doc.get(...)`으로 이미 additive하게 읽는 구조라 신규 위험 없음 |
| 기존 코드 영향 | 최소 — 신규 스크립트 1개 + `core/tsu_builder.py` 6~8줄. UI 업로드 파이프라인(`process_one_file`) 완전 무수정 |
| Rollback | 매우 높음 — 신규 스크립트를 삭제하고 `tsu_builder.py` diff만 되돌리면 됨. 이미 이 방식으로 들어간 문서/필드가 있어도 기존 필드 읽기 로직은 존재하지 않는 키를 요구하지 않으므로 무해 |

## Option C — Sidecar metadata file

원문 파일 옆에 `{stem}.nae_meta.json` 같은 사이드카 파일을 두고, ingest 시점에 같은 stem의 사이드카를 찾아 읽는 방식.

| 평가 항목 | 내용 |
|---|---|
| 안정성 | 중간 — 파일명 매칭(stem 일치)에 의존하므로 원본 파일명이 바뀌거나 재처리 시 사이드카가 누락/불일치할 위험 존재. `core/identity_registry.py`가 content-hash 기반 식별(파일명 아님)을 원칙으로 하는 기존 설계와 결이 다름(파일명 변경 시에도 `file_hash`로 문서를 추적하는 기존 원칙과 충돌 소지 — `find_by_file_hash`, SPRINT21-G-2 주석 참고) |
| 기존 코드 영향 | Option A와 유사하게 ingest 경로 내부에 사이드카 탐색 로직 추가 필요 — 신규 로직 규모는 Option B보다 큼 |
| Rollback | 가능하나 사이드카 탐색 로직 제거 + 이미 생성된 사이드카 파일 정리 두 가지가 필요해 Option B보다 절차 많음 |

## 비교 요약

| 옵션 | 안정성 | 코드 영향 | Rollback |
|---|---|---|---|
| A. DocumentContext 확장 | 중 | 큼 (4개 파일) | 중 |
| B. External registry lookup | **높음** | **최소 (2개 파일)** | **매우 높음** |
| C. Sidecar file | 중 (파일명 의존 리스크) | 중~큼 | 중 |

## 권장

**Option B 채택 권장.**

- 기존 검증된 선례(`scripts/ingest_logos_export.py`)를 그대로 재사용 — 새로운 위험을 도입하지 않음
- 코드 영향이 가장 작고(NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md 기준 신규 스크립트 1개 + `tsu_builder.py` 6~8줄), UI 업로드 파이프라인(`process_one_file`)을 전혀 건드리지 않아 기존 DBMA 문서 처리에 영향 없음이 구조적으로 보장됨
- Option C는 파일명 의존성이 기존 content-hash 기반 식별 원칙과 충돌할 수 있어 배제
