# STEP4-D Report — NAE Pilot Adapter Implementation

작성일: 2026-07-31

## 변경 파일

| 파일 | 종류 | 확인 |
|---|---|---|
| `scripts/ingest_nae_source.py` | 신규 | `scripts/ingest_logos_export.py` 구조 복제, NAE manifest 전용 |
| `core/tsu_builder.py` | 수정 (+18줄) | `git diff` 확인 완료 — `nae_metadata` additive 블록만 추가, 기존 코드 미변경 |

## test 결과

[STEP4D_TEST_REPORT.md](STEP4D_TEST_REPORT.md) 요약:

| 항목 | 결과 |
|---|---|
| 기존 DBMA 문서 regression | PASS (기존 TSU 테스트 40개 + reindex/dedupe 6개 = 46 tests 전부 통과) |
| NAE metadata 존재 | PASS (synthetic 테스트 픽스처 기준 — 실제 원문 미확보) |
| TSU output 보존 | PASS (기존 필드 전부 값/타입 유지 확인) |
| retrieval compatibility | PASS (`core/retrieval.py` 무수정) |

테스트는 스크래치패드 임시 디렉토리에서 합성 텍스트(실제 New Hampshire Confession 원문 아님, "[TEST FIXTURE]"로 명시)로 수행 — 운영 `output/`, `data/nae/` 실 데이터는 건드리지 않음.

## 문제점

1. **관찰 사항(버그 아님)**: dry-run에서 `verse_mapping.book_id`가 파일명 기반 매칭으로 우연히 채워지는 기존 로직 동작 확인(`_resolve_book_id()`) — 이번 변경과 무관, 실제 문서 ingest 시 재확인 필요 항목으로 기록.
2. **범위 외 발견**: `git status` 확인 중 `core/config.py`, `ui/pages/library.py`에 이번 세션에서 만들지 않은 기존 미커밋 변경(135줄, 14줄)이 존재함을 확인. **이번 STEP4-D 작업으로 생성된 변경이 아님** — 다른 세션(C1 등)의 진행 중 작업으로 추정. [[feedback_concurrent_c1_file_edits]] 메모리 기준 확인 절차를 따름. 손대지 않았으며, commit 대상에서도 제외해야 함.

## commit 준비 여부

**준비됨 (단, 이번 STEP4-D 변경분에 한함)**:
- `scripts/ingest_nae_source.py` (신규)
- `core/tsu_builder.py` (수정, `nae_metadata` 블록만)
- `docs/tasks/reports/` 하위 STEP4-D 관련 문서 다수

**제외 필요**:
- `core/config.py`, `ui/pages/library.py` — 이번 세션에서 만들지 않은 변경, 별도 세션 소유로 추정. 커밋 승인 요청 시 반드시 이 2개 파일을 staging에서 제외해야 함.

git commit 자체는 이번 지시(금지 사항)에 따라 미실행.

## 금지 사항 준수 확인

- Git commit: 미실행
- Git push: 미실행
- Vector 생성: 미실행
- Embedding: 실행되지 않음 — 단, `ingest_nae_source.py` 실행 시 `core/processing.py::detect_language` 등 기존 유틸이 내부적으로 `bge-m3` SentenceTransformer 모델을 로드하는 로그가 관측됨(기존 파이프라인의 표준 동작, 이번 코드가 별도로 embedding을 호출한 것 아님) — 실제 벡터 생성/저장 로직은 호출되지 않음
- 대량 문서 처리: 1건(합성 픽스처)만 처리, 대량 처리 없음
