# STEP3 Sample Document Spec

작성일: 2026-07-31
목적: TSU 파이프라인 검증용 테스트 문서 기준 정의. **아직 다운로드하지 않음.**

## 선정 조건

- Public Domain (저작권 문제 없음)
- Baptist 관련 자료
- 짧은 문서 (검증 목적 — 전체 파이프라인 실행 부담 최소화)
- 구조가 명확한 문서 (heading/조항 구분이 뚜렷해 `structure` 필드 검증 가능)

## 후보 (NAE_PUBLIC_DOMAIN_CANDIDATES_v1.md 기준 재검토)

| 항목 | 값 |
|---|---|
| title | New Hampshire Baptist Confession (1833) |
| author | New Hampshire Baptist Convention |
| year | 1833 |
| source_type | `confession` |
| 선정 이유 | 전체 분량이 짧고(18개 조항), 조항(article) 단위로 구조가 명확해 `heading_path`/`chunking` 검증에 적합. 성경 인용은 다수 포함하지만 본문 자체가 성경은 아니므로 `verse_mapping`이 대부분 비는 케이스(정상 동작)를 확인하기 좋음 |

대안 후보 (1순위 자료 확보 곤란 시):

| 항목 | 값 |
|---|---|
| title | The Baptist Confession of Faith (1689), 서문 및 1~5장 |
| author | Particular Baptist 목회자 연합 |
| year | 1689 |
| source_type | `confession` |
| 선정 이유 | 마찬가지로 조항 구조 명확, 다만 원문이 더 길어 "짧은 문서" 조건 충족을 위해 전체가 아닌 앞부분만 시범 사용 검토 |

## 필요 정보 (registry 등록 시 채울 값)

```yaml
title: "New Hampshire Baptist Confession (1833)"
author: "New Hampshire Baptist Convention"
year: 1833
source_type: confession
language: en
metadata:
  denomination: baptist
  theological_position: historical_baptist   # NAE_SOURCE_SCHEMA_v1.md 제안안 참고, 미확정
  copyright_status: public_domain
  processing_status: raw
```

## 비고

- 이 문서는 **선정 기준과 필요 정보 명세**만 다룸. 실제 원문 확보/다운로드는 STEP3 범위 밖(TASK 5 보고에서 "실제 파일럿 실행"을 별도 승인 요청 항목으로 명시할 예정).
- 최종 후보 확정은 HQ 검토 후 결정.
