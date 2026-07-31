# NAE Metadata Policy v1.0

작성일: 2026-07-31
상태: 확정 정책 문서 (설계 결정 완료). 단, 코드 반영은 별도 승인 후 진행 — 본 문서는 정책만 확정한다.

## 1. theological_position

- **저장 위치**: document level (문서 1건당 1개 값)
- **Chunk inheritance**: 같은 문서에서 파생된 모든 chunk(TSU record)는 소속 문서의 `theological_position` 값을 그대로 상속한다 — chunk마다 독립적으로 재판단하지 않는다.
- **위치**: `nae_metadata.theological_position` (ADR_NAE_THEOLOGICAL_METADATA.md 옵션 A 채택)
- **값 형식**: NAE_SOURCE_SCHEMA_v1.md 제안안(6개: conservative_baptist, southern_baptist, reformed_baptist, general_baptist, historical_baptist, academic_historical) 기준, 단일 값. 다중 태그 필요성이 확인되면 후속 버전에서 배열로 확장 검토.

## 2. baptist_theme

- **기존 TSU 필드 재사용** (ADR-009 예약, 신규 필드 생성하지 않음 — NAE_METADATA_BLOCK_DESIGN_v1.md 결론 유지)
- **도입 방식**: Pilot annotation(TASK 3 템플릿) 결과를 먼저 수동으로 축적한 뒤, 패턴이 안정되면 자동 태깅 로직으로 전환. 즉 "자동화 우선"이 아니라 "수동 검증 → 자동화"의 단계적 접근.
- **자동화 착수 조건**: Pilot annotation이 최소 유의미한 표본(예: 10건 이상 문서)에서 일관된 태깅 기준을 확인한 이후. 이번 정책 문서는 자동화 로직 자체를 설계하지 않음 — 조건만 명시.

## 3. doctrine_category

- **controlled vocabulary 예정**: 자유 텍스트가 아닌 사전 정의된 통제 어휘집(controlled vocabulary)으로 운영할 예정.
- **현재 상태**: 어휘집 목록은 이번 정책에서 확정하지 않음 — Pilot annotation 결과를 참고해 별도 문서(`NAE_DOCTRINE_VOCABULARY_v1.md` 등, 다음 반복)에서 확정.
- **기존 TSU 필드 재사용** (baptist_theme과 동일 원칙)

## 4. denomination_context

- **Optional 필드로 확정** (필수 아님, null 허용)
- **용도**: historical/theological 맥락 서술 — 예: "Landmark movement에 대한 반박으로 저술됨", "남침례교 부흥운동 배경에서 작성됨"
- **위치**: `nae_metadata.denomination_context`
- **작성 주체**: 자동 생성 대상 아님. Pilot annotation 또는 후속 전문가 검토를 통해 수동으로만 채워짐.

## 5. content_genre

- **Multi-value array로 확정** (STEP3-B에서 "단일값 vs 배열" 미결정이었던 사항 해소)
- 근거: 한 문서가 복수 장르에 걸치는 경우(예: 주석이면서 설교집)가 실제로 존재할 수 있으므로 배열이 더 안전한 기본값
- **값 목록**: NAE_SOURCE_TYPE_MODEL_v1.md의 6개 값(confession/theology/history/commentary/sermon/mission) + 보류되었던 `church_practice`, `pastoral` 추가 확정 → 총 8개 값
- **위치**: `nae_metadata.content_genre` (배열)

## 6. file_format

- **별도 필드로 확정, 기존 `source_type` 그대로 유지** (NAE_SOURCE_TYPE_MODEL_v1.md 결론 재확인)
- `content_genre`(콘텐츠 장르)와 완전히 독립된 축 — 혼동 방지를 위해 정책 문서에 재명시
- 신규 값 `epub`, `txt`, `docx`는 기존 `pdf`/`md`와 나란히 `source_type` enum에 추가 예정이나, 기존 파이프라인의 실제 지원 여부는 별도 코드 조사로 확인 필요(정책 확정과 별개)

## `nae_metadata` 최종 스키마 (정책 확정, 코드 미반영)

```json
"nae_metadata": {
  "theological_position": null,
  "historical_period": null,
  "denomination_context": null,
  "content_genre": [],
  "publication_year": null,
  "copyright_status": null,
  "processing_status": null
}
```

- `denomination`(NAE_SOURCE_SCHEMA_v1.md 원래 필드)은 `theological_position`과 개념이 겹쳐 이번 정책에서 별도 필드로 유지하지 않기로 확정 — `theological_position` 값 자체가 교단(baptist)과 세부 입장을 함께 표현하므로 중복 제거.
- `baptist_theme`, `doctrine_category`, `source_provenance`는 기존 TSU 최상위 필드를 그대로 사용(이 블록에 포함하지 않음).

## 코드 반영 관련 주의

이 문서는 **정책 확정**이며 `core/tsu_builder.py` 등 실제 코드 변경을 지시하지 않는다. 코드 반영은 별도 Task Order와 승인이 필요하다.
