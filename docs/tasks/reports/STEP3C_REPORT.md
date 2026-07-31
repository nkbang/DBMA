# STEP3-C Report — NAE Metadata Policy Finalization

작성일: 2026-07-31

STATUS: PASS

## 작성/수정 파일

- [NAE_METADATA_POLICY_v1.md](NAE_METADATA_POLICY_v1.md) (신규) — 6개 항목(theological_position/baptist_theme/doctrine_category/denomination_context/content_genre/file_format) 정책 확정
- [ADR_NAE_THEOLOGICAL_METADATA.md](ADR_NAE_THEOLOGICAL_METADATA.md) (수정) — Proposal → Decision Record 초안. 정식 ADR 번호는 미부여 상태 유지.
- [NAE_PILOT_ANNOTATION_TEMPLATE.md](NAE_PILOT_ANNOTATION_TEMPLATE.md) (신규) — source/genre/theological_position/doctrine_category/baptist_theme/provenance 필드 포함
- 본 보고서

## 정책 확정 요약

| 항목 | 확정 내용 |
|---|---|
| theological_position | document level, chunk inheritance |
| baptist_theme | 기존 TSU 필드 재사용, Pilot annotation → 자동화 순서 |
| doctrine_category | 기존 TSU 필드 재사용, controlled vocabulary 예정(목록 미확정) |
| denomination_context | optional, 서술형, 수동 작성만 |
| content_genre | multi-value array, 8개 값(기존 6개 + church_practice/pastoral 추가) |
| file_format | 기존 `source_type` 필드 그대로 유지, content_genre와 독립 축 |

## 남은 미결정 사항

- `doctrine_category` controlled vocabulary 실제 목록 (Pilot annotation 결과 축적 후 도출 예정)
- `baptist_theme` 자동화 착수 시점 (Pilot 결과 확인 후 별도 승인)
- `epub` 파일 포맷의 기존 파이프라인 지원 여부 (코드 조사 필요, 미실행)
- 정식 ADR 번호 부여 시점 (Pilot 결과 반영 후 HQ 승인 대상)

## 다음 추천

- Pilot annotation 실행(NAE_PILOT_ANNOTATION_TEMPLATE.md 사용)을 위한 원문 확보(다운로드) 승인 요청 — 이번 STEP3-C는 정책/템플릿만 확정, 실행 없음
- Pilot 결과가 쌓이면 doctrine_category 어휘집 초안 도출 및 baptist_theme 자동화 착수 여부 재검토

## 금지 사항 준수 확인

- TSU 생성: 미실행
- Embedding: 미실행
- Vector DB 변경: 미실행
- Code 수정: 미실행
- Commit: 미실행
