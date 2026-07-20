# SPRINT33-D Phase 3-A — D-5 Metrics Formal Evaluation

상태: 고정(fixed). ADR-007 Amendment A가 정의한 3축 metric을 genre
profile별로 정식 산출.

## 방법

`scripts/shadow_d5_metrics.py`(신규) — Beta corpus 12개 문서 전체에
대해 Axis 1/2/3을 계산. Phase 2-B의 ad-hoc 측정과 달리 builder의 결정
루프를 재구현하지 않고, `build_chunks()`가 이미 반환하는 chunk 시작
오프셋이 semantic boundary 오프셋 집합과 정확히 일치하는지만 확인하는
방식으로 Axis 2를 산출(핵심 로직 중복 없음).

Profile 분류(ADR-007 Amendment A 잠정 기준): candidate 중 하나라도
`chunk_size * 1.5`(=1800자)를 초과하면 Profile B, 아니면 Profile A.

---

## 결과

```text
document                          profile  recovery  semantic  outlier
11. 고린도전서                          A    100.0%     12.9%     0.0%
12. 고린도후서                          A     97.8%     41.3%     0.0%
2 Chronicles Vol.15                     B    100.0%     29.2%     2.8%
2 Kings Anchor Bible Commentary         B     85.7%      4.0%    18.6%
2 Kings Power and the Fury              B    100.0%     26.2%     3.0%
2 Kings, Volume 13                      B     88.9%      7.1%     4.0%
3. 마가복음                             A    100.0%     46.6%     0.0%
5. 요한복음1                            A    100.0%     28.7%     0.0%
6. 요한복음2                            A     97.7%     43.3%     0.0%
7. 사도행전1                            A    100.0%     11.7%     0.0%
8. 사도행전2                            A     77.8%      5.4%     0.0%
9. 로마서1                              A    100.0%     43.5%     0.0%
```

### Profile 집계

```text
Profile A (8개 문서):
  Axis 1 recovery rate:        256/260  = 98.5%
  Axis 2 semantic flush ratio: 300/1032 = 29.1%
  Axis 3 unsplittable outlier: 0/9006   =  0.0%

Profile B (4개 문서):
  Axis 1 recovery rate:        193/195  = 99.0%
  Axis 2 semantic flush ratio: 301/1835 = 16.4%
  Axis 3 unsplittable outlier: 389/7100 =  5.5%
```

---

## 매우 중요한 신규 발견 — `split_sentences_mixed()`의 구조적 한계

이번 정식 평가를 위해 Axis 3(unsplittable outlier) 계산 로직을
재검증하던 중, Phase 2-A의 "100% 분할 불가" 결론에 대한 더 근본적인
원인을 발견했다.

```text
core.text_normalizer.split_sentences_mixed()는 입력 텍스트를 오직
"\n"(줄바꿈) 기준으로만 분할한다(text_normalizer.py:266,
text.split("\n")) — 문장부호가 아니라 물리적 줄바꿈이 유일한 분할
단서다.

core.text_normalizer.split_paragraphs()가 만드는 candidate는 내부에
"\n"을 전혀 포함하지 않는다(collapse_soft_linebreaks가 문단 내부의
모든 줄을 " ".join()으로 이미 합쳐버림 — 문단 사이의 "\n\n"만 남음).

실측 검증:
  '이것은 첫문장입니다. 이것은 두번째 문장입니다. 이것은 세번째...'
  (줄바꿈 없음) → split_sentences_mixed() 결과 1개(분할 안 됨)

  '이것은 첫문장입니다.\n이것은 두번째 문장입니다.\n이것은 세번째...'
  (줄바꿈 있음) → split_sentences_mixed() 결과 3개(정상 분할)
```

**결론**: Phase 2-A가 "장문단은 색인/카탈로그처럼 문장 구조가 없는
콘텐츠라서 분할이 안 된다"고 서술한 것은 관측 자체는 정확했으나,
근본 원인 설명이 불완전했다. 실제로는 **콘텐츠의 문장 구조 유무와
무관하게, `split_paragraphs()`를 거친 어떤 문단이든 `split_sentences_
mixed()`에 넣으면 항상 분할되지 않는다** — 두 함수의 입출력 형태가
구조적으로 맞지 않기 때문이다.

**더 중요한 함의**: 이는 SPRINT33-D의 프로토타입 한계가 아니라
**production `core/chunking_optimizer.py`의 기존 동작에도 동일하게
적용된다.** `chunking_optimizer.py:305`의
`split_sentences_mixed(p) if split_sentences_mixed is not None else ...`
호출은 `p`가 `split_paragraphs()`의 산출물이므로, 이 분기가 실제로
문장 단위 분할을 수행한 적이 (일반적인 산문 문단에 대해서는) 거의
없었을 가능성이 있다. 이는 SPRINT33-D 범위를 벗어나는 production
코드의 기존 동작에 대한 관찰이며, **이번 조사에서 확인만 하고
수정하지 않았다**(chunking_optimizer.py 무접촉 원칙 유지) — 별도
Preflight 대상으로 기록해 둔다.
```

---

## 해석 — 3축 metric의 의미

```text
Axis 1(recovery, 98.5~99.0%): 두 profile 모두 매우 높고 균등 —
  semantic boundary 회수 능력 자체는 genre와 거의 무관하게 우수함이
  재확인됨.

Axis 2(semantic flush ratio, A=29.1% vs B=16.4%): Profile B가
  뚜렷하게 낮음 — 학술 주석서는 heading 밀도가 낮아 여전히 대부분의
  chunk가 safety-cap에 의해 결정됨(Phase 2-B의 원인 B가 profile B에서
  더 심함을 재확인).

Axis 3(unsplittable outlier, A=0.0% vs B=5.5%): Profile A는 항상 0 —
  Profile 분류 기준 자체가 이 값으로 결정되므로 당연한 결과(sanity
  check 성격). Profile B 내에서도 "2 Kings Anchor Bible"이 18.6%로
  가장 심각 — 이 문서가 색인/참고문헌 비중이 가장 높은 것으로 추정.
```

## 방법론 참고 — Phase 2-B 수치와의 근소한 차이

```text
이번 정식 측정(Axis 2)은 "chunk 시작 오프셋이 semantic boundary와
일치하는가"(구조적 일치)를 기준으로 하는 반면, Phase 2-B의 ad-hoc
측정은 "이 flush가 실제로 semantic 신호에 의해 트리거되었는가"(인과
관계)를 builder 루프를 재구현해 직접 추적했다. 두 방식은 안전망
flush 직후 다음 candidate가 우연히 semantic boundary인 경우를 다르게
계산할 수 있어 문서별로 몇 %p 차이가 존재한다(예: "11.고린도전서"
12.9% vs Phase 2-B 11.4%). 방향성과 결론(Profile B가 낮음)은 동일.
이번 방식은 core 로직을 재구현하지 않는다는 장점이 있어 공식
측정으로 채택.
```

## 완료 조건

```text
✅ Axis 1/2/3 profile별 정식 산출 완료
✅ regression: tests/ 전체 520 passed, 0 failed
✅ 신규 발견: split_sentences_mixed()의 줄바꿈 의존성 — production
   chunking_optimizer.py의 기존 한계 가능성 확인(수정하지 않음, 기록만)
✅ Phase 2-B 수치와의 방법론 차이 명시
코드 변경: scripts/shadow_d5_metrics.py, tests/test_shadow_d5_metrics.py
신규(둘 다 진단 전용). core/chunking_optimizer.py 등 여전히 무접촉.
```
