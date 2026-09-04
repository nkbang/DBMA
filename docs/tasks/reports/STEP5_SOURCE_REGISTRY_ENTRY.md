# STEP5 Source Registry Final Entry Template

작성일: 2026-07-31
상태: **PREPARED**
스키마: NAE_SOURCE_REGISTRY_SCHEMA_v1.md 기준, STEP4_PILOT_SOURCE_ENTRY.md(REGISTERED-CANDIDATE)를 계승·최종화

## 레코드

```yaml
source_id: baptist-confession-001
title: "The New Hampshire Confession of Faith (1833)"
author: "New Hampshire Baptist Convention"
year: 1833
content_genre:
  - confession
theological_position: historical_baptist
denomination_context: >
  Landmark 운동 이전, 초기 미국 침례교의 온건 칼빈주의(moderate Calvinist)
  신앙고백으로 널리 채택됨. 이후 많은 침례교단 신앙고백의 원형(template)
  역할을 함.
provenance:
  copyright_status: public_domain
  preferred_source: CCEL
  backup_source: Internet Archive
  acquired_from: null
  acquired_url: null
  acquired_date: null
  verification_method: null
  verification_result: null
  checksum: null
acquisition_status: PREPARED
```

## 상태 값 설명 (acquisition_status)

이전 STEP4_PILOT_SOURCE_ENTRY.md의 `REGISTERED-CANDIDATE`에서 한 단계 진전:

| 상태 | 의미 |
|---|---|
| `REGISTERED-CANDIDATE` (이전 단계) | 값만 채워짐, 확보 계획도 미수립 |
| **`PREPARED` (현재 단계)** | 확보 계획(preferred/backup source, provenance 기록 방법, 저장 경로) 확정. **원문은 여전히 미확보** |
| `ACQUIRED` (다음 단계) | 원문 파일 실제 확보, `provenance.acquired_*` 필드 채워짐 |
| `VERIFIED` (그 다음 단계) | STEP4_PD_VERIFICATION.md 4단계 검증 완료 |
| `INGESTED` (최종 단계) | `scripts/ingest_nae_source.py` 실행 완료, registry(`identity_registry.json`) 반영 |

## 이번 문서에서 채워지지 않은 값 (의도적)

- `provenance.acquired_from`/`acquired_url`/`acquired_date`/`verification_method`/`verification_result`/`checksum`: 전부 `null` — 원문 확보 전이므로 값이 존재할 수 없음
- `local_path`(NAE_SOURCE_REGISTRY_SCHEMA_v1.md 원 필드): 이번 템플릿에서 생략 — STEP5_SOURCE_ACQUISITION_RECORD.md의 "Local Storage Plan"에 경로 계획만 명시(`data/nae/sources/baptist/nhc_1833.txt`), 실제 파일 존재 전까지 레코드에는 반영하지 않음

## 다음 상태 전환 조건

- `ACQUIRED`로 전환: HQ의 원문 확보(다운로드) 승인 + 실제 확보 완료
- `VERIFIED`로 전환: STEP4_PD_VERIFICATION.md 절차 실행 완료
- `INGESTED`로 전환: `ingest_nae_source.py` 실행 승인 + 실행 완료
