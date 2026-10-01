# Phase 0 착지 범위 — 8절 예상 충돌 1~6항 최종 확인 (READ-ONLY)

- 작성: CUE(단일 주 작업 세션, HQ 지시 ③) · 2026-09-30
- 대상: [Phase 0 착지 범위 보고서](NAE_GS_PHASE0_LANDING_SCOPE_READONLY_HQ_REPORT.md)(`26acb1e2`) 8절 "예상 충돌·의존성" 1~6항
  - 7항(MAIN 미커밋 17개)은 "건드리지 않는다"로 정리돼 있어 제외했다.
- 기준 ref(`git ls-remote`로 원격과 같음을 확인)
  - `origin/dev/dbma-engine` `195189b8`
  - FU-007 C `b39572aa`
  - `origin/main` `88ca969b`
  - p4 브랜치 `55be70b1`
  - 결과 브랜치 원격 `26acb1e2`
- 방법
  - `git show`, `git grep`, `git rev-parse`, `git cat-file`
  - 병합 시뮬레이션은 저장소에 아무것도 쓰지 않는 구식 `git merge-tree <base> <ours> <theirs>`만 사용했다(`--write-tree` 미사용).
  - `git fetch`는 하지 않았다. 코드와 테스트는 실행하지 않았다.
- 표기: [CONFIRMED] / [INFERRED] / [UNKNOWN]
- **MUTATION: NONE.** 코드·ADR·prompt·index 변경 없음. 이 보고서 커밋만 한다.

## 목록 해석에 관한 기록

- 같은 시각에 다른 CUE 세션이 같은 결과 브랜치에 "Phase 0 사실 충돌 재검증(C1~C6)"을 로컬 커밋했다(`89b9c1bc`, 23:21, 이 보고서 작성 시점 미푸시).
- 그 세션의 C1~C6은 다음 여섯 가지다: C 검색 코어의 dev 미착지, C 전용 테스트, Tantivy 스키마, 인덱스 생성 경위, 호출자 범위, 문구.
- 이 보고서의 1~6항(8절)과는 **겹치지 않는 목록**이다. HQ가 뜻한 목록이 C1~C6이라면 이 보고서는 보완 자료다.

## 결과 요약

[CONFIRMED] 6개 항목 모두 **텍스트 충돌은 없다.** 남는 것은 HQ 승인 항목(H2~H4)에 붙는 조건 정보이며, 특히 4항의 스위치 조건이 중요하다.

| # | 항목 | 결과 | 관련 승인 항목 |
|---|---|---|---|
| 1 | ADR 번호(재부여 `3ea7ece1` 반영) | 충돌 0 | H3 |
| 2 | GS 경계 ADR-036 파일 | 단순 추가, 충돌 0 | H3 |
| 3 | main 신규 9커밋 | 겹치는 파일 1개(`chat.py`), 충돌 0. 회귀는 미확인 | H1 |
| 4 | 공개 자료 답변 경로 | 버튼 추가. **`modules.nae_pd.enabled`가 켜졌을 때만 표시** | H2 |
| 5 | 인용 검증기 경고 | dev에는 없고, C는 채팅 화면 경로와 공개 자료 패널에서 표시 | H4 |
| 6 | 검색 캐시 | dev에는 `qt=` 키 항목이 없음. 착지 후 키 형식이 바뀜, 영향은 작음(추론) | — |

## 1. ADR 번호 — 재부여 커밋 `3ea7ece1`을 C에 얹을 때

[CONFIRMED] `3ea7ece1`이 바꾼 파일의 출발 판(`3ea7ece1^`)과 C(`b39572aa`)의 판을 비교했다.

| 파일 | `3ea7ece1^` blob | C blob | 비교 |
|---|---|---|---|
| `NAE/public_answer.py` | `00472931` | `00472931` | 같음 |
| `ui/components/nae_public_section.py` | `2a8e4ee5` | `2a8e4ee5` | 같음 |
| `tests/test_nae_public_answer.py` | `2ec8336d` | `2ec8336d` | 같음 |
| `docs/NAE_EUAT_001_FOLLOWUP_TASK_ORDERS.md` | `a62e3f0c` | `a62e3f0c` | 같음 |
| `docs/NAE_EUAT_001_FU001_B_BUILD_REPORT.md` | `befa3b34` | `befa3b34` | 같음 |
| `docs/NAE_EUAT_001_FU007_BASELINE_DIVERGENCE_RESULT.md` | `ff8d4f20` | `ff8d4f20` | 같음 |
| CUE HQ 보고서 3건 | 있음 | **없음**(결과 브랜치에만 있는 문서) | — |
| ADR 파일(036→037 이름 변경) | — | C에는 036 이름으로 있음 | 이름 변경 |

- [CONFIRMED] `git merge-tree 3ea7ece1^ b39572aa 3ea7ece1`(C에 얹는 시뮬레이션) → **충돌 표시 0**.
- [INFERRED] CUE 보고서 3건까지 착지할지는 결과 브랜치의 문서를 어디까지 가져갈지에 달린 범위 결정이다(H3).

## 2. GS 경계 ADR-036 파일

| 확인 | 결과 |
|---|---|
| 위치 | `origin/claude/p4-final-validation-guide-b3af47`에만 있음(현재 `55be70b1`) [CONFIRMED] |
| 수락 이후 변경 | `e69eda64`(Accepted) 이후 p4 브랜치에 33커밋이 쌓였지만 **이 파일을 바꾼 커밋은 0개**. blob `366e7bec`가 같음 [CONFIRMED] |
| 다른 ref | C·main·dev·결과 브랜치 모두 같은 경로의 파일이 **없음** [CONFIRMED] |
| 반입 시 | 단순 파일 추가이며 경로 충돌이 없다 [CONFIRMED] |

## 3. main 신규 9커밋 (`d1c06d25..88ca969b`)

| 확인 | 결과 |
|---|---|
| 포함 PR | #89 침례교 주석 컬렉션 연결, #103 FU-004 문서, #95·#96 Production Registry supersession 링크 정정 [CONFIRMED] |
| 변경 파일 | 12개: `core/identity_registry.py`, `ui/pages/chat.py`, `scripts/repair_supersession_links.py`, `scripts/smith_e2e_verify.py`, 테스트 4, 문서 4 [CONFIRMED] |
| C와 겹치는 파일 | **`ui/pages/chat.py` 1개** [CONFIRMED] |
| 병합 시뮬레이션 | `git merge-tree d1c06d25 b39572aa origin/main` → 충돌 표시 0, 양쪽이 바꾼 파일 1개(자동 병합) [CONFIRMED] |
| Production Registry | 저장소에 들어온 것은 **정정 도구 코드와 실행 기록 문서**뿐이다. 레지스트리 데이터 파일은 git 변경 목록에 없다 [CONFIRMED]. 실제 레지스트리 데이터가 이미 정정됐는지는 [UNKNOWN] |
| `core/identity_registry.py` | main 9커밋이 바꾼 파일이다. **MAIN 체크아웃에도 이 파일의 미커밋(unstaged) 변경이 있다** [CONFIRMED]. 둘의 관계는 [UNKNOWN] |
| 회귀 | **미확인**(테스트를 실행하지 않음) |

## 4. 공개 자료 답변 경로 (ADR-037, 방안 B)

| 확인 | dev `195189b8` | C `b39572aa` |
|---|---|---|
| `ui/components/nae_public_section.py` | blob `023eb4b8`, 버튼은 "검색" 하나(L64) | blob `2a8e4ee5`, "검색"(L76) + **"이 근거로 답변 생성"**(`_render_public_answer`, L120~), `generate_stream` 호출(L147) |
| `NAE/public_answer.py` | 없음 | 있음 |
| 채팅에서 렌더 | `chat.py` L123 `render_nae_public_section(key_prefix="chat")` | `chat.py` L125 같은 호출 |
| 게이트 | 함수 첫머리에서 `module_registry.is_enabled("nae_pd")`가 거짓이면 아무것도 그리지 않음 | 같음(L38~L49) |
| `config.yaml` `modules.nae_pd.enabled` | `false` | `false` |

- [CONFIRMED] 버튼은 **`nae_pd`가 켜졌을 때만** 사용자에게 보인다. 저장소 기본값은 dev와 C 모두 꺼져 있다.
- [CONFIRMED] 현재 앱이 도는 MAIN 체크아웃의 `config.yaml`은 미커밋(staged) 상태로 `enabled: true`다(읽기만 함).
- Phase 0 보고서 8절 4항의 "사용자 화면에 버튼이 생긴다"는 **이 스위치 조건을 붙여야 정확하다.**

## 5. 인용 검증기 경고

| 확인 | dev | C |
|---|---|---|
| 생성 단계 검사(`core/generation.py` `_run_citation_check`) | 없음 | 4곳 |
| 채팅 표시(`ui/pages/chat.py`) | 없음 | `issue_messages` L46(import)·L581(화면 경로), 경고 출력 `_render_citation_warnings` L670 |
| 공개 자료 패널 | 없음 | `issue_messages` 2곳 |
| research 화면 | 없음 | 없음 |
| 스위치 | — | 없음(이슈가 있으면 표시) |

- [CONFIRMED] C를 착지하면 dev 채팅 화면에 경고("⚠️ 출처 확인 필요 — …")가 새로 나타날 수 있다.
- [INFERRED] 빈도는 낮을 수 있다: P0-5 APPINDEX 24건에서 이 검증기의 이슈는 0건이었다.
- 경고 문구를 ④-5 문구("지정하신 자료를 재확인하세요.")로 바꾸는 일은 Phase 0 이후 구현 범위다(Phase 0 보고서 7절).

## 6. 검색 캐시

| 확인 | dev | C | main(최신) |
|---|---|---|---|
| `QUERY_TRANSLATION_VERSION` | **없음** | `"4"` | `"3"` |
| `core/search_cache.make_cache_key`의 `qt=` 항목 | **없음** | 있음(L63~L67) | 있음 |

- [CONFIRMED] Phase 0 보고서의 "3→4"는 **main 기준**이다. 착지 대상인 dev에는 버전 값도, 캐시 키의 `qt=` 항목도 없다.
- [CONFIRMED] C를 착지하면 캐시 키 형식이 바뀌어 기존 캐시 항목은 쓰이지 않는다.
- [CONFIRMED] `HybridQueryProcessor`의 캐시 TTL 기본값은 600초다(`hybrid_candidate_pipeline.py` L475). 캐시는 만료 시각을 검사한다(`search_cache.py` L83~L95).
- [INFERRED] 기존 항목은 길어야 10분 안에 만료되므로 영향은 작다.
- [CONFIRMED] LLM 번역 모드·모델이 캐시 키에 없다는 문제(BACKLOG #3)는 C에서도 그대로다.

## HQ 확인 필요

1. **다른 세션의 로컬 커밋 `89b9c1bc`**
   - HQ 지시 ③(이 세션이 단일 주 작업 세션) 이후에 다른 세션이 커밋했다.
   - 처리(푸시 / 폐기)를 HQ가 정해야 한다. 이 세션은 되돌리지 않았다.
2. **"남은 6개 충돌"의 목록**: 8절 1~6항(이 보고서)과 C1~C6(다른 세션) 중 어느 쪽을 뜻했는지.
3. 이 결과를 H1~H4 승인에 반영할지
   - 특히 4항: 버튼은 `nae_pd` 스위치에 묶여 있다.
   - 3항: Production Registry 정정 도구가 함께 착지하고, `identity_registry.py`는 MAIN 미커밋 변경과 겹친다.
