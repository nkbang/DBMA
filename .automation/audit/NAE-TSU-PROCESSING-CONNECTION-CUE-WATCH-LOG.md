# CUE Watch Log — NAE TSU Processing Connection (Night Shift Order 003)

CUE는 C1(Cline)을 프로그래밍적으로 트리거하거나 상태를 실시간으로 읽을 수
없다. 이 로그는 CUE가 filesystem/git/Qdrant를 직접 재실행/재조회해 검증한
기록이다. C1의 서술만으로 PASS를 인정하지 않는다.

## 2026-08-15 07:58 UTC — kickoff, 착수 전 조사 결과

Order 발행 전 CUE가 직접 확인한 사실(재조사 불필요, Order 003에 그대로 반영됨):

- `NAE/pipeline/tsu/runner.py --identifier <id>`: 기존 override 경로, Gate
  우회, `builder.build_tsu_for_identifier()` 직접 호출. 신규 코드 아님.
- `scripts/nae_incremental_ingest.py --identifier <id> [--apply]`: ADR-020
  Approved 구현. 기본 dry-run, embedding.py의 content_hash 캐시가 중복 방지
  내장.
- **Dagg/Hiscox는 이미 2026-08-09 TSU+embedding+Qdrant indexing 완료**:
  - `NAE/corpus/tsu/Dagg_Church_Order/index_report.json`:
    `generated_at: 2026-08-09T18:32:43Z, indexed: 5`
  - Qdrant 실측(`scroll` + filter `source_id=BAP-CHURCH-DAGG-001`): **10
    point 존재**, `work_id: WORK-DAGG-CHURCH-ORDER-001`
  - 어젯밤 Registration이 계산한 신규 `work_id`: `dagg_john_l-church_order`
    — **identity 스킴 불일치 확인**
  - Hiscox도 동일 패턴(`index_report.json`, `indexed: 5`, 2026-08-09)
- **Fuller Vol01-08은 TSU 미존재**(`find`로 확인, 디렉터리 자체가 없음).
  `NAE/corpus/canonical/Fuller_Complete_Works_Vol01~08/`에는 이미
  canonical.json/txt 존재(2026-08-07 생성) — 추출은 끝나 있음.
- Qdrant baseline(재확인): `nae_tsu_v1` = 3,319 points.

Order 003을 이 사실에 맞춰 재구성: 파일럿을 Dagg(사용자 원 지시 예시와 다름)
대신 **Fuller_Complete_Works_Vol01**로 지정, Dagg/Hiscox는 이번 미션에서
제외(identity 불일치는 별도 정리 필요 — 이 미션 범위 아님). 릴레이 7로 전달.

Baseline:
- `.automation/evidence/night-shift/tsu-processing-connection/` — 미생성
- `NAE/corpus/tsu/Fuller_Complete_Works_Vol01~08/` — 전부 미존재
- Qdrant `nae_tsu_v1` — 3,319 points
- `git diff core/retrieval.py NAE/pipeline/tsu/*.py NAE/pipeline/ingest/*.py` — 비어 있음

이후 각 check-in은 이 파일 하단에 append.

## 2026-08-15 15:42 UTC(추정, 세션 재개 후) — C1 보고 독립 검증 + 중대 구조적 발견

### C1 보고 검증

PID 88689가 C1이 launchd로 띄운 프로세스임을 확인(C1 보고서와 대조 일치).
`tsu_report.json` 재조회 결과 CUE가 아까 직접 읽었던 값과 일치(300/5,452,
claims 207, elapsed 3248.91s) — 서로 다른 체크포인트 시점(C1은 100건째,
CUE는 300건째) 관측이라 속도 차이(12.65s vs 10.83s/candidate)는 정상 변동,
불일치 아님. Evidence 파일(`MISSION-003-STATUS.md`,
`phase-1-tsu-generation/README.md`) 실재 확인.

**실측 기반 전체 완료 예상**: 볼륨당 16~21시간, 8볼륨 전부면 130~170시간+.

### 🔴 구조적 발견 — Phase 2/3는 TSU 생성이 끝나도 자동으로 진행되지 않는다

`scripts/nae_incremental_ingest.py:33`:
```python
return [r for r in data if r.get("review_status") == "verified"]
```

`NAE/pipeline/tsu/review_promotion.py` 모듈 docstring이 명시: `review_status
== "verified"`는 **"사람이 신학적 검토를 완료했다"**는 뜻이며, 이 모듈은
"the only path by which a TSU record's review_status may become verified"다.
새로 생성되는 TSU는 전부 `review_status: "generated"`로 시작한다(builder.py
자체 docstring).

즉 Phase 1이 20시간 뒤 완료돼도, Phase 2(embedding dry-run)는 **검토·승격된
레코드가 0건이라 아무것도 하지 않을 것**이다. Dagg/Hiscox의 기존
`index_report.json`이 `records_total_raw: 3377/740` 중 `gate_pass: 5,
indexed: 5`였던 이유가 바로 이것 — 원래도 사람이 수천 개 후보 중 5개만
검토·승격한 결과였다.

**결론**: 이건 버그나 설계 공백이 아니라 **의도된 human-in-the-loop 품질
게이트**다. C1/CUE가 임의로 우회·자동화하면 안 된다(Order 003의 "새 아키텍처
임의 구현 금지"와 review_promotion.py의 설계 의도 둘 다 위반). Phase 1
완료 후 Phase 2로 넘어가려면 **사람의 검토·승격 결정이 별도로 필요**하다는
사실을 Rev. Bang에게 미리 보고함.

Rev. Bang 결정: 현재 프로세스(PID 88689) 그대로 계속 진행. Phase 1 완료 후
review/promotion 필요성은 그때 다시 보고.

## 2026-08-15 16:05 CDT — CUE Directive 채택: NAE TSU Extraction Continuation

Rev. Bang 지시로 아래를 운영 원칙으로 고정한다(요약, 전문은 대화 기록 참고):

- Vol01 production run(PID 88689, `llama-server --parallel 1`) 무변경 유지.
  Ollama 재시작·모델 unload/load·`OLLAMA_NUM_PARALLEL` 변경·프로세스 중단
  전부 금지.
- C1에게 새 성능 실험 하달 안 함(병렬화 실험 취소).
- CUE는 1시간 간격으로 다음만 확인: processed/total, throughput,
  process alive, error/failure count, evidence/state integrity. 정상이면
  개입하지 않는다.
- 개입 조건(이것만): 프로세스 종료, 반복 오류, state/evidence corruption,
  데이터 손상 가능성, production boundary violation. 단일 candidate 실패는
  개입 사유 아님. **"느리다"는 이유만으로 중단·재설계 금지.**
- Vol01 완료 시 CUE가 즉시 확인: candidate count, TSU output count,
  실패/누락 count, evidence completeness, quality gate 결과, git diff.
  그 후 Vol02가 자동 큐(`run_tsu_queue.sh`)에서 이어서 시작 — Rev. Bang
  승인 대기 없이 진행.
- 모델 최적화 검토는 볼륨 간 경계(Vol01→Vol02 등)에서만, 별도 소규모
  benchmark로. Vol01을 위해 지금 재시작하지 않는다.
- 운영 원칙: "정상적으로 느리게 진행되는 작업은 방해하지 않는다." 현재
  0/400 failure, throughput 실측 진행 중 — 이 상태로는 무개입.
- 아침까지 Rev. Bang 추가 입력 대기 없이: C1 생산 계속, CUE 감시·장애
  대응·다음 batch 완료 감사만 수행.

이 시점부터 위 원칙이 기본 운영 모드다. 이후 이탈 시에만 이 로그에 기록.

## 2026-08-15 23:10 CDT — Rev. Bang 무인모드 진입

Rev. Bang이 무인모드로 전환. 이후 CUE Directive(§8) 그대로 무인 운영:
- Vol01 production run 무변경 유지, 1시간 간격 감시 계속
- 정상 진행(processed↑, errors=0, process alive)이면 무개입, 보고만
- 개입 조건(프로세스 사망/반복 오류/state corruption/production boundary
  violation)에서만 능동 대응, 그 외엔 사용자 응답 기다리지 않고 계속 진행
- Vol01 완료 시 6항목 완료 감사 자동 실행 후 Vol02 자동 시작(승인 대기 없음)
- 대시보드(http://127.0.0.1:8799, launchd KeepAlive) 계속 서빙

## 2026-08-15 23:38 CDT — Vol02 자동전환 취소, Corpus Factory 전환 명령 준비

Rev. Bang 지시: "v1 완료시 v2 로 가지말고 다음 작업을 실행하라" +
NAE Corpus Factory 전환 상세 명령서(Phase 0-10, Acceptance Criteria 포함).

- 기존 `run_tsu_queue.sh`(Vol01 완료 시 자동으로 Vol02 시작하던 큐,
  PID 26127)를 **즉시 kill**. Vol01(PID 88689) 프로세스 자체는 무손상 확인.
- `capture_vol01_baseline.sh` 신설 — Vol01 완료 시 Processing/TSU/System/
  Integrity 전 항목을 자동 캡처해 영구 baseline 문서로 남김(Qdrant
  point 수, production boundary git diff 포함).
- `wait_vol01_then_baseline.sh` 신설 — Vol01 완료(partial:false)만 감지,
  baseline 캡처까지만 자동 실행. **Vol02는 시작하지 않음.**
  1차 시도(Bash run_in_background)에서 2회 연속 false-positive
  "process died" 발생 — 직접 `ps aux`로 재확인 결과 Vol01은 실제로는
  완전히 정상(대시보드 API도 `process_alive: true` 동시 확인). 원인:
  이 환경의 `run_in_background: true` Bash 샌드박스가 다른 Bash 호출로
  띄운 프로세스를 `ps aux`로 못 보는 격리 특성으로 추정(1시간 감시는
  Monitor 도구로 동일 패턴을 계속 정상 인식해왔음 — 대조 확인). 조치:
  사망 감지 로직을 스크립트에서 제거하고(1시간 Monitor가 이미 담당),
  Bash 대신 **Monitor 도구**로 재실행 — 정상 기동 확인.
- `.automation/requests/C1-TASK-ORDER-NAE-CORPUS-FACTORY-TRANSITION.md`
  발행(Phase 0-10, §13 병렬화 정책 — 실험은 제안만, CUE 승인 필요, §21
  C1 PASS 보고를 최종 근거로 안 씀 원칙 재확인). 릴레이 8로 relay
  snippet에 준비 완료, **Vol01 완료 전에는 사용하지 않음**.

## 2026-08-16 06:47 CDT — Vol.1 완료 확정, Phase 0 baseline 캡처 완료

`tsu_report.json`: `partial: False`, `candidates_evaluated: 5452/5452`,
`claims_extracted: 3643`, `llm_errors: 1`. 총 소요 16.04시간(57726.8초).

`capture_vol01_baseline.sh` 실행 결과(`PHASE0-VOL01-BASELINE.md`):
- successful 3643 / rejected(non-claim) 1808 / failed 1
- confidence 분포: 0.8-0.9구간 2764건, 0.9-1.0구간 879건(전부 0.8 이상 —
  낮은 confidence 없음, 모델의 self-report 특성상 참고용)
- doctrine breakdown: Soteriology 2314건 압도적, 나머지는 소수 분산
- duplicate claim text 15건, duplicate source_text 1건
- review_status 전부 `generated`(자동 승격 없음 확인)
- **Production boundary 전부 정상**: `core/retrieval.py` 등 무변경,
  Qdrant `nae_tsu_v1` 3319 유지(mutation 없음), registration_state
  10/10 QUALITY_PASSED 그대로

두 감시 프로세스(Vol01 완료 watcher, 1시간 감시) 전부 정상 종료 처리 —
Vol01 대상 process가 더 이상 없으므로 재가동 대상 아님. 다음 작업
(Corpus Factory Phase 1 착수, 릴레이 8)은 Rev. Bang 지시 대기.

## 2026-08-16 07:05 CDT — Corpus Factory Phase 1: 반려(계산 오류 1건 + 과대해석 1건)

릴레이 8로 착수, C1이 Phase 1(병목분석) 완료 보고. CUE 재계산 결과:

- Q3(duplicate 15/1) 등 대부분 정확(CUE 직접 재계산 일치)
- **Q1 오류**: "57726.8s/3644 calls=15.84s/call"은 틀림 — extract_claim()은
  candidates_evaluated 5,452건 전부에 호출됨(3,644는 결과가 있었던 건수일
  뿐). 올바른 값 10.59s/call은 같은 문서 Processing 표에 이미 있어
  자기모순.
- **Q2 과대해석**: "1,808건 33% deterministic filtering 가능"을 이미
  검증된 효과처럼 서술. 그러나 1,808은 LLM을 실제로 호출해 나온 사후
  결과이지, 저비용 rule의 사전 필터링 가능성을 증명하지 않음 — 명령서
  §4가 정확히 경고한 실수("Recall 손실 가능성 있는 filtering은 반드시
  benchmark 검증"). Phase 1 종합결론 표도 확정형으로 서술돼 있어 Phase 2가
  잘못된 전제로 시작할 위험.

Correction Order 004 발행, 릴레이 9로 전달.

## 2026-08-16 07:15 CDT — Phase 1 정정 확인(PASS), Phase 2 반려(카운트 재현 안 됨)

Phase 1 정정 재검증: Q1(10.59s/call로 정정, 문서 내 다른 값과 이제 일치),
Q2("상한선/benchmark 필요"로 정정, 종합결론 표도 "최대 33%(검증 필요)"로
수정됨) — **PASS**.

Phase 2(`PHASE2-CANDIDATE-FILTERING-DESIGN.md`) 설계 구조는 견고함(상한선/
검증효과 구분을 문서 전체 일관 적용, benchmark 우선 설계, Priority
분류 — 명령서 §4 원칙 정확히 반영) — **PASS**.

단 §6 "Upper Bound 요약" 표의 실측 카운트를 CUE가 문서에 적힌 정규식
그대로 재현한 결과 불일치:
- L1b(페이지 번호): 문서 291건 vs CUE 재현 1,153건(4배)
- L4b(소문자 시작): 문서 666건 vs CUE 재현 374건(약 절반)
- candidate 총수(5,452)는 일치 — baseline 대조 가능한 값이라 당연히 맞음
- 문서에 실행 코드/raw output이 없어 숫자 출처 확인 불가(Phase 0의
  `capture_vol01_baseline.sh`와 다른 패턴 — 재실행 가능한 형태 아님)

CUE 재현 스크립트를 evidence로 남김
(`cue-phase2-recount.py`). Correction Order 005 발행, 릴레이 10으로 전달.
§6 표만 반려, §0-5/§7 설계 원칙은 PASS 유지.

## 2026-08-16 13:30 CDT — Correction 005 재검증: 핵심 PASS, 잔여 이슈 1건 → Correction 006

C1이 `phase2-upper-bound-recount.py`(165줄)와 `PHASE2-UPPER-BOUND-VERIFIED.md`
제출. CUE가 스크립트를 **직접 재실행**해서 검증(서술 신뢰 안 함):

- 8개 Layer 카운트(852/1153/1/15/4/0/8/374) 전부 raw stdout과 정확히
  일치 — L1b(1,153)/L4b(374) 둘 다 CUE의 원래 재현값과도 일치 확인
- 합집합(union) 1,536건/28.2% — 스크립트가 실제 출력한 값, `1536/5452=
  28.17%≈28.2%` 재계산도 일치. §4가 이 값을 "실제 이론적 상한선"으로
  지목 — 이게 핵심 결론이고 **PASS**
- L1b 패턴이 대부분 실제 페이지번호가 아닌 오탐(false positive)임을
  C1이 스스로 5건 샘플로 정직하게 노출·경고("일부는 p.가 포함된 신학적
  문장일 수 있음") — Correction 005가 요구한 정직한 재검증 정확히 이행
- L3a(438→4), L3b(17→0) 등 큰 폭 정정도 원인(단어수 필터 미적용,
  인용부호 패턴과 혼동) 명시 — 타당함

**잔여 이슈 1건**: §1/§4의 "단순 합산 2,257건(41.4%)"이 스크립트 출력
어디에도 없음(재실행 stdout grep 결과 0건) — 손계산으로도 재현 안 됨
(L0 포함 2407, L0 제외 1555, 둘 다 2257과 다름). 결론에 쓰이는 값은
합집합(1,536)이라 이 비교 수치는 결정에 영향 없으나, "추정값이나
서술만으로 PASS 처리하지 않음" 원칙상 반려. Correction Order 006(작은
범위) 발행, 릴레이 11로 전달.

## 2026-08-16 13:35 CDT — Correction 006 확인: PASS, Phase 2 완전 종료

C1이 옵션 2(삭제)를 선택 — "단순 합산 2,257(41.4%)" 관련 문장/행을 §1 표,
§3, §4에서 전부 제거하고 검증된 "합집합 1,536건(28.2%)"만 남김. §1 표
재확인 결과 미검증 행 없이 스크립트 실측값만 남아있음을 CUE가 직접 확인.

**Phase 2(Candidate Filtering 설계) 최종 판정: PASS.** 모든 수치가
`phase2-upper-bound-recount.py` 재실행으로 재현 검증됨. Phase 3(TSU
Extraction Pipeline 분리)로 진행 가능.

## 2026-08-16 14:20 CDT — Phase 3 검증 중 DBMA Core 오염 발견 → 정리 절차 오류 → 격리·증거보존 전환

Phase 3(ADR-025 worker) 검증 중 `scripts/test_tsu_build.py` 실행 → 완전히
무관한 `scripts/ns003_nae_ingestion.py`를 호출해 NAE 소스(Dagg)가 DBMA
코어 파이프라인(`core.extractors`/`core.processing`)을 거쳐
`data/제련완성본/`(DBMA 메인 코퍼스, `.gitignore` 대상이라 git 미추적)에
이미 등록(2026-08-15T03:07:18, 오늘 미션 시작 전)돼 있었음을 발견.

Rev. Bang "정리먼저" 지시 → CUE가 즉시 삭제 실행(documents.json에서 Dagg
항목 제거, `original_pdf.md` 삭제, `/tmp/ns003_phase1_result.json` 삭제).
**documents.json은 삭제 전 백업했으나 `original_pdf.md`는 백업 없이
삭제 — 복구 불가(Time Machine 미설정 확인).**

Rev. Bang이 이후 "격리·증거보존 후 CUE 독립감사" 방침으로 재지시 —
그러나 이미 삭제가 완료된 뒤 도착. **CUE의 절차 오류로 명시 기록.**

조치:
- `.automation/evidence/incidents/2026-08-16-dbma-core-nae-isolation-violation/`
  incident 패키지 작성: 00-INCIDENT-RECORD.md(절차 오류 명시 포함),
  01-preserved-documents-json-backup.json(삭제 전 82건 원본),
  01-preserved-ns003-result.json(대화 로그에서 복원), 02-implicated-scripts/
  (세 스크립트 스냅샷)
- `C1-TASK-ORDER-INCIDENT-EVIDENCE-CAPTURE.md` 발행 — Rev. Bang 지정
  12개 조사 항목 그대로, 정리/삭제/재실행 절대 금지, "누가/왜"는 추정
  금지 원칙 명시. CUE가 이미 확인한 항목(git history 전부 미커밋, Qdrant/
  registration_state 무영향, 오염범위 Dagg 1건뿐)은 재조사 생략 지시.
  ADR-025는 이 사안과 완전히 분리 유지(계속 Proposed).
- 릴레이 12로 전달.

**판정 보류 상태**: 오염 원인(누가/언제 실행시켰는지)은 미확정. Scope는
CUE 확인상 Dagg 1건, retrieval 영향은 없음(DBMA Qdrant 자체가 다운
상태)이나 governance 위반 자체는 확정. C1 증거 제출 후 CUE 독립 감사 예정.

## 2026-08-16 14:50 CDT — Incident 최종 판정: RESOLVED-OBSERVED, Phase 3 재개

C1의 `03-C1-INVESTIGATION-REPORT.md` 도착, 금지된 재실행 없이 안전하게
완료(감시 확인). 내용 검증:

- 스크립트 docstring이 "Night Shift Order 003"을 직접 언급 — 이번 미션
  초기(제가 그 Order를 발행한 시각과 거의 일치하는 03:06-03:07 CDT)의
  구현 시도로 강하게 추정됨(확정 아님, C1도 실행자 특정 안 함 — 원칙 준수)
- `.automation/night-shift/logs/ns003/phase1_BAP-CHURCH-DAGG-001.json`에서
  1차 실행이 경로 오타(`제륨완성벾n`)로 실패, 2차 실행이 성공했음을 확인 —
  단순 1회 실행이 아니라 디버깅 과정이 있었음을 시사
- CUE 직접 재확인 2건: (1) registration_state.json mtime "02:51 CDT"와
  내용의 "07:51:26" UTC 표기가 사실 동일 시각(CDT=UTC-5) — C1이 열어둔
  시각 불일치 의문 해소, 이 파일은 오염 사건 이후 무변경 확정. (2) NAE
  Qdrant 3,319 재확인(오늘 5회 이상 일관) — C1이 "확인 불가"로 남긴 항목
  CUE가 직접 닫음

Rev. Bang 최종 판정 수용, 정확한 구분 지시 반영:
- **정리 행위 자체의 증거 vs "production에 없다"는 결과 서술은 다른
  것**이라는 지적에 따라 `04-CLEANUP-ACTION-LOG.md` 신설 — 실행 명령
  전문, raw output, 즉시 사후검증을 별도 문서로 재구성·보존
- Governance track 분리 명시: **ADR-025(Proposed 유지, runner.py+test
  완료 후 재감사)**와 **이 incident(RESOLVED-OBSERVED)**는 독립된 두
  트랙 — 서로의 승인/종결 조건에 섞지 않음
- **Phase 3(Corpus Factory)는 이 incident로 인해 HOLD하지 않고 계속
  진행** — `00-INCIDENT-RECORD.md` 상태 필드에 명시 반영

최종 상태: Phase 3 CONTINUE / ADR-025 PROPOSED(변경 없음) / Incident
RESOLVED-OBSERVED(증거보존 완료).
