# NAE Manifest & Authority SSOT

| 항목 | 경로 | 역할 | Writer | Authority |
|------|------|------|--------|-----------|
| **M2** (SSOT) | `NAE/pipeline/registration/state/source_manifest.yaml` | Source Registry (14 records, schema '1.2') | registration pipeline (`manifest_writer.py`) | **최종 권위** |
| **M1** (mirror) | `NAE/authority/source_manifest.yaml` | Authority Mirror (10 records, schema '1.2') | derived from M2 | non-authoritative |
| **M3** (backlog) | `NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv` | Acquisition Backlog Tracker (25 rows, CSV) | acquisition layer | backlog only |

## Category (TSU) vs Authority Class (M2) 계층 구분

ADR-030 v2.1 §7에 따라 두 분류 체계는 완전히 분리된다:

| 계층 | 필드 | 수준 | 정의 |
|------|------|------|------|
| **TSU** (document-level) | `content_genre`, `theological_category` | 문서 단위 | 실제 TSU record의 콘텐츠/신학적 분류 |
| **M2 Source** (governance-level) | `authority_class` | source 단위 | source-level governance classification |

```
author → work → edition → source_file → authority_class (M2 governance)
                                      → content_genre (TSU document)
                                      → theological_category (TSU document)
```

## M2 Schema 필드 (ADR-030 §5)

- `authority_class`: enum — `primary_doctrinal | historical_witness | reference | application`
- `content_genre`: list[str] — document-level content classification
- `theological_category`: list[str] — document-level theological classification
- `tradition`: str — source의 신학적 전통/교파 소속
- `raw_path`: str — RAW 디렉토리 내 원본 파일 상대 경로
- `checksum_target`: str — 해시 계산 대상 식별자

모든 필드 `required: false`. 미결정 레코드는 키 자체를 생략 (WARNING-first, ADR §7.5).

## References

- ADR-030 v2.1 §7 (Source Authority Model)
- ADR-030 v2.1 §8 (Manifest & Authority SSOT)
- `resources/theological_sources/modern/source_manifest.schema.yaml` (M2 governing schema)
