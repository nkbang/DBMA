# NAE Source Metadata Schema v1

작성일: 2026-07-31
목적: 향후 TSU(Theological Source Unit) 변환 및 Vector Index 관리를 위한 소스 메타데이터 표준 정의.
현재 이 스키마는 설계 문서이며, 어떤 코드/파이프라인에도 아직 적용되지 않았다.

## 필드 정의

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `source_id` | string | Y | 고유 식별자. 형식 제안: `{denomination}-{source_type}-{sequence}` 예: `baptist-confession-001` |
| `title` | string | Y | 원문 제목 (원어 표기 병기 권장) |
| `author` | string | N | 저자명. 공저/무명 자료는 `unknown` 또는 편집자 표기 |
| `publication_year` | int | N | 최초 출판 연도. 불확실 시 `circa` 접두 텍스트 필드로 별도 표기 |
| `denomination` | enum | Y | `baptist` / `general_protestant` / `other` — [[project_nae_unified_search_v3]] 확장 범위와 연결 |
| `theological_position` | string (제안: enum) | N | 신학적 입장 태그. 현재 자유 텍스트, 하단 "enum 제안안" 참고 — 미확정 |
| `language` | enum | Y | `ko` / `en` / `grc`(헬라어) / `hbo`(히브리어) / `other` |
| `copyright_status` | enum | Y | `public_domain` / `licensed` / `unknown` — TASK 4 목록과 직접 연동 |
| `source_type` | enum | Y | `confession` / `history` / `theology` / `commentary` / `practice_guide` / `mission_report` / `sermon` / `other` |
| `processing_status` | enum | Y | `raw` / `staged` / `chunked` / `embedded` / `indexed` — 파이프라인 단계 추적용 |

## 설계 원칙

- 이 스키마는 `data/nae/metadata/`에 소스 1건당 1개 메타데이터 레코드(JSON/YAML)로 저장하는 것을 전제로 설계됨.
- `source_id`는 파일 경로가 아닌 논리 식별자로, 원본 파일이 `sources/{category}/`에서 `processed/`로 이동해도 불변.
- `processing_status`는 [[project_chunking_next_steps]]의 D-5 게이트 및 content_quality 검증 결과와 연동 가능하도록 예약.
- 기존 DBMA 코어 문서 메타데이터 스키마(`core/`)와는 별도 네임스페이스. 통합 여부는 향후 별도 검토.

## `theological_position` enum 제안안 (미확정)

아래는 검토용 제안 목록이며 최종 확정된 것이 아니다. HQ/CUE 후속 반복에서 확정 필요.

- `conservative_baptist`
- `southern_baptist`
- `reformed_baptist`
- `general_baptist`
- `historical_baptist`
- `academic_historical` (특정 신앙고백에 속하지 않는 학술/역사 서술)

주의사항:
- 위 목록은 미국 침례교 전통 분류에 편중되어 있어, 한국 침례교(기독교한국침례회 등) 맥락 반영 여부는 별도 검토 필요.
- 값이 상호 배타적이지 않을 수 있음(예: 한 자료가 `southern_baptist`이면서 `reformed_baptist` 성향일 수 있음) — 단일 enum이 아닌 다중 태그 구조로 전환할지 여부도 미결정.

## 미결정 사항 (다음 반복에서 확정 필요)

- `theological_position`의 enum 최종 확정 (위 제안안 검토 후)
- 헬라어/히브리어 원문 포함 자료의 `language` 다중값 처리 방식
- `source_id` 채번 규칙의 자동화 여부
