# ADR (Decision Record 초안): NAE Theological Metadata 배치

작성일: 2026-07-31
갱신일: 2026-07-31 (STEP3-C, Proposal → Decision Record 초안으로 전환)
상태: **Decision Record 초안 — 최종 ADR 번호 미부여.** NAE_METADATA_POLICY_v1.md 확정에 따라 아래 결정 사항은 정책으로 채택되었으나, 정식 ADR 번호 부여 및 `docs/architecture/adr/` 편입은 별도 HQ 승인 후 진행한다.

## 배경

STEP3 조사(STEP3_TSU_PIPELINE_ANALYSIS.md)에서 기존 TSU 스키마가 `baptist_theme`, `doctrine_category`, `theological_claim` 3개 필드를 ADR-009 기준으로 이미 예약해두었으나 태깅 로직은 미승인 상태임을 확인. NAE 자료 도입 시 이 기존 예약 필드와 신규 `nae_metadata.theological_position`이 개념적으로 인접해 관계 정리가 필요.

## 검토 대상

### 1. theological_position 위치

**옵션 A**: `nae_metadata` 블록 내부에 위치 (NAE_METADATA_BLOCK_DESIGN_v1.md 제안대로)
- 장점: 기존 ADR-009 예약 필드를 건드리지 않음. NAE 전용 확장으로 명확히 격리됨
- 단점: 향후 NAE 외 다른 신학 전통(예: 장로교, 감리교) 자료를 추가할 때 `nae_metadata`라는 이름 자체가 좁아짐

**옵션 B**: 기존 최상위 필드로 승격 (예: `theological_position`을 `baptist_theme`처럼 TSU record 최상위에 추가)
- 장점: 향후 다른 교단 자료 확장 시 이름이 자연스러움
- 단점: TSU 최상위 스키마 변경 — "기존 TSU 변경 없이"라는 이번 Task Order 원칙과 충돌 소지

**결정**: 옵션 A 채택 확정 (NAE_METADATA_POLICY_v1.md §1). 최상위 스키마 확장은 이번 범위 밖이며, 필요 시 별도 승인을 거쳐 진행.

### 2. baptist_theme 관계

- 기존 `baptist_theme`(ADR-009 예약, chunk-level 콘텐츠 태깅)과 NAE `theological_position`(document-level 출처 속성)은 **층위가 다르다**:
  - `baptist_theme`: "이 chunk가 다루는 신학 주제는 무엇인가" (예: `["침례_예식", "교회_정치"]`)
  - `theological_position`: "이 문서를 저술한 전통/입장은 무엇인가" (예: `southern_baptist`)
- 두 필드는 **독립적으로 병존 가능**하며 통합할 필요 없음. 다만 `baptist_theme` 태깅 로직을 NAE 자료부터 먼저 시작할지는 ADR-009의 "아직 확정하지 않는 것" 범위를 벗어나는 결정이므로 별도 승인 필요.

### 3. doctrine_category 관계

- `baptist_theme`과 유사한 상황 — content-level 태깅이며 `theological_position`(document-level)과 층위가 다름.
- `doctrine_category`가 채워지기 시작하면 `nae_metadata.theological_position`과 함께 검색 필터링(예: "Reformed Baptist 입장의 침례 교리 자료만") 조합이 가능해지는 설계 잠재력이 있음 — 단, 이는 향후 Retrieval Sprint 범위이며 이번 ADR 제안에서는 가능성만 기록.

## 결정 사항 (Decision, STEP3-C 정책 확정 반영)

1. `theological_position`은 `nae_metadata` 블록 내부, **document-level 저장 + chunk inheritance** 방식으로 확정 (NAE_METADATA_POLICY_v1.md §1)
2. `baptist_theme`/`doctrine_category`는 기존 필드 그대로 재사용 확정, NAE 전용 신규 필드 생성하지 않음. `doctrine_category`는 향후 controlled vocabulary로 운영 예정(어휘집은 미확정, 별도 문서)
3. `baptist_theme` 태깅은 **자동화 우선이 아니라 Pilot annotation(수동) → 자동화 전환** 순서로 착수 확정 (NAE_METADATA_POLICY_v1.md §2). 자동화 착수 자체는 여전히 ADR-009 범위 확장에 해당하므로, Pilot 결과 확인 후 별도 승인 필요.

## 정식 ADR 전환 조건 (남은 절차)

- 위 결정 사항은 정책 문서(NAE_METADATA_POLICY_v1.md) 수준에서 확정되었으나, 정식 ADR 번호 부여는 아직 보류
- `nae_metadata` 블록의 최종 필드 목록은 NAE_METADATA_POLICY_v1.md로 확정 완료
- Pilot annotation(NAE_PILOT_ANNOTATION_TEMPLATE.md) 실행 결과를 반영해 최종 검토 후, HQ 승인 시 `docs/architecture/adr/` 규칙에 따라 정식 ADR 번호 부여 및 파일 이동 (이번 단계에서는 미실행)
