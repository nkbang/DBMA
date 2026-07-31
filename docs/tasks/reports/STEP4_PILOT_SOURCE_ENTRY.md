# STEP4 Pilot Source Entry

작성일: 2026-07-31
스키마: NAE_SOURCE_REGISTRY_SCHEMA_v1.md
상태: **REGISTERED-CANDIDATE** (원문 다운로드 전)

## 레코드

```yaml
source_id: baptist-confession-001
title: "The New Hampshire Confession of Faith (1833)"
author: "New Hampshire Baptist Convention"
year: 1833
publisher: "New Hampshire Baptist Convention"
copyright_status: public_domain
provenance:
  source_url: null
  acquisition_status: not_acquired
  acquisition_date: null
content_genre:
  - confession
theological_position: historical_baptist
denomination_context: >
  Landmark 운동 이전, 초기 미국 침례교의 온건 칼빈주의(moderate Calvinist)
  신앙고백으로 널리 채택됨. 이후 많은 침례교단 신앙고백의 원형(template)
  역할을 함.
local_path: null
```

## 상태 설명

- `REGISTERED-CANDIDATE`: 이 문서에 값이 채워졌으나, **원문 파일은 아직 존재하지 않음**. `identity_registry.json`에도 아직 반영되지 않음.
- `local_path: null`은 의도적 — 원문 다운로드가 승인·완료된 후에만 실제 경로(예: `data/nae/sources/baptist/nhc_1833.txt`)로 채워질 예정.
- `provenance.acquisition_status: not_acquired`가 이 문서 전체의 실질적 상태를 대표함.

## 다음 상태로 전환하는 조건

- `acquired`: HQ가 원문 확보(다운로드)를 승인하고 실제로 파일이 확보된 이후
- `verified`: 확보된 원문의 Public Domain 근거(STEP4_PD_VERIFICATION.md 절차)를 실제로 검증 완료한 이후

## 출처 (STEP4_SOURCE_REGISTRATION.md 재확인)

이 레코드는 이전 STEP4_SOURCE_REGISTRATION.md 명세를 NAE_SOURCE_REGISTRY_SCHEMA_v1.md 형식으로 재구성한 것 — 내용상 새 결정 없음, 형식 통일만 수행.
