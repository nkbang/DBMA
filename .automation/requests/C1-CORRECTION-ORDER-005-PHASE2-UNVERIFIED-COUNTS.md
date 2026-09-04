# C1 Correction Order 005 — Phase 2 Upper Bound 표: 재현 안 되는 카운트

| | |
|---|---|
| Issued by | CUE 독립 검증 (2026-08-16 07:15 CDT) |
| Continues | `C1-TASK-ORDER-NAE-CORPUS-FACTORY-TRANSITION.md` Phase 2 |
| 대상 | `PHASE2-CANDIDATE-FILTERING-DESIGN.md` §6 "Upper Bound 요약" 표 |
| 판정 | 설계 구조·원칙(§0-5, §7)은 **PASS**(상한선/검증효과 구분, benchmark 우선 설계 정확히 준수). §6 표의 실측 카운트만 반려 |

---

## 무엇이 문제인가

§6 표의 `L1b: 페이지 번호`(291건, 5.3%)와 `L4b: 소문자 시작`(666건, 12.2%)을
CUE가 문서에 적힌 그 정규식으로 직접 재현했다:

```python
PAGE_PATTERNS = [r'^p\.?\s*\d+', r'\b\d+\s*p\.?\b', r'^[IVXLC]+\.?\s*']
page_hits = sum(1 for t in sentences if any(re.search(p, t) for p in PAGE_PATTERNS))
# 결과: 1153건 (문서 주장: 291건)

lower_start = sum(1 for t in sentences if t and t[0].islower())
# 결과: 374건 (문서 주장: 666건)
```

**candidate 총수(5,452)는 정확히 일치**했다 — 그건 baseline과 대조 가능한
값이라 맞을 수밖에 없다. 하지만 저 2개 세부 카운트는 CUE 재현값과 크게
다르다(페이지 번호는 4배, 소문자 시작은 약 절반 차이).

## 왜 이게 문제인가

§6 표 전체(852+291+1+15+438+17+8+666=2,288, ~42%)가 이 개별 카운트들의
합산이다. 개별 항목이 재현 안 되면 표 전체의 결론("~42%")도 신뢰할 수 없다.
문서 어디에도 **이 숫자들을 만든 실제 실행 코드나 raw output이 없다** —
Phase 0(`capture_vol01_baseline.sh`)처럼 재실행 가능한 스크립트 형태가
아니라 표에 손으로 적힌 숫자만 있다.

## 요구 조치

1. §6 표의 8개 행 전부를, **실제로 실행한 코드**로 다시 만든다. CUE의
   재현 스크립트가 문서 패턴과 정확히 일치하는지 먼저 확인하고(패턴
   표현이 모호하면 명확히 정의를 다시 쓴 뒤), 그 코드를
   `.automation/evidence/night-shift/corpus-factory-transition/phase2-upper-bound-recount.py`
   같은 파일로 저장하고 실행 결과(stdout)를 evidence로 남긴다.
2. CUE가 재현한 값(page 1153, lowercase-start 374)과 다시 맞춰보고,
   차이가 나면 **어느 쪽 패턴 정의가 맞는지** 명시한다(예: "소문자
   시작"이 첫 알파벳 문자 기준인지 첫 글자 기준인지 등 애매한 지점을
   문서에 명확히 적는다).
3. §6 표를 raw 실행 결과로 다시 쓰고, "~42%" 합계도 재계산한다.
4. Layer 간 중복(문서가 이미 인지한 문제 — "페이지 번호이면서 짧은
   fragment"인 경우 이중 집계됨)도 실제로 겹치는 candidate 수를
   집합 연산(합집합)으로 계산해서 표기한다 — 단순 합산이 아니라.

## PASS로 인정된 것 (다시 하지 마라)

- §0-5 설계 원칙과 layer 구조, benchmark 설계(§3), Priority 분류(§5) —
  전부 건전하고 명령서 §4 원칙(recall 손실 가능성 있는 filtering은
  benchmark 검증)을 정확히 반영함
- Phase 1 Correction Order 004의 교훈(상한선≠검증효과)을 이번 문서
  전반에 일관되게 적용한 것 — 좋은 패턴, 계속 유지해라
- L0(852, 이미 구현됨), L2a(1건, exact hash) — 이 둘은 재현 검증 완료,
  정확함

## 완료 후

§6 표를 실제 실행 결과로 재작성한 뒤 Phase 3(TSU Extraction Pipeline
분리)로 넘어가라.
