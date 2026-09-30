# FU-007 / GS 릴리스 라인 결정 자료 — HQ 보고서

> **번호 재부여 안내(2026-09-30, HQ ② 결정 A)**: 이 문서에서 공개 자료 근거 답변 ADR을 가리키는 "ADR-036"(또는 ADR-036-B)은 **ADR-037**(`docs/architecture/ADR-037-NAE-Public-Evidence-in-Answer-Generation.md`)로 재부여됐다. GS 경계 ADR은 ADR-036을 유지한다. 본문은 재부여 이전 시점의 기록으로 그대로 둔다.

- 작성: CUE · 2026-09-30
- 단계: GS 설계 검토(YELLOW) 이후 HQ 결정 순서 ① 착지 라인
- 선행 문서:
  - [FU-007 기준선 분기 조사](NAE_EUAT_001_FU007_BASELINE_DIVERGENCE_RESULT.md)
  - [FU-007 통합 시도 결과](NAE_EUAT_001_FU007_INTEGRATION_TRIAL_RESULT.md)
  - [GS 설계 검토](NAE_GS_PRODUCTION_INTEGRATION_DESIGN_REVIEW_HQ_REPORT.md)
- 방법: 읽기 전용
  - `git fetch`를 하지 않았다. 원격 ref가 로컬 값과 같은지는 `git ls-remote`로 확인했다.
  - 병합 충돌은 저장소에 아무것도 쓰지 않는 구식 `git merge-tree`로 확인했다.
- 표기: [CONFIRMED] git으로 확인 / [INFERRED] 추론 / [UNKNOWN] 미확인
- **MUTATION: NONE.** 이 문서 커밋만 한다.

> 이 문서는 추천하지 않는다. main과 dev/dbma-engine 중 어느 쪽을 릴리스 라인으로 할지는 HQ가 결정한다.

## 1. 결정 질문

**릴리스 라인을 `origin/main`으로 할 것인가, `origin/dev/dbma-engine`으로 할 것인가.**

[CONFIRMED] 이 결정 하나가 **FU-007 병합 방향**과 **GS 착지 라인**을 함께 정한다. GS와 그 입력인 근거 계층은 한쪽 라인에만 있다(5.1·5.2절).

## 2. 기준 ref (원격 SHA, 2026-09-30 확인)

| ref | SHA | 비고 |
|---|---|---|
| origin/main | `ced87898` | [CONFIRMED] **FU-007 시작 시점(`d1c06d25`)보다 5커밋 전진**: PR #89 침례교 주석 컬렉션 연결(`732fb435`), PR #103 FU-004 문서 |
| origin/dev/dbma-engine | `195189b8` | FU-007 시작 이후 변동 없음 |
| origin/feat/peb-v0.1 | `828c250d` | 참고 |
| tmp/fu007-integration-trial | `78cb6b50` | FU-007 결과 브랜치(이 문서 커밋 전) |
| tmp/fu007-combined-translation | `b39572aa` | P0-5·GS 검토에 쓴 코드 |

## 3. 베타 태그 계보

| 태그 | 커밋 | 날짜 | main | dev |
|---|---|---|---|---|
| v1.3.0 | `07ec084d` | 07-17 | 포함 | 포함 |
| beta-v1.3.0-rc1 ~ rc3 | `2abf9bbb` `916bd345` `48842061` | 07-28 | 포함 | 포함 |
| beta-v1.3.0-rc4, rc5 | `6d570140` `42440559` | 08-17, 08-18 | 포함 | 포함 |
| **beta-v1.3.0-rc6** | `d16095e2` | 09-23 | **미포함** | 포함 |

- [CONFIRMED] `BETA_LATEST_TAG.txt`: main에는 `beta-v1.3.0-rc5`, dev에는 `beta-v1.3.0-rc6`.
- [CONFIRMED] rc6는 PR #73 병합(`c6708cf2`, 09-23)으로 dev에 들어왔다. 이 병합은 main에 없다.
- [CONFIRMED] rc6와 main의 공통 조상은 `f075e38f`(09-18)이다. **릴리스 계보는 09-18 이후 dev 쪽에만 이어진다.**
- [UNKNOWN] 실제 배포된 베타 빌드(DMG)가 rc6에서 빌드됐는지는 확인하지 않았다. rc6 이후 새 베타 태그는 없다.

## 4. main과 dev/dbma-engine 비교

### 4.1 커밋 위상
- [CONFIRMED] 어느 쪽도 다른 쪽의 조상이 아니다. **완전히 갈라져 있다.**
- [CONFIRMED] merge-base는 `39026424`(09-25, 사이드바 "내서재" 수정)이다.
  - 이 커밋은 두 라인이 **각각 병합한 기능 브랜치의 커밋**이다. dev의 1차 부모 이력에는 없다.
  - 따라서 "09-25에 갈라졌다"는 표현은 부정확하다. 릴리스 계보(rc6)는 09-18부터 dev에만 있다.

### 4.2 각 라인에만 있는 커밋

| 기준 | main에만 | dev에만 |
|---|---|---|
| 모든 커밋(병합 포함) | 91 | 84 |
| 병합 제외 | 73 | 63 |
| 내용이 같은 커밋(`git cherry` 패치 동등) | — | **0** |

- main 고유 73의 구성: `grounded-synthesis` 47(문서 41, 기능 5, 테스트 1), `evidence` 2, `retrieval` 6. 나머지는 NAE·EUAT 문서, ADR-036 방안 B, 하드코딩 경로 핫픽스, 검색 캐시 스레드 안전, CI 고정 등.
- dev 고유 63의 구성: PEB v0.1(파일 12개 + 하네스), NAE Phase 1 화면 통합(#75), ADR-035(#76), 온보딩 수정 5, 베타 런처, 릴리스 자산(S6-1), rc6 태그 갱신(#69), SermonArtifact, 한국어 조사 토큰화, 번역 전처리, 오염 문자 표식·라틴 고지, Fuller F3 검수 문서 등.

### 4.3 앞섬 / 뒤처짐

| main 기준 시점 | main에만 / dev에만 (병합 포함) |
|---|---|
| `35a842f9` (FU-007 기준선 조사) | 82 / 84 ← 예전 "84/82" |
| `d1c06d25` (FU-007 시작) | 86 / 84 |
| `ced87898` (현재) | **91 / 84** |

[CONFIRMED] dev가 멈춰 있는 동안 main만 전진해 격차가 벌어지는 중이다.

## 5. 기능 계보 (3층 분리)

"파일이 있음"은 "제품에서 쓰이고 준비됨"과 다르다.

### 5.1 Layer 1 — Retrieval / Evidence

| 기능 | main | dev | 도입 커밋 |
|---|---|---|---|
| EvidencePool / 근거 계층(evidence_pool / model / assembly / adapters) | 있음 | **없음** | main `6fad67d9`·`78882aea`·`a08a29f8` (09-27, GS P1~P3) |
| 권말 색인 강등(`index_page_detector`) | 있음 | 없음 | main `3f64027f` (09-26) |
| 한→영 용어 번역·구절 가중·UNK 폴백 | 있음 | 없음 | main `ae822afd` 외 (09-26) |
| LLM 번역 전처리 + 한국어 조사 토큰화 | 없음 | 있음 | dev `398bc5cd`·`64286013` (09-22~26) |
| 코퍼스 소속·역할별 병합(AD-01/02) | 있음 | 없음 | main PR #93 (09-29) |
| 침례교 주석 컬렉션 연결 | 있음 | 없음 | main PR #89 (09-29, FU-007 이후) |

- [CONFIRMED] 근거 계층은 main에서 **GS 작업의 일부로** 들어왔다. dev에 없는 이유도 같다.
- [CONFIRMED] 앱 경로에서 근거 계층을 쓰는 곳은 0이다(GS 설계 검토).

### 5.2 Layer 2 — Grounded Synthesis

| 기능 | main | dev |
|---|---|---|
| grounded_claims / citation / answer / synthesis_input | 있음(`dc939c40`·`a250995b`·`0c14dc3a`·`d0350b50`, 09-27) | **없음** |
| GS 경계 ADR-036 | 없음(`p4-final-validation-guide` 브랜치에만) | 없음 |

[CONFIRMED] GS는 main에 있지만 앱 경로에 **연결되지 않았다**(설계 검토 YELLOW, 구현 HOLD).

### 5.3 Layer 3 — Product / Operations

| 기능 | main | dev | 비고 |
|---|---|---|---|
| PEB 생성 경로(`core/generation.py`) | 있음 | 있음 | 서로 다르고 자동 병합된다. main에는 인용 검증 연결, dev에는 오염 표식·라틴 고지 |
| 인용 검증기(`core/citation_verifier.py`) | 있음(`e1b3a109`, 09-29 FU-003) | 없음 | |
| PEB v0.1 인수 하네스(`peb/`) | 없음 | 있음(09-23~25) | |
| 온보딩·NAE Phase 1 화면 | 옛 판 | 새 판(#75, 온보딩 수정 5건) | `ui/pages/onboarding.py`, `ui/app.py`, `dashboard.py`, `library.py`가 두 라인에서 서로 다름 |
| 배포 파이프라인 | rc5 기준 | rc6 기준, 릴리스 자산(S6-1), 베타 런처 수정 | `BETA_LATEST_TAG.txt`, `scripts/setup_beta_tester.command` 다름 |
| ADR-035 목회자 서재 자동화 | 없음 | 있음(#76) | `core/raw_folder_watcher.py` 등 |
| ADR-036 방안 B(공개 자료 근거 답변) | 있음(09-29) | 없음 | `nae_public_section.py`는 09-12판이 양쪽에 있음 |
| 하드코딩 절대경로 제거 핫픽스 | 있음(09-28) | 없음 | |
| 한국어 번역 | 사전 방식 | LLM 방식 | 결합안 C는 `tmp` 브랜치에만 있음 |

[UNKNOWN] 각 라인의 현재 전체 회귀 결과는 이번에 실행하지 않았다(참고: FU-007 시점 main 3,490 passed, 결합안 3,554 passed).

## 6. 병합 충돌

[CONFIRMED] 현재 main(`ced87898`)과 dev(`195189b8`)를 병합하면 충돌 파일은 **3개로 변동이 없다**. main 전진분(PR #89가 `chat.py` 수정)은 자동 병합된다.

양쪽이 모두 바꿨지만 자동 병합되는 파일: `core/generation.py`, `ui/pages/chat.py`, `tests/test_candidate_generator.py`

| 파일 | main 쪽 변경 | dev 쪽 변경 | 기능적 의미 |
|---|---|---|---|
| `core/query_translation.py` (양쪽이 새로 만듦) | 사전 기반 한→영 용어 추가, 구절 표기 확장 | LLM 전체 문장 번역, 코퍼스 언어 고지 | 한국어 질의 검색 복구의 서로 다른 구현 |
| `core/candidate_generator.py` | 번역어 추가, 구절 구문 가중 | 한국어 형태소 `_search` 필드 질의 | 검색 질의 조립 |
| `core/hybrid_candidate_pipeline.py` | 권말 색인 강등, 과다 수집 | Stage-1 전 LLM 번역과 0건 재번역, 책 필터 생략 | 후보 생성 흐름 |

해결안은 이 문서에서 제시하지 않는다. 실험 기록은 FU-007 통합 시도 결과 문서 1·8절에 있다.

## 7. FU-007 결과 브랜치와의 관계

| 브랜치 | vs main | vs dev | 내용 |
|---|---|---|---|
| `tmp/fu007-integration-trial` `78cb6b50` | merge-base `d1c06d25`, 9 앞섬 / 5 뒤처짐 | merge-base `39026424`, 95 앞섬 / 84 뒤처짐 | [CONFIRMED] **문서만 바뀜**(코드 변경 0), 병합 커밋 없음 |
| `tmp/fu007-combined-translation` `b39572aa` | merge-base `d1c06d25`, 86 앞섬 / 5 뒤처짐 | **dev 전체를 포함**, 88 앞섬 / 0 뒤처짐 | [CONFIRMED] 부모가 `d1c06d25`(main)와 `195189b8`(dev)인 병합 + 결합안 1커밋. **main 최신 5커밋 미포함** |

- [CONFIRMED] P0-5와 GS 설계 검토의 사실은 모두 `b39572aa`(두 라인의 병합본) 기준이다.
- [INFERRED] 어느 라인을 택하든 이 결과를 그대로 착지시킬 수는 없다. 선택한 라인 위에서 병합을 다시 하고 main 전진분을 반영해야 한다.

## 8. GS 착지에 대한 함의

- [CONFIRMED] GS 착지 라인 결정은 FU-007 릴리스 라인 결정과 **같은 문제**다.
  - GS(Layer 2)와 그 입력인 근거 계층(Layer 1 일부)은 main에만 있다.
  - 사용자 배포 계보(rc6)와 Layer 3의 최신 제품·운영 변경은 dev에만 있다.
- [CONFIRMED] 따라서 어느 쪽을 택해도, 다른 쪽의 한 층을 통째로 들여와야 한다.
  - main 채택: dev의 Layer 3(화면·온보딩·배포 rc6·PEB·ADR-035)을 들여와야 함
  - dev 채택: main의 Layer 1·2(근거 계층·GS·인용 검증기·검색 개선·핫픽스)를 들여와야 함
  - 병합 자체의 텍스트 충돌은 두 경우 모두 같은 3개다.
- GS의 존재 자체를 라인 선택의 근거로 제시하지 않는다. GS 구현은 설계 검토 결과 HOLD 상태다.

## 9. HQ 결정이 필요한 사실

1. **릴리스 라인**: 사용자 배포 계보(rc6, dev)와 GitHub 기본 브랜치·최근 PR 흐름(main, PR #89~#103)이 서로 다른 라인을 가리킨다.
2. **결정 전까지 격차가 계속 벌어진다**: main 고유 커밋이 82 → 86 → 91로 늘었다.
3. 충돌 3개(번역 구현)의 선택은 FU-007 결합안 권고(C)와 연결된 **별도 결정**이다.
4. main에 있는 운영 수정(하드코딩 경로 핫픽스, 검색 캐시 스레드 안전, CI 고정)은 배포 계보(dev)에 없다.
5. dev에 있는 사용자 화면·온보딩·배포 수정은 main에 없다.

## 10. 미확인

- 실제 배포된 베타 빌드의 커밋(rc6 태그와 DMG의 대응)
- 각 라인의 현재 전체 회귀 결과
- 텍스트 충돌이 아닌 의미상 충돌. 예: `generation.py`의 오염 고지와 인용 검증기의 이중 경고(BACKLOG #6)
- 병합 후 Tantivy 인덱스 재빌드의 운영 영향(스키마 변경은 dev 쪽 조사 토큰화 필드)
- `feat/peb-v0.1`(`828c250d`)이 릴리스 결정에서 갖는 지위

## 11. MUTATION: NONE

- 조사 중 저장소·코드·git 변경 없음(fetch도 하지 않음)
- 사용한 명령: `ls-remote`, `rev-list`, `merge-base`, `log`, `cat-file`, `show`, 구식 `merge-tree`(출력만)
- 이 보고서의 커밋만 수행한다.
