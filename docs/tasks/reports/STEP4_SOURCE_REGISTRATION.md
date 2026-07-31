# STEP4 Source Registration — The New Hampshire Confession of Faith (1833)

작성일: 2026-07-31
목적: STEP3_SAMPLE_DOCUMENT_SPEC.md 1순위 후보를 Pilot 대상으로 확정 등록. NAE_METADATA_POLICY_v1.md 확정 스키마 기준으로 채움.
주의: 이 문서는 **등록 명세**이며, 원문 확보(다운로드)나 실제 registry 기록은 포함하지 않는다.

## title

The New Hampshire Confession of Faith (1833)

## author/body

New Hampshire Baptist Convention (집단 저작 — 개인 저자 없음)

## year

1833

## copyright status

`public_domain` — 저술 200년 가까이 경과, 원문 원저작자(단체) 소멸, 미국/한국 저작권법 기준 모두 보호기간 만료로 판단. 실제 확보 시 구체 판본(스캔본 등)의 편집저작권 여부는 별도 확인 필요(NAE_PUBLIC_DOMAIN_CANDIDATES_v1.md 비고 원칙 유지).

## content_genre

`["confession"]` — NAE_METADATA_POLICY_v1.md §5 기준 단일 장르, 배열 형식 준수

## theological_position

`historical_baptist` — NAE_SOURCE_SCHEMA_v1.md 제안 enum 중 선택. 근거: 특정 현대 교단(남침례교 등)에 귀속되기보다 19세기 초 미국 침례교 전반에서 광범위하게 채택된 역사적 신앙고백이므로 `southern_baptist`보다 `historical_baptist`가 더 정확. document-level 값이며 NAE_METADATA_POLICY_v1.md §1에 따라 파생될 모든 chunk가 이 값을 상속.

## denomination_context

"Landmark 운동 이전, 초기 미국 침례교의 온건 칼빈주의(moderate Calvinist) 신앙고백으로 널리 채택됨. 이후 많은 침례교단 신앙고백의 원형(template) 역할을 함." — optional 서술형 필드, NAE_METADATA_POLICY_v1.md §4 기준. 이 서술은 일반적으로 알려진 역사적 배경에 근거한 초안이며, 실제 등록 시 원문/역사 자료 대조 검증 필요.

## provenance

```yaml
author: "New Hampshire Baptist Convention"
publication_year: 1833
copyright_status: public_domain
denomination_context: "위 denomination_context 참고"
source_url: null   # 미확보, 실제 확보 시 기입
acquisition_status: not_acquired  # 이번 STEP4에서 다운로드 미실행
```

## 등록 상태

- registry(`identity_registry.json`) 실제 기록: **미실행** — 이 문서는 등록에 필요한 값만 사전 확정
- 원문 파일: **미확보**
