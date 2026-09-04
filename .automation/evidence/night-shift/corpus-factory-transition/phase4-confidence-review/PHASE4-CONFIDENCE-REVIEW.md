
# Phase 4 — Confidence-based Review

- designed_at: 2026-08-16T21:45:00Z
- baseline_source: PHASE0-VOL01-BASELINE.md, PHASE1-BOTTLENECK-ANALYSIS.md
- 이 문서는 confidence score 기반 review routing 설계다.

## 설계 원칙

1. **confidence ≠ theological truthiness**: confidence는 신학적 진실성을 의미하지 않음
2. **Human Review 우선**: LOW confidence candidate는 반드시 Human Review 대상
3. **ADR-022 준수**: 자동 재시도/자동 승격 금지 원칙 유지

## Confidence Classification (기존 worker.py 기반)

```python
# NAE/pipeline/tsu/worker/worker.py::_classify_confidence()
if raw_confidence >= 0.9:
    label = "HIGH"
elif raw_confidence >= 0.8:
    label = "MEDIUM"
else:
    label = "LOW"
```

## Review Routing

```
HIGH   (confidence >= 0.9) → 자동 후속 처리 가능
     → Embedding Queue로 이동 (Phase 5)
     → 단, ADR-022 §8에 따라 자동 promotion 금지
        → Human Review gate 통과 필요

MEDIUM (0.8 <= confidence < 0.9) → Sampling / Targeted Review
     → 10-20% sampling Human Review
     → 나머지 자동 후속 처리 (단, Human Review gate 통과 필요)

LOW    (confidence < 0.8) → Human Review
     → 100% Human Review 대상
     → 신학적 판단 필수
```

## Vol.1 Baseline에서의 Confidence 분포

```
{'0.8-0.9': 2764, '0.9-1.0': 879}
```

**해석**:
- HIGH (0.9-1.0): 879건 (24.1%)
- MEDIUM (0.8-0.9): 2764건 (75.9%)
- LOW (<0.8): 0건 (baseline에 없음)

**주의**: baseline confidence distribution이 0.8-1.0만 있음 — LOW가 없는지, 아니면 0.8 미만은 is_claim=false로 걸러진 것인지 확인 필요

## Human Review Gate

```
[CONFIDENCE_CLASSIFIED] → [Confidence-based Routing]
    HIGH → [Embedding Queue] (Human Review gate 통과 후)
    MEDIUM → [Sampling Review] → [Human Review gate 통과 후]
    LOW → [Human Review] → [Human Decision] → [Promotion Gate]
```

**핵심**: 모든 candidate는 Human Review gate를 통과해야 promotion됨
(ADR-022 §8 — 자동 승격 금지)

## 구현 우선순위

1. **confidence classification 검증** (기존 worker.py::_classify_confidence())
   - baseline 데이터와 일치하는지 확인
   - LOW confidence candidate가 실제로 없는지 확인

2. **review routing 로직 설계** (신규)
   - HIGH/MEDIUM/LOW routing 로직
   - sampling rate 설정 (MEDIUM: 10-20%)

3. **Human Review gate 구현** (신규)
   - human_decision.json 기반 판정
   - exception_queue.json 연동

4. **Promotion Gate 연동** (Phase 5에서 구현)
   - Human Review 통과 candidate만 embedding queue로 이동

## 다음 단계

Phase 4 설계 완료 → CUE audit → Phase 5 (Embedding & Promotion Gate)
