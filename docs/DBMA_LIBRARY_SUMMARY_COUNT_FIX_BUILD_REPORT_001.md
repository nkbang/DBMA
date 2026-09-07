# DBMA 내 서재 요약 카운트 불일치 수정 Build Report 001

**Project:** DBMA-LIBRARY-SUMMARY-COUNT-FIX-001
**Date:** 2026-09-07
**Nature:** Phase 1 = UI 집계 로직 버그 수정(읽기 전용 필터). Phase 2 = 유령
문서 98건 데이터 정리 — `ingest_status` 전이(EXCLUDED) + TSU 데이터셋/색인
재빌드. **Corpus/Retrieval/Embedding 파이프라인 로직 미변경.** 사용자 명시 승인.
**Git Commit:** 자동 수행 (CUE Operating Policy v1.0, 버그 수정 + 승인된 데이터 정리 → C1 Review 불요)

---

## 1. 문제 요약

대시보드 "내 서재 요약"에서 **보유 문서 107권 vs 정리된 자료 200개**로,
정리된 문서 수가 보유 문서 수를 크게 초과하는 물리적으로 불가능한 표시가
사용자에게 보고됨.

### 근본 원인

1. `ui/pages/processing.py::_render_ingestion_form()`의 "처리 대상 폴더"
   후보 목록이 `data/` 아래 "지원 확장자 파일이 든 모든 하위 폴더"를
   무조건 넣었다 — 여기에 파이프라인 **출력 폴더**
   `data/제련완성본`(`DEFAULT_OUTPUT_DIR`, 변환 `.md`·청크 덤프가 쌓이며
   레지스트리 본체도 위치)까지 포함됨.
2. 2026-09-07 14:20 처리 실행이 그 출력 폴더를 대상으로 돌아,
   `<원본>_pdf.md` / `<원본>_pdf_chunks.txt` / `<원본>_md.md` /
   `<원본>_md_chunks.txt` 형태의 **파이프라인 중간 산출물 98건이 신규
   "문서"로 레지스트리에 등록**됨.
3. 이 유령 항목들은 `chunk_count>0`, `ingest_status=PROCESSED`,
   `superseded_by=None`이라 `_get_effective_documents()`의 기존 필터를
   전부 통과 → "정리된 자료" = 실제 ~102 + 유령 ~98 = 200.
4. 추가로, 잘못된 처리가 `output/bench/tsu_dataset.jsonl`에 비-UTF8 바이트를
   유입시켜 `_get_unprocessed_raw_files()`가 `UnicodeDecodeError`로 죽고,
   "내 서재 요약"의 처리 완료/미처리 표시 전체가 예외로 중단됨.

---

## 2. 수정 내용

### `ui/pages/dashboard.py`

- `_is_pipeline_artifact_name(source_file)` 신규 헬퍼 — source_file이
  사용자 원본이 아니라 파이프라인 산출물인지 파일명 규칙으로 판별:
  - `_chunks.txt` / `_chunks_meta.json`로 끝남 → 청크 덤프
  - `_<지원확장자>.md`로 끝남 → 추출·변환 단계의 마크다운 출력
    (사용자가 올린 마크다운은 `이름.md`이지 `이름_pdf.md`가 아님)
- `_get_effective_documents()` 필터에 `not _is_pipeline_artifact_name(...)`
  조건 추가. "정리된 자료"·"유형별 문서" 두 카드가 계속 이 함수 하나를
  공유하므로 둘 다 동일하게 교정됨.
- `_get_unprocessed_raw_files()`의 TSU 데이터셋 읽기를
  `encoding="utf-8", errors="replace"`로 변경 — 깨진 줄은 기존 `json.loads`
  실패 경로로 건너뛰므로 집계 영향 없음, 대시보드 전체 크래시만 방지.

### `ui/pages/processing.py`

- `_render_ingestion_form()`의 폴더 후보 수집에서:
  - `DEFAULT_OUTPUT_DIR`(및 `data/제련완성본`)를 `_blocked_dirs`로 제외.
  - 폴더 안에 `_chunks.txt` / `_chunks_meta.json` 산출물이 보이면 원본
    폴더가 아니라고 판단해 후보에서 제외.
- 직접 경로 입력으로도 출력 폴더를 지정하면 `st.error` 표시 후
  `DEFAULT_RAW_DIR`로 되돌림.

### `tests/test_dashboard_effective_documents.py`

- `TestPipelineArtifactExclusion` 추가:
  - 변환 `.md`·청크 덤프·`_chunks_meta.json`·`_md.md`가 effective 집합에서
    빠지고 실제 `.pdf`/`.md` 원본만 남는지 검증.
  - `_is_pipeline_artifact_name()` 경계 케이스(원본 `이름.md`,
    `이름.pdf`, 빈 문자열은 산출물 아님) 검증.

---

## 3. 검증 결과 (실측)

수정 후 `dbma_env`에서 실제 함수 호출:

```
_get_effective_documents()          → 103   (수정 전 200)
_get_raw_processing_breakdown()     → {'total': 107, 'processed': 66, 'unprocessed': 41}
_get_unprocessed_raw_files()        → 41건 (크래시 없이 정상 반환, 수정 전 UnicodeDecodeError)
파생 산출물 잔존                     → 0
```

- 보유 문서(107) ≥ 정리된 자료(103) — 사용자가 신고한 "불가능한" 상태 해소.

### Regression

```
tests/test_dashboard_effective_documents.py   4 passed
tests/test_dashboard_raw_breakdown.py         9 passed
tests/test_processing_pending_count.py         4 passed
-k "dashboard or processing or library or raw_hygiene or raw_breakdown or effective"
                                             171 passed, 0 failed
```

- `tests/test_sermon_research_hub.py` / `tests/test_reading_session.py`의
  일부 실패는 **본 변경과 무관한 선존(pre-existing) 상태** — 미커밋
  상태의 `NAE/` 설교 초안 작업 및 테스트 격리 문제로, 깨끗한 stash 트리
  에서도 동일하게 실패함(확인 완료). 본 커밋은 해당 파일들을 건드리지
  않음.

### Architecture / ADR

- RAW·Retrieval Engine·Embedding Engine·TSU Pipeline·Production Registry
  **미변경** (UI 읽기 전용 필터만 수정). Approved ADR 충돌 없음.
- 사소한 버그 수정이므로 CUE Operating Policy상 C1 Review 대상 아님.

---

## 4. Phase 2 — 레지스트리 유령 항목 98건 실제 정리 (2026-09-07, 사용자 승인)

사용자 지시("레지스트리 유령 항목 98건도 정리해줘")로 데이터 정리 수행.

### 4.1 추가 근본 원인 — reconcile_pending()의 EXCLUDED 미처리

`core/background_index_builder.py`가 5초마다 `reconcile_pending()`을 호출하는데,
그 pending 스캔이 `pipeline_state == "PROCESSED"`만 보고
`ingest_status == "EXCLUDED"`를 무시했다. 유령 98건 중 69건이
`pipeline_state == "PROCESSED"`였기에, EXCLUDED로 표시해도 리컨사일러가 5초마다
`reindex_document()`로 되살려 TSU 데이터셋에 재삽입했다. 1차 정리 시도에서
실행 중이던 Streamlit 서버 3개(그 중 하나는 launchd `com.dbma.nae.dashboard`,
KeepAlive)의 리컨사일러와 데이터셋 쓰기 경쟁이 발생 → 데이터셋 오염(정상
레코드 ~3,060건 유실, 유령 재출현). `backups/phantom_registry_cleanup_
20260907_152046/`에서 전량 복원 후 아래 구조로 재수행.

### 4.2 코드 수정

**`core/index_orchestrator.py::reconcile_pending()`** — pending 스캔에
`and doc.get("ingest_status") != "EXCLUDED"` 추가. 제외된 문서를 리컨사일러가
다시 색인하지 않는다. 회귀 테스트
`tests/test_reconcile_pending.py::test_excluded_documents_are_not_reconciled`.

### 4.3 데이터 정리 스크립트 (dry-run 기본, 백업 필수)

- **`scripts/cleanup_phantom_registry_entries.py`** — RAW에 없고 산출물 이름
  규칙에 맞는 registry 문서를 찾아 `registry_lock()` 보유 상태에서 ①98건
  `ingest_status=EXCLUDED`+`pipeline_state=INDEXED`, ②TSU 데이터셋 레코드 제거,
  ③매니페스트 재작성, ④후보/성경 색인 전체 재빌드. `reconcile_pending()`도
  같은 lock을 쓰므로 앱이 떠 있어도 뒤에서 직렬화된다.
- **`scripts/sync_tsu_dataset_to_registry.py`** — `ingest_status=="EXCLUDED"`인
  모든 문서(오늘 98 + 이전부터의 13)의 레코드를 데이터셋에서 제거하고
  매니페스트/색인 재빌드. 이전 EXCLUDED 13건의 레코드 5,086건이 위 리컨사일러
  버그로 계속 남아 있었다.

### 4.4 실측 결과

| 항목 | 정리 전 | 정리 후 |
|---|---|---|
| registry EXCLUDED | 13 | 111 (13 + 유령 98) |
| TSU 데이터셋 | 89,738줄 (손상 1, 유령 38,724) | 45,927 (EXCLUDED 소속·손상 0) |
| 후보 색인 | 손상(열기 실패) | 재빌드 45,927 |
| 성경 색인 | stale | 재빌드 86,042 |
| `reconcile_pending()` 재실행 | 유령 재삽입 | `pending:0`, 데이터셋 불변 |
| 대시보드 정리된 자료 | 200 | **103** (보유 107 이하) |

### 4.5 회귀

```
tests/test_reconcile_pending.py                     6 passed
-k "reconcile|orchestrator|dashboard|raw_hygiene|candidate|bible_index|registry_lock|background_index|reindex"
                                                 353 passed, 0 failed
```

### 4.6 Architecture / ADR

- **Retrieval·Embedding Engine 미변경.** TSU 데이터셋/색인 조작은
  `reconcile_pending()`·`exclude_document_from_index()`가 이미 수행하는 연산
  (EXCLUDED 문서 레코드 purge + 색인 재빌드)을 배치로 실행한 것이며 파이프라인
  로직·스코어링·스키마는 불변.
- Production Registry 변경은 `ingest_status` 전이(`unexclude_document()`로
  복원 가능)에 한정, 사용자 명시 승인 있음.
- `reconcile_pending()` 수정은 명백한 버그 수정 → C1 Review 대상 아님.

### 4.7 남은 항목 (별도 작업, 이번 범위 밖)

1. `.md` 설교·연구 원고 41건이 registry는 `PROCESSED`(chunk>0)인데 TSU
   데이터셋에 레코드 없음(원본 데이터셋도 76문서만 — **오늘 이전부터의 상태**).
   이 때문에 "정리된 자료 103" vs "처리완료 65 / 미처리 42"가 다른 기준으로
   잡힘. 신고된 불일치(정리 > 보유)는 해소. 완전 일치엔 이 41건 재색인 필요.
2. `data/제련완성본/`에 유령/중복 산출물 파일 ~290개 잔존(실제 문서의 정상
   청크 출력과 섞여 있어 일괄 삭제 위험). `scripts/cleanup_duplicate_outputs.py`
   로 별도 정리.
3. 손상 1줄이 있던 `output/bench/tsu_dataset.jsonl`은 정리 과정에서 재작성되어
   해소됨.
