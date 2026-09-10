---
title: ClaimGuard TrustTier 위장 제거 빌드 보고서
created: 2026-09-10
author: CUE
status: 구현 완료 · 회귀 통과
audit_item: PM 정렬 감사 R2 / P0-4 (선결 로직 #1)
base: claude/p0-1-quality-integration (← origin/dev/dbma-engine @ 09d8ac2)
scope: core/claim_guard.py, tests/test_claim_guard.py, tests/test_generation_claim_guard.py
---

# ClaimGuard TrustTier 위장 제거

## 문제

`core/claim_guard.py::wrap_ranked_candidates()`가 모든 검색 결과를
`trust_tier=TrustTier.T1`로 감쌌다. 답변 생성 경로(`GenerationService.
_run_claim_guard`)는 이 어댑터 하나로만 ClaimGuard에 증거를 넘긴다.

두 가지 결과:

1. **라벨 부정확** — 현행 코퍼스(Fuller·Hiscox·Dagg 등)의 TSU는 성경
   본문이 아니라 19세기 신학·주석서에서 추출한 문헌 단위다. TrustTier
   정의상 T3(주석/사전/논문 등 문헌 근거)인데 T1(본문)로 표기됐다.

2. **규칙 2a 사문화** — `ClaimGuard.evaluate()`는 `has_t1`을 계산하지만
   어디에서도 소비하지 않았다. 문서화된 규칙 2a("위험 표현 있음 + T1
   근거 0개 → absolute_claim_blocked")가 죽어 있었고, 어차피 모든 증거가
   T1로 위장돼 도달 불가능한 분기이기도 했다.

→ "T1 본문 근거 없이는 절대·최상급 주장을 막는다"는 안전장치가 존재하는
것처럼 보이지만 실제로는 발화하지 못하는 상태였다.

## 변경

### 1. `_infer_trust_tier(candidate)` 신설 — 후보별 실제 등급 판정

| 신호 | 판정 |
|---|---|
| `metadata["trust_tier"]` 또는 `source_provenance.trust_tier` 존재 | 그 값 사용 (향후 dataset_registry 연동 대비) |
| `metadata["source_type"] == "scripture"` 또는 `is_scripture_text is True` | T1 |
| 그 외 (검색 후보의 절대다수) | **T3** |

성경 본문 자체임을 나타내는 **양성 신호가 있을 때만** T1로 올린다.
신호가 없으면 문헌 근거(T3)로 두고 본문으로 위장하지 않는다.

### 2. `wrap_ranked_candidates()` — `trust_tier=TrustTier.T1` → `_infer_trust_tier(c)`

`evidence_axis`는 `"t1_hybrid_search"` 그대로 둔다 — 이것은 검색 축의
이름이지 trust tier가 아니다(ParallelRetriever 설계상 하이브리드 검색축).

### 3. `ClaimGuard.evaluate()` — 규칙 2a 활성화

2b(T2/T4 단독) 반환 직후, 2c(경쟁 후보 탐색) 앞에:

```python
if not has_t1:
    result.absolute_claim_blocked = True
    result.scope_qualifier_required = True
    result.reason = "T1(본문) 근거 없이 절대·최상급 주장 불가"
    ...
    return result
```

규칙 순서는 docstring 명세 그대로 2b → 2a → 2c → 2d.

## 동작 변화

| 상황 (답변에 절대·최상급 표현 있음) | 변경 전 | 변경 후 |
|---|---|---|
| 검색 후보 = 주석 TSU (양성 신호 없음) | T1로 위장 → 2c else-branch로 우연히 차단, reason="전체 코퍼스 비교 불가" | T3 판정 → **규칙 2a로 차단**, reason="T1(본문) 근거 없이 절대·최상급 주장 불가" |
| 후보에 `source_type="scripture"` | T1 (우연히 맞음) | T1 (신호 기반) |
| 후보 메타에 명시적 `trust_tier` | 무시하고 T1 | 명시값 존중 |

차단 결과(`absolute_claim_blocked`) 자체는 현행 wiring(db_path 없음)에서
이전에도 우연히 True였다. 이번 변경의 실질은 **(a) 근거 등급 라벨의
정직성**과 **(b) 차단 사유가 올바른 규칙(2a)에서 나오는 것** —
경쟁 후보 DB가 연결되는 향후 시나리오에서 T1 위장은 "본문 근거 있음"으로
오판돼 차단이 풀렸겠지만, 이제는 풀리지 않는다.

## 범위 밖 (후속)

- `has_t3`는 여전히 계산만 되고 미사용 — 별도 정리 대상 (규칙 확장 시).
- 개인 서재 ingest 경로가 성경 전용 업로드에 `source_type="scripture"`를
  세우지 않는다 → 그런 업로드는 보수적으로 T3 처리된다(차단이 더 강해질
  뿐이라 무해). dataset_registry 연동은 P0 범위 밖.
- ClaimGuard는 여전히 사후 탐지만 한다 — "출처 없이 지어낸 진술"은
  탐지 대상 아님(선결 로직 #2 유보 경로에서 별도 처리).

## 검증

```bash
~/envs/dbma311/bin/python -m pytest -q tests/
```

- ClaimGuard 관련 파일: 142 passed
- 전체 회귀: **2881 passed, 15 skipped** (신규 4건: T3 판정 / scripture 신호 /
  명시적 tier 존중 / 규칙 2a 차단)
