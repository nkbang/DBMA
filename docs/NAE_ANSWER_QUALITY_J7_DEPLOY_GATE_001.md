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
| **G7 P0-5 사용자 채점** | FAIL 0 · NOT VERIFIED ≤ 4/24 · PASS ≥ 14/24 | ⏳ **대기 — 사용자 전용** |

## 6. G7이 기다리는 것

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

## 7. 전환을 선택할 경우 남는 작업 (J6 보고서 §5)

1. `generate_stream()`(UI 주 경로)과 `SermonDraftService`에 `think` 처리 —
   **이것 없이 전환하면 UI 답변이 빈 문자열이 된다.**
2. `config.yaml::ollama.default_gen_model` 변경.
3. 후보 Modelfile을 임시 태그(`nae-gen-qwen38:ab`)에서 정식 산출물로 승격
   (`Modelfile.theology-gen`과 같은 방식으로 저장소에 커밋).
4. `_gen_options`의 `num_predict` 재검토(후보 중위 836자·최대 2,441자).
