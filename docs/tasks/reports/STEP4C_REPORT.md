# STEP4-C Report — NAE Metadata Adapter Design Finalization

작성일: 2026-07-31

## 판정

**READY** (설계 확정 — 코드 구현 자체는 별도 승인 필요)

## 근거

STEP4-B에서 미확정이었던 "core/processing.py의 NAE 메타데이터 lookup 메커니즘"이라는 핵심 블로커가, 기존 코드베이스 선례(`scripts/ingest_logos_export.py`) 재사용으로 **완전히 해소됨**:

- 코드 변경 범위가 4개 파일(~25~30줄, 미확정 lookup 로직 포함)에서 **2개 파일(신규 스크립트 1개 + `tsu_builder.py` 6~8줄)**로 축소
- `DocumentContext`/`core/processing.py`/`register_document()` 3개는 **완전 무수정**으로 확정 — 기존 UI 업로드 파이프라인과 완전히 격리된 경로
- Input Strategy 3옵션(A/B/C) 비교 결과 Option B가 안정성/영향범위/rollback 모든 기준에서 우위, 이미 프로덕션 검증된 패턴이므로 신규 리스크 없음

## 작성 파일

- [NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md](NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md) — injection point(신규 스크립트 1곳), data flow, affected modules(2개) / unchanged modules(4개)
- [NAE_METADATA_INPUT_STRATEGY.md](NAE_METADATA_INPUT_STRATEGY.md) — Option A/B/C 비교, **Option B 채택 권장**
- [NAE_METADATA_ADAPTER_TEST_PLAN.md](NAE_METADATA_ADAPTER_TEST_PLAN.md) — 4개 검증 항목(기존 문서 무영향/NAE 상속/TSU 출력 보존/검색 호환성), 우선순위 명시
- 본 보고서

## 확정된 설계 요약

| 항목 | 확정 내용 |
|---|---|
| Injection point | 신규 `scripts/ingest_nae_source.py` — `register_document()` 호출 후 `registry["documents"][doc_id].update({...})`로 additive 주입 |
| 수정 대상 | `core/tsu_builder.py`만 (nae_metadata 블록 구성, ~6~8줄) |
| 무수정 대상 | `DocumentContext`, `core/processing.py`, `core/identity_registry.py::register_document()`, `core/retrieval.py` |
| Input 방식 | Option B (External metadata registry lookup) — manifest 기반, Logos 선례 재사용 |
| 테스트 전략 | 신규 테스트 파일 분리 추가, 기존 TSU 관련 테스트로 회귀 확인 |

## 미결정 사항 (구현 시 참고)

- `scripts/ingest_nae_source.py`의 manifest 형식은 STEP4_PILOT_SOURCE_ENTRY.md/NAE_SOURCE_REGISTRY_SCHEMA_v1.md를 기반으로 하되, `scripts/ingest_logos_export.py`의 `_REQUIRED_MANIFEST_FIELDS` 같은 필수 필드 게이트를 NAE용으로 별도 정의해야 함 — 이번 문서에서는 설계 원칙만 확정, 정확한 manifest JSON 스키마는 구현 단계에서 확정
- `doctrine_category` controlled vocabulary는 여전히 미확정 (STEP3-C에서 이미 남겨진 사항, 이번 STEP4-C 범위 아님)

## 다음 단계

- 코드 구현(신규 스크립트 작성 + `tsu_builder.py` 수정) 착수는 **별도 Task Order 및 코드 수정 승인 필요** — 이번 STEP4-C는 설계 확정까지만 완료
- 구현 승인 시 NAE_METADATA_ADAPTER_TEST_PLAN.md 우선순위(TSU output preservation → 기존 문서 무영향 → NAE 상속 → 검색 호환성) 순서로 검증 진행 권장

## 금지 사항 준수 확인

- 코드 수정: 미실행
- TSU 생성: 미실행
- Embedding: 미실행
- Vector DB 변경: 미실행
- Git commit: 미실행
