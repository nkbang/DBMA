# ADR-035 구현 Build Report

**작성일:** 2026-09-23
**작성자:** CUE
**관련:** `docs/architecture/ADR-035-NAE-Pastoral-Library-Automation.md`,
PR #76

---

## 구현 전 재확인에서 발견한 것

구현 착수 직전 코드를 다시 확인하는 과정에서, ADR-035 §3.1의 3번째
채택 항목("인덱스 자동 갱신")이 **이미 완전히 구현되어 있음**을
발견했다 — `core/background_index_builder.py`(HQ 제안 ⑧)가 백그라운드
데몬 스레드로 `reconcile_pending()`을 주기 실행하고, 처리 완료 시
즉시 트리거까지 하고 있었다. ADR-035를 정정(§2/§3.1)해 이 항목을
구현 범위에서 제외했다 — 실제 구현 범위는 2건으로 줄었다.

## 구현 항목

| 항목 | 파일 | 방식 |
|---|---|---|
| 1. RAW 폴더 신규 파일 감지 알림 | `core/raw_folder_watcher.py`(신규), `ui/pages/dashboard.py::_render_new_raw_files_notice()` | `.batch_state.json` 기준 미처리 파일 목록 반환, 하루 1회 폴링 제한(마커 파일), Dashboard에 배너로 알림만 — 자동 처리 없음, "처리하기" 클릭 시 Processing 화면으로 이동 |
| 2. 검색 결과 자동 수집(옵트인) | `ui/pages/research.py`, `ui/pages/sermon_research.py` | "설교 연구" 화면에 토글(기본 꺼짐) 추가, 켠 사용자는 검색 실행 시 상위 3건이 `sermon_research_selection` 버퍼에 자동 반영. 기존 수동 버튼 유지 |

## 구현 중 발견·수정한 버그

기존 `ui/pages/research.py`에 `_send_to_sermon_research(source_file,
document_id, detail)`(문서 상세 패널 전용)가 이미 존재하는 걸 놓치고
같은 이름으로 새 헬퍼를 정의했다가, 테스트 실행 중
`test_send_to_sermon_research_from_search_result` 실패로 즉시
발견했다(모듈 레벨 이름 shadowing — 나중 정의가 이긴다). 새 헬퍼를
`_append_search_result_to_sermon_research`로 개명해 해결.

## 테스트

| 대상 | 결과 |
|---|---|
| `tests/test_research_auto_collect_opt_in.py`(신규 4건) | passed |
| `tests/test_raw_folder_watcher.py`(신규 5건) | passed |
| 관련 기존 테스트(research/sermon_research_hub/dashboard/onboarding 등) | 50 passed |
| 전체 회귀 `pytest tests/ -q` | **3164 passed, 17 skipped(기존), 0 failed** |

## C1 Review 반영 사항 재확인

- RQ3(중복 감지): RAW 워처는 `.batch_state.json` 기준 미처리 여부로
  판정하므로, 처리 완료되면 자동으로 목록에서 빠진다 — 별도 dedup
  상태를 새로 만들지 않고 기존 마커 파일 메커니즘으로 자연 해소됨.
- RQ3(리소스 누수): 매 폴링이 새로 스캔하고 끝나며 파일 핸들을 들고
  있지 않는다 — 테스트(`test_find_new_raw_files_does_not_touch_filesystem_beyond_reading`)로 확인.
- RQ3(동시성): 인덱스 갱신 자체는 이미 구현된 기존 idempotent 설계를
  그대로 쓰므로 이 구현에서 새로 다룰 필요가 없었다(위 "구현 전 재확인" 참고).

## 남은 것

ADR-035 §5 승격 조건 4개 중 "구현 완료"·"회귀 테스트 통과"는 이번에
충족. 남은 것은 **사용자(Rev. Bang) 최종 승인**뿐 — 승인 시 ADR-035
Status를 Proposed → Approved로 갱신한다.
