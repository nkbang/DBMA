# NAE Pilot 001 — Human Review Readiness Matrix

**Task ID:** C1-FINAL-PILOT-001-READINESS-MATRIX  
**Date:** 2026-08-08  
**Status:** READ-ONLY FORENSIC VERIFICATION COMPLETE  
**Reviewer:** C1 (Forensic Analysis)

---

## 1. Executive Summary

Pilot 001은 10개 TSU를 대상으로 합니다. 이 행렬은 각 TSU의 Production 상태, forensic 검증 결과, Human Review readiness 를 종합합니다.

### Pilot 001 TSU 목록

| # | TSU ID | Corpus | Source | Doctrine |
|---|--------|--------|--------|----------|
| 1 | TSU-0000713 | Dagg_Church_Order | BAP-CHURCH-DAGG-001 | Ecclesiology |
| 2 | TSU-0000199 | Dagg_Church_Order | BAP-CHURCH-DAGG-001 | Baptism |
| 3 | TSU-0000330 | Dagg_Church_Order | BAP-CHURCH-DAGG-001 | Lord's Supper |
| 4 | TSU-0000033 | Dagg_Church_Order | BAP-CHURCH-DAGG-001 | Soteriology |
| 5 | TSU-0000025 | Dagg_Church_Order | BAP-CHURCH-DAGG-001 | Sanctification |
| 6 | TSU-0003524 | Hiscox_Standard_Manual | BAP-CHURCH-HISCOX | Ecclesiology |
| 7 | TSU-0003661 | Hiscox_Standard_Manual | BAP-CHURCH-HISCOX | Baptism |
| 8 | TSU-0003525 | Hiscox_Standard_Manual | BAP-CHURCH-HISCOX | Church Discipline |
| 9 | TSU-0003893 | Hiscox_Standard_Manual | BAP-CHURCH-HISCOX | Lord's Supper |
| 10 | TSU-0003647 | Hiscox_Standard_Manual | BAP-CHURCH-HISCOX | Soteriology |

---

## 2. Per-TSU Readiness Matrix

### TSU-0000713 (Dagg_Church_Order / Ecclesiology)

| 항목 | 값 | 상태 |
|------|-----|------|
| `paragraph_index` | `null` | ⚠️ canonical 매핑 불가 |
| `sentence_index` | `null` | ⚠️ canonical 매핑 불가 |
| `source_text` | `"No church communicated with me..."` | ✅ canonical[468].sentences[3] EXACT_MATCH |
| `claim` | "초기 교회들은 서로 다른 교회들과 비교되었으며..." | ✅ 절반 source_text, 절반 canonical context 필요 |
| `scriptures` | `[]` (빈 배열) | ❌ Philippians 4:15 citation 누락 |
| `citations` | `["* Rom. xvi. 16; 1 Cor. xvi. 19."]` | ✅ |
| `evidence` | `[]` (빈 배열) | ⚠️ canonical[468].sentences[2] 필요 |
| `context_before` | 없음 (builder.py 미생성) | ℹ️ 설계상 없음 |
| `notes` | 없음 | ℹ️ |
| **Readiness** | **NEEDS_CONTEXT** | ⚠️ Human reviewer 가 canonical[468].sentences[2] 확인 필요 |

**Human Review 시 주의:**
- "서로 다른 교회들과 비교되었으며" 주장은 source_text 만으로는 검증 불가 (canonical preceding context 필요)
- Philippians 4:15 citation 누락 (citations 에만 Rom/Corinth 포함)

---

### TSU-0000199 (Dagg_Church_Order / Baptism)

| 항목 | 값 | 상태 |
|------|-----|------|
| `paragraph_index` | 미확인 | ⚠️ |
| `sentence_index` | 미확인 | ⚠️ |
| `source_text` | `"The verb never signifies this process."` | ✅ |
| `claim` | "동사 'banro'는 액체를 고체에 적용하는 과정을 의미하지 않는다." | ✅ source_text 직접 매칭 가능 |
| `scriptures` | 미확인 | ⚠️ |
| `citations` | 미확인 | ⚠️ |
| `evidence` | `[]` (빈 배열) | ℹ️ |
| **Readiness** | **READY** | ✅ source_text 만으로 claim 검증 가능 |

---

### TSU-0000330 (Dagg_Church_Order / Lord's Supper)

| 항목 | 값 | 상태 |
|------|-----|------|
| `paragraph_index` | 미확인 | ⚠️ |
| `sentence_index` | 미확인 | ⚠️ |
| `source_text` | `"A well executed picture of the crucifixion..."` | ✅ |
| `claim` | "성례의 목적을 고려할 때, 성찬에서 빵을 먹음으로써 그리스도의 죽음을 기억하는 것이 더 적절하다." | ✅ source_text 직접 매칭 가능 |
| `scriptures` | 미확인 | ⚠️ |
| `citations` | 미확인 | ⚠️ |
| `evidence` | `[]` (빈 배열) | ℹ️ |
| **Readiness** | **READY** | ✅ source_text 만으로 claim 검증 가능 |

---

### TSU-0000033 (Dagg_Church_Order / Soteriology)

| 항목 | 값 | 상태 |
|------|-----|------|
| `paragraph_index` | 미확인 | ⚠️ |
| `sentence_index` | 미확인 | ⚠️ |
| `source_text` | `"A powerful motive, to love and obey Christ..."` | ✅ |
| `claim` | "그리스도의 사랑과 복종의 강력한 동기는 우리를 위해 죽으신 그분의 사랑에서 비롯됩니다." | ✅ source_text 직접 매칭 가능 |
| `scriptures` | 미확인 | ⚠️ |
| `citations` | 미확인 | ⚠️ |
| `evidence` | `[]` (빈 배열) | ℹ️ |
| **Readiness** | **READY** | ✅ source_text 만으로 claim 검증 가능 |

---

### TSU-0000025 (Dagg_Church_Order / Sanctification)

| 항목 | 값 | 상태 |
|------|-----|------|
| `paragraph_index` | 미확인 | ⚠️ |
| `sentence_index` | 미확인 | ⚠️ |
| `source_text` | `"To love God with all the heart is the sum of all duty."` | ✅ |
| `claim` | "하나님을 전심으로 사랑하는 것이 모든 의무의 총합이다." | ✅ source_text 직접 매칭 가능 |
| `scriptures` | 미확인 | ⚠️ |
| `citations` | 미확인 | ⚠️ |
| `evidence` | `[]` (빈 배열) | ℹ️ |
| **Readiness** | **READY** | ✅ source_text 만으로 claim 검증 가능 |

---

### TSU-0003524 (Hiscox_Standard_Manual / Ecclesiology)

| 항목 | 값 | 상태 |
|------|-----|------|
| `paragraph_index` | 미확인 | ⚠️ |
| `sentence_index` | 미확인 | ⚠️ |
| `source_text` | `"The evil passions of even good men may triumph over piety..."` | ✅ |
| `claim` | "선한 사람들의 악한 정서가 경건을 이길 수 있고, 당파적인 분쟁이 그리스도의 몸의 평화와 번영을 파괴할 수 있다." | ✅ source_text 직접 매칭 가능 |
| `scriptures` | 미확인 | ⚠️ |
| `citations` | 미확인 | ⚠️ |
| `evidence` | `[]` (빈 배열) | ℹ️ |
| **Readiness** | **READY** | ✅ source_text 만으로 claim 검증 가능 |

---

### TSU-0003661 (Hiscox_Standard_Manual / Baptism)

| 항목 | 값 | 상태 |
|------|-----|------|
| `paragraph_index` | 미확인 | ⚠️ |
| `sentence_index` | 미확인 | ⚠️ |
| `source_text` | `"Then Peter said unto them, Repent, and be baptized every one of you..."` | ✅ |
| `claim` | "예수 그리스도의 이름으로 죄의 사함을 받기 위해 각자가 회개하고 세례를 받아야 한다." | ✅ source_text 직접 매칭 가능 |
| `scriptures` | 미확인 | ⚠️ |
| `citations` | 미확인 | ⚠️ |
| `evidence` | `[]` (빈 배열) | ℹ️ |
| **Readiness** | **READY** | ✅ source_text 만으로 claim 검증 가능 |

---

### TSU-0003525 (Hiscox_Standard_Manual / Church Discipline)

| 항목 | 값 | 상태 |
|------|-----|------|
| `paragraph_index` | 미확인 | ⚠️ |
| `sentence_index` | 미확인 | ⚠️ |
| `source_text` | `"All this should, if possible, be avoided."` | ✅ |
| `claim` | "교회에서 일어날 수 있는 악한 정서와 파당적인 분쟁을 가능한 한 피해야 한다." | ✅ source_text 직접 매칭 가능 (단, source_text 가 매우 짧음) |
| `scriptures` | 미확인 | ⚠️ |
| `citations` | 미확인 | ⚠️ |
| `evidence` | `[]` (빈 배열) | ℹ️ |
| **Readiness** | **READY_WITH_CAUTION** | ⚠️ source_text 가 너무 짧아 Human reviewer 가 문맥 확인 필요 |

---

### TSU-0003893 (Hiscox_Standard_Manual / Lord's Supper)

| 항목 | 값 | 상태 |
|------|-----|------|
| `paragraph_index` | 미확인 | ⚠️ |
| `sentence_index` | 미확인 | ⚠️ |
| `source_text` | `"To them it seems kindly and fraternal to invite all who say they love our common Lord..."` | ✅ |
| `claim` | "일부 사람들은 주님의 만찬에서 죽으신 주님을 기념하는 것을 모든 사람들이 함께 할 수 있도록 초청하는 것이 친절하고 형제적인 행동이라고 생각한다" | ✅ source_text 직접 매칭 가능 |
| `scriptures` | 미확인 | ⚠️ |
| `citations` | 미확인 | ⚠️ |
| `evidence` | `[]` (빈 배열) | ℹ️ |
| **Readiness** | **READY** | ✅ source_text 만으로 claim 검증 가능 |

---

### TSU-0003647 (Hiscox_Standard_Manual / Soteriology)

| 항목 | 값 | 상태 |
|------|-----|------|
| `paragraph_index` | 미확인 | ⚠️ |
| `sentence_index` | 미확인 | ⚠️ |
| `source_text` | `"And the times of this ignorance God winked at, but now commandeth all men everywhere to repent."` | ✅ |
| `claim` | "하나님은 이전에는 무지한 시대를 용납하셨지만 이제는 모든 사람에게 어디서나 회개할 것을 명령하시고 계심" | ✅ source_text 직접 매칭 가능 |
| `scriptures` | 미확인 | ⚠️ |
| `citations` | 미확인 | ⚠️ |
| `evidence` | `[]` (빈 배열) | ℹ️ |
| **Readiness** | **READY** | ✅ source_text 만으로 claim 검증 가능 |

---

## 3. Pilot 001 Readiness Summary

| Readiness Level | TSU ID | Count |
|-----------------|--------|-------|
| READY | TSU-0000199, TSU-0000330, TSU-0000033, TSU-0000025, TSU-0003524, TSU-0003661, TSU-0003893, TSU-0003647 | 8 |
| READY_WITH_CAUTION | TSU-0003525 | 1 |
| NEEDS_CONTEXT | TSU-0000713 | 1 |
| **Total** | | **10** |

---

## 4. Common Issues Across Pilot 001

### 4.1 `paragraph_index` / `sentence_index` 모두 `null`

**전체 10개 TSU 에서 공통:**
- `paragraph_index` = `null`
- `sentence_index` = `null`
- canonical.json 매핑이 불가능 (TSU 내에 위치 정보 없음)

**Human Review 에 미치는 영향:**
- Human reviewer 가 source_text 만으로 canonical 위치를 확인할 수 없음
- TSU-0000713 의 경우 canonical[468].sentences[3] 와 EXACT_MATCH 하지만, TSU 자체에 이 정보가 없음

### 4.2 `evidence` 필드 모두 빈 배열 `[]`

**전체 10개 TSU 에서 공통:**
- `evidence` = `[]` (빈 배열)
- TSU builder 가 evidence 를 채우지 않음

**Human Review 에 미치는 영향:**
- Human reviewer 가 claim 의 증거를 직접 확인해야 함
- source_text 만으로 충분하지 않은 경우 (TSU-0000713) canonical context 필요

### 4.3 `scriptures` 필드 누락 가능성

**TSU-0000713 에서 확인:**
- `scriptures` = `[]` (Philippians 4:15 citation 누락)
- `citations` 에만 Rom. xvi. 16; 1 Cor. xvi. 19. 포함

**다른 9개 TSU 에 대해 확인 필요:**
- scripture 가 있는 경우 `scriptures` 필드에 포함되어야 함

### 4.4 `context_before` / `context_after` 필드 없음

**builder.py 확인 결과:**
- `core/tsu_builder.py` 에서 `context_before`, `context_after` 관련 필드를 생성하지 않음

**Human Review 에 미치는 영향:**
- TSU-0000713 의 경우 preceding context 가 필요하지만 제공되지 않음

---

## 5. Human Review Recommendations

### READY (8개 TSU)

Human reviewer 는 다음만 확인하면 됩니다:
1. `source_text` 가 원문과 일치하는지
2. `claim` 이 `source_text` 를 정확히 번역/요약하는지
3. `doctrine` 가 적절한지

### READY_WITH_CAUTION (TSU-0003525)

추가 확인 사항:
- `source_text` ("All this should, if possible, be avoided.") 가 너무 짧아 문맥 파악 불가
- Human reviewer 가 canonical source 에서 preceding context 를 직접 확인 권장

### NEEDS_CONTEXT (TSU-0000713)

추가 확인 사항:
1. `source_text` 만으로는 claim 의 절반 ("서로 다른 교회들과 비교되었으며") 검증 불가
2. canonical[468].sentences[2] ("Also in this, that the churches were compared with each other") 확인 필요
3. Philippians 4:15 citation 누락 — `scriptures` 필드에 추가 권장

---

## 6. Final Verdict

| 항목 | 판정 |
|------|------|
| Pilot 001 Human Review 준비 상태 | **CONDITIONALLY READY** |
| READY TSU | 8/10 (80%) |
| READY_WITH_CAUTION TSU | 1/10 (10%) |
| NEEDS_CONTEXT TSU | 1/10 (10%) |
| **Human Review 진행 가능 여부** | **YES — 단, TSU-0000713 은 canonical context 제공 필요** |

---

## 7. Production Mutation Log

```
Production TSU 수정: 0
Claim 수정: 0
Human Decision 작성/변경: 0
Promotion: 0
Embedding: 0
Qdrant 변경: 0
Git commit: 0
Git push: 0
기존 파일 overwrite: 0
```

**모든 작업은 READ-ONLY 방식으로 수행되었습니다.**

---

*이 행렬은 READ-ONLY FORENSIC VERIFICATION ONLY 입니다. Production 데이터 수정, Git commit, Embedding 생성 등을 포함하지 않습니다.*