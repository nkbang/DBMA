# STEP3 Report — TSU Conversion Pipeline Validation v1.0

작성일: 2026-07-31

STATUS: PASS

## FILES

- [STEP3_TSU_PIPELINE_ANALYSIS.md](STEP3_TSU_PIPELINE_ANALYSIS.md) — 기존 파이프라인 구조/입출력/NAE 적용 가능성 조사
- [STEP3_SAMPLE_DOCUMENT_SPEC.md](STEP3_SAMPLE_DOCUMENT_SPEC.md) — 검증용 시범 문서 기준 (New Hampshire Confession 1833 1순위)
- [STEP3_TSU_MAPPING.md](STEP3_TSU_MAPPING.md) — 필드 매핑 검토, `nae_metadata` additive 블록 제안
- [STEP3_VALIDATION_PLAN.md](STEP3_VALIDATION_PLAN.md) — 5개 검증 기준 및 파일럿 실행 계획(미실행)
- 본 보고서

## ISSUES

1. **`source_type` 이름 충돌**: 기존 TSU/registry의 `source_type`은 파일 포맷(pdf/md) 의미로 이미 사용 중. NAE 스키마의 `source_type`(confession/commentary 등 콘텐츠 장르)과 동명이의 — 필드명 재사용 시 혼란 위험. TASK 3에서 `content_genre`로 별칭 제안함.
2. **`theological_position`와 기존 `baptist_theme`/`doctrine_category`의 관계 미정리**: 기존 TSU는 ADR-009 기준 콘텐츠 태깅용 예약 필드(`baptist_theme`, `doctrine_category`, `theological_claim`)를 이미 갖고 있음. NAE의 `theological_position`(출처 문서 자체의 입장)과 개념적으로 겹치거나 보완 관계일 수 있어, 두 체계를 병존시킬지 통합할지는 미결정.
3. **`verse_mapping`이 대부분 비게 됨은 정상**: Baptist 신학 문서는 성경 본문이 아니므로 `verse_mapping`이 비는 것은 파이프라인 결함이 아니라 스키마상 정상 케이스(book_id=UNK 처리 경로가 이미 이를 지원).

이슈는 모두 "설계상 결정 필요" 항목이며, 파이프라인 코드 결함이나 실행 중 오류가 아님.

## RECOMMENDATION

1. `nae_metadata` additive 블록(6개 필드: denomination, theological_position, content_genre, publication_year, copyright_status, processing_status) 설계를 HQ 검토 후 확정
2. `theological_position` vs `baptist_theme`/`doctrine_category` 관계 정리를 별도 설계 결정(ADR급)으로 승격 검토
3. STEP3_VALIDATION_PLAN.md의 파일럿(1건, dry-run) 실행을 별도 Task Order로 승인 요청 — 이번 STEP3는 계획/조사만 완료, 실제 TSU 생성/embedding 미실행

## 금지 사항 준수 확인

- git commit: 미실행
- git push: 미실행
- source code 수정: 미실행 (읽기 전용 조사만 수행)
- 실제 TSU 생성: 미실행
- embedding 실행: 미실행
