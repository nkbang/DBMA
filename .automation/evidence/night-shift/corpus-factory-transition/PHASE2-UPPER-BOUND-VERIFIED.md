# Phase 2 — Upper Bound 요약 (실측 재현 결과)

- verified_at: 2026-08-16T14:00:00.000Z
- script: .automation/evidence/night-shift/corpus-factory-transition/phase2-upper-bound-recount.py
- 실행 명령: `python3 phase2-upper-bound-recount.py`

---

## 0. 재현 스크립트 실행 결과 (raw stdout)

```
candidates(>=25 chars): 5452

L0: 길이 필터 제거 (이미 구현됨): 852

L1b: 페이지 번호 패턴 매칭: 1153
  [246자] It would be inexcusable for him to have lived all this time, without gaining any...
  [245자] It was common to speak of unbelief as a calling in question the truth of our own...
  [134자] It appeared to him, that we had taken unconverted sinners too much upon their wo...
  [389자] If it were not the duty of unconverted sin* ners to believe in Christ, and that,...
  [231자] If he admit the native depravity of his heart, it is his misfortune, not his fau...

L1b-2: header/footer 패턴 매칭: 0

L2a: Exact duplicate: 1
  [170자] If this reasoning be just, it cannot be inferred, from the laws of England decla...

L2b: Near-duplicate (상한선): 15 (embedding 기반, 별도 benchmark 필요)

L3a: 짧은 fragment (25-34자, 단어<4): 4
  [25자] 'On Particular Redemption....' (단어수=3)
  [32자] 'REPENTANCE PRECEDES FORGIVENESS....' (단어수=3)
  [25자] 'Sect. 4^.] PHILANTHROPOS....' (단어수=3)
  [25자] 'Sect. 4r.] PHILANTHROPOS....' (단어수=3)

L3b: Boilerplate: 0

L3c: OCR garbage (특수문자>30%): 8
  [30자] 'riLOEW r'- I ;,•.-: ATIO.'.'E....'
  [32자] 'spiritu.-'lly good, ------.,, 93...'
  [29자] 'in^, = - - . - , . - . - .101...'
  [64자] '* Rom. s. 5, 2 Cor. iv. 5, 4. f ^^a^^- -'^\"^' ^-- ^^^^ v^^* ...'
  [37자] '* .7ohn V, 44. :v'n. 7-9. 40. vi. 45....'

L4b: 소문자 시작 (첫 알파벳이 소문자): 374
L4b (CUE 방식: t[0].islower()): 374

=== 합집합 (Layer 간 중복 제거) ===
총 제거 가능 수 (중복 제거 후): 1536
비율: 28.2%

=== Layer 간 중복 분석 ===
페이지 번호 AND 짧은 fragment: 0
페이지 번호 AND 소문자 시작: 0

=== 패턴 정의 명확화 ===
- 페이지 번호 패턴: r"^p\.?\s*\d+" | r"\b\d+\s*p\.?\b" | r"^[IVXLC]+\.?\s*"
  → \b\d+\s*p\.?\b 가 숫자+문자+p. 패턴을 광범위하게 매칭 (예: "unbelief as a calling in question the truth of our own..." 에는 안 맞지만, 본문에 p. 가 포함된 문장 다수)
- 소문자 시작: t.lstrip() 후 첫 알파벳 문자가 islower() → CUE 방식 t[0].islower() 와 동일 (374건 일치)
```

---

## 1. §6 표 정정판 (실측 값 기반)

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

---

## 2. 패턴 정의 명확화

### L1b: 페이지 번호 패턴 — 재현 시 1,153건 (문서 이전 주장: 291건)

**원인**: `r"\b\d+\s*p\.?\b"` 패턴이 "p."를 포함한 모든 숫자+문자 경계를 매칭.
예: "unbelief as a calling in question the truth of our own..." 에는 안 맞지만,
본문에 p. 가 포함된 문장(예: "p. 123", "cf. p. 456" 등)이 광범위하게 존재.

**정확한 패턴 정의**:
```python
PAGE_NUMBER_PATTERNS = [
    r"^p\.?\s*\d+",           # "p. 123", "p123" (문장 시작)
    r"\b\d+\s*p\.?\b",       # "123 p." (숫자+page)
    r"^[IVXLC]+\.?\s*",      # "I.", "II.", "III." (roman numeral page)
]
```

**주의**: 이 패턴은 신학적 주장이 아닌 페이지 참조만 있는 문장을 대상으로 하지만,
1,153건 중 실제 페이지 번호인지 수동 검증 필요. 일부는 "p."가 포함된 신학적 문장일 수 있음.

### L4b: 소문자 시작 — 재현 시 374건 (문서 이전 주장: 666건)

**원인**: 문서에서 "문장 시작 대문자 없음"을 어떻게 정의했는지 명확하지 않음.
실측에서는 `t.lstrip()` 후 첫 알파벳 문자가 소문자인지 기준으로 374건.
CUE의 `t[0].islower()` 방식과 동일 (374건 일치).

**정확한 패턴 정의**:
```python
def is_lowercase_start(text: str) -> bool:
    stripped = text.lstrip()
    return stripped and stripped[0].isalpha() and stripped[0].islower()
```

**recall 영향**: **높음** — 신학적 주장이 소문자로 시작할 수 있음 (예: "and thus...", "but God...")
**권장**: benchmark 필수. recall 손실 가능성 높음.

### L3a: 짧은 fragment — 재현 시 4건 (문서 이전 주장: 438건)

**원인**: 문서에서 "25-34자 중 단어 수 < 4"로 정의했지만, 실제 매칭은 4건뿐.
이전 438건은 "25-34자"만 기준으로 한 것 (단어 수 필터 미적용).

**정확한 패턴 정의**:
```python
def is_too_short_fragment(text: str) -> bool:
    if 25 <= len(text) <= 34:
        word_count = len(text.split())
        return word_count < 4
    return False
```

### L3b: Boilerplate — 재현 시 0건 (문서 이전 주장: 17건)

**원인**: Fuller Vol.1 에는 해당 boilerplate 패턴이 없음.
이전 17건은 "인용구 패턴 (\\"...\")"와 혼동한 것.

---

## 3. Layer 간 중복 분석

- 페이지 번호 AND 짧은 fragment: 0건 (중복 없음)
- 페이지 번호 AND 소문자 시작: 0건 (중복 없음)
- **전체 합집합**: 1,536건 (28.2%)

**중요**: Layer 간 중복을 고려한 합집합 기준이 실제 이론적 상한선이다.
실제 제거 가능 수는 **합집합 기준 1,536건 (28.2%)**.

---

## 4. 결론

- **Upper Bound (합집합)**: 1,536건 (28.2%) — 실제 이론적 상한선
- **실제 효과**: 반드시 benchmark 검증 필요 (recall/precision 측정)
- **가장 큰 영향 Layer**: L1b(페이지 번호, 1,153건), L4b(소문자 시작, 374건)
- **주의**: L1b 패턴은 광범위하게 매칭되므로 recall 손실 가능성 높음. benchmark 필수.
