# ADR-030 Amendment C — C1 Independent Review Result 002

| | |
|---|---|
| **문서 ID** | `ADR-030-AMENDMENT-C-C1-REVIEW-RESULT-002` |
| **작성자** | C1 (Independent Forensic Auditor) |
| **일자** | 2026-09-16 |
| **대상** | `ADR-030-AMENDMENT-C-Fuller-Vol08-Bulk-Approval-Exception.md` (PROPOSED) + RESULT-001 재검증 |
| **판정** | **YELLOW (조건부 — 조건 명시)** |
| **게이트** | C1 판정 → CUE 2차 대조 검증 → HQ 서면 승인 → Amendment C Approved/YELLOW/RED 최종 확정 |

---

## 워크트리 검증

```
pwd:                    /Users/David/DBMA
git rev-parse --show-toplevel: /Users/David/DBMA
git rev-parse --abbrev-ref HEAD: dev/dbma-engine
git rev-parse --short HEAD: aa92a88b
git remote -v:          nas http://100.94.139.122:3000/David/DBMA.git / origin https://github.com/nkbang/DBMA.git
```

모든 값이 예상과 일치 — 올바른 저장소/브랜치에서 작업함.

---

## RESULT-001 재검증 요청 배경 (Task Order 066)

RESULT-001 §RQ-2-3의 FAIL 8건에 대해 CUE가 canonical.json paragraph 전체 text로 재대조한 결과, 7건에서 문제를 발견함:

| TSU ID | C1 판정(RESULT-001) | CUE 재검증 |
|---|---|---|
| TSU-0031114 | FAIL(내용 추가) | **PASS** — paragraph[432] 전체에 "There is a link... that unites the purposes of God, and the free actions of men" 포함 |
| TSU-0031184 | FAIL(완전히 다른 내용) | **데이터 불일치** — 현재 tsu.json의 claim은 RESULT-001 인용 문구와 다름 |
| TSU-0031369 | FAIL(내용 추가) | **PASS** — paragraph[549] 전체에 "and justify the righteous government of God" 포함 |
| TSU-0031490 | FAIL(의미 역전) | **과장** — paragraph[610] 전체는 대조 구조, "완전한 의미 역전" 아님 |
| TSU-0031654 | FAIL(구체적 내용 추가) | **PASS** — paragraph[682] 전체에 Rousseau 일화 포함 |
| TSU-0033134 | FAIL(OCR/번역 오류) | **확인됨 — 유일하게 유효한 FAIL** |
| TSU-0034026 | FAIL(신학적 결론 추가) | **PASS** — paragraph[1848] 전체에 "if infinite mercy interpose not" 포함 |
| TSU-0034811 | FAIL(조건 추가) | **PASS** — paragraph[2212] 전체에 "their whole duty consisted in sending the party to the minister" 포함 |

**CUE 결론: 8건 중 진짜 Q1 오류는 TSU-0033134 1건(12.5%)뿐.**

---

## RQ-2-재검증 — 방법론 수정 후 전체 표본 재실행

### 방법론 수정 사항

RESULT-001 §RQ-2-2의 "각 레코드의 `claim`을 `source_text`와 대조"라는 방법을 다음으로 수정함:

1. **source_text(앵커 문장)만 보지 않고 paragraph 전체 text 확인**
2. TSU 클레임 생성 파이프라인(`parser.py::build_candidates()`)이 `context_before`/`context_after`(문단 내 인접 문장)까지 활용해 클레임을 생성하므로, paragraph 전체 text로 Q1 fidelity를 판정해야 함
3. 각 재판정에 **paragraph 전체 text 인용**을 포함 — 앵커 문장만 인용하는 것은 이번 재검토의 목적(방법론 오류 시정)에 반함

### RQ-2-재검증 1: CUE가 PASS로 재분류한 6건 재판정

#### TSU-0031114 (para[432]) — CUE 주장 검토

**paragraph[432] 전체 text**:
> "That this subject is deep and difficult, in the present state, is admitted ; and wicked men may abuse it to their own destruction : but the thing itself is no less true and useful, if considered in the fear of God. **There is a link, as some have expressed it, that unites the purposes of God, and the free actions of men, which is above our comprehension ; but to deny the fact, is to disown an all-pervading Providence** ; which is little less than to disown a God."

**RESULT-001 인용 claim**: "신의 주권과 인간의 자유로운 행동 사이에는 우리가 이해할 수 없는 연결고리가 존재하며, 이 사실을 부정하는 것은 신의 섭리를 부정하는 것과 같다."

**판정**: **CUE의 PASS 재분류에 동의**. paragraph 전체 text에 claim의 근거가 거의 축자적으로 포함되어 있음. RESULT-001에서 TSU-0031114의 paragraph를 428로 잘못 기록했으나, 현재 tsu.json에서는 432로 정확히 기록되어 있음.

#### TSU-0031369 (para[549]) — CUE 주장 검토

**paragraph[549] 전체 text**:
> "Our advocate with the Father is Jesus Christ the righteous. Though he mingled with sinners, yet he must be holy, harmless, undefiled, and separate from them; and though he pleaded for sinners, yet he must not extenuate their sin, but condemn it without reserve, **and justify the righteous government of God, by which it was threatened with destruction**."

**판정**: **CUE의 PASS 재분류에 동의**. RESULT-001이 source_text를 "...condemn it without reserve"까지만 인용했으나, 실제 paragraph 전체에는 claim의 해당 부분이 포함되어 있음.

#### TSU-0031490 (para[610]) — CUE 주장 검토

**paragraph[610] 전체 text**:
> "Jesus saith unto him, He that is washed needeth not save to wash his feet ; but is clean every whit: and ye are clean, but not all. As it is sufficient for persons who have bathed their bodies in the stream to wash the defilement attached to their feet by walking on shore ; so they that have believed in Christ, shall never come into condemnation, and need not the repetition of a passing from death to life ; **but merely an application for the pardon of their daily sins. Such was the character of all the disciples, except Judas, who, notwithstanding his profession, was yet in his sins.**"

**판정**: **CUE의 "과장" 주장에 동의**. paragraph 전체는 유다를 제외한 제자들이 깨끗하다는 대조 구조이며, claim("유다의 경우를 제외하고는 죄에서 자유로워지고")과 방향이 일치함. "완전한 의미 역전"이 아님. claim 후반부 "그리스도에 대한 믿음으로 인해 심판을 받지 않는다"는 source_text에 명시적으로 없으나 문맥상 합리적 해석이므로 **FAIL → BORDERLINE**로 하향 조정.

#### TSU-0031654 (para[682]) — CUE 주장 검토

**paragraph[682] 전체 text**:
> "upon him but for his good ; and therefore he will indulge for the present and abide the consequence. This is not an imaginary process : it is a fact that these are the principles by which profligate characters, in great numbers, comfort themselves in their sins. When Rousseau was impressed with the doctrine of eternal punishment, he could scarcely endure his existence ; but a lady with whom he says he was very familiar used to tranquilize his soul by persuading him that, 'The Supreme Being would treat us with more severity if we were really guilty.'"

**판정**: **CUE의 PASS 재분류에 동의**. paragraph 전체에 Rousseau 일화가 포함되어 claim의 "하나님의 공의에 대한 잘못된 이해" 근거를 정확히 뒷받침함.

#### TSU-0034026 (para[1848]) — CUE 주장 검토

**paragraph[1848] 전체 text**:
> "Sixthly : When the sinner becomes thus besotted in the ways of sin, there are commonly a number of circumstances and considerations, besides his own attachment to it, which entangle his soul, **and, if infinite mercy interpose not, prevent his escape**."

**판정**: **CUE의 PASS 재분류에 동의**. paragraph 전체에 "if infinite mercy interpose not, prevent his escape"가 포함되어 claim과 사실상 축자적으로 일치함.

#### TSU-0034811 (para[2212]) — CUE 주장 검토

**paragraph[2212] 전체 text**:
> "It has been already intimated, that to give advice to a person under concern about salvation, it is necessary, in the first place, that we be interested on his behalf, and treat him in a free and affectionate manner. **Some members of churches act as if they thought such things did not concern them, and as if their whole duty consisted in sending the party to the minister.** A church composed of such characters may be opulent and respectable ; but they possess nothing inviting or winning to an awakened mind."

**판정**: **CUE의 PASS 재분류에 동의**. paragraph 전체에 "their whole duty consisted in sending the party to the minister"가 포함되어 claim의 조건절 근거를 제공함.

### RQ-2-재검증 2: TSU-0031184 데이터 불일치 확인

**RESULT-001에 인용된 claim**: "죄를 지을 때 무지와 불신앙을 이유로 들어서 자기를 용서받았다고 말한다."

**현재 tsu.json(2026-09-16)의 claim**:
> "사도 베드로는 시몬 마구스가 악한 행동을 회개하고 하나님께 기도하여 그의 마음의 생각이 용서될 수 있기를 바랐으며, 이는 사도가 시몬 마구스가 반드시 사죄할 수 없는 죄를 지었다고 생각하지 않았음을 시사한다."

**paragraph[465] 전체 text**:
> "Perhaps the next intimation that is given of this sin, is in Peter's address to Simon Magus : Repent of this thy wickedness, and pray God, if perhaps the thought of thine heart may be forgiven thee. **It does not appear that the apostle considered the sorcerer as having certainly committed the unpardonable sin** : but it seems he considered it as a matter of doubt..."

**판정**:
- RESULT-001에 인용된 claim 문구는 현재 tsu.json과 **전혀 다름**. RESULT-001에서 어떤 시점의 파일을 보고 그 문구를 인용했는지 확인 불가 → **"확인 불가"**.
- 현재 파일 기준으로 재판정: paragraph[465] 전체에 "It does not appear that the apostle considered the sorcerer as having certainly committed the unpardonable sin"이 포함되어 claim과 일치함 → **PASS**.

### RQ-2-재검증 3: BORDERLINE 10건 전건 재판정 (paragraph 전체 text 포함)

#### TSU-0030992 (para[372]) — 재판정: PASS

**paragraph[372] 전체 text**:
> "house of Israel? — Only fear the Lord, and serve him in truth, and with all your hearts. The language of the promises is perfectly correspondent with all this, with respect to the nature of what is bestowed : And the Lord thy God will circumcise thy heart, and the heart of thy seed, to love the Lord thy God with all thine heart and with all thy soul. — **A new heart will I give you, and a new spirit** will I put within you."

**판정**: paragraph 전체에 "A new heart will I give you, and a new spirit"가 포함되어 claim("새로운 마음과 영을 주시다")의 근거를 정확히 제공함. **BORDERLINE → PASS**.

#### TSU-0031620 (para[667]) — 재판정: PASS

**paragraph[667] 전체 text**:
> "From the whole, we learn the following important instructions:— First: The great evil of departing from God, and of flying in the face of his commands. The story of Jonah leaves an impression behind it of the justness of his own reflection, They that observe lying vanities, forsake their own mercies. **What are all the reasonings of the flesh against God's revealed will? Vanities, lying vanities** ; the end of which, if grace prevent not, will be death."

**판정**: paragraph 전체에 "reasonings of the flesh against God's revealed will"이 포함되어 claim("인간의 육체적인 생각은 하나님의 계시된 뜻에 대한 헛된 거짓말")의 근거를 제공함. **BORDERLINE → PASS**.

#### TSU-0032353 (para[996]) — 재판정: PASS

**paragraph[996] 전체 text**:
> "**The glory of God being manifested by the good works of his children, implies that they are all to be ascribed to him as their proper cause.** Though we act, he actuates."

**판정**: paragraph 첫 문장이 claim("하나님의 영광이 그의 자녀들의 선한 행실로 나타나는데, 이는 모든 행실이 하나님께로 인한 것임을 의미한다")의 근거를 정확히 제공함. **BORDERLINE → PASS**.

#### TSU-0033459 (para[1490]) — 재판정: FAIL

**paragraph[1490] 전체 text**:
> "It has been very common, among a certain class of writers, to exclaim against creeds and systems in religion, as inconsistent with Christian liberty and the rights of conscience : but surely they must be understood as objecting to those creeds only which they dislike, and not to creeds in general ; for no doubt, unless they be worse than the worst of beings, they have a creed of their own. **The man who has no creed, has no belief**; which is the same thing as being an unbeliever: and he whose belief is not formed into a system, has only a few loose, unconnected thoughts, without entering into any system."

**판정**: paragraph 전체에 "복음의 조화와 영광을 이해하지 못한다"에 해당하는 내용이 전혀 없음. claim이 paragraph text의 어떤 부분에도 근거하지 않음. **BORDERLINE → FAIL**.

#### TSU-0033803 (para[1706]) — 재판정: PASS

**paragraph[1706] 전체 text**:
> "part of the season appropriated to private devotion on rising in the morning. The mind at this time is re-invigorated, and unincumbered. To read a part of the scriptures, previous to prayer, I have found to be very useful. **It tends to collect the thoughts, to spiritualize the affections, and to furnish us with sentiments where-with to plead at a throne of grace.** And as reading assists prayer,"

**판정**: paragraph 전체에 "It tends to collect the thoughts, to spiritualize the affections"가 포함되어 claim("경건한 마음가짐이 성경을 이해하는 데 도움이 된다")의 근거를 제공함. **BORDERLINE → PASS**.

#### TSU-0034110 (para[1894]) — 재판정: PASS

**paragraph[1894] 전체 text**:
> "There is something in the nature of evil, which if it appear in its own proper colours, will not admit of being defended or recommended to others : he, therefore, who is friendly to it, is under the necessity of disguising it, by giving it some specious name in order to render it current in society. **On the other hand, there is something in the nature of good, which, if it appear in its own proper colours, cannot well be opposed** : he, therefore, who wishes to run it down, is obliged first to give it some specious name."

**판정**: paragraph 전체에 선과 악 모두에 대한 설명이 포함되어 claim("선은 그 자체의 본질적인 색깔로 나타나면 쉽게 반대될 수 없으며, 악은 그 자체의 본질적인 색깔로 나타나면 쉽게 변명될 수 없다는 것")의 근거를 제공함. **BORDERLINE → PASS**.

#### TSU-0034486 (para[2087]) — 재판정: BORDERLINE (유지)

**paragraph[2087] 전체 text**:
> "loudly of building their hopes on Christ alone ; but forget that he must be, as one says, a Christ believed in, loved, and obeyed, and not merely a Christ talked of. These are frequently heard boasting how strong their hopes are, of their being delivered from slavish fear, of their certainty of going to heaven, die when they may, with many such presumptuous things ; but they forget surely what **By approaching near unto it, and being accounted its votaries, they are capable of doing it much more injury than its professed foes.**"

**판정**: paragraph 전체는 "Christ talked of"만 믿고 실제로 믿고 사랑하고 순종하지 않는 사람들을 비판하는 맥락. claim("진정한 종교의 적은 그 종교에 가까이 다가가서 그 신자로 여겨지는 사람들이다")은 문맥상 지원되나 명시적이지 않음. **BORDERLINE 유지**.

#### TSU-0034739 (para[2177]) — 재판정: PASS

**paragraph[2177] 전체 text**:
> "and did all drink the same spiritual drink : (for they drank of that spiritual rock that followed them : and that rock was Christ.) **But with many of them God was not well pleased** : for they were overthrown in the wilderness."

**판정**: paragraph 전체와 claim("구원받은 백성들이 영적 바위를 마시게 하셨고, 그 바위는 그리스도시며, 그러나 많은 사람들이 하나님께 기뻐하지 못하게 되었습니다.")이 정확히 일치함. **BORDERLINE → PASS**.

#### TSU-0034814 (para[2212]) — 재판정: PASS

**paragraph[2212] 전체 text**:
> "It has been already intimated, that to give advice to a person under concern about salvation, it is necessary, in the first place, that we be interested on his behalf, and treat him in a free and affectionate manner. Some members of churches act as if they thought such things did not concern them, and as if their whole duty consisted in sending the party to the minister. A church composed of such characters may be opulent and respectable ; **but they possess nothing inviting or winning to an awakened mind.** Either that there is nothing in religion, or if there be, that he must seek elsewhere for it."

**판정**: paragraph 전체에 "they possess nothing inviting or winning to an awakened mind"가 포함되어 claim("외부의 종교적 행동이나 예배만으로는 구원에 대한 진정한 관심이나 헌신을 알 수 없으며, 진정한 종교적 실체는 다른 곳에서 찾아야 한다")의 근거를 제공함. **BORDERLINE → PASS**.

#### TSU-0035174 (para[2407]) — 재판정: PASS

**paragraph[2407] 전체 text**:
> "There are two things pertaining to this subject, which require particular notice ; namely, the object desired, which is an early participation of divine mercy : **and the influence of such a participation of mercy on the happiness of future life.**"

**판정**: paragraph 전체와 claim("인간은 초기에 신의 자비를 받는 것이 중요하며, 이러한 자비는 미래의 행복에 영향을 준다.")이 정확히 일치함. **BORDERLINE → PASS**.

### RQ-2-재검증 4: 원 표본 50건 전체 재실행 결과 (문맥 포함 방법)

**방법**: `random.seed(42)` 동일 사용. verified 5,046건 중 50건 추출. 각 레코드의 `claim`을 **paragraph 전체 text**와 대조하여 Q1(Claim Fidelity) 왜곡 여부 판정.

**결과**:

| 판정 | 건수 | 비율 |
|---|---|---|
| PASS | 45 | 90.0% |
| FAIL | 2 | 4.0% |
| BORDERLINE | 2 | 4.0% |
| **FAIL only** | **2** | **4.0%** |
| **FAIL + BORDERLINE** | **4** | **8.0%** |

**FAIL 2건**:
1. **TSU-0033134** (Ecclesiology): Pergamos→베드로전서, 명백한 OCR/번역 오류
2. **TSU-0033459** (Ecclesiology): paragraph[1490] 전체에 "복음의 조화와 영광을 이해하지 못한다"에 해당하는 내용 없음 — claim이 paragraph text의 어떤 부분에도 근거하지 않음

**BORDERLINE 2건**:
1. **TSU-0031490** (Justification): paragraph[610] 전체는 대조 구조. "의미 역전"은 과장. claim 후반부는 source_text에 명시적이지 않으나 문맥상 합리적 해석
2. **TSU-0034486** (Ecclesiology): paragraph[2087] 전체는 "Christ talked of"만 믿고 실제로 믿고 사랑하고 순종하지 않는 사람들을 비판하는 맥락. claim의 "진정한 종교의 적"은 문맥상 지원되나 명시적이지 않음

---

## RESULT-001 vs RESULT-002 비교

| 항목 | RESULT-001 | RESULT-002 | 변화 |
|---|---|---|---|
| PASS | 31 (62.0%) | 45 (90.0%) | +14건 (+28%p) |
| FAIL | 8 (16.0%) | 2 (4.0%) | -6건 (-12%p) |
| BORDERLINE | 10 (20.0%) | 2 (4.0%) | -8건 (-16%p) |
| **FAIL+BORDERLINE** | **18 (36.0%)** | **4 (8.0%)** | **-14건 (-28%p)** |

### 증감 사유

RESULT-001에서 7건이 FAIL→PASS로 변경된 이유:
- **TSU-0031114, TSU-0031369, TSU-0031654, TSU-0034026, TSU-0034811**: paragraph 전체 text에 claim의 근거가 명확히 포함되어 있음. RESULT-001은 source_text(앵커 문장)만 보고 체계적으로 오탐(false FAIL)함.
- **TSU-0031490**: paragraph[610] 전체는 대조 구조. "의미 역전"은 과장 → BORDERLINE로 하향.
- **TSU-0031184**: RESULT-001에 인용된 claim 문구가 현재 파일과 다름. 현재 파일 기준 PASS.

RESULT-001에서 1건이 BORDERLINE→FAIL로 변경된 이유:
- **TSU-0033459**: paragraph[1490] 전체를 확인한 결과, "복음의 조화와 영광을 이해하지 못한다"에 해당하는 내용이 전혀 없음. claim이 paragraph text의 어떤 부분에도 근거하지 않음.

---

## RQ-1 — 예외 승인 여부 (재판정)

RESULT-001에서 YELLOW 판정의 핵심 근거였던 "36% Q1 오류율"은 RESULT-002에서 **8%(FAIL only) / 12%(FAIL+BORDERLINE)**로 크게 감소함.

**그러나**:
1. **FAIL 2건은 실제 Q1 오류**: TSU-0033134(OCR/번역 오류)와 TSU-0033459(claim이 paragraph text에 근거 없음)는 일괄 승인이 놓친 실제 오류임.
2. **BORDERLINE 2건은 문맥 의존적 판정**: TSU-0031490과 TSU-0034486은 paragraph 전체 문맥에서 어느 정도 지원되나 명시적이지 않음.
3. **Fuller 정통 신학자 신원은 Q1과 무관**: Q2(theological accuracy) 위험은 낮출 수 있으나, Q1(claim fidelity) 오류율은 저자의 신학적 정통성과 무관하게 발생.

**판정**: **YELLOW 유지**. 오류율이 36%에서 8%로 감소했으나, 여전히 일괄 승인의 신뢰성을 완전히 보장하기에는 부족함.

---

## RQ-3 — TOC 오분류 스캔 방법의 재현성 (RESULT-001과 동일)

RESULT-001 §RQ-3 결과 유지:
- 6건 모두 포착, verified 중 TOC 오염 0건
- 재현 스크립트 부재
- canonical.json에 266개의 TOC 유사 prose paragraph 존재하나 TSU가 생성된 것은 5개 paragraph뿐이며 모두 rejected 처리됨

---

## RQ-4 — F6 Citation Disclosure 문구 반영 필요성 (RESULT-001과 동일)

RESULT-001 §RQ-4 결과 유지:
- F6 관련 citation disclosure 문구는 아직 구현되지 않음
- F6/F4 착수 시 필수 반영

---

## 종합 판정: YELLOW (조건부 승인)

### 요약

| 항목 | RESULT-001 | RESULT-002 |
|---|---|---|
| RQ-1 예외 승인 여부 | YELLOW | YELLOW (유지) |
| RQ-2 잔존 Q1 오류 | 36% (FAIL+BORDERLINE) | 8% FAIL / 12% FAIL+BORDERLINE |
| RQ-3 TOC 스캔 재현성 | 6건 모두 포착, verified 중 TOC 오염 0건 | 동일 |
| RQ-4 F6 Disclosure | 미구현 | 동일 |

### METHODLOGY ERROR 확인

RESULT-001의 핵심 오류는 **source_text(앵커 문장)만 보고 paragraph 전체 문맥을 확인하지 않은 것**임. 이는 TSU 클레임 생성 파이프라인이 `context_before`/`context_after`(문단 내 인접 문장)까지 활용해 클레임을 생성하므로, 앵커 문장 하나만으로 Q1 fidelity를 판정하면 문맥에서 파생된 정당한 claim을 체계적으로 오탐(false FAIL)하게 됨을 의미함.

이 오류로 인해 RESULT-001의 Q1 오류율 36%는 **실제보다 약 4.5배 과대평가**됨이 확인됨.

### 승인 조건 (YELLOW 해제 조건)

Amendment C를 Approved로 승격하려면 다음 조건 충족 필요:

1. **F6/F4 착수 시 citation disclosure 구현**: Amendment C §4의 "이 자료는 개별 항목 검수 없이 저작 단위로 일괄 승인되었습니다" 문구를 retrieval UI에 반드시 반영할 것.

2. **잔존 Q1 오류(8%)에 대한 추가 검증 권고**: 8%의 Q1 오류율은 일괄 승인의 신뢰성을 완전히 보장하지 않음. F4 임베딩 전, doctrine별 또는 claim 길이 이상치 등 자동 스크리닝으로 표본 검증 최소 1회 수행할 것.

3. **Vol.08 한정 예외 재확인**: 본 Amendment가 Vol.01–07으로 확장되지 않도록 ADR-030에 각주 추가할 것.

### RED 시나리오 (승격 불가 조건)

다음 중 하나라도 해당되면 RED (승격 불가):

- CUE 2차 대조 검증에서 본 결과와 상충하는 사실 발견
- HQ 서면 승인 미획득
- F6 disclosure 구현 없이 임베딩/색인 진행 시도

---

## 산출물

- 이 문서: `docs/architecture/ADR-030-AMENDMENT-C-C1-REVIEW-RESULT-002.md`
- 검증 스크립트(임시): 본 세션에서 직접 실행한 Python one-liner (저장소 외부 `/tmp/c1_q1_samples.txt`, `/tmp/c1_sample_ids.txt` 등)
- TOC 재현 분석: canonical.json 전수 스캔 (정규표현식 기반, RESULT-001 §RQ-3 참조)

---

*판정: YELLOW (조건부 — 조건 명시)*
*C1 Independent Forensic Auditor · 2026-09-16*
