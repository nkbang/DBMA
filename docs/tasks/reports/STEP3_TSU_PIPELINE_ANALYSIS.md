# STEP3 TSU Pipeline Analysis

작성일: 2026-07-31
조사 방식: 읽기 전용 (grep/코드 열람), 코드 수정 없음.

## 현재 Pipeline 구조

```
원본 문서 (data/raw/ 등, DEFAULT_RAW_DIR)
  → core/processing.py (추출·정제·청킹, identity_registry에 문서 메타 기록)
  → output/{stem}_chunks.txt, identity_registry.json (DEFAULT_OUTPUT_DIR)
  → core/tsu_builder.py::build_tsu_records() (registry + chunk 텍스트 읽기 전용 소비)
  → core/tsu_builder.py::write_tsu_dataset() → output/bench/tsu_dataset.jsonl
  → core/tsu_builder.py::write_manifest() → output/bench/tsu_manifest.json
  → core/retrieval.py::RetrievalEngine (tsu_dataset.jsonl 소비, 검색 시점)
```

- CLI 진입점: `scripts/build_tsu_dataset.py` (argparse wrapper, 라이브러리 로직은 `core/tsu_builder.py`로 이미 승격됨 — SPRINT20-I-C-2-B)
- 실행: `python -m scripts.build_tsu_dataset --output-dir output [--dry-run]`
- ingest(`core/processing.py`)와 TSU 생성은 분리된 배치 후처리(batch post-processing)이며, 쿼리 시점(`core/retrieval.py`)과도 분리 — 기존 설계 원칙(SPRINT17-RG-5) 유지 확인.

## Input Specification

- 입력: `identity_registry.json`(`core/identity_registry.py`가 관리)의 `documents` 딕셔너리 + `output/{stem}_chunks.txt`(청크 텍스트)
- registry 문서 레코드 필드(관측): `source_file`, `chunk_count`, `language`(기본값 `-`), `source_type`, `book`, `title`, `author`, 그 외 `chapter`, `page`, `batch_id`가 ingest 시점에 함께 기록됨
- `source_tier`, `logos_location`, `rights`, `export_method`, `content_hash`, `review_status`는 registry에 **선택적으로만** 존재 — Logos export 등 외부 출처 문서를 위해 이미 예약된 필드(문서 없으면 `record["source_provenance"] = None`)
- 원본 문서는 `DEFAULT_RAW_DIR`(config.yaml `raw_dir`)에서 읽힘. PDF는 `collect_pdf_spans()`로 별도 heading 처리 경로를 탐

## Output TSU Structure

`output/bench/tsu_dataset.jsonl` — 레코드(JSONL, 1줄 1 TSU)당 필드:

| 필드 | 상태 |
|---|---|
| `tsu_id`, `document_id`, `chunk_id`, `content` | 필수, 항상 채워짐 |
| `verse_mapping` (`book_id`/`chapter`/`verse_start`/`verse_end`) | **성경 참조 전용** — book_id가 `UNK`이면 빈 dict |
| `themes` | 존재하지만 미사용 (빈 배열 고정) |
| `title`, `author`, `chapter`, `page`, `source_file`, `language`, `source_type` | registry 값 그대로 전파 |
| `content_quality` (`noise_type`/`quality_score`/`section_type`) | additive, SPRINT28-B |
| `structure` (`heading_path`/`heading_depth`/`heading_confidence`/`heading_source`) | additive, SPRINT29-C/32-C |
| `theological_claim`(None), `doctrine_category`([]), `baptist_theme`([]) | **이미 예약된 필드** — ADR-009, 아직 태깅 로직 없음(구조만 존재) |
| `source_provenance` (또는 None) | Logos 등 외부 출처 전용, additive |

manifest(`tsu_manifest.json`): `tsu_count`, `source_document_count`, `build_commit`, `dataset_sha256` 등 무결성/추적 메타.

## NAE 적용 가능 여부

**부분적으로 적용 가능, 그러나 핵심 가정 하나가 NAE 자료와 어긋남:**

1. `verse_mapping`은 **성경 본문 청크 전용**으로 설계되어 있다. `book_id`가 매칭되지 않으면(`UNK`) 빈 dict로 남으며, 이는 정상 동작(모르면 비워둔다 원칙). Baptist Confessions/History/Theology 자료는 성경 구절을 인용은 하지만 자체가 성경 본문은 아니므로, 대부분의 청크에서 `verse_mapping`이 비게 될 것으로 예상됨 — **이는 파괴적이지 않다** (스키마상 정상 케이스이며 `core/retrieval.py`가 이를 이미 옵셔널로 다룸).
2. `baptist_theme`, `doctrine_category`, `theological_claim` 필드가 **이미 스키마에 예약되어 있다** — ADR-009 기준 "아직 태깅 로직 미승인" 상태. NAE_SOURCE_SCHEMA_v1.md의 `theological_position`/`source_type` 설계와 개념적으로 맞닿아 있어, 향후 이 필드들을 채우는 것이 자연스러운 확장 경로로 보임.
3. `source_provenance`는 이미 "외부 출처(비-DBMA 원본) 문서"를 위해 설계된 옵셔널 블록 — NAE Public Domain 자료의 출처 추적(저작권 상태 등)에 재사용 가능.
4. `language` 필드는 `en`/`grc`/`hbo` 등 자유 값을 받을 수 있으나, registry 기본값이 `-`이고 실제 언어 감지 로직(`core/processing.py`)이 무엇을 지원하는지는 이번 조사 범위 밖(코드는 확인했으나 감지기 자체 미검증).

## 필요한 Adapter 여부

**필요함 — 그러나 core pipeline 변경이 아니라 registry-level 데이터 준비 단계로 해결 가능해 보임:**

- NAE 자료를 기존 pipeline에 태우려면 `core/processing.py`가 소비할 수 있는 형태(원본 파일 + registry 메타데이터 `source_file`/`title`/`author`/`language`/`source_type` 등)로 먼저 ingest되어야 함 — 이는 기존 `core/`가 이미 하는 일이므로 **신규 adapter 코드가 아니라 기존 ingest 경로를 그대로 통과시키는 문제**로 보임.
- 단, NAE_SOURCE_SCHEMA_v1.md의 `denomination`, `theological_position`, `copyright_status`, `processing_status` 필드는 현재 registry/TSU 스키마에 **대응 필드가 없음** — 이 필드들을 어디에 저장할지(registry 확장 vs TSU `source_provenance`류 additive 블록 재사용)는 미결정이며, TASK 3(Mapping 검토)에서 다룰 사항.
- 결론: **파이프라인 코드 자체의 구조적 변경은 불필요**해 보이나, NAE 전용 메타데이터를 위한 **additive 필드 제안**(TASK 3)이 필요.

## 확인 대상 커버리지

- `core/`: `tsu_builder.py`, `identity_registry.py`, `processing.py`(관련 부분), `config.py`, `retrieval.py`(소비 측만 참조) 확인
- `scripts/`: `build_tsu_dataset.py` 확인
- `tests/`: `test_tsu_structure.py`, `test_tsu_manifest.py`, `test_build_tsu_dataset_*.py` 존재 확인(목록만, 내용 미검토 — 범위 초과)
- `output/`: 실제 `tsu_dataset.jsonl`/`tsu_manifest.json` 파일 내용은 열람하지 않음(대량 데이터, 이번 조사 범위 아님) — 스키마는 코드 정의 기준으로만 분석
