# STEP3 TSU Mapping

작성일: 2026-07-31
목적: `Source Metadata → Document Chunk → TSU → Embedding Metadata` 단계별 필드 매핑 검토. 신규 필드는 **제안만**, 스키마 변경 실행 없음.

## 단계별 흐름

```
Source Metadata (NAE_SOURCE_SCHEMA_v1.md)
        ↓ (ingest: core/processing.py)
Document Chunk (identity_registry.json documents[document_id])
        ↓ (core/tsu_builder.py::build_tsu_records)
TSU record (output/bench/tsu_dataset.jsonl)
        ↓ (core/retrieval.py::RetrievalEngine 소비)
Embedding Metadata (검색 시점에 참조되는 필드)
```

## 필드별 재사용 가능 여부

| NAE Source 필드 | 기존 registry/TSU 대응 필드 | 재사용 가능 여부 |
|---|---|---|
| `source_id` | `document_id` (registry 자동 생성) | 재사용 가능 — 단, NAE `source_id` 포맷(`{denomination}-{source_type}-{sequence}`)과 `document_id` 생성 규칙이 다를 수 있어 1:1 매핑 확인 필요 |
| `title` | `title` | 그대로 재사용 가능 |
| `author` | `author` | 그대로 재사용 가능 |
| `publication_year` | 대응 필드 없음 (registry에 `chapter`/`page`는 있으나 연도 없음) | **신규 필드 필요** |
| `denomination` | 대응 필드 없음 | **신규 필드 필요** |
| `theological_position` | 대응 필드 없음 (TSU의 `baptist_theme`/`doctrine_category`와 개념적으로 인접하지만 동일하지 않음 — 전자는 "이 문서/청크의 신학적 입장", 후자는 ADR-009 기준 "교리 분류 태그") | **신규 필드 필요**, 단 `baptist_theme`/`doctrine_category`와 관계 정리 필요 |
| `language` | `language` | 그대로 재사용 가능 |
| `copyright_status` | 대응 필드 없음. `source_provenance.rights`가 개념적으로 가장 근접(Logos export용으로 예약됨) | `source_provenance` 블록 확장 재사용 검토 가능 |
| `source_type` | `source_type` (현재 `pdf`/`md` 등 **파일 포맷** 의미로 사용 중 — SPRINT32-C 참고) | **충돌 주의**: 기존 `source_type`은 파일 포맷 축(pdf/md), NAE 스키마의 `source_type`은 콘텐츠 장르 축(confession/commentary) — 동명 필드지만 의미가 다름. 이름 재사용 금지, 별도 필드명 필요 |
| `processing_status` | 대응 필드 없음 (registry에 `superseded_by` 등 상태 유사 개념은 있으나 파이프라인 단계 추적용은 아님) | **신규 필드 필요** |

## 추가 필요 필드 제안 (TSU record, additive)

기존 TSU record 필드를 변경하지 않는 조건으로, `content_quality`/`structure`/`source_provenance`와 같은 패턴의 새 sibling 블록 제안:

```json
"nae_metadata": {
  "denomination": null,
  "theological_position": null,
  "content_genre": null,
  "publication_year": null,
  "copyright_status": null,
  "processing_status": null
}
```

- `content_genre`로 명명 제안한 이유: 기존 `source_type`(파일 포맷)과의 이름 충돌 회피
- 이미 존재하는 `baptist_theme`/`doctrine_category`/`theological_claim`(ADR-009 예약 필드)과는 별개로 유지 제안 — 저것들은 "콘텐츠 태깅 결과", `nae_metadata`는 "출처 문서 자체의 속성"으로 층위가 다름
- 이 블록은 **제안 단계**이며 코드 반영은 하지 않음

## Embedding Metadata 단계

- `core/retrieval.py::RetrievalEngine`이 현재 읽는 필드는 `tsu_id`, `content`, `verse_mapping.chapter`(및 관련) 중심으로 관측됨(STEP3_TSU_PIPELINE_ANALYSIS.md 참고)
- `nae_metadata`(제안) 같은 additive 블록은 즉시 검색 랭킹에 영향을 주지 않음 — `content_quality`/`structure`가 그랬듯 "태그만 하고 아직 소비하지 않는" 단계로 도입 가능
- 실제 검색 시점 소비(필터링/가중치)는 별도 Retrieval Sprint 범위 — 이번 STEP3에서는 다루지 않음

## 결론

- 기존 필드 재사용 가능: `title`, `author`, `language`, `document_id`(≈`source_id`)
- 이름 충돌 주의: `source_type` (의미 다름, 재사용 금지 권장)
- 신규 additive 블록 제안: `nae_metadata` (6개 하위 필드) — 실행은 별도 승인 필요
