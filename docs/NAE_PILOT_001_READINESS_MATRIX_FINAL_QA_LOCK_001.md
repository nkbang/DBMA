# NAE Pilot 001 — Readiness Matrix Final QA Lock

**Task ID:** CUE-FINAL-QA-PILOT-001-READINESS-MATRIX-LOCK
**작성일:** 2026-08-08
**성격:** READ-ONLY FORENSIC VERIFICATION. Production 최종 잠금 전 검증.
**Authoritative Field:** `paragraph`(NOT `paragraph_index`), `sentence`(NOT `sentence_index`)
**대상:** `docs/NAE_PILOT_001_HUMAN_REVIEW_READINESS_MATRIX_CORRECTED_001.md`
**Git Commit/Push:** 미수행.

---

## 1. Production Field 직접 조회(정확한 키 `paragraph`/`sentence` 사용)

| TSU ID | Production paragraph | Production sentence | Expected paragraph | Expected sentence | Match |
|---|---|---|---|---|---|
| TSU-0000713 | 468 | 3 | 468 | 3 | ✅ EXACT |
| TSU-0000199 | 222 | 6 | 222 | 6 | ✅ EXACT |
| TSU-0000330 | 284 | 1 | 284 | 1 | ✅ EXACT |
| TSU-0000033 | 66 | 0 | 66 | 0 | ✅ EXACT |
| TSU-0000025 | 64 | 0 | 64 | 0 | ✅ EXACT |
| TSU-0003524 | 132 | 1 | 132 | 1 | ✅ EXACT |
| TSU-0003661 | 362 | 3 | 362 | 3 | ✅ EXACT |
| TSU-0003525 | 132 | 2 | 132 | 2 | ✅ EXACT |
| TSU-0003893 | 620 | 2 | 620 | 2 | ✅ EXACT |
| TSU-0003647 | 347 | 1 | 347 | 1 | ✅ EXACT |

**10/10 EXACT MATCH.**

---

## 2/3. Canonical Source Mapping + Match 판정

| TSU ID | Canonical Source Match |
|---|---|
| TSU-0000713 | EXACT_MATCH |
| TSU-0000199 | EXACT_MATCH |
| TSU-0000330 | EXACT_MATCH |
| TSU-0000033 | EXACT_MATCH |
| TSU-0000025 | EXACT_MATCH |
| TSU-0003524 | EXACT_MATCH |
| TSU-0003661 | EXACT_MATCH |
| TSU-0003525 | EXACT_MATCH |
| TSU-0003893 | EXACT_MATCH |
| TSU-0003647 | EXACT_MATCH |

각 TSU의 `record["paragraph"]`/`record["sentence"]`로 해당 book의
`canonical.json`을 조회해 `paragraphs[index=paragraph].sentences[sentence].text`
를 `record["source_text"]`와 문자열 비교. **10/10 EXACT_MATCH**(공백/
정규화 조정 없이 완전 일치).

---

## 4. Readiness 비교(C1 원본 vs CUE 정정본 vs Production Evidence)

| TSU ID | C1 원본 Readiness | CUE 정정본 Readiness(=검증 대상) | Production Evidence 근거 | Agreement |
|---|---|---|---|---|
| TSU-0000713 | NEEDS_CONTEXT | NEEDS_CONTEXT | claim의 "비교되었으며" 절이 canonical[468].sentences[2]에서만 확인됨(대상 문장=sentences[3]에는 없음) | ✅ CUE=Evidence 일치 |
| TSU-0000199 | READY | NEEDS_CONTEXT | "this process"(대상 문장=sentences[6])가 가리키는 대상이 canonical[222].sentences[5] 이전 문맥("liquid to the solid")에만 있음 | ✅ CUE=Evidence 일치, C1 원본과 불일치(원본 오류) |
| TSU-0000330 | READY | READY_FOR_HUMAN_REVIEW | 대상 문장(canonical[284].sentences[1]) 자체에 claim 내용이 완전히 포함됨 | ✅ 전원 일치 |
| TSU-0000033 | READY | READY_FOR_HUMAN_REVIEW | 대상 문장과 claim이 1:1 대응, 자기완결적 | ✅ 전원 일치 |
| TSU-0000025 | READY | READY_FOR_HUMAN_REVIEW | 대상 문장과 claim이 1:1 대응, 자기완결적(단 Q4 SCRIPTURE_MISMATCH 권고) | ✅ 전원 일치 |
| TSU-0003524 | READY | READY_FOR_HUMAN_REVIEW | 대상 문장과 claim이 1:1 대응, 자기완결적 | ✅ 전원 일치 |
| TSU-0003661 | READY | READY_FOR_HUMAN_REVIEW | 대상 문장(사도행전 2:38 직접 인용) 자체가 자기완결적(단 Q4 필수 플래그) | ✅ 전원 일치 |
| TSU-0003525 | READY_WITH_CAUTION(비표준 값) | NEEDS_CONTEXT | "All this"(대상 문장=canonical[132].sentences[2])가 가리키는 내용이 canonical[132].sentences[1](=TSU-0003524)에만 있음 | ✅ CUE=Evidence 일치, C1 원본과 불일치(원본 오류 — 비표준 값 사용) |
| TSU-0003893 | READY | READY_FOR_HUMAN_REVIEW | 대상 문장(canonical[620].sentences[2]) 자체로 claim 판단 가능, 화자("them") 구분도 claim에 정확히 보존됨(Q4 AMBIGUOUS 플래그 필수) | ✅ 전원 일치 |
| TSU-0003647 | READY | READY_FOR_HUMAN_REVIEW | 대상 문장(사도행전 17:30 직접 인용) 자체가 자기완결적(단 Q4 권고) | ✅ 전원 일치 |

### 지정 4건 개별 재확인(작업 명령서 §4 명시)

```
TSU-0000199 = NEEDS_CONTEXT  → CUE 정정본과 일치, Production evidence로 재확인됨
TSU-0003525 = NEEDS_CONTEXT  → CUE 정정본과 일치, Production evidence로 재확인됨
TSU-0000713 = NEEDS_CONTEXT  → CUE 정정본과 일치, Production evidence로 재확인됨
TSU-0003893 = READY_FOR_HUMAN_REVIEW → CUE 정정본과 일치, Production evidence로 재확인됨
```

---

## 5. Paragraph/Sentence Key Naming 근본 원인(최종 정리)

이전 혼선의 원인은 **존재하지 않는 키 이름 조회**였다:

```
record.get("paragraph_index")  -> None(항상, 키가 존재하지 않으므로)
record.get("paragraph")        -> 실제 값(예: 468)
```

TSU 레코드에는 `paragraph_index`/`sentence_index`라는 키가 **애초에
존재하지 않는다** — 정확한 필드명은 `paragraph`/`sentence`이다. 이번
검증은 작업 명령서가 명시한 authoritative field(`paragraph`/
`sentence`)만 사용했으며, 10/10 EXACT MATCH로 확인됐다.

---

## 6. 완료 보고

```
TSU ID | Production paragraph | Production sentence | Expected paragraph | Expected sentence | Match | Canonical source match | C1 readiness | CUE verified readiness | Agreement
TSU-0000713 | 468 | 3 | 468 | 3 | EXACT | EXACT_MATCH | NEEDS_CONTEXT   | NEEDS_CONTEXT           | AGREE
TSU-0000199 | 222 | 6 | 222 | 6 | EXACT | EXACT_MATCH | READY           | NEEDS_CONTEXT           | C1 원본과 불일치(CUE 정정본이 맞음)
TSU-0000330 | 284 | 1 | 284 | 1 | EXACT | EXACT_MATCH | READY           | READY_FOR_HUMAN_REVIEW  | AGREE
TSU-0000033 | 66  | 0 | 66  | 0 | EXACT | EXACT_MATCH | READY           | READY_FOR_HUMAN_REVIEW  | AGREE
TSU-0000025 | 64  | 0 | 64  | 0 | EXACT | EXACT_MATCH | READY           | READY_FOR_HUMAN_REVIEW  | AGREE
TSU-0003524 | 132 | 1 | 132 | 1 | EXACT | EXACT_MATCH | READY           | READY_FOR_HUMAN_REVIEW  | AGREE
TSU-0003661 | 362 | 3 | 362 | 3 | EXACT | EXACT_MATCH | READY           | READY_FOR_HUMAN_REVIEW  | AGREE
TSU-0003525 | 132 | 2 | 132 | 2 | EXACT | EXACT_MATCH | READY_WITH_CAUTION(비표준) | NEEDS_CONTEXT | C1 원본과 불일치(CUE 정정본이 맞음)
TSU-0003893 | 620 | 2 | 620 | 2 | EXACT | EXACT_MATCH | READY           | READY_FOR_HUMAN_REVIEW  | AGREE
TSU-0003647 | 347 | 1 | 347 | 1 | EXACT | EXACT_MATCH | READY           | READY_FOR_HUMAN_REVIEW  | AGREE
```

**Production paragraph/sentence field 10/10 EXACT MATCH.**
**Canonical source mapping 10/10 EXACT_MATCH.**
**CUE 정정본(`..._CORRECTED_001.md`)의 readiness 10/10이 Production
evidence로 재확인됨.**
**C1 원본(`..._MATRIX.md`)은 2건(TSU-0000199, TSU-0003525)에서
Production evidence와 불일치 — 정정본이 최종본으로 확정되어야 함.**

---

## 7. 결론

```
FINAL MATRIX STATUS = VERIFIED

(CUE 정정본 docs/NAE_PILOT_001_HUMAN_REVIEW_READINESS_MATRIX_CORRECTED_001.md
 기준으로 VERIFIED. C1 원본 docs/NAE_PILOT_001_HUMAN_REVIEW_READINESS_MATRIX.md
 기준으로는 2건 불일치로 DISCREPANCIES_FOUND — 원본은 최종본으로 사용하지 않음.)
```

---

## Safety

```
Production mutation = 0
Claim mutation = 0
Human Decision = 0
Promotion = 0
Embedding = 0
Qdrant = 0
Git commit/push = 0
```

READ-ONLY FORENSIC VERIFICATION ONLY.
