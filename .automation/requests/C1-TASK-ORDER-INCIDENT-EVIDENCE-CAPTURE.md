# C1 Task Order — Incident Evidence Capture (DBMA Core / NAE Isolation Violation)

| | |
|---|---|
| Issued by | CUE, on Rev. Bang's directive (2026-08-16) |
| Mode | **Evidence-only investigation. 절대 정리·삭제·복구·추가 실행 금지.** |
| Incident record | `.automation/evidence/incidents/2026-08-16-dbma-core-nae-isolation-violation/00-INCIDENT-RECORD.md` |
| ADR-025 | 이 작업과 무관 — Status **Proposed 그대로 유지**, 이 작업으로 승격/반려하지 않음 |

---

## 배경 (읽어라, 재조사 불필요한 부분)

CUE가 Phase 3(ADR-025 worker) 검증 중 `scripts/test_tsu_build.py`를 실행했다가,
NAE 소스(Dagg)가 **DBMA 코어 프로덕션 파이프라인**(`core.extractors`,
`core.processing`)을 거쳐 `data/제련완성본/`(DBMA 메인 코퍼스)에 이미
등록되어 있었다는 사실을 발견했다. 이 등록은 오늘 Corpus Factory 미션과
무관하며 `created_at: 2026-08-15T03:07:18`로, 훨씬 이전에 발생했다.

**CUE가 이미 삭제해버린 것(복구 불가)**:
- `data/제련완성본/original_pdf.md`
- `/tmp/ns003_phase1_result.json`(단, 전체 내용은 evidence 패키지에 복원해뒀음)
- `documents.json`의 Dagg 항목(삭제 전 백업 보존됨)

**절대 하지 마라**: 이미 벌어진 삭제를 되돌리려 하지 마라(백업으로 복원
시도 금지 — 그건 CUE/Rev. Bang이 판단할 일). 어떤 형태로든 NAE 소스를
DBMA Core 파이프라인에 다시 통과시키지 마라(추가 mutation 절대 금지).
`scripts/ns003_nae_ingestion.py`, `ns004_build_tsu.py`, `test_tsu_build.py`를
**실행하지 마라** — 읽기만 해라.

---

## 조사 범위 (Rev. Bang이 직접 지정한 12개 항목)

증거 패키지 위치를 먼저 확인해라: `.automation/evidence/incidents/2026-08-16-dbma-core-nae-isolation-violation/`
(01-preserved-documents-json-backup.json에 Dagg 항목 원본 전체 보존됨,
02-implicated-scripts/에 세 스크립트 스냅샷 보존됨 — 원본 삭제되기 전에
캡처됨).

1. `documents.json`의 Dagg entry — **위 백업 파일에서 확인해라, 이미 있다**
2. `data/제련완성본/original_pdf.md` — **이미 삭제됨, 파일 자체는 조사
   불가**. 대신 evidence 패키지의 `01-preserved-ns003-result.json`에서
   간접 정보(생성 로그)만 확인 가능
3. 해당 파일의 정확한 filesystem metadata — **위와 동일 사유로 불가능**.
   가능한 범위: `documents.json` 백업에 남은 `created_at`/`last_processed_at`/
   `file_hash`로 대체 조사
4. `scripts/ns003_nae_ingestion.py` — 코드 읽기 분석(무엇을 하는 스크립트인지,
   `process_single_source()`가 어떤 core 모듈을 호출하는지, NAE 경로를
   어떻게 참조하는지)
5. `scripts/test_tsu_build.py` — 코드 읽기 분석
6. `scripts/ns004_build_tsu.py` — 코드 읽기 분석
7. 이 세 스크립트 사이의 호출 관계 — import 그래프로 확인
8. **Git history 확인은 CUE가 이미 끝냈다** — `git log --all -- <세 파일>`
   결과 **전부 빈 결과, 즉 세 파일 다 git에 커밋된 적이 없다**(계속
   untracked 상태). 다시 조사하지 마라.
9. shell history나 실행 기록이 남아있는지(`~/.zsh_history`,
   `~/.bash_history`, `.automation/night-shift/logs/` 등에 이 스크립트
   실행 흔적이 있는지) — 있으면 타임스탬프와 함께 인용
10. Dagg가 DBMA Core에 들어간 이후 생성된 downstream artifact가 추가로
    있는지 — CUE가 `grep -rl "0d849d7ba30bafddaa0a544c93dd8c66" data/
    output/`로 확인한 결과 registry 외에는 없었다(재확인만 해라, 못 찾으면
    "CUE 결과와 일치, 추가 artifact 없음"이라고만 적어라)
11. `documents.json` 82건(현재 81건, Dagg 제거 후) 전체에 대해 NAE
    source(Dagg/Fuller/Hiscox 등 author/title 매칭)가 추가로 있는지 —
    CUE가 이미 전수 검색해서 **Dagg 1건뿐**임을 확인했다. 위 백업 파일
    (Dagg 포함 82건 원본)로 재검증해라
12. Qdrant(6333 DBMA production, 7333 NAE)/registration_state.json/
    ADR-020 incremental_state.json에 영향이 있었는지 최종 확인 — CUE가
    이미 확인한 것: DBMA Qdrant(6333)는 **현재 프로세스 자체가 안 떠있음**
    (Connection refused), NAE Qdrant(7333)는 baseline 3,319 그대로,
    `registration_state.json`의 Dagg 항목은 무변경. **재확인만 해라.**

## 절대 결론 내리지 마라 — 이것만 확인해서 보고해라

"누가/왜 2026-08-15 03:07:18에 이 ingestion을 실행시켰는가"는 **추정하지
마라.** 코드와 로그가 직접 말해주는 사실만 적어라. 모르면 "확인 불가"라고
정직하게 적어라 — 이게 이번 지시서 전체에서 가장 중요한 원칙이다.

## Evidence 저장 위치

`.automation/evidence/incidents/2026-08-16-dbma-core-nae-isolation-violation/`
아래에 `03-C1-INVESTIGATION-REPORT.md`로 작성해라. 각 항목(1-12)에 번호를
그대로 달아서 답하고, 실행한 명령이 있으면(읽기 전용만) command+raw output을
포함해라.

## 완료 후

이 조사는 CUE의 독립 감사 대상이다. C1의 결론(있다면)을 CUE가 신뢰하지
않고 재확인한다 — "정리 가능/불가능" 판정은 C1이 내리지 않는다, CUE가
Rev. Bang에게 보고 후 결정한다.
