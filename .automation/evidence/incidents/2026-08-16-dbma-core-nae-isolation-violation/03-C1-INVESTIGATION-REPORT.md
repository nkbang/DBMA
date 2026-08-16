# C1 Investigation Report — DBMA Core / NAE Corpus Isolation Violation

- 작성: C1 (Independent Forensic Auditor)
- 작성일: 2026-08-16
- 대상: `.automation/requests/C1-TASK-ORDER-INCIDENT-EVIDENCE-CAPTURE.md`
- 상태: **EVIDENCE CAPTURED — CUE 판정 대기**

---

## 조사 원칙

- "누가/왜 2026-08-15 03:07:18에 이 ingestion을 실행시켰는가"는 **추정하지 않음**.
- 코드와 로그가 직접 말해주는 사실만 기록. 모르면 "확인 불가".
- 정리/삭제/복구/재실행 절대 금지. 모든 스크립트 읽기 전용.

---

## 1. `documents.json`의 Dagg entry

**근거 파일**: `01-preserved-documents-json-backup.json` (삭제 전 백업)

```json
{
  "document_id": "0d849d7ba30bafddaa0a544c93dd8c66",
  "file_hash": "0d849d7ba30bafddaa0a544c93dd8c6613d40fe87987406a2f21d4c6a45be653",
  "source_file": "original.pdf",
  "created_at": "2026-08-15T03:07:18",
  "processing_version": "1.1.x",
  "status": "processed",
  "chunk_count": 725,
  "language": "en",
  "noise_score": 16.6,
  "noise_mode": "pdf",
  "source_type": "pdf",
  "is_ocr": false,
  "book": null,
  "chapter": null,
  "page": null,
  "title": "Church Order a Treatise",
  "author": "J. L. Dagg",
  "doc_type": "기타",
  "pipeline_state": "PROCESSED",
  "superseded_by": null,
  "supersedes": null,
  "pipeline_flags": {
    "ingested": true,
    "copied": true,
    "extracted": true,
    "cleaned": true,
    "chunked": true,
    "output_generated": true,
    "verified": true
  },
  "last_processed_at": "2026-08-15T03:07:18"
}
```

**확인 사항**:
- 백업 파일 총 82건 중 Dagg 항목 1건 확인.
- `updated_at` (documents.json 최상위): `2026-08-15T03:07:18` — Dagg ingestion 시점과 일치.
- 현재 documents.json: 81건 (Dagg 제거 확인).

---

## 2. `data/제련완성본/original_pdf.md`

**결과**: 파일 자체 삭제됨 — 조사 불가.

**간접 정보만**: `01-preserved-ns003-result.json`의 logs에서 생성 경로 확인:
```
"[Phase 1] MD saved: /Users/David/DBMA/data/제련완성본/original_pdf.md"
```

---

## 3. 해당 파일의 정확한 filesystem metadata

**결과**: 불가능 (파일 삭제됨).

**대체 조사**: `documents.json` 백업에 남은 메타데이터로 대체 (항목 1 참조).
---

## 4. `scripts/ns003_nae_ingestion.py` — 코드 분석

**근거 파일**: `02-implicated-scripts/ns003_nae_ingestion.py` (스냅샷)

### 스크립트 개요
- Night Shift Order 003: NAE TSU → Embedding → Qdrant Production Ingestion
- Pipeline: Registration (QUALITY_PASSED) → processing.py::process_one_file() → tsu_builder.py::build_tsu_records() → NAE/pipeline/ingest/pipeline.py::apply() → verification

### 핵심 경로
```python
PROD_REGISTRY = PROJECT_ROOT / "data" / "제련완성본" / "registry" / "documents.json"
PROD_OUTPUT_DIR = PROJECT_ROOT / "data" / "제련완성본"
QDRANT_URL = "http://localhost:7333"
QDRANT_COLLECTION = "nae_tsu_v1"
```

### `process_single_source()` 가 호출하는 core 모듈
1. `processing.py::process_one_file()` — extraction + chunking + registry update
2. `tsu_builder.py::build_tsu_records()` — TSU record generation
3. `NAE/pipeline/ingest/pipeline.py::apply()` — embedding + Qdrant upsert

### NAE 경로 참조
- `REG_STATE_PATH = PROJECT_ROOT / "NAE" / "pipeline" / "registration" / "state" / "registration_state.json"`
- `raw_checksum_ledger.jsonl`에서 raw source path 조회
- `NAE/pipeline/ingest/pipeline.py::apply()`로 embedding + Qdrant upsert

---

## 5. `scripts/test_tsu_build.py` — 코드 분석

**근거 파일**: `02-implicated-scripts/test_tsu_build.py` (스냅샷)

### 스크립트 개요
- `ns003_nae_ingestion.process_single_source()`를 호출하여 Phase 1 실행
- hardcoded source_id: `"BAP-CHURCH-DAGG-001"`
- 결과를 `/tmp/ns003_phase1_result.json`에 저장

### 핵심 코드
```python
from scripts.ns003_nae_ingestion import process_single_source
source_id = "BAP-CHURCH-DAGG-001"
result = process_single_source(source_id)
Path('/tmp/ns003_phase1_result.json').write_text(json.dumps(output, ...))
```

---

## 6. `scripts/ns004_build_tsu.py` — 코드 분석

**근거 파일**: `02-implicated-scripts/ns004_build_tsu.py` (스냅샷)

### 스크립트 개요
- 단일 identifier에 대해 TSU 빌드
- hardcoded default: `'Fuller_Complete_Works_Vol01'`
- `NAE/pipeline/tsu/builder::build_tsu_for_identifier()` 호출

### 핵심 코드
```python
from NAE.pipeline.tsu import builder
identifier = sys.argv[1] if len(sys.argv) > 1 else 'Fuller_Complete_Works_Vol01'
result = builder.build_tsu_for_identifier(identifier)
```

---

## 7. 세 스크립트 사이의 호출 관계

**근거**: import 그래프 분석 (읽기 전용)

```
test_tsu_build.py
  └→ ns003_nae_ingestion.process_single_source()
       ├→ core.processing.process_one_file()
       ├→ core.tsu_builder.build_tsu_records()
       └→ NAE.pipeline.ingest.pipeline.apply()

ns004_build_tsu.py
  └→ NAE.pipeline.tsu.builder.build_tsu_for_identifier()
```

**확인 사항**:
- `test_tsu_build.py` → `ns003_nae_ingestion.py` 직접 import
- `ns004_build_tsu.py`는 독립 스크립트 (다른 스크립트와 import 관계 없음)
- `ns003_nae_ingestion.py`가 DBMA Core (`core.processing`, `core.tsu_builder`) 와 NAE (`NAE.pipeline.ingest.pipeline`) 양쪽을 호출하는 **교차점**

---

## 8. Git history 확인

**결과**: CUE가 이미 끝냄 — 재조사 금지.

**문서에 기록된 사실**: `git log --all -- <세 파일>` 결과 전부 빈 결과, 즉 세 파일 다 git에 커밋된 적 없음 (계속 untracked 상태).

---

## 9. shell history나 실행 기록

### ~/.zsh_history
```
(no matches)
```

### ~/.bash_history
```
(no matches)
```

### .automation/night-shift/logs/ns003/
```
phase1_BAP-CHURCH-DAGG-001.json (mtime: 2026-08-15 03:06)
```

**해당 파일 내용**:
```json
{
  "source_id": "BAP-CHURCH-DAGG-001",
  "success": false,
  "error": "process_one_file failed: [Errno 2] No such file or directory: '/Users/David/DBMA/data/제륨완성벾n/original_pdf.md'",
  "logs": [
    "[Phase 1] Raw dir: /Users/David/DBMA/NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order",
    "[Phase 1] Files: ['hocr.html', 'original.pdf', 'metadata.json', 'ocr.txt']",
    "[Phase 1] Processing PDF: original.pdf",
    "[Phase 1] process_one_file success=False, skipped=None"
  ]
}
```

**중요 발견**: 첫 실행은 **에러로 종료됨**. 경로 오타 (`제륨완성벾n` vs `제련완성본`) 로 인해 `original_pdf.md` 생성 실패.

**그러나**: `documents.json` 백업의 `created_at: 2026-08-15T03:07:18`는 이 에러 이후에 Dagg 항목이 **성공적으로** 등록되었음을 의미함. 즉, 첫 실패 후 재시도 또는 별도 실행이 있었음.

---

## 10. Dagg ingestion 이후 생성된 downstream artifact

**조사**: `grep -rl "0d849d7ba30bafddaa0a544c93dd8c66" data/ output/`

**결과**: CUE 결과와 일치 — **registry 외에는 추가 artifact 없음**.

**추가 확인**: `find data/ -name "*dagg*" -o -name "*Dagg*"` — 결과 없음.

---

## 11. documents.json 전수 검색 — NAE source 추가 여부

**근거**: `01-preserved-documents-json-backup.json` (82건)

**NAE 관련 키워드**: `dagg`, `fuller`, `hiscox`, `baptist`, `nae`, `church order`

**결과**: **Dagg 1건뿐**. Fuller, Hiscox 등 다른 9건은 DBMA Core에 없음.

```
NAE-related entries found: 1
{
  "doc_id": "0d849d7ba30bafddaa0a544c93dd8c66",
  "title": "Church Order a Treatise",
  "author": "J. L. Dagg",
  "source_file": "original.pdf",
  "created_at": "2026-08-15T03:07:18"
}
```

---

## 12. Qdrant / registration_state / incremental_state 영향 확인

### registration_state.json
**파일**: `/Users/David/DBMA/NAE/pipeline/registration/state/registration_state.json` (mtime: 2026-08-15 02:51)

```json
{
  "BAP-CHURCH-DAGG-001": {
    "state": "QUALITY_PASSED",
    "updated_at": "2026-08-15T07:51:26.197775+00:00"
  },
  ... (Fuller 8건, Hiscox 1건)
}
```

**확인**: Dagg 항목 존재 (`QUALITY_PASSED`). mtime `2026-08-15T02:51`는 ingestion (`03:07:18`) **이전** — 즉, 이 파일의 마지막 수정은 Dagg ingestion 이전. Dagg 항목의 `updated_at` (`07:51:26`) 은 ingestion 이후이지만, 이는 registration pipeline의 별도 단계에서 업데이트된 것으로 보임.

### incremental_state.json
**파일**: `/Users/David/DBMA/NAE/pipeline/ingest/state/incremental_state.json` (mtime: 2026-08-11 16:16)

**결과**: `grep -i "dagg"` — **매칭 없음**. Dagg 항목 없음.

### Qdrant
- DBMA Qdrant (6333): **Connection refused** (프로세스 안 떠있음)
- NAE Qdrant (7333): **실행 중** (v1.18.2)

**확인 불가**: NAE Qdrant collection `nae_tsu_v1`의 baseline 3,319가 Dagg ingestion 전/후인지 확인하려면 실제 vector store 쿼리가 필요하나, CUE가 이미 "baseline 3,319 그대로"라고 보고함. 이 보고서에서는 CUE 결과 인용.

---

## 종합 사실 정리 (추정 배제)

| 항목 | 사실 |
|------|------|
| Dagg ingestion 시점 | `2026-08-15T03:07:18` (documents.json `created_at`) |
| 첫 ns003 실행 결과 | **에러** (경로 오타: `제륨완성벾n`) |
| Dagg 최종 등록 | 성공 (첫 실패 이후 별도 실행 또는 재시도) |
| documents.json 오염 규모 | 82건 중 Dagg 1건 |
| downstream artifact | registry 외 없음 |
| NAE source 추가 | Fuller, Hiscox 등 DBMA Core에 없음 |
| Qdrant (6333) | 프로세스 안 떠있음 — 실제 검색 결과 반영 없음 |
| registration_state | Dagg 항목 `QUALITY_PASSED` 존재 |
| incremental_state | Dagg 항목 없음 |
| 세 스크립트 git 커밋 | 전부 미커밋 (untracked) |

---

## 확인 불가 사항 (정직하게)

| 항목 | 이유 |
|------|------|
| **누가/무엇이 2026-08-15 03:07:18에 ingestion을 실행시켰는가** | shell history 없음, git 커밋 없음, 로그에 실행자 정보 없음 |
| **왜 실행됐는가 (의도적 테스트 vs 실수)** | 코드/로그가 의도를 포함하지 않음 |
| **첫 실패 후 어떻게 성공했는가** | 재시도 로직이 스크립트에 있는지 확인 불가 (에러 경로만 확인) |
| **NAE Qdrant baseline 3,319가 Dagg 전/후인지** | 실제 vector store 쿼리 없이 확인 불가 |

---

## 결론

C1은 이 조사를 **증거 수집** 목적으로 수행함. "정리 가능/불가능" 판정은 C1이 내리지 않음. CUE가 Rev. Bang에게 보고 후 결정한다.

모든 사실은 코드와 로그가 직접 말해주는 내용만 기록함. "누가/왜"에 대해서는 확인 불가로 정직하게 기록함.

---

*이 보고서는 ADR-025 승격/반려와 무관함. ADR-025는 Proposed 상태 유지.*
