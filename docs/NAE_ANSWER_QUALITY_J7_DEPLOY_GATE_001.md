---
title: "J7 — 배포 게이트 점검 001"
created: 2026-10-18
status: 기계 게이트 통과 · **G7(사용자 채점) 대기**
base: feat/nae-answer-quality-journey @ 26314b3a (dev/dbma-engine 계보)
venv: ~/envs/dbma311
related:
  - docs/NAE_ANSWER_QUALITY_JOURNEY_PLAN_v1.md (J7)
  - docs/NAE_ANSWER_QUALITY_J6_SCORING_SHEET_001.md (채점 입력)
  - docs/RELEASE_SECURITY_CHECKLIST_STATUS.md (이번 실행으로 갱신)
---

# J7 — 배포 게이트 점검 (2026-10-18)

계획서 J7의 게이트는 네 가지다 — 보안 프리플라이트 / Windows 절차서 /
회귀 전량 / **P0-5 사용자 채점**. 앞의 셋은 기계적으로 판정했고, 마지막
하나는 질의세트 문서 규정상 **사용자 전용**이라 대기 상태다.

## 1. 보안 프리플라이트 — R7 통과 ✅

`scripts/security_preflight.py`(dry-run) 재실행. 보고서
`docs/RELEASE_SECURITY_CHECKLIST_STATUS.md` 갱신.

| # | 항목 | 판정 |
|---|---|---|
| 1 | Qdrant 로컬 인증 | 해당없음 (배포 실행 경로는 TSU 전량 메모리 적재, Qdrant 미사용) |
| 2 | 디스크 암호화(FileVault) | **적용됨** (FileVault is On) |
| 3 | RAW 디렉터리 권한 | **적용됨** (`data/RAW` = 0700) |
| 4 | 인제스트 로그 출처+타임스탬프 | **적용됨** (registry 레코드가 감사 로그 역할) |
| 5 | 업로드 문서 최소 스캔 | 부분 충족 (노이즈 분류는 있고 프롬프트 인젝션 전용 탐지는 없음 — 백로그) |

**R7 통과.** 사용자 조치 필요 항목은 2번(개인 기기 설정이라 앱이 강제 불가,
INSTALL.md 권고로 대응)뿐이고, 5번은 배포 차단 결함이 아니라 백로그다.
2026-09-17 판정과 동일하다.

## 2. Windows 절차서 11개 점검

`scripts/windows/verify_windows_readiness.py` 실행.

### 2.1 1차 실행 — 10 PASS / 1 FAIL

| 점검 | 결과 |
|---|---|
| 01 environment ~ 09 streamlit_smoke | 전부 PASS (의존 15개 import, ollama 0.40.6, file_lock 상호배제, 인코딩 왕복, registry 교체 경합 367저장/11,419읽기 무실패, streamlit health ok) |
| **10 apptest_pages** | **FAIL** — `AppTest script run timed out after 120(s)` (191.1s 소요) |
| 11 pytest_windows_set | PASS (51 passed) |

### 2.2 재현 안 됨 — 일시적 현상으로 판정

같은 점검만 분리해 재실행:

```text
[PASS] 09_streamlit_smoke    1.5s
[PASS] 10_apptest_pages      3.9s   6개 페이지 예외 없이 렌더링
```

추가 확인(두 체크아웃 모두 정상):

| 조건 | Dashboard 1페이지 | 6페이지 전부 |
|---|---|---|
| 작업 브랜치(worktree) | 3.3s · 예외 0 | **6/6 선택일치·예외 0** |
| 프로덕션 체크아웃 | 4.0s · 예외 0 | — |

처음에는 "프로덕션 체크아웃의 다른 세션 미커밋 변경 때문"이라고 추정했으나
**그 추정은 틀렸다** — 프로덕션 체크아웃에서도 4.0초에 통과한다. 엔진 적재도
2.9초로 병목이 아니다(119,595 TSU).

원인을 특정하지 못했다. 재현되지 않으므로 코드 결함으로 단정하지 않고
**일시적 자원 경합**(앱 부팅 시 Ollama 모델 적재·언로드와 겹쳤을 가능성)으로
기록한다. 다만 **이 게이트는 타이밍에 민감하다**는 사실 자체는 남긴다 —
AppTest 1페이지 기본 타임아웃이 120초이고, 모델이 차가운 상태에서 부팅이
그 안에 끝나지 않을 수 있다. 재실행으로 판정하는 운영 규칙이 필요하다.

### 2.3 2차 전체 실행 — 11/11 PASS

```text
[INFO] 01_environment              0.0s
[PASS] 02_dependencies             6.1s   필수 15개 import 성공
[PASS] 03_external_binaries        0.0s   ollama 0.40.6
[PASS] 04_ollama_server            0.0s   bge-m3 + 생성 모델 있음(모델 16개)
[PASS] 05_app_import               3.8s   import ui.app (fcntl 의존 제거 확인)
[PASS] 06_file_lock                1.6s   스레드·프로세스 상호배제, 한글 경로
[PASS] 07_encoding_roundtrip       0.1s   히브리어·폴리토닉 헬라어·한글·em dash
[PASS] 08_registry_replace_stress 12.1s   저장 648회·읽기 17,944회 무실패
[PASS] 09_streamlit_smoke          1.3s   /_stcore/health = ok
[PASS] 10_apptest_pages            3.8s   6페이지 예외 0 (1차에서 FAIL했던 항목)
[PASS] 11_pytest_windows_set      24.9s   51 passed
```

**1차 대비 경합 증거**: 같은 점검 11이 1차에서 **786.0s**였고 2차에서
**24.9s**다(31배). 점검 8의 처리량도 1차 367저장/11,419읽기 → 2차
648저장/17,944읽기로 늘었다. 1차 실행 시점에 머신이 무언가에 눌려 있었다는
뜻이고, 10번의 120초 타임아웃도 같은 원인으로 설명된다. 산출물:
`docs/NAE_ANSWER_QUALITY_J7_WINDOWS_READINESS_002_REPORT.md`.

## 3. 회귀 전량 ✅

```text
pytest tests --ignore=tests/nae
→ 3,438 passed / 20 skipped / 0 failed  (171.51s)
```

이번 여정에서 추가한 테스트가 포함된 수치다 — `test_paragraph_context.py`
22건, `test_sentence_window_context_expansion.py` +8건,
`test_generation_denomination.py` +5건,
`test_generation_stream_contamination.py` +3건,
`test_sidecar_metadata.py` +4건.

## 4. 릴리스 경로 상태

| 항목 | 상태 |
|---|---|
| 배포 태그 | `beta-v1.3.0-rc7` (`BETA_LATEST_TAG.txt`, 무변경) |
| 작업 브랜치 | `feat/nae-answer-quality-journey` — origin에 push 완료 |
| 릴리스 계보(dev) 대비 | **14 커밋 / 26 파일 / +6,786 −65** |
| PR 생성 | **불가** — 이 셸에서 GitHub API가 차단됨(`api.github.com` network unreachable). `git push`는 정상 동작한다. PR은 사용자가 웹에서 열거나 네트워크가 열린 환경에서 열어야 한다 |
| main 병합 | 해당 없음 (예외 규정 — 승인 대상) |

## 5. 게이트 판정

| 게이트 | 기준 | 결과 |
|---|---|---|
| 보안 프리플라이트 | R7 통과 | ✅ 통과 |
| Windows 11개 점검 | 전항 PASS | ✅ **11/11 PASS**(2차 전체 실행). 1차의 10번 FAIL은 재현되지 않음 — 같은 실행의 점검 11이 786s→24.9s로 줄어 자원 경합이 원인으로 보인다 |
| 회귀 전량 | 0 failed | ✅ 3,438 passed / 0 failed |
| **G7 P0-5 사용자 채점** | FAIL 0 · NOT VERIFIED ≤ 4/24 · PASS ≥ 14/24 | ❌ **미통과** — PASS 17 ✅ · 대기 0 ✅ · **FAIL 1 ❌**(E2). 아래 §7 |

## 6. G7 확정 판정 (2026-10-22, 사용자 결정 ⓐ)

채점은 두 라운드로 진행됐다. 1차(24건)는 슬라이더가 1건을 빼고 전부 0이라
승인된 판정식으로 환산할 수 없었고, 2차(11건)는 **슬라이더 11/11이 모두
입력돼** 환산이 성립했다.

사용자 결정: **기준 환산을 G7의 기록으로 삼는다**(사용자 총괄 판정은 전부
PASS였으나, 기준 문서를 개정하지 않는 쪽을 택했다).

### 6.1 환산 (docs/NAE_GOLD_QUERY_SET_P0_5_001.md §채점 기준, 3축)

| ID | 구분 | 정합 | 유용 | 언어 | 평균 | 판정 |
|---|---|---:|---:|---:|---:|---|
| B1 · C2 · H2 | 실답변 | 4 | 4 | 4 | 4.00 | **PASS** |
| A1 | 부분 유보 | 4 | 4 | 4 | 4.00 | **PASS** |
| A3 · B2 · H1 | 실답변 | 3 | 3 | 3 | 3.00 | FLAG |
| C3 | 실답변 | 3 | 3 | **2** | 2.67 | FLAG |
| D1 | 부분 유보 | 3 | **2** | 3 | 2.67 | FLAG |
| E1 | 부분 유보 | 3 | 4 | 4 | 3.67 | FLAG |
| **E2** | 부분 유보 | **2** | **2** | **2** | **2.00** | **FAIL** |

순수 유보 13건(A2·B3·C1·D2·D3·E3·F1·F2·F3·G1·G2·G3·H3)은 "정직 유보 →
수동 PASS" 규칙 적용.

### 6.2 전체 24건

```text
PASS 17  (순수 유보 13 + 기준 PASS 4)
FLAG  6
FAIL  1  (E2)
대기  0
```

| 게이트 조건 | 기준 | 실측 | 판정 |
|---|---|---|---|
| PASS | ≥ 14/24 | **17** | ✅ |
| NOT VERIFIED(대기) | ≤ 4/24 | **0** | ✅ |
| FAIL | **0** | **1** | ❌ |

**→ G7 미통과. 1건 차이다.**

### 6.3 미통과 원인은 모델 회귀가 아니라 자료 공백이다

FLAG·FAIL 7건의 성격이 한 곳으로 모인다:

| 성격 | 해당 | 내용 |
|---|---|---|
| **코퍼스에 주제가 없음** | **E2 · D1 · E1** | 모델이 없다고 정직하게 밝힌 뒤 있는 자료로만 답했다. E2는 "우울증에 대한 임상적 지침이 자료에 없다"고 명시하고 Spurgeon의 '안식' 설교를 참고로 돌렸다 — 목회 상담 답으로는 얇을 수밖에 없다 |
| **잔존 오염** | C3 | 표식 2자 → 언어 2점 |
| 평범한 답 | A3 · B2 · H1 | 3/3/3. 결함이라기보다 수준 문제 |

채점이 코드 측정과 **독립적으로** 같은 결론에 도달했다 — 조건 ⑤의 병목은
자료이고, E(목회상담)·D(교단 비교) 유형은 19세기 영문 설교집으로 채울 수
없는 영역이다.

## 7. E2 — 자료 추가 후 재측정 (보류, 2026-10-22 사용자 결정)

**상태**: 보류. 질의 세트에서 분리하지 **않는다** — "코퍼스 범위 밖"으로
치우면 상담 유형의 공백이 기록에서 사라지기 때문이다.

**재개 조건**: 목회 상담 영역 자료가 코퍼스에 편입될 것. 구체적으로 E유형
3문항이 겨냥하는 주제다 — E1 이혼·간음 상담, **E2 우울증·정신건강 돌봄**,
E3 자녀 상실 위로. 한국어·영문 어느 쪽이든 무방하다.

**재개 절차**:
1. `scripts/j5_ingest_personal_library.py`의 `_SOURCES`에 자료와 표제지 실측
   서지를 추가하고 `--apply`(J5와 같은 경로).
2. `python3 scripts/p0_5_run_all.py --out <경로>` 로 E1·E2·E3 재수집
   (전체 24건을 다시 돌릴 필요는 없다).
3. `scripts/j7_scoring/build_round2.py`로 해당 건만 담은 채점표를 만들어
   3축 재채점.
4. E2가 FAIL을 벗으면 G7 게이트의 FAIL 0 조건이 충족된다 — 그때 J7을 닫는다.

**함께 재평가할 것**: D1(교단 비교)·E1도 같은 공백에서 온 FLAG다. 상담·비교
자료가 들어오면 함께 다시 잰다.

## 8. G7이 기다리던 것 (완료 기록)

채점 입력은 준비돼 있다:

1. **`docs/NAE_ANSWER_QUALITY_J6_SCORING_SHEET_001.md`** (670줄) — 같은 24건,
   같은 근거에 대한 현행 모델 vs qwen3.8 답변을 나란히 배치. 질의별로
   `판정: A / B / 무차 · 메모:` 한 줄만 채우면 된다. 이 결과가 **모델 전환
   여부**를 결정한다.
2. **`docs/NAE_ANSWER_QUALITY_J1_SIGNALS_001.md`** — 현행 모델 단독 신호표
   (하드 유보 0/24, 인용 메타 공백 0/120, 표식 4질의, 실답변 중위 510자).

함께 판단이 필요한 보류 2건(J1 §4·§6):

- **B1류 정합성 선언**("…개혁파 침례교 전통에 부합하며") — J3-b 게이트는
  0건 기준이라 현재 1/24로 미달이다. 내용은 사실이고 프로파일 누출도 없어
  위험한 실패 양식은 아니다. 지시문을 더 조이면 §2("전통과 다른 견해를
  감추지 마라")와 충돌할 수 있다.
- **유보 문구 변형** — C3가 고정 문구를 긍정문으로 바꿨다("이 질문은 현재
  등록된 자료로는 **충분히 답할 수 있습니다**").

## 9. 모델 전환 — 완료 (2026-10-20)

아래는 전환 전에 적어 둔 필수 작업 목록이고, **전부 끝났다**(커밋 `c8db23fa`):
`my-theology-bot-v4` 생성(교정 SYSTEM §4), `generate_stream()`·
`SermonDraftService` 포함 생성 경로 4곳의 thinking 처리, `DEFAULT_GEN_MODEL`
변경, `num_predict` 1024 → 2048(실측상 1024가 문장 중간에서 끊었다).

1. `generate_stream()`(UI 주 경로)과 `SermonDraftService`에 `think` 처리 —
   **이것 없이 전환하면 UI 답변이 빈 문자열이 된다.**
2. `config.yaml::ollama.default_gen_model` 변경.
3. 후보 Modelfile을 임시 태그(`nae-gen-qwen38:ab`)에서 정식 산출물로 승격
   (`Modelfile.theology-gen`과 같은 방식으로 저장소에 커밋).
4. `_gen_options`의 `num_predict` 재검토(후보 중위 836자·최대 2,441자).
