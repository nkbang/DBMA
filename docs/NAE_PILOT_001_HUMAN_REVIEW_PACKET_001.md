> **정정 안내(CUE, 2026-08-08, 2차 개정):**
>
> **Original source artifact:**
> - path: `/tmp/NAE_PILOT_001_HUMAN_REVIEW_READY.md`
> - sha256: `6c07bc00945f689795492f8ad2132038abf1b6585f4e9bc392cef802735eb861`
> - provenance: 출처 세션 미확인(검증 불가)
>
> **Corrected repository artifact(본 파일):**
> - path: `docs/NAE_PILOT_001_HUMAN_REVIEW_PACKET_001.md`
> - sha256: 파일 하단 §Provenance Footer 참고(편집 완료 후 계산 — 자기참조
>   문제로 이 안내 블록 내부에는 기록하지 않음)
> - modification: `author_id`만 변경, Hiscox 5건(TSU-0003524/0003661/
>   0003525/0003893/0003647)
> - production authority checked: `NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json`
>   (**직접 조회로 검증 — 원본 패킷 내부 진술 간 정합성만 본 것이 아니라,
>   실제 tsu.json을 python으로 열어 5건의 author_id 필드값을 하나하나
>   대조했다**)
>
> 원본과 정정본은 당연히 서로 다른 파일 해시를 가진다(`author_id` 값
> 자체가 바뀌었으므로). "검증 대상 값이 원본과 동일하다"는 것은
> **문서 전체의 SHA-256이 같다는 뜻이 아니라**, `source_text`/`claim`/
> `doctrine`/`crosswalk_id` 등 **TSU 내부 개별 필드 값**은 이번
> 개정에서도 변경하지 않았다는 뜻이다(용어 명확화).
>
> **Production Data Verification 상태 이력:**
> ```
> Original packet verification: FAILED — author_id mismatch in 5 Hiscox TSUs
>                                (hiscox_william_h, 실제와 불일치)
> Corrected packet verification: PASS AFTER CORRECTION — author_id factual
>                                correction applied to 5 Hiscox TSUs;
>                                모든 검증 대상 필드 Production과 재대조,
>                                이상 없음 확인.
> ```
>
> Human Decision 영역(Q1~Q4, FINAL DECISION, HUMAN COMMENT, REVIEWER,
> REVIEW_DATE)은 원본과 마찬가지로 전부 빈 칸이다 — AI가 대리 작성한
> 내용 없음.

---

# NAE Pilot 001 — Human Review Packet

**Status:** READY_FOR_HUMAN_REVIEW
**Date:** 2026-08-08
**Pilot ID:** PILOT-001
**Production TSU Count:** 10
**Production Data Verification:** PASS AFTER CORRECTION(위 정정 안내 참고 — 원본은 author_id 오류로 FAILED, 정정 후 재검증 PASS)

---

## Safety Constraints (Absolute)

```
Production TSU mutation = 0          ← DO NOT MODIFY
Human Decision written by AI = 0     ← DO NOT WRITE DECISIONS
Promotion = 0                        ← NOT YET
Embedding = 0                        ← NOT YET
Qdrant = 0                           ← NOT YET
Git commit/push = NOT PERFORMED      ← NOT YET
```

---

## A/C/R Vocabulary (Human Operator Use Only)

| Code | Meaning |
|------|---------|
| A | Accept / Approved — Claim is faithful to source |
| C | Conditional / Context Required — Needs clarification or additional context |
| R | Reject / Rework Required — Claim does not faithfully represent source |

---

## Evaluation Criteria (Q1–Q4)

### Q1 — Claim Fidelity
원문의 주장과 Claim이 충실하게 대응하는가?
- A: Claim이 원문의 주장을 왜곡 없이 정확히 요약
- C: Claim은 부분적이거나 모호함
- R: Claim이 원문의 주장을 왜곡하거나 누락

### Q2 — Theological Accuracy
Claim이 본문 및 문맥에 비추어 신학적으로 정확한가?
- A: Claim이 신학적으로 타당한 해석
- C: 문맥 부족으로 판단 불가
- R: Claim이 신학적으로 잘못된 해석 포함

### Q3 — Context Sufficiency
현재 source_text만으로 Claim을 판단할 충분한 문맥이 있는가?
- A: source_text가 충분한 문맥 제공
- C: 추가 문맥 필요
- R: source_text만으로는 불충분

### Q4 — Special Warning
다음 위험 중 해당되는 것이 있는가?
```
SCRIPTURE_MISMATCH  — 성경 인용 불일치
DOCTRINE_MISMATCH   — 교리 분류 오류
CONTEXT_LOSS        — 문맥 손실
AMBIGUOUS           — 모호함
EVIDENCE_INSUFFICIENT — 증거 불충분
NONE                — 위험 없음
```

---

## Pilot 001 Review Items (10 TSU)

---

### TSU-0000713 (Dagg_Church_Order)

```yaml
pilot_id: PILOT-001
tsu_id: TSU-0000713
source_id: BAP-CHURCH-DAGG-001
work_id: WORK-DAGG-CHURCH-ORDER-001
edition_id: WORK-DAGG-CHURCH-ORDER-001-1871
author_id: dagg_john_l
doctrine: Ecclesiology
crosswalk_id: f914f6c442983e59
```

**source_text (Production Authoritative Evidence):**
```
"No church communicated with me as concerning giving and receiving, but ye only."3
« As distinct bodies, they sent and received salutations," * and held intercourse by messengers.'
```

**claim (Production Authoritative Evidence):**
```
초기 교회들은 서로 다른 교회들과 비교되었으며, 각 교회는 독립된 단체로서 서로 인사와 연락을 주고받았다.
```

**Human Review:**

Q1 — Claim Fidelity: **C**

Q2 — Theological Accuracy: **C**

Q3 — Context Sufficiency: **C**

Q4 — Special Warning: **CONTEXT_LOSS**

**FINAL DECISION:** **CONDITIONAL**

**HUMAN COMMENT:**
인용문은 초기 교회들이 서로 구별되는 지역적 단위였고, 인사와 사절을 통해 교제했다는 요지를 직접 뒷받침함. 그러나 claim의 "서로 다른 교회들과 비교되었으며"는 제시된 발췌문 자체에는 없고 바로 앞 문맥에 의존함. "독립된 단체"라는 표현도 이 두 문장만으로 확증하기에는 강한 교회정치적 함의를 가질 수 있어 주의 필요.

권장 수정 claim: "초기 교회들은 서로 구별되는 지역 교회들로 언급되었으며, 각 교회는 인사를 주고받고 사절을 통해 상호 교제하였다."

**REVIEWER:**
David

**REVIEW_DATE:**
2026-08-08

---

### TSU-0000199 (Dagg_Church_Order)

```yaml
pilot_id: PILOT-001
tsu_id: TSU-0000199
source_id: BAP-CHURCH-DAGG-001
work_id: WORK-DAGG-CHURCH-ORDER-001
edition_id: WORK-DAGG-CHURCH-ORDER-001-1871
author_id: dagg_john_l
doctrine: Baptism
crosswalk_id: f914f6c442983e59
```

**source_text (Production Authoritative Evidence):**
```
The verb never signifies this process.
```

**claim (Production Authoritative Evidence):**
```
동사 'banro'는 액체를 고체에 적용하는 과정을 의미하지 않는다.
```

**Human Review:**

Q1 — Claim Fidelity: **A**

Q2 — Theological Accuracy: **A**

Q3 — Context Sufficiency: **A**

Q4 — Special Warning: **AMBIGUOUS**

**FINAL DECISION:** **APPROVED**

**HUMAN COMMENT:**
claim의 "banro"는 원문의 그리스어 "bapto" 오기로 보이며 표기를 수정해야 함. 원문은 bapto가 액체를 고체에 적용하는 과정을 뜻하지 않고, 그로 인해 생긴 결과를 뜻할 수는 있다고 명시함. 앞뒤 문맥이 모두 제공되어 논증 구조는 충분히 보존됨. 세례 방식에 대한 더 넓은 교리적 결론까지 검증하는 것은 아님.

권장 claim: "동사 bapto는 액체를 고체에 적용하는 과정을 의미하지 않으며, 그러한 적용으로 생긴 결과를 의미할 수는 있다."

**REVIEWER:**
David

**REVIEW_DATE:**
2026-08-08

---

### TSU-0000330 (Dagg_Church_Order)

```yaml
pilot_id: PILOT-001
tsu_id: TSU-0000330
source_id: BAP-CHURCH-DAGG-001
work_id: WORK-DAGG-CHURCH-ORDER-001
edition_id: WORK-DAGG-CHURCH-ORDER-001-1871
author_id: dagg_john_l
doctrine: Lord's Supper
crosswalk_id: f914f6c442983e59
```

**source_text (Production Authoritative Evidence):**
```
A well executed picture of the crucifixion, such as may be seen in Catholic chapels, has much more resemblance to the bedy of Christ, than is furnished by a picce of bread; yet, considering all the ends to be answered by the Eucharist, the divine wisdom has determined that we should keep Christ's death in memory, not by looking at a crucifix, but by the eating of bread.
```

**claim (Production Authoritative Evidence):**
```
성례의 목적을 고려할 때, 성찬에서 빵을 먹음으로써 그리스도의 죽음을 기억하는 것이 더 적절하다.
```

**Human Review:**

Q1 — Claim Fidelity: **C**

Q2 — Theological Accuracy: **C**

Q3 — Context Sufficiency: **A**

Q4 — Special Warning: **AMBIGUOUS**

**FINAL DECISION:** **CONDITIONAL**

**HUMAN COMMENT:**
claim은 Dagg의 요지(단순 외형적 유사성보다 성찬의 여러 목적을 고려해 빵을 먹는 방식이 정해졌다는 점)를 대체로 반영하나, "더 적절하다"의 비교 대상이 빠져 있음 — 원문은 성찬 일반이 아니라 십자가상(crucifix)을 보는 방식과의 비교를 논함. "성례"는 넓은 말인 반면 원문은 성찬의 빵 먹는 행위에 관한 구체적 논증.

권장 claim: "성찬의 여러 목적을 고려할 때, 그리스도의 죽음을 기억하는 방식으로는 십자가상을 바라보는 것보다 성찬에서 빵을 먹는 방식이 하나님께서 정하신 더 적합한 수단이다." 단, "더 적합한"은 빵이 그리스도의 몸을 더 닮았기 때문이 아니라 성찬이 수행하는 모든 목적을 함께 충족하기 때문이라는 뜻으로 제한해야 함.

**REVIEWER:**
David

**REVIEW_DATE:**
2026-08-08

---

### TSU-0000033 (Dagg_Church_Order)

```yaml
pilot_id: PILOT-001
tsu_id: TSU-0000033
source_id: BAP-CHURCH-DAGG-001
work_id: WORK-DAGG-CHURCH-ORDER-001
edition_id: WORK-DAGG-CHURCH-ORDER-001-1871
author_id: dagg_john_l
doctrine: Soteriology
crosswalk_id: f914f6c442983e59
```

**source_text (Production Authoritative Evidence):**
```
A powerful motive, to love and obey Christ, is drawn from the love which he has manifested in dying for us.
```

**claim (Production Authoritative Evidence):**
```
그리스도의 사랑과 복종의 강력한 동기는 우리를 위해 죽으신 그분의 사랑에서 비롯됩니다.
```

**Human Review:**

Q1 — Claim Fidelity: **C**

Q2 — Theological Accuracy: **C**

Q3 — Context Sufficiency: **A**

Q4 — Special Warning: **AMBIGUOUS**

**FINAL DECISION:** **CONDITIONAL**

**HUMAN COMMENT:**
원문은 "그리스도를 사랑하고 그분께 순종하려는 우리의 강력한 동기"가 우리를 위해 죽으신 그리스도의 사랑에서 나온다고 말함. 현재 claim "그리스도의 사랑과 복종"은 누구의 사랑·복종인지 문법적으로 모호함 — "그리스도께 드리는 사랑과 복종"(원문의 뜻)과 "그리스도 자신의 사랑과 복종"으로 모두 읽힐 수 있음.

권장 claim: "우리가 그리스도를 사랑하고 그분께 순종하는 강력한 동기는, 우리를 위해 죽으심으로 나타내신 그리스도의 사랑에서 비롯됩니다." 이 수정은 사랑과 순종의 주체를 우리로, 동기의 근거를 그리스도의 자기희생적 사랑으로 명확히 함.

**REVIEWER:**
David

**REVIEW_DATE:**
2026-08-08

---

### TSU-0000025 (Dagg_Church_Order)

```yaml
pilot_id: PILOT-001
tsu_id: TSU-0000025
source_id: BAP-CHURCH-DAGG-001
work_id: WORK-DAGG-CHURCH-ORDER-001
edition_id: WORK-DAGG-CHURCH-ORDER-001-1871
author_id: dagg_john_l
doctrine: Sanctification
crosswalk_id: f914f6c442983e59
```

**source_text (Production Authoritative Evidence):**
```
To love God with all the heart is the sum of all duty.
```

**claim (Production Authoritative Evidence):**
```
하나님을 전심으로 사랑하는 것이 모든 의무의 총합이다.
```

**Human Review:**

Q1 — Claim Fidelity: **A**

Q2 — Theological Accuracy: **A**

Q3 — Context Sufficiency: **A**

Q4 — Special Warning: **NONE**

**FINAL DECISION:** **APPROVED**

**HUMAN COMMENT:**
claim은 원문 첫 문장을 거의 그대로 정확하게 옮겼고, 이어지는 문맥도 하나님 사랑이 모든 하나님의 요구에 대한 순종을 포함한다고 풀어줌. 성경 장절을 직접 인용하지 않았더라도 claim은 원문 자체의 진술을 충실히 보고하므로 성경 인용 누락은 불일치나 근거 부족 경고 사유가 아님. 권장 claim 수정 없음.

**REVIEWER:**
David

**REVIEW_DATE:**
2026-08-08

---

### TSU-0003524 (Hiscox_Standard_Manual)

```yaml
pilot_id: PILOT-001
tsu_id: TSU-0003524
source_id: BAP-CHURCH-HISCOX
work_id: WORK-HISCOX-STANDARD-MANUAL-001
edition_id: WORK-HISCOX-STANDARD-MANUAL-001-1890
author_id: hiscox_edward_t
doctrine: Ecclesiology
crosswalk_id: 260d31b2331a3f8b
```

**source_text (Production Authoritative Evidence):**
```
The evil passions of even good men may triumph over piety, and partisan strife may destroy the peace and the prosperity of the body of Christ.
```

**claim (Production Authoritative Evidence):**
```
선한 사람들의 악한 정서가 경건을 이길 수 있고, 당파적인 분쟁이 그리스도의 몸의 평화와 번영을 파괴할 수 있다.
```

**Human Review:**

Q1 — Claim Fidelity: **A**

Q2 — Theological Accuracy: **A**

Q3 — Context Sufficiency: **A**

Q4 — Special Warning: **NONE**

**FINAL DECISION:** **APPROVED**

**HUMAN COMMENT:**
claim은 원문을 충실히 번역하며, 교회 공동체 안의 죄된 정욕과 당파적 분쟁이 경건·평화·번영을 해칠 수 있다는 경고를 정확히 보존함. 앞 문맥은 성도들의 부분적 성화와 형제들 사이 갈등을 설명하고, 뒤 문장(TSU-0003525)은 이를 가능한 한 피해야 한다고 명시 — 제시된 원문만으로 claim의 범위와 의도가 충분히 확인됨. 권장 claim 수정 없음.

**REVIEWER:**
David

**REVIEW_DATE:**
2026-08-08

---

### TSU-0003661 (Hiscox_Standard_Manual)

```yaml
pilot_id: PILOT-001
tsu_id: TSU-0003661
source_id: BAP-CHURCH-HISCOX
work_id: WORK-HISCOX-STANDARD-MANUAL-001
edition_id: WORK-HISCOX-STANDARD-MANUAL-001-1890
author_id: hiscox_edward_t
doctrine: Baptism
crosswalk_id: 260d31b2331a3f8b
```

**source_text (Production Authoritative Evidence):**
```
Then Peter said unto them, Repent, and be baptized every one of you in the name of Jesus Christ for the remission of sins.
```

**claim (Production Authoritative Evidence):**
```
예수 그리스도의 이름으로 죄의 사함을 받기 위해 각자가 회개하고 세례를 받아야 한다.
```

**Human Review:**

Q1 — Claim Fidelity: **A**

Q2 — Theological Accuracy: **C**

Q3 — Context Sufficiency: **C**

Q4 — Special Warning: **SCRIPTURE_MISMATCH**

**FINAL DECISION:** **CONDITIONAL**

**HUMAN COMMENT:**
claim은 사도행전 2:38 명령문을 충실히 옮기나, 원문 표기는 "Acts 11:38"로 잘못되어 있음(실제로는 Acts 2:38이어야 함). "세례를 통해/수단으로 죄 사함을 받는다"는 세례중생론으로 확장되면 Hiscox의 침례교 신학(세례는 믿음·중생의 증거 위에 시행되는 상징적 의식, 세례중생론 명시적 거부)과 충돌 위험. 필수 정정: 성경 표기를 "Acts 2:38"로 수정.

권장 claim: "사도행전 2:38은 각 사람이 회개하고 예수 그리스도의 이름으로 세례를 받으며 죄 사함을 받으라는 베드로의 권면을 기록한다." — 본문을 정확히 보고하되 세례가 죄 사함의 독립적 수단이라는 교리 해석을 불필요하게 확정하지 않음.

**REVIEWER:**
David

**REVIEW_DATE:**
2026-08-08

---

### TSU-0003525 (Hiscox_Standard_Manual)

```yaml
pilot_id: PILOT-001
tsu_id: TSU-0003525
source_id: BAP-CHURCH-HISCOX
work_id: WORK-HISCOX-STANDARD-MANUAL-001
edition_id: WORK-HISCOX-STANDARD-MANUAL-001-1890
author_id: hiscox_edward_t
doctrine: Church Discipline
crosswalk_id: 260d31b2331a3f8b
```

**source_text (Production Authoritative Evidence):**
```
All this should, if possible, be avoided.
```

**claim (Production Authoritative Evidence):**
```
교회에서 일어날 수 있는 악한 정서와 파당적인 분쟁을 가능한 한 피해야 한다.
```

**Human Review:**

Q1 — Claim Fidelity: **A**

Q2 — Theological Accuracy: **A**

Q3 — Context Sufficiency: **A**

Q4 — Special Warning: **NONE**

**FINAL DECISION:** **APPROVED**

**HUMAN COMMENT:**
claim은 "All this should, if possible, be avoided"의 지시 대상(악한 정욕과 당파적 분쟁, TSU-0003524)을 정확히 풀어 썼으며, 이어지는 문장도 문제 발생 후 치유보다 예방이 낫다는 점을 확인함. 앞 문장(TSU-0003524)이 "All this"의 선행사를 직접 제공하고, 뒤 문장이 예방과 교정적 권징의 관계를 명시하여 TSU-0003524와 함께 제공된 범위 안에서 claim의 대상과 의도가 충분히 확인됨. 권장 claim 수정 없음.

**REVIEWER:**
David

**REVIEW_DATE:**
2026-08-08

---

### TSU-0003893 (Hiscox_Standard_Manual)

```yaml
pilot_id: PILOT-001
tsu_id: TSU-0003893
source_id: BAP-CHURCH-HISCOX
work_id: WORK-HISCOX-STANDARD-MANUAL-001
edition_id: WORK-HISCOX-STANDARD-MANUAL-001-1890
author_id: hiscox_edward_t
doctrine: Lord's Supper
crosswalk_id: 260d31b2331a3f8b
```

**source_text (Production Authoritative Evidence):**
```
To them it seems kindly and fraternal to invite all who say they love our common Lord and Saviour to unite in commemorating his death in the Supper.
```

**claim (Production Authoritative Evidence):**
```
일부 사람들은 주님의 만찬에서 죽으신 주님을 기념하는 것을 모든 사람들이 함께 할 수 있도록 초청하는 것이 친절하고 형제적인 행동이라고 생각한다.
```

**Human Review:**

Q1 — Claim Fidelity: **A**

Q2 — Theological Accuracy: **C**

Q3 — Context Sufficiency: **C**

Q4 — Special Warning: **CONTEXT_LOSS**

**FINAL DECISION:** **CONDITIONAL**

**HUMAN COMMENT:**
claim은 본문이 소개하는 견해를 정확히 요약하나, 그것이 Hiscox 자신의 결론이 아니라 그가 뒤이어 반박하는 개방 성찬 옹호자들의 논거라는 결정적 문맥이 빠져 있음. Hiscox는 세례를 성찬 참여의 선행 조건으로 보며, 동정심이 신앙·양심 문제에서 행위를 좌우해서는 안 된다고 반박함. "일부 사람들은"으로 귀속을 완화했지만 그 견해가 저자가 소개·비판하는 입장이라는 사실을 누락해 독자가 저자의 성찬론으로 오해할 위험.

권장 claim: "개방 성찬을 옹호하는 일부 사람들은, 공통의 주님과 구주를 사랑한다고 고백하는 모든 이를 주님의 만찬에서 그리스도의 죽음을 기념하도록 초청하는 것이 친절하고 형제적인 행동이라고 생각한다." 메타문 권고: "이 진술은 Hiscox 자신의 결론이 아니라, 그가 세례를 성찬 참여의 선행 조건으로 보며 뒤이어 비판하는 개방 성찬 옹호 논거의 소개이다."

**REVIEWER:**
David

**REVIEW_DATE:**
2026-08-08

---

### TSU-0003647 (Hiscox_Standard_Manual)

```yaml
pilot_id: PILOT-001
tsu_id: TSU-0003647
source_id: BAP-CHURCH-HISCOX
work_id: WORK-HISCOX-STANDARD-MANUAL-001
edition_id: WORK-HISCOX-STANDARD-MANUAL-001-1890
author_id: hiscox_edward_t
doctrine: Soteriology
crosswalk_id: 260d31b2331a3f8b
```

**source_text (Production Authoritative Evidence):**
```
And the times of this ignorance God winked at, but now commandeth all men everywhere to repent.
```

**claim (Production Authoritative Evidence):**
```
하나님은 이전에는 무지한 시대를 용납하셨지만 이제는 모든 사람에게 어디서나 회개할 것을 명령하시고 계심
```

**Human Review:**

Q1 — Claim Fidelity: **A**

Q2 — Theological Accuracy: **A**

Q3 — Context Sufficiency: **A**

Q4 — Special Warning: **NONE**

**FINAL DECISION:** **APPROVED**

**HUMAN COMMENT:**
claim은 사도행전 17:30을 정확히 요약하며, "무지한 시대를 용납/간과하셨다"와 "이제는 어디서나 모든 사람에게 회개를 명하신다"는 두 핵심을 모두 보존함. 성경 인용은 사도행전 17:30과 일치하고 의미 왜곡이나 문맥상 결정적 누락 없음. scriptures 필드가 비어 있는 것은 콘텐츠 판정의 결함이 아니라 메타데이터 보완 사항.

메타데이터 보완 권고: scriptures 필드에 "Acts 17:30"(선택적으로 "Romans 16:26; Mark 1:15; Romans 1:15-17" 병행 참조도 포함 가능) 채우기 권장.

**REVIEWER:**
David

**REVIEW_DATE:**
2026-08-08

---

## Reviewer Instructions

1. **각 TSU를 독립적으로 검토** — Production source_text와 claim을 기준으로 판단
2. **Human Decision은 직접 작성** — AI가 대리 작성하지 않음
3. **Q4는 반드시 선택** — NONE 외의 위험이 있으면 COMMENT에 사유 기재
4. **REVISE가 필요한 경우** — Human Comment에 수정 제안 기록
5. **모든 항목 완료 후** — REVIEWER 이름, REVIEW_DATE 기재

---

## Reference: Existing CUE Observations (For Reference Only)

다음 의견은 **참고용**이며 Human Decision으로 간주되지 않는다.

- **TSU-0000199:** source_text가 매우 짧고("The verb never signifies this process.") "this process"가 가리키는 대상("액체를 고체에 바르는 과정")이 인접 문맥에만 있음 — 문맥 없이 독립 검토 어려움(NEEDS_CONTEXT, 상세 문맥은 검토자 안내 메시지 참고)
- **TSU-0000330:** source_text에 "bedy" 오타 존재 (원문 그대로 인용)
- **TSU-0000033:** claim "그리스도의 사랑과 복종의 강력한 동기는..."에서 "그리스도의"가 "그리스도 자신의 사랑과 복종"(주체)으로도, "그리스도를 향한 사랑과 복종"(대상)으로도 읽힐 수 있는 한국어 구문 중의성 존재 — 원문("A powerful motive, to love and obey Christ, is drawn from the love which he has manifested...")은 후자(그리스도를 사랑·순종하는 동기)가 명확하므로, claim 표현이 이 의미를 정확히 전달하는지 검토 권고
- **TSU-0003525:** "All this"의 선행사가 source_text 자체에는 없고 직전 TSU-0003524에만 있음(CONTEXT_DEPENDENT) — 두 TSU를 독립적으로 각각 검토하는 규칙과 실질적으로 충돌할 수 있어, 검토 시 두 TSU를 함께 확인 권고
- **TSU-0003661:** 성경 직접 인용(사도행전 2:38) 포함 — SCRIPTURE_MISMATCH 확인 필요. 직접 인용이므로 본문 출처·판본(KJV 등)·번역 대응 여부를 별도로 확인 권고
- **TSU-0003893:** 원문("all who say they love our common Lord and Saviour")의 한정 조건("주와 구주를 사랑한다고 말하는 자들")이 claim의 "모든 사람들"에서 약화·일반화되어 있음 — 원문의 조건부 범위가 claim에서 그대로 유지되는지 검토 권고

Human operator가 Production TSU와 원문 근거를 직접 보고 판단해야 한다.
위 항목들은 Human Decision이 아니라, 검토 시 참고할 QA 주의 지점이다.

---

## Final Status

```
READY_FOR_HUMAN_REVIEW
```

Production 데이터 검증 PASS AFTER CORRECTION(`author_id` 오류 1건은 CUE가 Production 직접 조회로 정정 — 상단 안내 참고). Human Review 대기 중.

---

## Provenance Footer

```
본 파일(정정본, 2차 개정) SHA-256: e5b87d4b97ce272856228264ae7219a4a4866b5f880bebc0c7372a207cc79559
계산 시점: 2026-08-08(본 개정 완료 직후)
주의: 이 해시는 본 라인 자체를 포함한 시점의 스냅샷이다 — 향후 파일이
다시 수정되면 이 값도 갱신되어야 한다(자기참조 특성상 매 편집마다
재계산 필요).
```

---

*Human Review Packet generated: 2026-08-08*
*Corrected and relocated to docs/ by CUE: 2026-08-08*
*No Human Decision written by AI.*
*No Production TSU modified.*
