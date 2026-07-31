# STEP3-B Report — NAE Metadata Architecture Review

작성일: 2026-07-31

STATUS: PASS

## 작성 파일

- [NAE_METADATA_BLOCK_DESIGN_v1.md](NAE_METADATA_BLOCK_DESIGN_v1.md) — `nae_metadata` additive 블록 설계, 8개 필드 제안. `baptist_theme`/`doctrine_category`/`source_provenance`는 기존 필드 재사용 원칙 명시.
- [NAE_SOURCE_TYPE_MODEL_v1.md](NAE_SOURCE_TYPE_MODEL_v1.md) — `file_format`(기존 `source_type` 그대로 유지) vs `content_genre`(신규, `nae_metadata` 하위) 축 분리.
- [ADR_NAE_THEOLOGICAL_METADATA.md](ADR_NAE_THEOLOGICAL_METADATA.md) — Proposal 형태. `theological_position` 위치(nae_metadata 내부 권장), `baptist_theme`/`doctrine_category`와의 층위 차이(document-level vs chunk-level) 정리.
- 본 보고서

## 결정 필요 사항

1. `theological_position`을 chunk-level 반복 저장할지 document-level 1회 저장할지 (NAE_METADATA_BLOCK_DESIGN_v1.md)
2. `baptist_theme`/`doctrine_category` 태깅 로직을 NAE 자료부터 먼저 착수할지 — ADR-009 범위 확장이 필요한 결정 (ADR_NAE_THEOLOGICAL_METADATA.md)
3. `denomination_context` 필드의 실제 필요성 — 활용처 불분명, 보류 후보
4. `content_genre`에 `church_practice`, `pastoral` 값 추가 여부 (NAE_BAPTIST_LIBRARY_STANDARD_v1.md 7개 분류 중 2개가 이번 지시서 목록에 없었음)
5. `epub` 파일 포맷의 기존 파이프라인 지원 여부 (코드 조사 필요, 이번 범위 밖)
6. 한 문서가 복수 `content_genre`에 걸치는 경우 단일값 vs 배열 처리

## Pilot TSU 생성 준비 여부

**미준비 (Not Ready).**

이유:
- `nae_metadata` 블록이 아직 Proposal 단계이며 코드에 반영되지 않음 — 파일럿을 지금 실행하면 STEP3_VALIDATION_PLAN.md의 "Metadata Inheritance" 기준에서 애초에 실패가 예정된 필드(`theological_position` 등)를 검증하게 되어 의미 있는 신호를 얻기 어려움
- 위 결정 필요 사항 1~4가 해소되어야 `nae_metadata` 스키마가 코드 반영 가능한 최종 형태가 됨
- 반대로 STEP3_VALIDATION_PLAN.md의 5개 기준 중 **Chunk Completeness, Citation Traceability, Retrieval Readiness는 지금도 검증 가능** — `nae_metadata` 없이도 기존 필드(`title`/`author`/`document_id` 등)만으로 판단되는 항목이기 때문

## 다음 추천

- 결정 필요 사항 1~4는 HQ 판단 필요 (기술적 조사로 해소되지 않는 정책적 결정)
- 5(epub 지원 여부)는 코드 조사로 해소 가능 — 별도 Task Order로 승인 요청 가능
- 위 결정이 완료되기 전이라도, `nae_metadata` 없이 검증 가능한 3개 기준(Chunk Completeness/Citation Traceability/Retrieval Readiness)만으로 제한된 범위의 dry-run 파일럿을 먼저 진행하는 것도 대안으로 고려 가능 — 단, 이는 이번 보고서 범위를 벗어나는 제안이며 별도 승인 필요

## 금지 사항 준수 확인

- TSU 생성: 미실행
- Vector 생성: 미실행
- 코드 수정: 미실행
- Git commit: 미실행
