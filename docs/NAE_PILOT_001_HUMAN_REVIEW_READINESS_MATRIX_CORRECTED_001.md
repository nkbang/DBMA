> **정정 안내(CUE, 2026-08-08):** 이 문서는
> `docs/NAE_PILOT_001_HUMAN_REVIEW_READINESS_MATRIX.md`(C1 작성)를
> Production TSU 전수 직접 대조로 재검증한 정정본이다. 원본을 덮어쓰지
> 않고 별도 파일로 저장했다.
>
> **정정 사유(전부 실측 확인):**
> 1. 원본은 "10건 전부 `paragraph_index`/`sentence_index` = null,
>    canonical 매핑 불가능"이라 했으나 **10건 전부 실제로는 non-null
>    값을 갖고 있으며 canonical.json 매핑이 실제로 가능함**(아래 표).
> 2. 원본은 "`evidence` 필드가 전부 빈 배열"이라 했으나, TSU 스키마에
>    **`evidence`라는 필드 자체가 존재하지 않는다**(35개 실제 필드
>    전수 확인, 없는 필드를 "빈 배열"로 보고한 오류).
> 3. TSU-0003525의 readiness가 이전 작업 명령서에서 명시적으로
>    `NEEDS_CONTEXT`로 지정되었음에도 원본은 `READY_WITH_CAUTION`(허용된
>    4개 값 — `READY_FOR_HUMAN_REVIEW`/`NEEDS_CONTEXT`/
>    `NEEDS_SOURCE_CORRECTION`/`NEEDS_CLAIM_REVIEW` — 에 없는 임의
>    5번째 값)으로 기록해 정정.
> 4. TSU-0003893의 readiness가 명시적으로 "READY_FOR_HUMAN_REVIEW +
>    저자 본인/제3자 발언 오독 위험 WARNING 명시"로 지정되었으나
>    원본에는 이 WARNING이 누락되어 정정.
> 5. §4.4에서 `core/tsu_builder.py`(무관한 legacy TSU v1 모듈)를 확인
>    대상으로 삼은 오류 — 실제 관련 모듈은
>    `NAE/pipeline/tsu/builder.py`이며, 여기서 `context_before`/
>    `context_after`가 LLM 프롬프트에만 쓰이고 TSU 레코드에는
>    저장되지 않음을 재확인.
> 6. Scripture citation gap을 10건 전체에 대해 독립적으로 재확인(원본은
>    TSU-0000713 1건만 확인, 나머지 9건 "미확인"으로 남김).
>
> readiness 어휘는 원 지시대로 `READY_FOR_HUMAN_REVIEW` /
> `NEEDS_CONTEXT` / `NEEDS_SOURCE_CORRECTION` / `NEEDS_CLAIM_REVIEW`
> 4개만 사용했다. Human Decision(A/R/C, APPROVE/CONDITIONAL/REJECT)은
> 작성하지 않았다.

---

# NAE Pilot 001 — Human Review Readiness Matrix(정정본)

**Task ID:** C1-FINAL-PILOT-001-READINESS-MATRIX(CUE 정정)
**Date:** 2026-08-08
**Status:** READ-ONLY FORENSIC VERIFICATION COMPLETE(Production 전수 직접 대조)

---

## 1. Pilot 001 TSU 목록 + 실제 Production 위치 정보

| # | TSU ID | Corpus | Doctrine | paragraph | sentence | canonical 매핑 |
|---|---|---|---|---|---|---|
| 1 | TSU-0000713 | Dagg_Church_Order | Ecclesiology | 468 | 3 | 가능(확인됨) |
| 2 | TSU-0000199 | Dagg_Church_Order | Baptism | 222 | 6 | 가능(확인됨) |
| 3 | TSU-0000330 | Dagg_Church_Order | Lord's Supper | 284 | 1 | 가능(확인됨) |
| 4 | TSU-0000033 | Dagg_Church_Order | Soteriology | 66 | 0 | 가능(확인됨) |
| 5 | TSU-0000025 | Dagg_Church_Order | Sanctification | 64 | 0 | 가능(확인됨) |
| 6 | TSU-0003524 | Hiscox_Standard_Manual | Ecclesiology | 132 | 1 | 가능(확인됨) |
| 7 | TSU-0003661 | Hiscox_Standard_Manual | Baptism | 362 | 3 | 가능(확인됨) |
| 8 | TSU-0003525 | Hiscox_Standard_Manual | Church Discipline | 132 | 2 | 가능(확인됨, TSU-0003524와 같은 문단) |
| 9 | TSU-0003893 | Hiscox_Standard_Manual | Lord's Supper | 620 | 2 | 가능(확인됨) |
| 10 | TSU-0003647 | Hiscox_Standard_Manual | Soteriology | 347 | 1 | 가능(확인됨) |

---

## 2. Per-TSU Readiness Matrix(정정)

### TSU-0000713 (Ecclesiology)

```
source_text integrity: canonical[468].sentences[3]와 EXACT_MATCH(확인됨)
claim integrity: 절반은 source_text 자체 지지, 절반("비교되었으며")은
                 canonical[468].sentences[2] 필요
context sufficiency: 불충분 — 선행 문맥 필요
scripture/citation gap: 빌립보서 4:15 인용이 citations/scriptures 어디에도
                        없음(citations=["* Rom. xvi. 16; 1 Cor. xvi. 19."]는
                        salutations 절에만 대응) — GAP=YES
special warning: SCRIPTURE_MISMATCH, CONTEXT_LOSS
```
**Readiness: NEEDS_CONTEXT**(수차례 재검증으로 확정)

### TSU-0000199 (Baptism)

```
source_text integrity: 정상(canonical paragraph=222, sentence=6과 일치)
claim integrity: "this process"가 무엇을 가리키는지는 context_before
                 ("an application of the liquid to the solid")를 봐야 확정
context sufficiency: 불충분 — 선행 문맥 필요
scripture/citation gap: citations=['2. Barro appears, in some cases, to be
                        used in the secondary'](언어학 각주, 성경 아님),
                        scriptures=[] — 해당 없음(성경 인용 자체가 아님)
special warning: AMBIGUOUS(citation 각주가 문장 중간에서 잘림)
```
**Readiness: NEEDS_CONTEXT**

### TSU-0000330 (Lord's Supper)

```
source_text integrity: 정상(canonical paragraph=284, sentence=1과 일치)
claim integrity: source_text 자체에 "we should keep Christ's death in
                 memory... by the eating of bread"가 명시적으로 포함,
                 claim과 직접 대응
context sufficiency: 충분 — 자기완결적
scripture/citation gap: citations=[], scriptures=[] — 해당 없음(신학
                        논증 문장, 성경 직접 인용 아님)
special warning: NO_OBJECTION
```
**Readiness: READY_FOR_HUMAN_REVIEW**

### TSU-0000033 (Soteriology)

```
source_text integrity: 정상(canonical paragraph=66, sentence=0과 일치)
claim integrity: source_text와 거의 1:1 대응
context sufficiency: 충분 — 자기완결적
scripture/citation gap: citations=[], scriptures=[] — 해당 없음
special warning: NO_OBJECTION
```
**Readiness: READY_FOR_HUMAN_REVIEW**

### TSU-0000025 (Sanctification)

```
source_text integrity: 정상(canonical paragraph=64, sentence=0과 일치)
claim integrity: source_text와 거의 1:1 대응("To love God with all the
                 heart is the sum of all duty.")
context sufficiency: 충분 — 자기완결적(단, 마태복음 22:37-38 대계명의
                     명백한 반향이나 원문 자체가 직접 인용 표기를 하지
                     않음)
scripture/citation gap: citations=[], scriptures=[] — 대계명 반향이
                        인용으로 명시되어 있지 않아 GAP 가능성 있음(WARNING)
special warning: SCRIPTURE_MISMATCH(대계명 반향 미인용)
```
**Readiness: READY_FOR_HUMAN_REVIEW**(Q4 SCRIPTURE_MISMATCH 플래그 권고)

### TSU-0003524 (Ecclesiology)

```
source_text integrity: 정상(canonical paragraph=132, sentence=1과 일치)
claim integrity: source_text와 거의 1:1 대응
context sufficiency: 충분 — 자기완결적. 단, 다음 TSU-0003525(paragraph=132,
                     sentence=2)와 원문상 바로 인접한 문장 — 함께 검토 권고
scripture/citation gap: citations=['5. Because that a case of discipline
                        undertaken under excitement is almost certain']
                        (신학 각주, 성경 아님), scriptures=[] — 해당 없음
special warning: NO_OBJECTION
```
**Readiness: READY_FOR_HUMAN_REVIEW**

### TSU-0003661 (Baptism) — HIGH ATTENTION

```
source_text integrity: 정상(canonical paragraph=362, sentence=3과 일치)
claim integrity: source_text(사도행전 2:38 KJV 직접 인용)와 정확히 대응
context sufficiency: 충분 — 성경 구절 자체가 자기완결적
scripture/citation gap: source_text가 사도행전 2:38 직접 인용인데
                        citations=['18. Then hath God also to the
                        Gentiles granted repentance'](다른 각주),
                        scriptures=[] — Acts 2:38 자체가 GAP=YES
special warning: SCRIPTURE_MISMATCH, DOCTRINE_MISMATCH 가능성(세례와
                 죄사함의 관계 표현이 침례교의 상징적 세례관과 문구가
                 어긋날 위험 — 신학적 정밀 검토 필요)
```
**Readiness: READY_FOR_HUMAN_REVIEW**(Q4 SCRIPTURE_MISMATCH + DOCTRINE_MISMATCH 플래그 필수)

### TSU-0003525 (Church Discipline)

```
source_text integrity: 정상(canonical paragraph=132, sentence=2와 일치)
claim integrity: 지시대명사("All this")가 가리키는 대상이 이 레코드
                 안에는 없고, 바로 앞 TSU-0003524(같은 paragraph=132,
                 sentence=1)에만 있음
context sufficiency: 불충분 — TSU-0003524와 함께 봐야 함(Task 7:
                     CONTEXT_DEPENDENT, 문자 그대로의 오염은 없으나
                     의미적 의존성 실재)
scripture/citation gap: citations=['5. Because that a case of discipline
                        undertaken under excitement is almost certain']
                        (TSU-0003524와 동일 각주 — 인접 문장), scriptures=[]
                        — 해당 없음
special warning: CONTEXT_LOSS
```
**Readiness: NEEDS_CONTEXT**(명령서 명시 지정, 이번 정정으로 확정)

### TSU-0003893 (Lord's Supper)

```
source_text integrity: 정상(canonical paragraph=620, sentence=2와 일치,
                       Production에 실제 존재 — "확인 불가" 주장은
                       이전 검증에서 오류로 확인됨)
claim integrity: "일부 사람들은 ~라고 생각한다"가 source_text("To them
                 it seems...")를 정확히 반영 — 화자 구분(제3자 견해
                 소개) 잘 보존됨
context sufficiency: 충분 — source_text 자체로 판단 가능
scripture/citation gap: citations=['3. They do not invite immersed
                        members'](신학 각주, 성경 아님), scriptures=[]
                        — 해당 없음
special warning: AMBIGUOUS — claim이 저자 본인의 신학적 입장인지,
                 저자가 소개(및 통상 비판)하는 개방 성찬 옹호자의
                 견해인지 이 TSU만으로는 불명확해 저자 본인 입장으로
                 오독될 위험이 있음(명령서 명시 요구사항)
```
**Readiness: READY_FOR_HUMAN_REVIEW**(Q4 AMBIGUOUS 플래그 필수)

### TSU-0003647 (Soteriology)

```
source_text integrity: 정상(canonical paragraph=347, sentence=1과 일치)
claim integrity: source_text(사도행전 17:30 KJV 직접 인용)와 정확히 대응
context sufficiency: 충분 — 성경 구절 자체가 자기완결적
scripture/citation gap: source_text가 사도행전 17:30 직접 인용인데
                        citations=['18. Then hath God also to the
                        Gentiles granted repentance'](다른 각주,
                        TSU-0003661과 동일 citation 텍스트 — 각주
                        번호 재사용 패턴), scriptures=[] — Acts 17:30
                        자체가 GAP=YES
special warning: SCRIPTURE_MISMATCH
```
**Readiness: READY_FOR_HUMAN_REVIEW**(Q4 SCRIPTURE_MISMATCH 플래그 권고)

---

## 3. Pilot 001 Readiness Summary(정정)

| Readiness | TSU ID | 건수 |
|---|---|---|
| READY_FOR_HUMAN_REVIEW | TSU-0000330, TSU-0000033, TSU-0000025, TSU-0003524, TSU-0003661, TSU-0003893, TSU-0003647 | 7 |
| NEEDS_CONTEXT | TSU-0000713, TSU-0000199, TSU-0003525 | 3 |
| **Total** | | **10** |

(원본 대비: READY 8→7건, NEEDS_CONTEXT 1→3건, 원본에만 있던
`READY_WITH_CAUTION`이라는 비표준 값 삭제)

---

## 4. Common Issues(정정)

### 4.1 paragraph/sentence — 정정: 전부 존재, canonical 매핑 가능

원본의 "10건 전부 null" 주장은 오류. 실측 결과 10건 전부 non-null
값을 가지며, `NAE/corpus/canonical/{Dagg_Church_Order,
Hiscox_Standard_Manual}/canonical.json`을 통해 실제 문맥 재구성이
가능함(이번 정정본의 §2 전체가 이 방법으로 작성됨).

### 4.2 evidence 필드 — 정정: 애초에 존재하지 않는 필드

TSU 스키마(35개 필드, `NAE/pipeline/tsu/builder.py` 실제 record 생성
로직 기준)에 `evidence`라는 필드 자체가 없다. "빈 배열"이라는 보고는
없는 필드를 있다고 전제한 오류.

### 4.3 Scripture citation gap — 10건 전체 확인 결과

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

### 4.4 context_before/context_after — 원본과 동일 결론(정정된 근거로 재확인)

`NAE/pipeline/tsu/builder.py`(원본이 확인 대상으로 삼았던
`core/tsu_builder.py`는 무관한 legacy 모듈) 확인 결과,
`context_before`/`context_after`는 `claim.py::extract_claim()` 호출
시 LLM 프롬프트 구성에만 사용되고 최종 TSU 레코드에는 저장되지 않음
— 결론 자체는 원본과 같으나 근거 파일이 정정됨.

---

## 5. Final Verdict(정정)

| 항목 | 판정 |
|---|---|
| Pilot 001 Human Review 준비 상태 | CONDITIONALLY READY |
| READY_FOR_HUMAN_REVIEW | 7/10 (70%) |
| NEEDS_CONTEXT | 3/10 (30%) |
| Human Review 진행 가능 여부 | YES — 단, TSU-0000713/TSU-0000199/TSU-0003525 3건은 canonical 선행 문맥을 함께 제공해야 함 |

---

## 6. Production Mutation Log

```
Production TSU 수정: 0
Claim 수정: 0
Human Decision 작성/변경: 0
Promotion: 0
Embedding: 0
Qdrant 변경: 0
Git commit: 0
Git push: 0
기존 파일 overwrite: 0(신규 파일 생성만)
```

---

*이 정정본은 READ-ONLY FORENSIC VERIFICATION ONLY이다. Production
데이터 수정, Git commit, Embedding 생성 등을 포함하지 않는다.*
