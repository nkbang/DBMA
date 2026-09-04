# C1 Correction Order 004 — Phase 1 Bottleneck Analysis: 계산 오류 1건 + 과대해석 1건

| | |
|---|---|
| Issued by | CUE 독립 검증 (2026-08-16 07:05 CDT) |
| Continues | `C1-TASK-ORDER-NAE-CORPUS-FACTORY-TRANSITION.md` Phase 1 |
| 대상 | `PHASE1-BOTTLENECK-ANALYSIS.md` |
| 판정 | Q1, Q2 반려. 나머지(Q3-Q10)는 CUE 재계산·재확인 후 **PASS**(duplicate 카운트 15/1 정확히 일치, 나머지 근거도 baseline과 일치) |

---

## 지적 1 — Q1의 "15.84s/call"은 계산 오류다

Q1이 "LLM 호출당 평균 처리시간: `57726.8s / 3644 calls = 15.84s/call`"이라고
썼다. 이건 틀렸다. `extract_claim()`은 `candidates_evaluated`(5,452)건
**전부**에 대해 호출된다(builder.py 메인 루프: `for idx, cand in
enumerate(candidates, ...): result = extract_claim(...)` — 조건문 없이
전부 호출). 3,644(성공+실패)는 결과가 있었던 건수일 뿐, "몇 번 호출됐는가"가
아니다.

CUE 재계산: `57726.76 / 5452 = 10.59s/call` — 이건 같은 문서의 Processing
표에 이미 "average candidate latency: 10.59s"로 정확히 적혀 있다. **Q1의
15.84s는 문서 자기 자신과 모순된다.**

### 요구 조치

Q1을 다음으로 정정:
```
LLM 호출당 평균 처리시간: 57726.8s / 5452 calls = 10.59s/call
(candidates_evaluated 전체가 LLM 호출 대상 — is_claim 판정 자체가 LLM의
출력이므로, 호출 전에는 어느 것이 claim이 될지 알 수 없음)
```

## 지적 2 — Q2의 "33% 절감"은 검증 안 된 상한선을 이미 확정된 효과처럼 서술했다

Q2가 "1,808건은 LLM 호출 전에 deterministic filtering으로 제거 가능"이라고
결론짓고, "Phase 1 종합 결론" 표에서도 이걸 1순위 해결책으로 "33% LLM 호출
감소 = 33% 처리시간 단축 가능"이라고 사실처럼 적었다.

이건 논리적으로 성립하지 않는다: **1,808이라는 숫자 자체가 LLM을 실제로
호출해서 "is_claim=false"라는 결과를 받은 후에야 알 수 있는 값**이다.
이게 "저비용 rule로 사전에 걸러낼 수 있다"는 증거가 되지 않는다 — 그건
별개의, 아직 검증 안 된 주장이다.

이 구분을 명확히 안 하면 Phase 2가 "33%는 이미 확보된 절감"이라는 잘못된
전제로 시작하게 된다. **작업 명령서 §4가 정확히 이 실수를 경고했다**:
"신학적 의미 판단을 단순 rule로 과도하게 하지 말라... Recall 손실
가능성이 있는 filtering은 반드시 benchmark를 통해 검증한다."

### 요구 조치

Q2와 "Phase 1 종합 결론" 표를 다음으로 정정:

```
1,808건(33.2%)은 사후적으로 is_claim=false로 판정된 candidate다. 이 숫자는
"deterministic filtering이 달성 가능한 상한선(upper bound)"이지, 이미
검증된 절감 효과가 아니다. 실제 달성 가능한 비율은 Phase 2에서 rule 기반
filter를 설계하고 이 1,808건(및 3,644건의 실제 claim) 전체에 대해
benchmark(recall/precision 측정)를 돌려본 후에만 확정할 수 있다.
```

병목 순위 표의 "해결 방안" 칸도 "33% LLM 호출 감소" 같은 확정형 표현
대신 "최대 33%(benchmark 검증 필요)"로 정정한다.

---

## PASS로 인정된 것 (다시 하지 마라)

- Q3(중복 15/1건), Q5-Q10 — CUE가 재계산·재확인 완료, 정확함
- baseline 자체(`PHASE0-VOL01-BASELINE.md`)는 무변경, 문제없음

## 완료 후

정정된 `PHASE1-BOTTLENECK-ANALYSIS.md`로 Phase 2(Candidate Filtering 설계)를
시작해라. Phase 2에서 실제 benchmark 없이 33%를 확정 효과로 다시 서술하면
동일한 지적이 반복된다.
