# NAE Source Type Model v1

작성일: 2026-07-31
목적: STEP3_TSU_MAPPING.md에서 발견된 `source_type` 이름 충돌(기존=파일 포맷, NAE 스키마 초안=콘텐츠 장르)을 두 개의 독립된 축으로 명시적으로 분리.

## 문제

- 기존 registry/TSU의 `source_type`: 파일 포맷 축. 관측된 값: `pdf`, `md` 등 (`core/tsu_builder.py` SPRINT32-C 주석 기준)
- NAE_SOURCE_SCHEMA_v1.md 초안의 `source_type`: 콘텐츠 장르 축(confession/history/theology/...)
- 동일 필드명으로 서로 다른 개념을 가리키면 기존 파이프라인 코드(`source_type == "pdf"` 같은 조건 분기)와 충돌 위험 — [[feedback_avoid_risky_uncertain_design]] 원칙상 신뢰 안 된 이름 재사용은 지양

## 해결: 두 축 분리

### file_format (기존 `source_type` 필드 — 이름/의미 변경 없음, 그대로 유지)

| 값 | 설명 |
|---|---|
| `pdf` | PDF 원본 (기존 파이프라인 이미 처리) |
| `md` | Markdown 원본 (기존 파이프라인 이미 처리) |
| `epub` | EPUB — Public Domain 전자책에서 흔함. **기존 파이프라인 지원 여부 미확인, 조사 필요** |
| `txt` | 순수 텍스트 — Project Gutenberg 등에서 흔함 |
| `docx` | Word 문서 |

### content_genre (NAE_METADATA_BLOCK_DESIGN_v1.md의 `nae_metadata.content_genre`로 저장 — 신규, additive)

| 값 | 설명 | NAE_BAPTIST_LIBRARY_STANDARD_v1.md 분류 대응 |
|---|---|---|
| `confession` | 신앙고백서 원문 | Baptist Confessions |
| `theology` | 조직신학/교리 해설 | Baptist Theology |
| `history` | 역사 서술 | Baptist History |
| `commentary` | 성경 주석 | Biblical Commentary |
| `sermon` | 설교/설교집 | Pastoral Ministry와 교차 |
| `mission` | 선교 신학/역사/사례 | Missions |

- `church_practice`(교회 실행)와 `pastoral_ministry`(목회)는 이번 6개 값에 명시되지 않음 — NAE_BAPTIST_LIBRARY_STANDARD_v1.md 7개 분류 중 2개가 이번 지시서 목록에서 누락된 것으로 보임. 다음 반복에서 `church_practice`, `pastoral` 추가 여부 확인 필요(결정 필요 사항 참고).

## 매핑 예시

동일 문서라도 두 축이 독립적으로 값을 가짐:

```
New Hampshire Baptist Confession (1833), PDF 스캔본
  file_format: pdf
  content_genre: confession

Spurgeon 설교집, 순수 텍스트 파일
  file_format: txt
  content_genre: sermon
```

## 기존 코드 영향 확인

- `core/tsu_builder.py`에서 `source_type == "pdf"` 조건으로 `PdfHeadingProvider` 분기가 있음(SPRINT32-C) — 이 로직은 **file_format 축**을 사용하므로 그대로 유지되어야 하며, `content_genre` 도입이 이 분기에 영향을 주지 않음을 확인.
- `content_genre`는 신규 additive 필드이므로 기존 `if source_type == "pdf"` 등 어떤 기존 조건문도 건드리지 않음.

## 결정 필요 사항

1. `epub` 파일 포맷의 기존 파이프라인(`core/processing.py`) 지원 여부 확인 (이번 문서는 설계만, 코드 조사는 범위 밖)
2. `content_genre`에 `church_practice`, `pastoral` 추가 여부
3. 한 문서가 복수 장르에 걸치는 경우(예: 주석이면서 설교집) 처리 방식 — 단일 값 vs 배열
