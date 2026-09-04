# NAE Metadata Block Design v1

작성일: 2026-07-31
목적: 기존 TSU record를 변경하지 않는 additive `nae_metadata` 블록 설계. 코드 반영 없음 — 설계 문서.

## 설계 원칙

- 기존 TSU 필드(`tsu_id`, `content`, `verse_mapping`, `title`, `author`, `content_quality`, `structure`, `baptist_theme`, `doctrine_category`, `theological_claim`, `source_provenance` 등) **변경 금지, 삭제 금지**
- `nae_metadata`는 `content_quality`/`structure`와 동일한 패턴의 additive sibling 블록 — 값이 없으면 `null` 또는 빈 배열, 절대 추론/기본값 생성 금지 (기존 코드베이스 "모르면 비워둔다" 원칙, [[feedback_industry_standard_practices]] 준수)
- 기존에 이미 예약된 `baptist_theme`/`doctrine_category`/`theological_claim`/`source_provenance`와의 **중복을 만들지 않는 것**이 핵심 설계 목표 — 아래 검토에서 각 필드별로 기존 필드와의 관계를 명시

## 검토 대상 필드별 분석

### theological_position
- 기존 대응 필드 없음.
- **역할 구분**: 이 필드는 "출처 문서 자체가 표방하는 신학적 입장/전통"(예: `southern_baptist`, `reformed_baptist`) — 문서 단위(document-level) 속성에 가깝다.
- `nae_metadata`에 포함 **권장**. 단, chunk마다 반복 저장할지 document 레벨에서 한 번만 저장할지는 미결정(TASK 3 ADR 후보에서 다룸).

### baptist_theme
- **기존 TSU 필드(ADR-009, 이미 예약됨)**와 이름이 동일.
- `nae_metadata`에 새로 만들지 않고 **기존 필드를 그대로 재사용**하는 것을 권장. 이는 "이 chunk가 다루는 침례교 신학 주제" — content-level 태깅으로 이미 설계된 자리와 정확히 일치.
- 단, ADR-009는 "태깅 로직은 아직 미승인"이라고 명시 — NAE 자료에 한해 이 필드를 채우기 시작하려면 ADR-009 범위를 벗어나는 새로운 결정이 필요(TASK 3 ADR 후보 대상).

### doctrine_category
- baptist_theme과 동일한 상황 — **기존 TSU 필드(ADR-009 예약)** 재사용 권장, 신규 필드 불필요.

### source_provenance
- **기존 TSU 필드(Logos export용으로 이미 예약, additive, None 기본값)**와 이름 동일.
- 현재 하위 필드(`source_tier`, `logos_location`, `rights`, `export_method`, `content_hash`, `review_status`)는 Logos 특화. NAE Public Domain 자료에는 `logos_location`/`export_method` 같은 필드가 의미 없음.
- 옵션 A: 기존 `source_provenance`를 범용화(Logos 전용 필드는 optional 유지, NAE용 필드 추가) — 재사용이지만 스키마 확장 필요
- 옵션 B: `nae_metadata` 안에 별도 `copyright_status`/`public_domain_basis` 필드 신설 — 이름 충돌 없음, 그러나 "출처 근거"라는 개념이 두 블록에 분산됨
- **권장**: 옵션 B (분산이지만 명확). Logos 전용 스키마를 신학 출처 일반 스키마로 억지로 넓히면 SPRINT 히스토리의 additive-only 원칙과 충돌 우려.

### historical_period
- 기존 대응 필드 없음. NAE_SOURCE_SCHEMA_v1.md의 `publication_year`보다 넓은 개념(예: "17세기 초기 침례교", "19세기 남침례교 부흥운동기") — 자유 텍스트 또는 세기 단위 enum 검토 대상.
- `nae_metadata`에 포함 권장. `publication_year`(연도, 숫자)와는 별개로 유지 — 하나는 정확한 연도, 하나는 서술적 시대 분류.

### denomination_context
- 기존 `denomination`(NAE_SOURCE_SCHEMA_v1.md)과 유사하나, "이 문서가 다른 교단과 대비하여 어떤 맥락에서 저술되었는가"(예: "Landmark movement에 대한 반박으로 작성됨")를 포착하려는 의도로 추정.
- `denomination`(단순 분류 태그)과 `denomination_context`(서술적 배경)는 역할이 다르므로 병존 가능 — 단, 실제 활용처가 불분명해 **우선순위 낮음으로 보류 제안**.

## `nae_metadata` 블록 최종 제안 (Proposal, 미확정)

```json
"nae_metadata": {
  "denomination": null,
  "theological_position": null,
  "historical_period": null,
  "denomination_context": null,
  "content_genre": null,
  "publication_year": null,
  "copyright_status": null,
  "processing_status": null
}
```

- `baptist_theme`, `doctrine_category`는 **여기 포함하지 않음** — 기존 TSU 최상위 필드를 그대로 재사용
- `source_provenance`는 **여기 포함하지 않음** — 기존 필드를 재사용하되 NAE 자료는 대부분 `null`(Logos 출처가 아니므로), 저작권 정보는 `nae_metadata.copyright_status`로 별도 관리

## 결정 필요 사항 (다음 반복)

1. `theological_position`을 chunk-level로 반복 저장할지 document-level 1회만 저장할지
2. `baptist_theme`/`doctrine_category` 태깅 로직을 NAE 자료에 한해 먼저 시작할지 여부 — ADR-009 범위 확장 필요
3. `denomination_context` 실제 필요성 재확인 (보류 후보)
