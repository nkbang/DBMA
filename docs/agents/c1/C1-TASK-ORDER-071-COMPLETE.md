# C1 Task Order 071 — ADR-035 초안 독립 리뷰 (완료 기록)

- 리뷰 수행: C1 (PLAN MODE)
- 최종 검증·반영: CUE (2026-09-23) — C1의 응답을 코드 재실측 없이 그대로
  채택하지 않고, 반영 전에 직접 파일을 다시 확인함(C1 자체 보고 검증
  없이 신뢰 금지 원칙)

---

## 요약

| RQ | C1 판정 | CUE 재검증 결과 | ADR-035 반영 |
|---|---|---|---|
| RQ1 | 부분 동의(경로 오타 2건) | **library.py는 C1이 틀림, research.py는 C1도 틀림** — 아래 상세 | 두 인용 모두 정정 |
| RQ2 | 동의 | 실측 일치 확인 | 변경 없음 |
| RQ3 | 부분 동의(위험 시나리오 3건 누락) | 3건 중 2건(중복 감지, 동시성) 타당 — §3.1에 구현 조건으로 반영. 1건(메모리 누수)은 폴링 계층 자체가 아직 미구현 상태라 근거를 확인할 코드가 없어 별도 반영 보류 | §3.1에 조건 2건 추가 |
| RQ4 | 동의 + 보강 권고 | "Production Registry" = `core/dataset_registry.py`(ADR-023 §후속기록에서 이미 이렇게 확정) 확인, 보강 타당 | 헤더 표에 파일 경로 명시 |

## RQ1 상세 재검증

C1은 두 인용 모두 "오타"라고 판정했으나, 직접 재실측한 결과 **하나는
ADR-035가 맞고 C1이 틀렸으며, 다른 하나는 ADR-035와 C1 둘 다 틀렸다**:

1. **`ui/pages/library.py:856`(휴지통 자동 삭제)**: C1은 "실제 호출
   위치는 843"이라 주장했으나, 843은 `_render_trash_section()` 함수
   정의/docstring이 시작하는 줄이고, 실제 `auto_purged =
   maybe_purge_expired_trash()` 호출문은 **856이 맞다**(재확인 완료,
   `grep -n "auto_purged = maybe_purge_expired_trash()"` → 856).
   ADR-035의 원래 인용이 정확했다 — 변경하지 않음.
2. **`research.py:169`(세션 자동 생성)**: 여기는 ADR-035가 실제로
   틀렸다. 단, C1이 제시한 "170"도 틀렸다 — Phase 1 화면 통합(PR #75)
   에서 `render_research_workspace_page()`를 파일 앞부분에 추가하며
   `create_session()` 호출이 뒤로 밀려, **실제 현재 위치는
   `ui/pages/research.py:198`**이다(`grep -n "create_session()"`으로
   재확인). ADR-035를 이 줄번호로 정정했다. 파일 경로 누락("research.py"
   → "ui/pages/research.py")도 함께 수정.

## RQ3 상세 재검증

- **중복 감지(dedup)** 및 **동시성 제어(직렬화)**: 타당한 지적. 아직
  구현 전 단계이므로 코드 반증은 불가능하지만, 설계 원칙으로 §3.1에
  "구현 시 반드시 지킬 조건"으로 명문화했다 — 특히 동시성 제어는 새
  락(lock)을 만드는 대신 `process_one_file()`이 이미 전제하는 파일
  단위 순차 호출을 automation 계층이 깨지 않는 방식으로 반영해,
  불필요한 신규 인프라 도입을 피했다(CLAUDE.md "불필요하게 넓은
  리팩터링 금지" 원칙에 맞춤).
- **메모리 누수(폴링 장기 실행)**: 방향은 타당하나, 이 automation
  계층(§3.1의 `core/raw_folder_watcher.py`) 자체가 아직 코드로
  존재하지 않아 "실측"으로 검증할 대상이 없다. §3.1에 "매 폴링마다
  새로 스캔하고 리소스를 즉시 해제"라는 일반 원칙만 추가하고, 구체적인
  구현(스레드 vs 프로세스, 파일 핸들 관리)은 실제 구현 PR에서
  다루기로 범위를 분리했다 — 이 ADR은 설계 문서이지 구현 스펙이
  아니기 때문(§0 원칙).

## 결론

ADR-035는 C1 Review를 반영해 다음을 수정했다:
1. `library.py:856` 인용 유지 + C1의 오류 정정 기록 추가
2. `research.py` 인용을 `ui/pages/research.py:198`로 정정
3. "Production Registry" = `core/dataset_registry.py` 명시
4. §3.1에 중복 감지·동시성 제어 조건 2건 추가

Status는 계속 **Proposed** — 남은 승격 조건은 구현 완료·회귀 테스트·
사용자(Rev. Bang) 승인 3가지.
