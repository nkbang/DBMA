# S1-4 — llama3.2:3b 설교 생성 품질 실측

- 작성자: CUE · 일자: 2026-09-15
- 근거: `docs/DBMA_RELEASE_GAP_CLOSURE_PIPELINE_v1.md` S1-4(B-5) 나머지 절반
- 대상: `scripts/setup_beta_tester.command`가 8~16GB Mac에 배정하는 `llama3.2:3b`
- 실행 환경: `~/DBMA`(실제 코퍼스, 스펄전 4종 6,380 TSU), judge는
  `dbma-planner-r1-q6:70b`

## 결론 — 배포 차단 유지, 단 원인은 예상과 다르다

**`llama3.2:3b`를 8~16GB 사양 목회자에게 기본값으로 배정하는 것은 아직
안전하지 않다.** 그러나 원인은 "3b가 작아서"만이 아니었다 — 실측 중 두
가지 **실제 코드 결함**을 발견해 그 자리에서 고쳤고(§2), 고친 뒤에도
남는 문제(§3)는 모델 크기와 무관하게 8b(현재 기본 모델)에서도 재현됐다.

## 1. 1차 실측 — 순수 반복 루프 (수정 전)

`SermonDraftService.expand_point()`를 `llama3.2:3b`로 두 개 독립 주제에
호출:

| 주제 | groundedness | 증상 |
|---|---:|---|
| 로마서 5:1-5, 고난 중의 소망 | **0.0/5** | "우리에게 사랑을 주는 하나님으로서"를 20회+ 그대로 반복 |
| 요한복음 3:16, 하나님의 사랑 | **2.0/5** | "하나님의 사랑은 성령의 역할을 통해..." 반복, "passage" 영어 혼입 |

## 2. 원인 진단 — `repeat_penalty` 자체가 빠져 있었다

`core/generation.py::_gen_options()`는 GenerationService(Q&A·본문해설)용
Ollama 옵션(`repeat_penalty=1.3`, `num_predict=1024`)을 강제하지만, 주석에
"SermonDraftService 는 긴 출력이 정상이라 이 헬퍼를 쓰지 않는다"고 적혀
있었다 — `repeat_penalty`와 `num_predict`가 하나로 묶여 함께 생략됐다.

가설 검증(동일 프롬프트·모델, `repeat_penalty`만 추가):

| 조건 | groundedness | 비고 |
|---|---:|---|
| A. 기존(옵션 없음) | 0.0/5 | 퇴행 반복 |
| B. `repeat_penalty=1.3` 추가 | **3.0/5** | Spurgeon 원자료를 실제로 인용하기 시작 |

**수정한 것:**
- `core/generation.py::_sermon_gen_options()` 신설 — `repeat_penalty`는
  `_gen_options()`와 공유하되, `num_predict`는 별도 값(`DEFAULT_SERMON_NUM_PREDICT`,
  기본 2048)을 쓴다. 기존 1024는 B 테스트에서 출력을 문장 중간("...S")에서
  잘랐다 — 두 옵션을 하나로 묶어 취급한 것이 원래 설계 오류였다.
- `config.yaml::rag.sermon_num_predict` 추가(기본 2048).
- `SermonDraftService.generate_outline()`/`expand_point()`의 `ollama.generate`
  호출 2곳을 `_sermon_gen_options()`로 교체.
- 부수 발견: B 테스트 출력에 **데바나가리 문자**("सफ란다")가 섞여
  나왔다 — 기존 `_SCRIPT_CONTAMINATION_RE`(CJK/태국/그리스/키릴/히브리/
  아랍)에 없던 구멍. 범위에 추가했다.
- 회귀 테스트: `tests/test_sermon_draft_repeat_penalty.py`(4건, 옵션이
  실제로 전달되는지 mock으로 검증), `tests/test_script_contamination_broadened_ranges.py`
  에 데바나가리 케이스 추가(1건).

## 3. 수정 후 실측 — 실제 파이프라인(재시도+새니타이즈 포함)에서는 부족

단발 `ollama.generate` 호출이 아니라 **실제 `SermonDraftService` 전체
경로**(오염 탐지 → 재시도 2회 → 새니타이즈)로 다시 실측했다.

| 모델 | groundedness | 증상 |
|---|---:|---|
| llama3.2:3b | 0.0/5 | 개요 생성 중 태국어·중국어·"靈"(령) 등 다중 스크립트 오염 3회 연속 감지 → 재시도 소진 → 새니타이즈 후 `outline.points == ['', '', '']`(빈 문자열). 대지 확장은 영어 단어가 문장 곳곳에 섞임("God의사랑은 우리 lives를 change하는 power") |
| **llama3.1:8b (현재 기본 모델)** | **0.0/5** | **동일 증상** — 개요 오염 감지 2회, `outline.points == ['', '', '']`. 확장 텍스트는 KJV 영어 원문을 그대로 인용하고 한국어와 뒤섞임 |

**중요한 재확인:** 이 결과는 3b만의 문제가 아니다. judge의 근거를 보면
"검색된 자료는 성령님과 사역에 관한 내용으로 완전히 무관합니다"라고
명시한다 — **"요한복음 3:16, 하나님의 사랑" 질의에 대해 검색이 반환한
후보 자체가 주제와 약하게만 관련**돼 있었다(스펄전 코퍼스가 4종뿐이라
이 주제를 직접 다루는 자료가 부족했을 가능성). 근거가 약할 때 두 모델
모두 자기 내장 지식(KJV 원문 암송)으로 채워 넣었다 — **모델 크기와
무관한, 근거 강제(grounding enforcement) 자체의 공백**이다.

## 4. 종합 판정

| 질문 | 답 |
|---|---|
| `repeat_penalty` 누락이 실제 버그였는가 | **예** — A/B 테스트로 확정(0/5 → 3/5), 수정 완료·테스트로 고정 |
| 수정이 3b를 배포 가능하게 만드는가 | **아니오** — 실제 파이프라인에서는 다중 스크립트 오염·개요 공백화가 남는다 |
| 8b(현재 기본)는 안전한가 | **이 실측 범위에서는 8b도 같은 증상을 보였다** — 기존 "golden set groundedness 5.00/5" 주장(`setup_beta_tester.command` 주석)과 직접 배치되므로, 그 주장의 측정 조건(질의 세트·재현성)을 별도로 재검증해야 한다 |
| 근본 원인이 모델 크기인가 검색 결과 관련성인가 | **후자일 가능성이 크다** — 이번 실측 2개 질의 모두 코퍼스가 얇게만 다루는 주제였다. 표본이 작아(n=2) 확정할 수 없다 |

## 5. 권고

1. **8~16GB 사양의 `llama3.2:3b` 기본 배정은 보류한다.** 이번 수정
   (repeat_penalty)은 유지하되, 모델 티어 결정 자체는 아래 3번이
   끝난 뒤로 미룬다.
2. **새로 발견한 결함**(오염 심할 때 `outline.points`가 조용히
   빈 문자열이 되고 UI가 경고 없이 빈 카드를 보여줌)은 이 수정
   범위 밖이라 별도 작업으로 분리했다(백그라운드 제안 등록됨).
3. **설교 경로에 `_GROUNDING_DIRECTIVE` 수준 근거 강제 적용**
   (`DBMA_SERMON_ARTIFACT_PIPELINE_DESIGN_v1.md` §4.4가 이미 별건 백로그로
   남겨둔 항목) — 이번 실측이 그 필요성의 구체적 증거가 됐다. 검색
   결과가 약할 때 "자료가 부족합니다"로 멈추는 것이, 모델이 내장
   지식으로 채우는 것보다 나아야 한다.
4. **재현 가능한 groundedness 벤치마크가 필요하다** — 이번 2개 질의
   n=2 실측은 결론을 내리기엔 표본이 작다. 다양한 주제(코퍼스가
   두텁게 다루는 것/얇게 다루는 것 섞어서) 10~20개 질의 세트로
   3b/8b/70b를 동일 조건에서 비교하는 것을 다음 단계로 권고한다.

## 6. 실측 원시 데이터

- 1차(반복 루프): `/tmp/s1_4_3b_quality_result.json`,
  `/tmp/s1_4_3b_quality_result_2.json`(세션 종료 시 삭제될 수 있음,
  본 문서가 요약본)
- A/B(repeat_penalty 가설검증): 스크립트만 보존,
  `docs/agents/`로 옮기지 않음(일회성 진단 스크립트)
