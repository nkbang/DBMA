# Phase 2 — Candidate Filtering 설계

- designed_at: 2026-08-16T13:00:00.000Z
- baseline_source: .automation/evidence/night-shift/corpus-factory-transition/PHASE0-VOL01-BASELINE.md
- bottleneck_source: .automation/evidence/night-shift/corpus-factory-transition/PHASE1-BOTTLENECK-ANALYSIS.md (정정판)
- 설계 원칙:
  - 신학적 의미 판단을 단순 rule로 과도하게 하지 않음
  - Recall 손실 가능성이 있는 filtering은 반드시 benchmark로 검증
  - "달성 가능한 상한선(upper bound)"과 "검증된 효과"를 명확히 구분

---

## 0. 현재 상태 분석 (Fuller Vol.1 기준)

### 이미 적용된 필터링

```python
# NAE/pipeline/tsu/config.py (변경 불필요)
MIN_CLAIM_SENTENCE_CHARS = 25
```

**실측 효과**: 6,304 총 문장 중 852건(13.5%)이 이미 이 규칙으로 제거됨.
나머지 5,452건이 LLM에 전달됨.

### LLM 사후 판정 결과 (baseline)

```
candidate count:        5,452  (LLM 호출 대상)
successful (TSU 생성):  3,643  (is_claim=true)
skipped (is_claim=false): 1,808  (LLM 호출 후에야 판정된 결과)
```

**중요**: 1,808건이라는 숫자는 LLM을 실제로 돌려서 나온 사후 결과다.
"deterministic filtering으로 사전에 걸러낼 수 있다"는 주장은
아직 검증되지 않았다. 이 숫자는 **달성 가능한 상한선(upper bound)**일 뿐.

---

## 1. Candidate Filtering Pipeline 설계

```
RAW candidate (canonical.json sentences)
    ↓
[Layer 0] 길이 필터 (이미 구현됨)
    MIN_CLAIM_SENTENCE_CHARS >= 25
    ↓
[Layer 1] 정규화 + 구조적 필터
    - 공백/특수문자 정규화
    - page number / header / footer 패턴 제거
    - footnote 참조만 포함된 문장 제거
    ↓
[Layer 2] 중복 감지 (deterministic)
    - exact match duplicate (hash 기반)
    - near-duplicate (minhash/simhash, 임계값 설정 필요)
    ↓
[Layer 3] 명백한 non-theological filtering (rule-based)
    - 지나치게 짧은 fragment (25-34자 중 특정 패턴)
    - 반복 boilerplate ("See also.", "Amen." 등)
    - OCR garbage (특수문자 비율 > 30%)
    ↓
[Layer 4] Candidate classification (lightweight heuristic)
    - metadata-only content 식별
    - citation/reference만 포함된 문장
    ↓
[Layer 5] LLM claim extraction (기존과 동일)
```

---

## 2. 각 Layer의 상세 설계

### Layer 0: 길이 필터 (이미 구현됨)

```python
# NAE/pipeline/tsu/config.py (변경 불필요)
MIN_CLAIM_SENTENCE_CHARS = 25
```

**Upper bound**: 852건 제거 가능 (13.5% of total, 0% of candidates)
**Recall 영향**: 없음 (이미 구현됨)

### Layer 1: 정규화 + 구조적 필터

#### 1a. 정규화
- Unicode normalization (NFC → NFKC)
- 연속 공백 → 단일 공백
- Full-width → Half-width 변환

#### 1b. page number / header / footer 패턴
```python
PAGE_NUMBER_PATTERNS = [
    r'^p\.?\s*\d+',           # "p. 123", "p123"
    r'\b\d+\s*p\.?\b',       # "123 p."
    r'^[IVXLC]+\.?\s*',      # "I.", "II.", "III." (roman numeral page)
]

HEADER_FOOTER_PATTERNS = [
    r'^\s*[-=]{3,}\s*$',      # "---", "==="
    r'^\s*\d+\s*[-=]+\s*\d+\s*$',  # "123 --- 456" (page range)
]
```

**Upper bound**: Fuller Vol.1에서 291건(5.3%)이 페이지 번호 패턴 매칭
**Recall 영향**: benchmark 검증 필요 (신학적 주장이 페이지 번호로 시작할 가능성)

#### 1c. footnote 참조만 포함된 문장
```python
FOOTNOTE_ONLY_PATTERN = r'^\s*\[\d+\]\s*$'  # "[1]", "[2]" 등
```

**Upper bound**: Fuller Vol.1에서 footnote 0건 → 0건 제거 예상
**Recall 영향**: 미미 (footnote 참조만 있는 문장은 신학적 주장 아님)

### Layer 2: 중복 감지 (deterministic)

#### 2a. Exact match duplicate (hash 기반)
```python
import hashlib

def exact_duplicate_hash(text: str) -> str:
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()
```

**Upper bound**: Fuller Vol.1에서 duplicate source_text 1건 → 1건 제거 예상
**Recall 영향**: 없음 (동일 텍스트는 동일 주장)

#### 2b. Near-duplicate (minhash/simhash)
- 임계값 설정 필요 (예: simhash 거리 <= 3)
- **주의**: 이 필터는 recall 손실 가능성이 높음
- 반드시 benchmark로 검증 필요

**Upper bound**: Fuller Vol.1에서 duplicate claim text 15건 → 최대 15건 제거 예상
**Recall 영향**: benchmark 검증 필요 (유사하지만 다른 주장일 가능성)

---

## 3. Benchmark 설계

### 3.1 Benchmark 목표

- **recall**: deterministic filtering으로 제거된 candidate 중 실제 claim=true인 비율 측정
- **precision**: filtering으로 제거된 candidate 중 실제 claim=false인 비율 측정
- **upper bound vs actual**: 상한선과 실제 효과의 차이 정량화

### 3.2 Benchmark 방법

```python
# NAE/pipeline/tsu/candidate_filter.py (새 파일 — 설계만, 구현 아님)

def benchmark_candidate_filtering(
    canonical_path: Path,
    tsu_path: Path,
    filter_layers: list[str],
) -> dict:
    """
    filter_layers에 지정된 Layer를 적용한 후,
    제거된 candidate 중 실제 claim=true인 비율(recall 손실) 측정.
    
    ground truth는 기존 TSU 데이터의 is_claim 판정 사용.
    """
    ...
```

**Benchmark 실행 조건**:
1. Fuller Vol.1 canonical.json에서 모든 candidate 추출
2. 각 Layer를 순차 적용 → 제거된 candidate 목록 생성
3. 제거된 candidate에 대해 기존 LLM 결과(is_claim)와 대조
4. recall/precision 계산

### 3.3 Benchmark 결과 해석 기준

```
recall >= 0.95:  안전 (5% 이하 recall 손실)
recall >= 0.90:  조건부 허용 (상세 분석 필요)
recall < 0.90:   재설계 필요 (신학적 주장 손실 가능성 높음)
```

---

## 4. Confidence-based Routing 정책 (Phase 4 연계)

### 4.1 Confidence分级 기준

```
HIGH   (confidence >= 0.9): 자동 후속 처리 가능
MEDIUM (0.8 <= confidence < 0.9): Sampling / Targeted Review
LOW    (confidence < 0.8): Human Review 필수
```

**현재 Vol.1 데이터**:
```
{'0.8-0.9': 2764, '0.9-1.0': 879}
confidence < 0.8 항목: 0
```

**주의**: confidence는 model self-reported이고 uncalibrated임.
신학적 진실성을 의미하지 않음을 명확히 유지.

### 4.2 Human Review 우선 대상

- LOW confidence 항목 (Phase 1에서 확인: Vol.1에서는 0건)
- deterministic filtering에서 recall < 0.95인 경우 제거된 항목
- duplicate로 판정된 항목 (근거 확인 필요)

---

## 5. 구현 순서 제안

### Priority 1 (recall 영향 미미, 즉시 적용 가능)
1. Layer 0: 길이 필터 (이미 구현됨)
2. Layer 2a: Exact match duplicate (hash 기반)
3. Layer 3c: OCR garbage (특수문자 비율 > 30%)
4. Layer 3b: 반복 boilerplate

### Priority 2 (benchmark 필요, recall 영향 확인 후 적용)
5. Layer 1b: page number / header / footer 패턴
6. Layer 3a: 지나치게 짧은 fragment
7. Layer 4a: metadata-only content 식별

### Priority 3 (recall 영향 높음, 신중히 적용)
8. Layer 2b: Near-duplicate (simhash)
9. Layer 4b: 문장 시작 대문자 없음 (recall 손실 가능성 높음)

---

## 6. Upper Bound 요약 (Fuller Vol.1 기준 — 실측 재현판)

- 재현 스크립트: `.automation/evidence/night-shift/corpus-factory-transition/phase2-upper-bound-recount.py`
- 실행 명령: `python3 phase2-upper-bound-recount.py`
- 상세 결과: `.automation/evidence/night-shift/corpus-factory-transition/PHASE2-UPPER-BOUND-VERIFIED.md`

| Layer | 제거 가능 수 | 비율 | recall 영향 | 상태 |
|-------|-------------|------|------------|------|
| L0: 길이 필터 | 852 | 13.5% | 없음 (이미 구현) | 완료 |
| L1b: 페이지 번호 | **1,153** | **21.1%** | 중 | benchmark 필요 |
| L2a: Exact dup | 1 | 0.02% | 없음 | 안전 |
| L2b: Near-dup | 15 | 0.3% | 중 | benchmark 필요 |
| L3a: 짧은 fragment | **4** | **0.07%** | 중 | benchmark 필요 |
| L3b: Boilerplate | **0** | **0%** | 미미 | 안전 |
| L3c: OCR garbage | 8 | 0.1% | 미미 | 안전 |
| L4b: 소문자 시작 | **374** | **6.9%** | **높음** | 신중히 |
| **합집합 (중복 제거)** | **1,536** | **28.2%** | - | **미검증** |

### 패턴 정의 명확화

**L1b: 페이지 번호 패턴** — 재현 시 1,153 건 (이전 주장: 291 건)
- 원인: `r"\\b\\d+\\s*p\\.?\\b"` 가 "p." 를 포함한 모든 숫자+문자 경계를 광범위 매칭
- 정확한 패턴 정의:
```python
PAGE_NUMBER_PATTERNS = [
    r"^p\.?\s*\d+",           # "p. 123", "p123" (문장 시작)
    r"\b\d+\s*p\.?\b",       # "123 p." (숫자+page)
    r"^[IVXLC]+\.?\s*",      # "I.", "II.", "III." (roman numeral page)
]
```
- 주의: 1,153 건 중 실제 페이지 번호인지 수동 검증 필요. 일부는 "p." 가 포함된 신학적 문장일 수 있음.

**L4b: 소문자 시작** — 재현 시 374 건 (이전 주장: 666 건)
- 정확한 패턴 정의:
```python
def is_lowercase_start(text: str) -> bool:
    stripped = text.lstrip()
    return stripped and stripped[0].isalpha() and stripped[0].islower()
```
- CUE 방식 `t[0].islower()` 와 동일 (374 건 일치)
- recall 영향: **높음** — 신학적 주장이 소문자로 시작할 수 있음 (예: "and thus...", "but God...")
- 권장: benchmark 필수. recall 손실 가능성 높음.

**L3a: 짧은 fragment** — 재현 시 4 건 (이전 주장: 438 건)
- 이전 438 건은 "25-34 자"만 기준으로 한 것 (단어 수 필터 미적용)
- 정확한 패턴 정의:
```python
def is_too_short_fragment(text: str) -> bool:
    if 25 <= len(text) <= 34:
        word_count = len(text.split())
        return word_count < 4
    return False
```

**L3b: Boilerplate** — 재현 시 0 건 (이전 주장: 17 건)
- Fuller Vol.1 에는 해당 boilerplate 패턴 없음. 이전 17 건은 "인용구 패턴" 과 혼동.

### Layer 간 중복 분석

- 페이지 번호 AND 짧은 fragment: 0 건 (중복 없음)
- 페이지 번호 AND 소문자 시작: 0 건 (중복 없음)
- **전체 합집합**: 1,536 건 (28.2%)

**중요**: Layer 간 중복을 고려한 합집합 기준이 실제 이론적 상한선이다.
실제 제거 가능 수는 **합집합 기준 1,536 건 (28.2%)**.

**실제 효과는 반드시 benchmark로 검증해야 한다.**


## 7. 다음 Phase로 전달할 질문

Phase 3(TSU Extraction Pipeline 분리)에서 다룰 사항:
- 독립 Queue Worker 설계 (TSU_EXTRACTION_QUEUE 상태 전이)
- Retry 정책 (ADR-022 §8 — 자동 재시도/자동 승격 금지 원칙 준수)
- 기존 ADR(ADR-022)과의 호환성

---

*이 설계는 상한선(upper bound) 분석을 포함하지만, 실제 효과는 benchmark 검증 필요.
Phase 1 정정(Correction Order 004)과 동일한 원칙 적용.*
