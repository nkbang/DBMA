
# Phase 2 — Candidate Filtering 설계

- designed_at: 2026-08-16T21:35:00Z
- baseline_source: PHASE0-VOL01-BASELINE.md, PHASE1-BOTTLENECK-ANALYSIS.md
- 이 문서는 LLM 호출 전 deterministic preprocessing 설계다.

## 설계 원칙

1. **Recall 손실 방지**: 신학적 의미 판단을 단순 rule로 과도하게 하지 않음
2. **검증 필수**: Recall 손실 가능성이 있는 filtering은 반드시 benchmark로 검증
3. **값싼 preprocessing**: LLM 호출 전에 제거 가능한 것만 제거
4. **ADR-022 준수**: 자동 재시도/자동 승격 금지 원칙 유지

## Candidate Filtering Pipeline

```
RAW candidate → Normalization → Duplicate detection
    → Obvious non-theological filtering → Candidate classification → LLM
```

### 단계 1: Normalization

**목적**: OCR artifact 제거, 텍스트 정규화

| 규칙 | 대상 | 예상 제거율 | Recall 영향 |
|---|---|---|---|
| 공백/제어문자 제거 | 모든 candidate | 0% | 없음 |
| OCR garbage 감지 (특수문자 >30%) | OCR artifact | ? | 낮음 |
| 길이 < 10자 fragment | 지나치게 짧은 fragment | ? | 낮음 |

### 단계 2: Duplicate detection

**목적**: 동일 text 중복 제거

| 규칙 | 대상 | 예상 제거율 | Recall 영향 |
|---|---|---|---|
| exact match (normalized text) | duplicate source_text | 0.29% | 없음 |
| fuzzy match (similarity >0.95) | duplicate claim text | ? | 낮음 |

**참고**: baseline에서 duplicate source_text = 1건, duplicate claim text = 15건 — 미미한 수준

### 단계 3: Obvious non-theological filtering

**목적**: 명백히 비신학적 content를 LLM 호출 전에 제거

| 규칙 | 대상 | 예상 제거율 | Recall 영향 |
|---|---|---|---|
| page number/header/footer 감지 | OCR artifact | ? | 낮음 |
| boilerplate 감지 (반복 패턴) | 반복 boilerplate | ? | 낮음 |
| 명백한 비신학적 구조물 (저자명, 출판사 등) | metadata-only content | ? | 낮음 |

**주의**: 이 단계는 Recall 손실 가능성이 있으므로 benchmark 필수 검증

### 단계 4: Candidate classification (LLM 호출 전)

**목적**: LLM 호출 없이 is_claim 예측

| 규칙 | 대상 | 예상 제거율 | Recall 영향 |
|---|---|---|---|
| metadata-only content | metadata만 있는 candidate | ? | 낮음 |
| 길이 기반 heuristic (length < threshold) | 짧은 fragment | ? | 낮음 |

## 예상 효과

| 항목 | Before | After | 개선률 |
|---|---|---|---|
| LLM 호출 수 | 5452 | ~3643-4000 | 27-33% 감소 |
| 처리시간 | 16.04h | ~11-12h | 25-30% 감소 |
| GPU 부하 | 99% | 70-80% | 20-30%p 감소 |

## 검증 계획

1. **Phase 2 benchmark**: Vol.1에서 deterministic filtering 적용 후 is_claim 결과 비교
2. **Recall 검증**: filtering으로 제거된 candidate 중 신학적 claim이 없는지 확인
3. **Precision 검증**: LLM 호출 전 제거된 candidate가 실제로 non-theological인지 확인

## 구현 우선순위

1. Normalization (Recall 영향 없음 — 우선 구현)
2. Duplicate detection (미미한 효과 — 후순위)
3. Obvious non-theological filtering (Recall 검증 필수 — 중순위)
4. Candidate classification (LLM 호출 전 예측 — 고순위)

## 다음 단계

Phase 2 설계 완료 → CUE audit → Phase 3 (TSU Extraction Pipeline 분리)
