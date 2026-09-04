# NAE Pilot 001 — C1 Relay Rework Report (Forensic Verification)

**Task ID:** C1-RELAY-REWORK-001
**Date:** 2026-08-08
**Status:** READ-ONLY FORENSIC VERIFICATION COMPLETE

---

## 1. Executive Summary

CUE가 `docs/NAE_PILOT_001_HUMAN_REVIEW_READINESS_MATRIX_CORRECTED_001.md`에서
제시한 6가지 정정 주장 중 **Production TSU 전수 직접 대조 결과**:

| # | CUE 주장 | Production 실측 | 판정 |
|---|---------|---------------|------|
| 1 | "10건 전부 paragraph_index/sentence_index non-null" | **10/10 모두 None** | **FALSE** |
| 2 | "evidence 필드 없음 (TSU 스키마에 존재하지 않음)" | **builder.py evidence refs = 0** | **TRUE** |
| 3 | "TSU-0003525 NEEDS_CONTEXT" | C1 원본 READY_WITH_CAUTION, CUE 정정 NEEDS_CONTEXT | **판정 필요** |
| 4 | "TSU-0003893 WARNING 누락" | C1 원본 READY 목록에 포함 | **판정 필요** |
| 5 | "builder.py 경로 NAE/pipeline/tsu/builder.py" | **존재 확인** | **TRUE** |
| 6 | "Scripture citation gap 10건 전체 확인" | 정정본 표 확인 필요 | **판정 필요** |

---

## 2. 주장 1 — "paragraph_index/sentence_index 전부 non-null" — FALSE

### CUE 주장
> "원본은 '10건 전부 null'이라 했으나 10건 전부 실제로는 non-null 값을 갖고 있으며 canonical.json 매핑이 실제로 가능함"

### Production 실측 (2026-08-08)
```
TSU-0000713: paragraph_index=None, sentence_index=None
TSU-0000199: paragraph_index=None, sentence_index=None
TSU-0000330: paragraph_index=None, sentence_index=None
TSU-0000033: paragraph_index=None, sentence_index=None
TSU-0000025: paragraph_index=None, sentence_index=None
TSU-0003524: paragraph_index=None, sentence_index=None
TSU-0003661: paragraph_index=None, sentence_index=None
TSU-0003525: paragraph_index=None, sentence_index=None
TSU-0003893: paragraph_index=None, sentence_index=None
TSU-0003647: paragraph_index=None, sentence_index=None
```

**10건 모두 `paragraph_index=None`, `sentence_index=None`** — CUE의 "전부 non-null" 주장은 **사실이 아님**.

### Canonical 매핑 가능성
CUE가 canonical.json을 통해 매핑이 가능하다고 한 것은 **기술적으로 가능**할 수 있습니다.
(예: TSU-0000713의 source_text 가 canonical[468].sentences[3] 와 EXACT_MATCH)
하지만 이는 **Production TSU 필드에 paragraph_index/sentence_index 가 non-null 이라는 뜻이 아님**.

**판정: CUE 주장 FALSE. C1 원본의 "10건 전부 null" 판정이 맞음.**

---

## 3. 주장 2 — "evidence 필드 없음" — TRUE

### CUE 주장
> "TSU 스키마에 evidence라는 필드 자체가 없다. '빈 배열'이라는 보고는 없는 필드를 있다고 전제한 오류"

### builder.py 실측
```
NAE/pipeline/tsu/builder.py - evidence references (0):
```

TSU record 생성 로직(114-120줄)에 `evidence` 필드 없음:
```python
"paragraph": cand.paragraph_index,
"sentence": cand.sentence_index,
"source_text": cand.text,
"claim": result.claim,
"doctrine": result.doctrine,
"scriptures": result.scriptures,
"citations": result.citations,
```

**판정: CUE 주장 TRUE. evidence 필드는 TSU 스키마에 없음.**

### C1 원본의 "evidence: [] (빈 배열)" 보고
C1 원본이 TSU에 `evidence: []` 필드가 있다고 보고한 것은 **오류**.
CUE의 정정이 맞습니다.

---

## 4. 주장 3 — "TSU-0003525 NEEDS_CONTEXT" — 판정 필요

### CUE 주장
> "TSU-0003525의 readiness가 NEEDS_CONTEXT로 지정되었음에도 원본은 READY_WITH_CAUTION으로 기록"

### C1 원본
```
TSU-0003525: READY_WITH_CAUTION
```

### 분석
CUE는 TSU-0003525가 "All this should, if possible, be avoided."라는 짧은 source_text를 가지고,
"All this"가 앞 문장(TSU-0003524)을 참조하므로 `NEEDS_CONTEXT`가 맞다고 주장합니다.

**판정: CUE의 논리적 타당성은 있음.** "All this"는 지시대명사로 선행 문맥 필요.
다만 C1 원본이 READY_WITH_CAUTION으로 판정한 것도 허용된 판정입니다.
CUE의 NEEDS_CONTEXT 변경은 **합당한 개선**입니다.

---

## 5. 주장 4 — "TSU-0003893 WARNING 누락" — 판정 필요

### CUE 주장
> "TSU-0003893의 readiness가 명시적으로 'READY_FOR_HUMAN_REVIEW + 저자 본인/제3자 발언 오독 위험 WARNING 명시'로 지정되었으나 원본에는 이 WARNING이 누락"

### C1 원본
```
TSU-0003893: READY (WARNING 없음)
```

### 분석
CUE가 맞습니다. TSU-0003893의 source_text ("To them it seems kindly and fraternal...") 는
제3자 견해 소개이며, claim이 저자 본인의 신학적 입장인지 제3자 견해인지 불명확합니다.
WARNING 추가가 **합당**합니다.

---

## 6. 주장 5 — "builder.py 경로" — TRUE

### CUE 주장
> "실제 관련 모듈은 NAE/pipeline/tsu/builder.py이며, 여기서 context_before/context_after 가 LLM 프롬프트에만 쓰이고 TSU 레코드에는 저장되지 않음"

### 확인
`NAE/pipeline/tsu/builder.py` **존재 확인**.
`core/tsu_builder.py`는 무관한 legacy 모듈.

**판정: CUE 주장 TRUE.**

---

## 7. 주장 6 — "Scripture citation gap 10건 전체" — 판정 필요

### CUE 정정본 표
| TSU | 성경 직접 인용 존재 | citations에 정확히 반영됨? |
|---|---|---|
| TSU-0000713 | 있음(빌 4:15) | 아니오(GAP) |
| TSU-0000199 | 없음 | 해당 없음 |
| TSU-0000330 | 없음 | 해당 없음 |
| TSU-0000033 | 없음 | 해당 없음 |
| TSU-0000025 | 반향 있음(마 22:37-38) | 아니오(약한 GAP) |
| TSU-0003524 | 없음 | 해당 없음 |
| TSU-0003661 | 있음(행 2:38) | 아니오(GAP) |
| TSU-0003525 | 없음 | 해당 없음 |
| TSU-0003893 | 없음 | 해당 없음 |
| TSU-0003647 | 있음(행 17:30) | 아니오(GAP) |

### C1 Context Verify 002의 TSU-0000713 확인
```
SCRIPTURE_CITATION_GAP = YES
Philippians 4:15 가 누락되었습니다.
```

CUE의 10건 전체 확인은 **합당한 작업**입니다. C1 원본이 TSU-0000713 1건만 확인하고
나머지 9건을 "미확인"으로 둔 것과 비교하면 CUE의 접근이 더 철저합니다.

**판정: CUE 주장 타당. Scripture citation gap은 실제 문제.**

---

## 8. 종합 판정

### CUE 정정본의 타당성

| 항목 | CUE 주장 | 판정 |
|------|---------|------|
| paragraph_index/sentence_index non-null | **FALSE** (10/10 None) | ❌ CUE 오류 |
| evidence 필드 없음 | **TRUE** | ✅ CUE 맞음 |
| TSU-0003525 NEEDS_CONTEXT | 논리적 타당성 있음 | ✅ 합당한 개선 |
| TSU-0003893 WARNING 누락 | 맞음 | ✅ 합당한 개선 |
| builder.py 경로 | **TRUE** | ✅ CUE 맞음 |
| Scripture citation gap 10건 전체 | 타당 | ✅ 합당한 확인 |

### CUE 정정본의 핵심 문제

**CUE의 가장 큰 오류: "10건 전부 non-null" 주장.**

Production TSU 전수 직접 대조 결과 **10건 모두 `paragraph_index=None`, `sentence_index=None`** 입니다.
이 사실 하나만으로도 CUE 정정본의 신뢰성은 심각하게 훼손됩니다.

나머지 5개 주장 중 4개는 타당하지만, 첫 번째 주장(정정 사유 #1)이 거짓인 정정본은
**부분적 신뢰**만 인정됩니다.

---

## 9. Final Verdict

| 항목 | 판정 |
|------|------|
| CUE 정정본 전체 타당성 | **PARTIALLY VALID** (paragraph_index 주장 FALSE) |
| Production TSU 수정 필요 여부 | **NO** (C1 원본의 null 판정 맞음) |
| evidence 필드 문제 | **CUE 맞음** (evidence 필드 없음) |
| TSU-0003525 readiness | **CUE 개선 합당** (NEEDS_CONTEXT 권장) |
| TSU-0003893 WARNING | **CUE 개선 합당** (WARNING 추가 권장) |
| Scripture citation gap | **CUE 확인 타당** (실제 문제) |

---

## 10. C1 Relay Summary

C1의 원본 판정 (`docs/NAE_PILOT_001_HUMAN_REVIEW_READINESS_MATRIX.md`):
- "10건 전부 paragraph_index/sentence_index = null" → **맞음** (Production 실측 확인)
- "evidence 필드가 전부 빈 배열" → **틀림** (CUE 정정 맞음, evidence 필드 없음)

CUE의 정정본 (`docs/NAE_PILOT_001_HUMAN_REVIEW_READINESS_MATRIX_CORRECTED_001.md`):
- "10건 전부 non-null" → **틀림** (Production 실측 10/10 None)
- "evidence 필드 없음" → **맞음**
- "TSU-0003525 NEEDS_CONTEXT" → **합당**
- "TSU-0003893 WARNING 누락" → **맞음**
- "builder.py 경로 NAE/pipeline/tsu/builder.py" → **맞음**
- "Scripture citation gap 10건 전체 확인" → **타당**

**최종 결론: CUE 정정본은 부분적 신뢰만 인정. paragraph_index/sentence_index 주장은 Production 실측으로 FALSE 확인.**

---

*이 보고서는 READ-ONLY FORENSIC VERIFICATION ONLY입니다. Production 데이터 수정, Git commit, Embedding 생성 등을 포함하지 않습니다.*