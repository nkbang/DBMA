---
title: Build Report — main → fix/merge-production-path-safety 병합 및 질의 번역 통합
created: 2026-10-08
status: 구현 완료 · 전체 회귀 통과 · 커밋됨 (번역 방식 (a)+B 승인: Rev. Bang, 2026-10-08)
scope: core/query_translation.py, core/query_translation_llm.py, core/candidate_generator.py, core/hybrid_candidate_pipeline.py, ui/components/nae_public_section.py, tests/
baseline: 브랜치 `e5908af9` / main `7d65f4ec` / merge-base `39026424`
venv: `~/envs/dbma311`
---

# Build Report — main 병합과 질의 번역 통합

`fix/merge-production-path-safety`가 `main`보다 99커밋 뒤처져 있어 병합했다.
충돌 5개가 났고, 그중 4개는 **양쪽이 2026-09-26에 같은 문제(한국어 질의 →
영문 코퍼스 검색)를 각자 다른 방식으로 푼 것**에서 나왔다. 병합 커밋은 `5616b65e`.

## 두 번역 방식

| | 브랜치 (`398bc5cd`) | main (`ae822afd`) |
|---|---|---|
| 방식 | LLM으로 질의 전체 번역 (`llama3.1:8b`) | 닫힌 용어 사전 + 성구 참조 규칙 (LLM 없음) |
| 결과물 | 번역문을 다시 파싱 | `ParsedQuery.translated_terms`/`translated_phrases` |
| 장점 | 사전 밖 질의도 번역 | 결정적·지연 0·캐시/회귀 테스트 가능 |
| 약점 | 지연·비결정성 | 사전이 못 덮으면 번역어가 없음 |

## 결정 — 방식 (a) + 보강 B

- **기본 경로**: main의 사전 번역. LLM을 부르지 않는다.
- **B (사전 LLM 번역)**: 한글 질의이고, 사전이 영어 번역어를 **하나도** 못 만들고,
  코퍼스 한국어 비중이 20% 미만일 때만 Stage-1 **전에** LLM으로 번역한다.
- **0건 폴백**: 그래도 Stage-1이 0건이면 LLM 번역으로 한 번 더 시도한다.

### 왜 (a)만으로는 부족했나 (B의 근거)

(a)를 그대로 적용하면 브랜치의 계약 테스트 2건이 실패했다
(`test_hangul_query_is_translated_before_stage1`,
`test_noise_match_does_not_suppress_translation`). 이 테스트는 "한국어 토큰이 영문
OCR 잡음에 걸려 0건이 되지 않으면 0건 폴백은 영영 발동하지 않는다"는 브랜치의
실측(P0-5 유보 17건 중 16건)을 지킨다. main 사전이 실제로 비는 질의를 직접 측정했다.

| 질의 | 사전 번역어 | 판정 |
|---|---|---|
| 우울증 목회 돌봄 | 없음 (`[]`) | B가 LLM 번역을 발동 |
| 광야에서 길을 잃은 성도를 위한 위로 | `saints`만 | 부분 커버 — 미해결 |
| 정죄 없음 | `sin, sins` | **오역**(정죄→죄) — 미해결, 사전 품질 문제 |
| 칭의와 성화의 관계 | 정확 | LLM 호출 없음 |

## 변경

| 파일 | 내용 |
|---|---|
| `core/query_translation.py` | main 것을 그대로 채택 (사전·성구 번역·`verse_phrase_match_kind`) |
| `core/query_translation_llm.py` | **신규** — 브랜치의 LLM 번역(`translate_to_english`, `contains_hangul`, `corpus_language_notice`)을 분리 이동. 한 모듈에 두 방식이 섞이지 않게 함 |
| `core/candidate_generator.py` | 번역어를 질의에 덧붙인 **뒤** 색인과 같은 방식으로 토큰화(대칭 유지), main의 구절 구문 가중 유지 |
| `core/hybrid_candidate_pipeline.py` | main의 색인 페이지 강등(`fetch_k` 과다 조회 + `_demote_index_pages`)과 브랜치의 `_generate_candidates` 분리를 합침. 사전-LLM 번역(B)·0건 폴백 유지. 빈 Bible Index 폴백 텔레메트리는 main 계약(`route_fallback_from`)을 따름 |
| `ui/components/nae_public_section.py` | main의 ADR-036 공개 자료 답변·출처 기반 고지를 살리고 `NAE.*`는 `try/except ImportError`로 가져옴 |
| `ui/pages/chat.py`, `ui/pages/sermon_draft.py` | `corpus_language_notice` import를 새 모듈로 |
| `tests/test_ad01_ad02_corpus_membership.py` | 양쪽의 합집합 (24건) |
| `tests/test_query_translation_fallback.py` | import 경로 갱신, 두 계약 테스트의 질의를 "사전이 비는 질의"로 교체, **계약 3 신규** |

### 설계 판단

1. **NAE import.** `.gitattributes`에 `NAE/ export-ignore`가 있고 `chat.py`·
   `research.py`가 이 모듈을 맨 위에서 import한다. main의 맨 위 `from NAE…`를 그대로
   받으면 배포본에서 `chat.py` 임포트가 실패한다. 처음에는 함수 안 지연 import로
   옮겼으나 `test_nae_public_answer`가 모듈 속성을 monkeypatch해 1건이 깨졌고,
   모듈 맨 위 `try/except ImportError` + `None` 센티널로 바꿨다. NAE가 없는
   환경을 시뮬레이션해 임포트 성공을 확인했다(이 경로는 `nae_pd` 활성 시에만 도달).
2. **토큰화 순서.** 번역어 덧붙이기 → `_tokenize_for_index`. 영어 번역어도 색인
   쪽과 같은 규칙으로 분절된다.
3. **0건 폴백 유지.** 사전-LLM 번역 뒤에도 0건이면 한 번 더 시도한다. 이미 후보를
   찾은 질의는 건드리지 않는다.

## 검증

| 구분 | 결과 |
|---|---|
| 충돌 5개 해결 후 관련 테스트 (번역·폴백·book filter·NAE 공개 답변·AD01/02) | 95 passed |
| 전체 회귀 (`tests`) | **3,688 passed, 21 skipped, 0 failed** (152초) |
| 비교: `main` 전체 회귀 (`7d65f4ec`) | 3,513 passed, 21 skipped, 0 failed |
| 신규 계약 테스트 | 사전이 덮는 질의("칭의와 성화의 관계")는 Stage-1 전에 LLM을 부르지 않는다 |
| NAE 부재 시뮬레이션 | `ui.components.nae_public_section` 임포트 성공, `get_disclosure`/`select_evidence`는 `None` |

병합은 임시 worktree에서 수행·검증한 뒤 실제 브랜치에 빨리감기로 반영했다
(반영 직전 메인 체크아웃의 추적 파일 변경 0 확인).

## 남은 위험

- **사전 품질.** 사전이 일부만 덮는 질의(`saints`만)나 오역하는 질의(`정죄`→`sin`)는
  B가 발동하지 않으므로 개선되지 않는다. B의 조건은 "번역어가 하나도 없음"이다.
- **실제 코퍼스 검증 없음.** 모든 검증은 단위·통합 테스트다. 119,595건 코퍼스에서 위
  질의들의 실제 검색 결과를 병합 전후로 비교하지는 않았다.
- **Retrieval 변경.** Retrieval 계열 파일 3개(`candidate_generator`,
  `hybrid_candidate_pipeline`, `query_translation*`)를 건드렸다. 사용자 승인
  (2026-10-08, 방식 (a) → 보강 B)을 받아 수행했고 ADR 충돌은 없다.
- **기존 문제(범위 밖).** `tests/test_query_enhancements_full_regression.py`의 테스트
  3건이 `assert` 대신 `dict`를 `return`한다(PytestReturnNotNoneWarning 20건의 원인).
  사실상 아무것도 검증하지 못하며 이번 변경과 무관하다.

## 다음 조치

- [x] 충돌 5개 해결, 전체 회귀 통과
- [x] 실제 브랜치 반영(빨리감기), Build Report
- [ ] 실제 코퍼스로 한국어 질의 4종 병합 전후 비교
- [ ] 사전 보강 여부 판단 (부분 커버·오역 질의)
- [ ] `return dict` 테스트 3건을 `assert`로 정리

진행률: 60%
