# NAE Metadata Adapter Architecture v1

작성일: 2026-07-31
결정 배경: Path B(nae_metadata additive block) 채택. 코드 수정 전 최소 변경 설계 확정 문서.

## 핵심 발견 — 기존 선례 재사용

STEP4-B(STEP4_METADATA_ADAPTER_PROPOSAL.md)에서 4개 파일(DocumentContext/processing.py/register_document/build_tsu_records) 수정을 제안했으나, 코드 조사 결과 **거의 동일한 문제를 이미 해결한 선례가 존재**함을 확인:

`scripts/ingest_logos_export.py` — Logos 외부 자료 ingest 시 `source_tier`/`logos_location`/`rights`/`export_method`/`review_status`를 registry에 주입하는 기존 스크립트. 방식:

```python
metadata = build_document_metadata(content=..., title=..., author=..., doc_type="logos_export")
record, is_new = register_document(registry, metadata, output_dir)
# register_document()의 고정 스키마를 수정하지 않고, 반환된 registry dict를 직접 update
registry["documents"][document_id].update({
    "source_tier": entry["source_tier"],
    ...
})
```

- `core/tsu_builder.py`는 이 필드들을 이미 `doc.get("source_tier")` 형태로 **additive하게 읽고 있음**(`source_provenance` 블록, STEP3_TSU_PIPELINE_ANALYSIS.md에서 이미 확인) — 즉 **tsu_builder.py도 수정 없이 그대로 재사용 가능**했던 선례.
- 이 패턴을 NAE에 그대로 적용하면 STEP4-B에서 제안했던 4개 파일 수정 중 **`DocumentContext`/`core/processing.py`/`register_document()` 3개는 수정 불필요**로 축소됨.

## Injection Point

**단일 지점**: 신규 스크립트 `scripts/ingest_nae_source.py`(가칭, Logos 스크립트와 대칭 이름) 내부에서, `register_document()` 호출 직후 `registry["documents"][document_id].update({...})`로 NAE 필드 주입.

- 기존 4개 파일 중 수정이 필요한 곳은 **`core/tsu_builder.py` 단 1곳** — registry에서 `doc.get("nae_theological_position")` 등을 읽어 `record["nae_metadata"]` 블록을 구성하는 부분(기존 `source_provenance` 처리부와 동일 패턴)

## Data Flow

```
NAE manifest.json (사람이 직접 작성 — STEP4_PILOT_SOURCE_ENTRY.md 형식)
  ↓
scripts/ingest_nae_source.py (신규)
  - 원문 추출 (기존 core/extractors.py 재사용)
  - 청킹 (기존 로직 재사용)
  - build_document_metadata() + register_document() (기존 함수, 무수정 호출)
  - registry["documents"][doc_id].update({nae_theological_position, ...}) — additive 직접 주입
  ↓
identity_registry.json (nae_* 키 additive 저장)
  ↓
core/tsu_builder.py::build_tsu_records() — 【유일한 수정 지점】
  - doc.get("nae_theological_position") 등을 읽어 record["nae_metadata"] 블록 구성
  ↓
output/bench/tsu_dataset.jsonl (nae_metadata 블록 포함 TSU record)
  ↓
core/retrieval.py — 무수정, 새 필드 미소비이므로 검색 동작 불변
```

## Affected Modules

| 모듈 | 변경 여부 | 비고 |
|---|---|---|
| `scripts/ingest_nae_source.py` (신규) | 신규 생성 | `scripts/ingest_logos_export.py` 구조 복제 |
| `core/tsu_builder.py` | 수정 (약 6~8줄) | `nae_metadata` 블록 구성 추가, 기존 `source_provenance` 처리부와 동일 위치·패턴 |

## Unchanged Modules

| 모듈 | 이유 |
|---|---|
| `core/document_context.py` (`DocumentContext`) | Logos 선례처럼 registry dict 직접 update로 우회 — dataclass 필드 추가 불필요 |
| `core/processing.py` (`process_one_file` 등) | NAE ingest는 별도 스크립트 경로(Logos와 동일)이므로 기존 UI 업로드 파이프라인 미경유 |
| `core/identity_registry.py` (`register_document()`) | 고정 스키마 그대로 유지, 신규 필드는 반환된 dict에 직접 update |
| `core/retrieval.py` | additive 필드 미소비, 검색 로직 무영향 |

## STEP4-B 대비 변경점

- STEP4-B 제안(4개 파일, ~25~30줄) → STEP4-C 확정(**2개 파일**: 신규 스크립트 1개 + `tsu_builder.py` 6~8줄) — 기존 코드 수정 범위가 대폭 축소됨
- STEP4-B에서 "미확정"으로 남았던 `core/processing.py`의 NAE 메타데이터 lookup 메커니즘 문제 자체가 **해소됨** — 별도 스크립트 경로를 쓰면 UI 업로드 파이프라인에 lookup을 끼워 넣을 필요가 없음(Logos 자료도 UI 업로드가 아닌 CLI manifest 경로로만 들어옴)
