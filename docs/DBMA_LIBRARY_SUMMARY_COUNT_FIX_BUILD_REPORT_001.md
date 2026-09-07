# DBMA 내 서재 요약 카운트 불일치 수정 Build Report 001

**Project:** DBMA-LIBRARY-SUMMARY-COUNT-FIX-001
**Date:** 2026-09-07
**Nature:** UI 집계 로직 버그 수정 — **Production Registry 데이터 변경 아님** (읽기 전용 필터만 수정)
**Git Commit:** 자동 수행 (CUE Operating Policy v1.0, 사소한 버그 수정 → C1 Review 불요)

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

## 4. 다음 조치 (데이터 정리 — 별도 승인 필요, 본 커밋 범위 밖)

1. **레지스트리 유령 항목 98건**은 그대로 남아 있음 — 대시보드 요약에는
   더 이상 노출되지 않으나, 검색·파일 스코프 선택기·벡터 인덱스에는
   여전히 존재. Library 페이지 상단 "원본이 사라진 문서" 알림
   (`find_orphaned_processed_documents` → 98건 전부 해당)에서 정리
   가능하며, 일괄 정리 스크립트가 필요하면 별도 요청 시 작성. Production
   Registry 대량 변경이므로 사용자 승인 후 수행.
2. `output/bench/tsu_dataset.jsonl`에 비-UTF8 바이트가 있어 재생성 권장.
3. `.md` 설교 원고 ~38건이 레지스트리에는 PROCESSED이나 TSU 데이터셋에
   없어 "처리 완료 66 / 미처리 41"이 "정리된 자료 103"과 다른 기준으로
   집계됨. 신고된 불일치(정리 > 보유)는 아니나, 두 지표를 완전 일치
   시키려면 해당 원고들의 실제 색인 여부 확인 후 별도 결정 필요.
