# Incident Record — DBMA Core / NAE Corpus Isolation Violation

- 발견: CUE, 2026-08-16 13:36 CDT (Phase 3 검증 중 우연히 발견)
- 분류: DBMA/NAE corpus isolation 위반 (governance incident)
- 상태: **RESOLVED-OBSERVED (증거보존 완료)** — Rev. Bang 최종 판정,
  2026-08-16 확정. 오염 범위 확정(Dagg 1건), production state 정상
  복귀 확인, 원인은 정황상 추정되나 실행자 특정 증거 없음(미확정으로
  유지). Cleanup 행위 자체의 증거는 `04-CLEANUP-ACTION-LOG.md` 참고.

## Governance Track 분리 (Rev. Bang 지시)

이 incident와 ADR-025(Phase 3 worker)는 **서로 독립된 두 개의 governance
track**이다:

- **ADR-025**: Status `Proposed` 유지. `runner.py` 연동 + unit test 완료 후
  CUE 재감사를 거쳐야 Approved 승격 검토. 이 incident와 승인 조건을
  섞지 않는다.
- **이 incident**: `RESOLVED-OBSERVED`로 종결. Phase 3(Corpus Factory)
  진행의 HOLD 사유가 아니다 — Phase 3는 계속 진행한다.

## ⚠️ CUE의 절차 오류 — 반드시 먼저 밝힘

Rev. Bang의 최초 지시("정리먼저")에 따라 CUE가 **증거보존 없이 즉시 삭제를
실행**했다. 이후 Rev. Bang이 "격리·증거보존 후 독립감사" 방침을 재지시했으나
그 시점에는 이미 삭제가 완료된 뒤였다. 이는 절차상 CUE의 실수다 —
"삭제는 신중하게, 먼저 격리 후 판단"이 맞는 순서였는데 지키지 못했다.

## 이미 실행되어 되돌릴 수 없는 조치 (2026-08-16 14:08 CDT경)

| 조치 | 되돌릴 수 있는가 |
|---|---|
| `data/제련완성본/original_pdf.md` 삭제(`rm -f`) | ❌ 불가 — 백업 없음, Time Machine 미설정/조회 불가 확인됨 |
| `/tmp/ns003_phase1_result.json` 삭제 | ❌ 파일 자체는 불가, 단 **전체 내용이 이 세션 대화 로그에 원문 그대로 보존됨** — 아래 `01-preserved-ns003-result.json`에 재수록 |
| `data/제련완성본/registry/documents.json`에서 Dagg 항목 제거 | ⚠️ 부분 가능 — 삭제 **전** 원본 파일을 백업해뒀음(`01-preserved-documents-json-backup.json`), 항목 내용 전체 보존됨. 원하면 이 백업으로 항목을 그대로 복원 가능 |

## 보존된 증거

- `01-preserved-documents-json-backup.json` — 삭제 전 documents.json 전체(82건, Dagg 항목 포함)
- `01-preserved-ns003-result.json` — 삭제된 /tmp 결과 파일의 원문(세션 로그에서 복원)
- `02-implicated-scripts/` — 관련 스크립트 3개의 스냅샷(현재 상태 그대로, 아직 삭제 안 함)

## CUE가 이미 확인한 사실 (재조사 불필요)

- 오염 규모: documents.json 82건 전수 검색 결과 NAE 관련 항목 **Dagg 1건뿐**
  (Fuller, Hiscox 등 다른 9건은 DBMA Core에 없음)
- 해당 항목 `created_at`: **2026-08-15T03:07:18** — 오늘(8/16) Corpus Factory
  Phase 3 시작보다 훨씬 이전, 그리고 세션 초반 어젯밤 작업 시간대
- 관련 스크립트 3개의 실제 파일 mtime: `ns003_nae_ingestion.py`(8/15 03:23),
  `test_tsu_build.py`(8/15 13:54), `ns004_build_tsu.py`(8/15 14:13) — 전부
  `data/` 자체가 `.gitignore` 대상이라 git으로는 추적 안 됨
- CUE가 08-16 13:36경 `test_tsu_build.py`를 검증 목적으로 직접 실행 —
  로그에 `skipped=True`로 찍혀 **추가 mutation 없이 기존 항목만 재확인**한
  것으로 확인됨(같은 file_hash, 같은 created_at 유지 확인 후 삭제)
- DBMA production Qdrant(6333)는 **현재 프로세스 자체가 떠있지 않음**
  (`Connection refused`) — 이 경로로 실제 검색 결과에 반영된 적은 없음(단,
  이게 governance 위반의 심각성을 낮추는 근거는 아님 — Rev. Bang 지적대로
  retrieval impact와 governance impact는 별개)

## CUE가 판정하지 않은 것 (증거 부족 — 추정 금지)

- 누가/무엇이 2026-08-15 03:07:18에 이 ingestion을 실행시켰는가
- 왜 실행됐는가(의도적 테스트였는지, 실수였는지)
- 이 세 스크립트가 서로 어떤 호출 관계인지 전부
