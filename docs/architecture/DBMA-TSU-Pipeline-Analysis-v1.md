---
title: DBMA TSU Pipeline Analysis v1
category: architecture
sprint: SPRINT17-RG-1
purpose: DocumentContext 구현(Phase 4, tsu_refs 매핑) 착수 전, TSU 생성/소유권을 확인한다.
status: research (조사 전용 — 코드 미수정)
created: 2026-07-16
scope_modified: docs/architecture/ only (코드 미수정)
based_on:
  - docs/architecture/ADR-002-Document-Identity-and-Retrieval-Unit.md (SPRINT16-C-2)
  - docs/architecture/DBMA-SPRINT17-Implementation-Plan-v1.md (§6 Risk: "TSU 생성 파이프라인 위치 미확인")
---

# DBMA TSU Pipeline Analysis v1

목적: SPRINT17 Implementation Plan §6이 "높음" 등급 리스크로 지정한
"TSU 생성 파이프라인 위치 미확인 상태로 Phase 4 착수"를 해소하기 위한
선행 조사. 코드는 읽기만 했으며 아무것도 수정하지 않았다.

---

## 1. tsu_id Generation — 조사 결과

**핵심 발견: 현재 코드베이스에 TSU를 생성하는 코드가 존재하지 않는다.**

- `core/tsu/` 디렉터리는 존재하지만 **비어 있다** (`ls core/tsu/` → 결과 없음).
- `output/SPRINT5_ENGINEERING_VALIDATION/REAL_TSUE_INTEGRATION_MAP.md`
  (2026-07-06 작성)는 `core/tsu/tsu_extractor.py`, `core/tsu/tsu_model.py`,
  `core/tsu/jsonl_exporter.py`, `core/tsu/verse_parser.py`,
  `core/tsu/tsu_validator.py`를 "Production TSU Engine"으로 문서화하지만,
  이 파일들은 git 이력에 **한 번도 커밋된 적이 없다**
  (`git log --all -- core/tsu/` → 빈 결과).
- 실제로 존재하는 코드는 `scripts/repair_tsu_book_id.py`,
  `scripts/repair_tsu_book_metadata.py` — 두 스크립트 모두 이름 그대로
  **"repair"** 스크립트다. 즉 tsu_id가 이미 존재한다고 가정하고
  `verse_mapping.book_id`를 수정하는 후처리 도구이며, tsu_id를 최초로
  발급하는 로직이 아니다.
- `output/SPRINT5_ENGINEERING_VALIDATION/tsu_ranker.py`("Sprint 7 — Hybrid
  TSU Ranking Engine")도 이미 만들어진 TSU를 **랭킹(스코어링)**하는
  코드이지 생성 코드가 아니다.

**tsu_id 포맷**(repair 스크립트에서 역산 가능): `TSU-{book_id}-{sequence:06d}`
(예: `TSU-1PE-000936`). `book_id`는 3자리 성경 축약형(BGU 스타일),
`sequence`는 6자리 zero-padded 순번. 이 포맷이 어디서 최초로 부여되는지는
**현재 코드베이스에서 추적 불가능** — 생성 시점 코드가 소실되었거나,
Sprint 5~8 시점에만 존재했던 일회성 스크립트(커밋되지 않음)로 실행된 뒤
결과 데이터셋만 남고 코드는 사라진 것으로 추정된다.

---

## 2. TSU Storage

- **기대 경로 불일치(모순) 발견**:
  - `core/retrieval.py`의 `RetrievalEngine` 기본값은
    `output/bench/tsu_dataset.jsonl` (JSONL, 파일당 1레코드).
  - `core/runtime_state.py::_check_tsu_dataset()`는
    `output/tsu/tsu_dataset.json` (단수 JSON, 디렉터리도 다름)을 확인한다.
  - 두 모듈이 서로 다른 경로/포맷을 "TSU 데이터셋 위치"로 가정하고 있다 —
    현재 `runtime_state.py`의 파이프라인 상태 점검(`TSU: N docs`)은
    `retrieval.py`가 실제로 로드하는 파일을 보고 있지 않을 가능성이 높다.
- **파일 존재 여부**: 두 경로 모두 현재 작업 트리에 **파일이 존재하지 않는다**
  (`find . -iname "tsu_dataset.jsonl"` → 결과 없음). `output/`, `output_sav/`는
  `.gitignore`에 등록되어 있어 데이터셋 자체는 버전 관리 대상이 아니다 —
  즉 TSU 데이터셋은 **재현 가능한 빌드 산출물로 취급되고 있으나, 그것을
  재생성하는 코드가 현재 없다.**
- 과거 산출물 기록(`output/SPRINT5_ENGINEERING_VALIDATION/TSU_DATASET_VALIDATION_REPORT.md`,
  생성일 2026-07-06): 총 10,338개 TSU, 28개 소스 문서, scripture mapping rate
  100%, 메타데이터 완전성 99.86% — 이 수치들은 **한 번 생성된 스냅샷의 기록**이며
  현재 재실행 가능성은 검증되지 않았다.

---

## 3. TSU Metadata (스키마)

`repair_tsu_book_id.py`/`repair_tsu_book_metadata.py`가 읽고 쓰는 필드를
역산하면 TSU 레코드는 최소한 다음 필드를 갖는다:

```text
{
  "tsu_id": "TSU-{book_id}-{sequence:06d}",
  "verse_mapping": { "book_id": "...", ... },
  "content": "...",
  "themes": [...],           # core/retrieval.py:786 docstring 참조
  # source_document 필드는 검증 리포트의 "TSUS PER DOCUMENT" 표에서
  # 존재가 확인되나(문서명별 TSU 개수 집계), 정확한 키 이름은
  # 현재 코드에서 직접 확인 불가 — validation report는 md 산출물이라
  # 원본 키를 보존하지 않음.
}
```

`retrieval.py::RankedCandidate`(94-107행)는 `tsu_id`, score 필드들만
보유하며, `verse_mapping`/`themes` 등 원본 메타데이터는 후보 랭킹
단계에서 이미 축약되어 있다 (ADR-002 §6 "RankedCandidate 변경 없음" 원칙과
일치 — 이 부분은 계획과 실제 코드가 정합함).

---

## 4. Retrieval Dependency

- `core/retrieval.py::RetrievalEngine`은 `tsu_dataset_path`(JSONL)를 유일한
  데이터 원천으로 받아 TF-IDF 인덱스를 구축한다 (`_build_index()`,
  1001행 부근). 즉 **Retrieval은 TSU 생성 파이프라인과 완전히 분리되어
  있고, 정적 JSONL 파일만 있으면 동작한다** — ADR-001이 확정한
  "RetrievalEngine을 유일한 Retrieval Authority로 둔다"는 원칙과 부합.
- 그러나 그 정적 JSONL을 만드는 공급망이 위 1절처럼 코드베이스에 없으므로,
  **RetrievalEngine은 실질적으로 "TSU가 이미 존재한다"는 전제에 의존하는
  소비자일 뿐, TSU 생명주기의 어느 단계에도 관여하지 않는다.**
- `ui/pages/research.py`(121-125행)는 `RankedCandidate`를
  `{"type": "tsu", "tsu_id": ...}` 형태로 UI에 노출만 할 뿐, TSU 생성과는
  무관하다.

---

## 5. Document/Chunk ↔ TSU 관계

- `core/document_identity.py`는 `document_id`(콘텐츠 해시 기반, 결정적)와
  `chunk_id = f"{document_id}_chunk_{index:05d}"`를 발급한다 — 이는 **처리
  파이프라인 공간**(SPRINT16-C-1/ADR-002가 "processing space"로 정의한 영역)의
  식별자다.
- TSU 데이터셋의 "TSUS PER DOCUMENT" 집계(§2 참조)는 사람이 읽을 수 있는
  **문서 파일명**(예: `"1 Peter_ Volume 49 ... _pdf_chunks_a1ae63ba"`)을
  키로 쓴다 — 이는 `document_id`(해시)도 `chunk_id`도 아니다. 즉 현재
  TSU 쪽에는 `document_id`/`chunk_id`로 되돌아갈 수 있는 **명시적 매핑
  필드가 없다** — 파일명 문자열이 유사-외래키 역할을 하고 있을 뿐이다.
- ADR-002가 "document_id/chunk_id(처리 공간)와 tsu_id(연구/검색 공간)를
  통합하지 않고 매핑 테이블로 연결"하기로 결정한 배경이 여기서 확인된다:
  두 공간은 이미 서로 다른 키 체계(해시 vs 파일명 기반 순번)를 쓰고 있어
  통합이 애초에 불가능했다.

---

## 6. Architecture Impact

1. **Phase 4 전제 조건 미충족**: SPRINT17 계획 §3 Phase 4("tsu_refs 매핑을
   채우는 프로세스 설계·구현")는 "TSU가 안정적으로 생성되고 있다"는
   암묵적 전제 위에 있었다. 실제로는 **TSU 생성 코드 자체가 현재
   코드베이스에 없으므로**, "매핑을 채우는 프로세스"를 설계하기 전에
   "TSU를 (재)생성하는 프로세스"부터 정의해야 한다 — 매핑은 그 다음
   문제다.
2. **`runtime_state.py` vs `retrieval.py` 경로 불일치**는 SPRINT16 문서에서
   보고된 바 없는 **신규 발견**이다. 이는 ExecutionContext(§2, SPRINT17
   계획서) 설계 시 `get_pipeline_stage_status()`가 "TSU 준비됨" 여부를
   판단할 때 어느 경로를 신뢰할지 결정해야 하는 문제로 이어진다.
3. **`document_id`/`chunk_id` ↔ TSU 매핑 키 부재**를 실측으로 확인했다 —
   ADR-002의 "매핑 테이블" 결정은 옳았으나, 매핑 테이블을 채우려면
   먼저 TSU 레코드에 `document_id`(현재는 파일명 문자열만 있음)를
   기록하는 지점이 TSU 생성 과정 어딘가에 있어야 한다. 그 지점이 아직
   설계되지 않았다.
4. **`core/tsu/tsu_extractor.py` 등은 "존재하는 것으로 문서화되었으나
   실재하지 않는" 상태** — SPRINT16 Module Responsibility 문서나 Migration
   Matrix가 이 모듈들을 참조했다면 그 부분은 재검증이 필요하다(별도 확인
   권고, 본 문서 범위 밖).

---

## 7. SPRINT17 Implementation Requirements (권고)

Phase 4 착수 전 다음을 **선행 작업(Phase 3.5 또는 별도 조사 스프린트)**으로
명시할 것을 권고한다:

1. **TSU 생성 소유권 결정**: TSU 생성 코드를 (a) 처음부터 재설계/재구현할지,
   (b) Sprint 5~8 시점의 미커밋 스크립트를 복구할 방법이 있는지(있다면
   사람 확인 필요), (c) 아니면 TSU 파이프라인 자체를 SPRINT17 범위 밖으로
   명시적으로 미루고 기존 정적 JSONL 스냅샷만 임시로 재사용할지 결정.
2. **경로/포맷 단일화**: `output/bench/tsu_dataset.jsonl`과
   `output/tsu/tsu_dataset.json` 중 하나를 유일한 정본 경로로 선언하고
   나머지는 폐기 대상으로 문서화(코드 변경은 Phase 4 이후).
3. **TSU 레코드에 document_id 필드 추가 설계**: 매핑 테이블(ADR-002 §6)이
   동작하려면 TSU 생성 시점에 파일명이 아니라 `core/document_identity.py`가
   발급한 `document_id`를 함께 기록해야 한다 — 이 필드 추가는 TSU 생성
   로직이 재구현될 때 반드시 포함되어야 할 요구사항이다.
4. **Phase 4 Definition of Ready 갱신**: SPRINT17 계획 §3 Phase 4 항목에
   "TSU 생성 파이프라인 소유권 확정" 및 "document_id 필드 포함 여부 확인"을
   착수 조건으로 추가할 것을 제안 (계획 문서 자체 수정은 별도 승인 후 진행).

---

*본 문서는 SPRINT17-RG-1 범위(`docs/architecture/`)에서 조사만 수행했으며,
`core/`, `ui/`, `scripts/`, `tests/`, `config.yaml`, `dbma.py`는 읽기만 하고
수정하지 않았다.*
