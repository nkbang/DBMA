# C1 Task Order 027 — ClaimGuard recall 개선 (계측 → 원인 진단 → 사전 확장 → 재검증)

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P0 (Sprint E 실측 결과 후속)
**선행 작업**: Task Order 026(Sprint E) 완료·검증됨 — 골드셋 30개, 실측 `true_positive=1, false_negative=15`.
**근거 문서**: [docs/DBMA-SEQ-ClaimGuard-Goldset-v1-Baseline-2026-07-29.md](../../DBMA-SEQ-ClaimGuard-Goldset-v1-Baseline-2026-07-29.md),
`output/claim_guard_eval/goldset_v1_result_20260729T235820Z.json`
**작성일**: 2026-07-29
**모드 제약**: `core/retrieval.py`, `core/parallel_retriever.py`, `core/generation.py`, `ui/pages/chat.py` 절대
미접촉. 이번 작업 대상은 `core/claim_guard.py`(사전만) + `scripts/evaluate_claim_guard_goldset.py`(계측 추가) +
골드셋 재실행뿐이다.

---

## 1. 배경 — 왜 "사전을 바로 넓히지 않는가"

Sprint E 결과, 위험 표현이 기대되는 16개 질의 중 실제로 잡힌 건 1개뿐이다. 그런데 **현재 평가 결과 JSON에는
LLM이 실제로 생성한 답변 텍스트가 저장되어 있지 않다** — `ClaimGuard`는 질의가 아니라 **생성된 답변**을
검사하는 구조이므로, 답변 텍스트를 보지 않고서는 미탐 원인이 "사전에 없는 단어라서"인지 "모델이 애초에
그 단어를 안 썼기 때문"인지 구분할 수 없다. 근거 신호를 검증하지 않고 사전만 넓히면, 이미 의도적으로
좁게 설계된 항목(예: 사전이 bare `"모든"`이 아니라 `"모든 학자"`로 좁혀진 건, `neutral` 카테고리 질의
답변에도 "모든"이라는 단어가 흔히 등장해 오탐이 폭증할 위험 때문일 가능성이 높음 — Sprint D 설계 의도
추정, 확인 필요)을 무너뜨릴 수 있다. 그래서 순서를 다음과 같이 고정한다: **계측 → 실제 답변 확인 →
근거 있는 사전 확장 → neutral 카테고리 오탐 여부까지 재검증.**

---

## 2. 구현 범위

### 2.1 `scripts/evaluate_claim_guard_goldset.py`에 계측 추가

각 결과 항목(`results` 리스트의 dict)에 `"generated_answer": <전체 답변 텍스트>` 필드를 추가한다.
(현재 스크립트가 `GenerationResult`/`GenerationStream.to_result()`를 이미 호출하고 있을 것이므로, 그
`.answer` 값을 결과 dict에 그대로 저장하면 됨 — 새 API 호출 추가 없이 이미 갖고 있는 값을 저장만 하는
것.) 기존 필드는 변경하지 않고 추가만 한다.

### 2.2 30개 재실행 + 미탐 15건 원문 분석

`scripts/evaluate_claim_guard_goldset.py`로 골드셋 30개를 다시 실행한 뒤, 이전 미탐 15건
(cg-001,002,006,007,008,019,020,021,022,023,024,025,026,027,030)의 `generated_answer`를 직접 읽고
아래 두 그룹으로 분류해 보고서에 표로 정리한다:

- **그룹 A**: 답변에 위험 표현이 실제로 등장하는데(예: "유일하게", "최초로", "모든") 사전이 그 정확한
  형태를 못 잡은 경우 → 사전 확장 후보
- **그룹 B**: 답변 자체가 위험 표현을 전혀 안 쓰고 다른 식으로 서술한 경우(예: "가장 나이 많은 인물은
  므두셀라입니다"처럼 질문의 "가장"을 반복하지 않고 답한 경우) → 사전을 넓혀도 못 잡음, 별도 과제로 남김
  (예: 답변이 사실상 절대적 서술인지 판단하려면 키워드 매칭이 아니라 다른 접근이 필요 — 이번 Task Order
  범위 밖, 발견 사실만 기록)

### 2.3 그룹 A 근거로만 `core/claim_guard.py`의 `ABSOLUTE_SUPERLATIVE_TERMS` 확장

- 그룹 A에서 실제로 관찰된 표현만 추가한다 (안 나온 표현을 추측해서 미리 넣지 않음 — YAGNI, "근거 없는
  변경 금지").
- 후보로 검토할 것(그룹 A 분석 결과에 따라 실제 등장한 것만 채택): `"최초로"`, `"가장 먼저"`, `"유일하게"`
  등 활용형. **bare `"가장"`, bare `"모든"`처럼 지나치게 흔한 단어는 그룹 A에 나타나더라도 바로 추가하지
  말고, §2.4의 neutral 오탐 테스트를 먼저 통과하는지 확인한 뒤에만 추가한다.**
- 기존 16개 항목은 그대로 유지, 추가만 한다(제거 금지).

### 2.4 neutral 카테고리 오탐 검증 (필수 게이트)

사전을 확장한 뒤, **neutral 카테고리 8개(cg-009~018 중 neutral 표시분)의 `generated_answer`에 새로
추가한 표현이 우연히 등장해 `false_positive`가 발생하는지** 반드시 확인한다. 만약 특정 후보 표현(특히
bare `"모든"`, `"가장"` 같은 것)이 neutral 답변에도 자주 등장해 오탐을 만든다면, **그 표현은 사전에
넣지 않는다** — recall을 올리려다 precision을 깨는 것은 이번 작업의 목표가 아니다.

---

## 3. 검증 계획

1. `tests/test_claim_guard.py`의 `TestDetectRiskFullList::test_all_terms_match_at_least_once`가 확장된
   목록에 대해서도 통과하는지 (새 표현 추가 시 이 테스트가 자동으로 커버함).
2. 골드셋 30개 재실행 후 **before/after 비교표** 작성: `true_positive`/`false_negative`/`false_positive`가
   각각 어떻게 바뀌었는지. **false_positive가 1건이라도 늘었다면 그 원인이 된 확장 표현을 되돌릴 것.**
3. 전체 회귀 스위트 재실행 — 1020/1020(또는 신규 테스트 추가분 포함 그 이상) 유지 확인.

---

## 4. 보고 형식

1. `scripts/evaluate_claim_guard_goldset.py`(계측 추가분), `core/claim_guard.py`(사전 확장분) diff
2. 그룹 A/B 분류표 (15건 각각 `generated_answer` 요약 + 분류 근거)
3. 사전에 실제로 추가한 표현 목록과, **검토했지만 neutral 오탐 위험으로 추가하지 않은 표현**도 함께 기록
4. before/after 비교표 (tp/fp/fn)
5. pytest 전체 실행 결과 — 정확한 숫자를 pytest 출력에서 그대로 복사
6. 그룹 B(사전 확장으로 해결 안 되는 케이스)에 대한 후속 과제 제안 — 구현은 하지 말고 제안만

---

## 5. 다음 조치

이 결과를 바탕으로 CUE가 그룹 B 케이스에 대한 대응(예: 답변의 의미론적 절대성 판단이 필요한지, 아니면
이번 범위로 충분한지)을 사용자와 논의 후 결정.
