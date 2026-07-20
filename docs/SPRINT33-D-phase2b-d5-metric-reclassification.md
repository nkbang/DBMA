# SPRINT33-D Phase 2-B — D-5 Metric Reclassification Preflight

상태: Investigation only. Code change: none.

## 목적

Phase 6-B metric을 그대로 쓸 수 있는지 재평가하고, genre/profile별
metric 분리, orphaned boundary recovery와 chunk-size constraint의 독립
평가 정의, D-5 acceptance criteria 수정 초안을 작성한다.

---

## 1. Phase 6-B Metric 재평가 — 그대로 사용 가능

```text
Phase 6-B의 confirmed/orphaned rate는 "기존 chunk 시작 오프셋 ↔
semantic boundary 오프셋" 간의 거리만 측정하며, chunk 생성 로직이나
문단 길이와는 무관하다. Phase 2-A/2-B에서 발견한 장문단/safety-cap
이슈는 "새 chunk를 어떻게 만드는가"의 문제이지 "기존 chunk와 semantic
boundary가 얼마나 가까운가"의 측정 방식과는 독립적이다.

→ Phase 6-B 수치(confirmed 2.19~2.5%, orphaned 63.11~70.3%)와 Phase 1
  수치(orphaned recovery 98.7%)는 재계산 없이 그대로 유효.
```

---

## 2. 신규 발견 — Chunk 크기 초과의 두 번째 원인(전 문서 공통)

Phase 2-A는 "개별 장문단(>1800자, 분할 불가)"을 원인으로 지목했으나,
이번 조사에서 **한국어 "클린 프로즈" 문서(장문단 0건)에서도** shadow
chunk 중앙값이 1800~2500자로 나타나는 것을 확인 — 별도 원인이 추가로
존재한다.

### Flush 원인 분해(semantic vs safety_cap)

```text
document                       total  semantic     safety_cap
11. 고린도전서                    132   15(11.4%)   116(87.9%)
12. 고린도후서                    109   40(36.7%)    68(62.4%)
2 Chronicles Vol.15               530  126(23.8%)   403(76.0%)
2 Kings Anchor Bible               377    8(2.1%)   369(97.9%)
2 Kings Power/Fury                 340   64(18.8%)   275(80.9%)
2 Kings, Volume 13                 588   27(4.6%)    561(95.4%)
3. 마가복음                        163   71(43.6%)    91(55.8%)
5. 요한복음1                       108   27(25.0%)    80(74.1%)
6. 요한복음2                       120   43(35.8%)    76(63.3%)
7. 사도행전1                       120   14(11.7%)   105(87.5%)
8. 사도행전2                       149    7(4.7%)    141(94.6%)
9. 로마서1                         131   49(37.4%)    81(61.8%)
```

**핵심 발견**: 전 문서에서 chunk flush의 과반(55.8%~97.9%)이 semantic
boundary가 아니라 **safety cap(1.5×chunk_size=1800)**에 의해
발생한다. 최고 semantic 비율을 보이는 "3. 마가복음"조차 55.8%가
safety-cap 유발이다. 즉 Phase 1 빌더는 "semantic-first"로 설계되었지만
실제로는 여전히 대다수 chunk가 길이 기반으로 결정되고 있다 — 원인은
semantic boundary 밀도 자체가 낮기 때문(예: "2 Kings Anchor Bible"은
heading 매칭이 947개 candidate 중 소수에 불과).

이것이 chunk 크기 중앙값이 목표(1200자)보다 훨씬 높은 1800~2500자
근처에 몰리는 이유다 — Phase 1의 안전망 배율(1.5x)이 목표치보다 높게
설정되어 있어, semantic 신호가 없는 구간에서는 항상 1800자 근처까지
누적된 뒤에야 강제 flush되기 때문.

### 두 가지 독립 원인 정리

```text
원인 A(genre-specific, Phase 2-A):
  개별 candidate 자체가 >1800자이며 분할 불가능한 후주 콘텐츠(색인/
  카탈로그/참고문헌). 4개 영문 WBC 문서에만 존재. 극단적 이상치(max
  4000~6511)를 유발.

원인 B(universal, 이번 Phase 2-B 신규 발견):
  semantic boundary 밀도가 낮아 대부분의 flush가 safety cap(1800)에서
  발생. 전 12개 문서 공통. 중앙값을 1800~2500자로 끌어올리는 주 원인.

→ 두 원인은 서로 다른 해법을 요구한다: 원인 A는 hard size fallback
  (Phase 2-A §3 옵션 C) 없이는 해결 불가, 원인 B는 safety cap 배율
  자체를 낮추거나(예: 1.5x→1.2x) semantic feature의 recall을 높이면
  (예: PageHeaderArtifact/Scripture Reference 등 추가 feature) 개선
  가능 — 서로 독립적인 튜닝 축이다.
```

---

## 3. Genre/Profile 분리

```text
Profile A — Low Back-matter Density (한국어 8개 문서):
  개별 장문단(>1800자) 0건. Chunk 크기 문제는 원인 B(safety cap
  dominance)만 해당.
  orphaned recovery: 97.7~100%(최저 97.7%, "6.요한복음2")

Profile B — High Back-matter Density (영문 WBC/주석서 4개 문서):
  개별 장문단 다수 존재(52~122개/문서). 원인 A+B 동시 작용.
  orphaned recovery: 85.7~100%(최저 85.7%, "2 Kings Anchor Bible")
  chunk 크기 이상치: max 3845~6511자(Profile A는 이런 극단값 없음,
  Profile A 최대는 2717자 "7.사도행전1")

→ 두 프로파일은 recovery rate에서도(Profile A가 전반적으로 더 높고
  안정적) chunk-size 특성에서도 뚜렷이 구분된다. ADR-007이 이미 제안한
  Signal-Profile 분리 원칙이 D-5 acceptance criteria에도 그대로
  적용되어야 한다.
```

---

## 4. Orphaned Boundary Recovery와 Chunk-size Constraint의 독립 평가

```text
제안: 다음 3개를 서로 독립적인 평가 축으로 분리한다(2개가 아니라
3개 — 원인 A/B 분해 결과 반영).

축 1. Orphaned Boundary Recovery Rate
     — Phase 1 방법론 그대로(semantic boundary 회수율). corpus 전체
       공통 기준 적용 가능(genre 무관하게 이미 85.7~100% 확보).

축 2. Chunk Size Compliance — Safety-cap Dominance (원인 B)
     — "semantic flush 비율" 자체를 추적. 목표: 낮을수록 나쁨(현재
       2.1~43.6%). Profile 무관 공통 축. Phase 5 스타일의 weight/
       threshold 조정이나 신규 feature(recall 향상)로 개선 가능한 영역.

축 3. Chunk Size Compliance — Unsplittable Outlier Ratio (원인 A)
     — 문서 내 candidate 중 "분할 불가 & >1800자" 비율. Profile B에만
       존재(Profile A는 항상 0). Hard size fallback 구현 여부에 따라
       결정되는 영역 — 별도 구현 항목(Phase 2-A §3 옵션 C)이 선행되지
       않으면 개선 불가능한 축.

세 축을 하나의 pass/fail로 합치지 않고 개별 보고하는 것을 권고 —
합치면 원인 A(소수 문서에만 존재하는 극단치)가 축 1/2의 실제 개선을
가릴 위험이 있다(Phase 1의 "orphaned recovery 98.7%"라는 강한 성과가
"chunk 크기 이상치" 서술 하나로 묻힐 뻔한 것과 동일한 문제).
```

---

## 5. D-5 Acceptance Criteria 수정 초안

```text
기존 초안(Phase 2 킥오프):
  P95 chunk size <= 1800 AND max chunk size < 2400 AND
  orphaned recovery >= Phase 1 baseline

수정 제안(초안, 확정 아님):

  [공통, corpus 전체]
    orphaned recovery >= 90%          (Phase 1 실측 최저치 85.7%보다
                                        약간 낮게 잡아 여유 확보 —
                                        정확한 값은 더 많은 corpus
                                        확보 후 재조정 필요)

  [Profile A 전용]
    semantic flush ratio >= 20%       (현재 Profile A 범위 11.4~43.6%,
                                        중간값 근처)
    P95 chunk size <= 1800
    max chunk size <= 2717            (Profile A 실측 최대치 기준,
                                        임의 라운드업 없이 실측값 사용)

  [Profile B 전용]
    unsplittable outlier ratio 별도 보고(게이트 기준 아님 — hard size
    fallback 구현 전까지는 통과 불가능한 기준을 강제하지 않음)
    semantic flush ratio >= 5%        (Profile B 최저 2.1% 대비 소폭
                                        상향 목표)
    max chunk size: 게이트 기준에서 제외, 참고 지표로만 유지

주의: 이 값들은 Phase 2 측정용 후보이며 확정 acceptance criteria가
아니다(HQ 지시 원칙 유지).
```

---

## 완료 조건

```text
✅ Phase 6-B metric 재사용 가능 여부 확인 — 재계산 불필요, 그대로 유효
✅ Genre/Profile 분리 — Profile A(한국어, 8개)/B(영문 WBC, 4개)로 확정,
   recovery/size 특성 모두 뚜렷이 구분됨을 실측 확인
✅ 신규 발견 — chunk 크기 초과의 두 번째 독립 원인(safety-cap
   dominance, 전 문서 공통) 확인 및 정량화
✅ 독립 평가 축 3개 정의(orphaned recovery / semantic flush ratio /
   unsplittable outlier ratio) — 2개가 아니라 3개로 세분화 필요함을 확인
✅ D-5 acceptance criteria 수정 초안 작성(genre 분리 반영)
코드 변경 없음.
```
