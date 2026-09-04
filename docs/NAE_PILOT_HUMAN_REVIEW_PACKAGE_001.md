# NAE Pilot Human Review Package 001

**Project:** NAE-PILOT-HUMAN-REVIEW-PACKAGE-001
**작성일:** 2026-08-08
**성격:** 목회자/신학 검토자용 최종 검토 자료 준비. **AI는 어떤 TSU도 승인/거부하지 않는다.**
**Authority:** `docs/NAE_PILOT_TSU_REVIEW_PREPARATION_001.md`(10건 확정, 교체 없음)
**Git Commit/Push:** 미수행.

---

## 사용 안내(검토자용)

- `[ORIGINAL TEXT]`의 굵게 표시된 문장이 실제로 claim이 추출된 원문
  문장이며, 앞/뒤 문장은 동일 문단(paragraph) 내에서 **직전/직후
  문장을 canonical.json에서 그대로 가져온 것**이다 — 요약·재구성
  없음. 문단 시작/끝이라 앞/뒤 문장이 없는 경우는 "(문단 시작 —
  이전 문장 없음)" 등으로 명시했다.
- `[FLAGS]`는 CUE가 사전 관찰한 참고 표시일 뿐이며 **최종 신학적
  판단이 아니다** — 검토자가 무시하거나 재평가할 수 있다.
- 모든 `[REVIEW DECISION]`은 `PENDING`이다. AI가 사전에 승인/거부한
  항목은 없다.

---

==================================================
PILOT TSU REVIEW #01
==================================================
**TSU ID:** TSU-0000713
**SOURCE:** BAP-CHURCH-DAGG-001
**WORK:** WORK-DAGG-CHURCH-ORDER-001 (John L. Dagg, *Church Order*, 1871)

**[ORIGINAL TEXT]**
(앞 문장) Also in this, that the churches were compared with each other...(전체 문맥은 원문 paragraph 참고)
**(claim 원문) "No church communicated with me as concerning giving and receiving, but ye only." "As distinct bodies, they sent and received salutations,"**
(문단 끝 — 다음 문장 없음)

**[THEOLOGICAL CLAIM]**
초기 교회들은 서로 다른 교회들과 비교되었으며, 각 교회는 독립된 단체로서 서로 인사와 연락을 주고받았다.

**[DOCTRINE]**
Ecclesiology

**[SCRIPTURE]**
(비어 있음 — TSU 레코드의 `scriptures` 필드는 빈 배열)

**[CITATION]**
`["* Rom. xvi. 16; 1 Cor. xvi. 19."]`

**[EVIDENCE ASSESSMENT]**
원문 자체가 빌립보서 4:15("아무 교회도 나와 더불어 주고 받는 내 일에 참여하지 아니하고 오직 너희만 하였느니라")를 직접 인용하고 있다. 그러나 TSU의 `scriptures` 필드는 비어 있어, **원문에 실제로 존재하는 성경 인용이 metadata에는 반영되지 않은 상태**다.

**[METADATA PROVENANCE]**
```
metadata_schema_version: 1.1.0
source_id: BAP-CHURCH-DAGG-001
author_id: dagg_john_l
work_id: WORK-DAGG-CHURCH-ORDER-001
edition_id: WORK-DAGG-CHURCH-ORDER-001-1871
volume_id: null
publication_year: 1871
source_type: reference
copyright_status: public_domain
usage_permission: research
access_control: public
tsu_access: full
category: null
category_status: AUTHORITATIVE_SOURCE_MISSING
citation_policy: null
citation_policy_status: AUTHORITATIVE_SOURCE_MISSING
metadata_provenance.crosswalk_id: f914f6c442983e59
```

**[REVIEW QUESTIONS]**
1. Claim Fidelity: 원문의 두 문장을 "교회 간 비교/독립성/인사 교환"으로 재진술한 것이 정확한가?
2. Theological Accuracy: 신약 지역교회의 독립성(자율성) 개념 서술이 보수적 침례교 교회론과 충돌하지 않는가?
3. Doctrine Classification: Ecclesiology 분류가 정확한가, 아니면 Church Covenant/다른 범주가 더 적합한가?
4. Evidence: 위 두 원문 문장이 claim을 충분히 뒷받침하는가?
5. Scripture/Citation: 원문의 빌립보서 4:15 인용이 `scriptures` 필드에 누락된 것이 이 claim의 신뢰도에 영향을 주는가?

**[FLAGS]**
`SCRIPTURE_MISMATCH` — 원문에 명시적 성경 인용이 있으나 `scriptures` 필드가 비어 있음(임의 보충하지 않았음, 검토자 판단 필요)

**[REVIEW DECISION]**
PENDING

---

==================================================
PILOT TSU REVIEW #02
==================================================
**TSU ID:** TSU-0000199
**SOURCE:** BAP-CHURCH-DAGG-001
**WORK:** WORK-DAGG-CHURCH-ORDER-001

**[ORIGINAL TEXT]**
(앞 문장) Hence, the rendering to smear is liable to mislead us into the opinion that the effect is here spoken of, and not the process, when the reverse is manifestly true.
**(claim 원문) "The verb never signifies this process."**
(뒤 문장) It may signify the effect of it, but never the process itself.

**[THEOLOGICAL CLAIM]**
동사 'baptizō'는 액체를 고체에 적용하는 과정을 의미하지 않는다.

**[DOCTRINE]**
Baptism

**[SCRIPTURE]**
(비어 있음)

**[CITATION]**
`["2. Barro appears, in some cases, to be used in the secondary"]`(각주 조각, 문장이 완결되지 않음)

**[EVIDENCE ASSESSMENT]**
헬라어 원어(βαπτίζω) 어원 논증의 일부로, 앞뒤 문맥과 함께 읽으면 "효과(effect)는 의미할 수 있으나 과정(process) 자체는 의미하지 않는다"는 저자의 언어학적 주장 흐름이 자연스럽게 이어진다. 다만 citation 각주 자체가 잘려 있어 그 근거를 온전히 확인하기 어렵다.

**[METADATA PROVENANCE]**
```
metadata_schema_version: 1.1.0
source_id: BAP-CHURCH-DAGG-001
author_id: dagg_john_l
work_id: WORK-DAGG-CHURCH-ORDER-001
edition_id: WORK-DAGG-CHURCH-ORDER-001-1871
volume_id: null
publication_year: 1871
source_type: reference
copyright_status: public_domain
usage_permission: research
access_control: public
tsu_access: full
category: null
category_status: AUTHORITATIVE_SOURCE_MISSING
citation_policy: null
citation_policy_status: AUTHORITATIVE_SOURCE_MISSING
metadata_provenance.crosswalk_id: f914f6c442983e59
```

**[REVIEW QUESTIONS]**
1. Claim Fidelity: "이 동사는 이 과정을 결코 의미하지 않는다"를 "baptizō는 과정을 의미하지 않는다"로 일반화한 것이 정확한가(대명사 "this process"가 지시하는 대상 확인 필요 — 앞 문맥의 "smear" 관련 과정)?
2. Theological Accuracy: 침례(침수)와 관련된 헬라어 어원 논증이 신학적으로 왜곡되지 않았는가?
3. Doctrine Classification: Baptism 분류가 적절한가?
4. Evidence: 각주가 잘려 있는 상태에서도 claim이 충분히 뒷받침되는가, 아니면 원본 각주 전문 확인이 필요한가?
5. Scripture/Citation: 이 언어학적 논증에 특정 성경 구절이 결부되어야 하는가, 아니면 성경 인용 없이도 타당한가?

**[FLAGS]**
`AMBIGUOUS` — citation 각주가 문장 중간에서 잘려 근거를 온전히 확인할 수 없음. 대명사("this process")가 가리키는 대상이 claim 문장만으로는 불명확 — 위 문맥 확인 필요

**[REVIEW DECISION]**
PENDING

---

==================================================
PILOT TSU REVIEW #03
==================================================
**TSU ID:** TSU-0000330
**SOURCE:** BAP-CHURCH-DAGG-001
**WORK:** WORK-DAGG-CHURCH-ORDER-001

**[ORIGINAL TEXT]**
(앞 문장) The objection states that little resemblance can be found between the mode of eating bread and the mode in which Christ's body was broken and given for us.
**(claim 원문) "A well executed picture of the crucifixion, such as may be seen in Catholic chapels, has much more resemblance to the body of Christ, than is furnished by the breaking and eating of bread; and yet no one would think of substituting the picture for the bread, in the celebration of the ordinance."**
(뒤 문장) In like manner, some means might have been devised for representing more exactly the sufferings of Christ...

**[THEOLOGICAL CLAIM]**
성례의 목적을 고려할 때, 성찬에서 빵을 먹음으로써 그리스도의 죽음을 기억하는 것이 더 적절하다.

**[DOCTRINE]**
Lord's Supper

**[SCRIPTURE]**
(비어 있음)

**[CITATION]**
(비어 있음)

**[EVIDENCE ASSESSMENT]**
원문은 "그림이 빵보다 그리스도의 몸에 더 유사하지만, 그렇다고 그림으로 대체하지 않는다"는 **반론에 대한 답변** 구조다 — claim이 이 반어법적 논증의 결론("빵이 더 적절하다")만 취해 앞뒤 논증 흐름 없이는 다소 단정적으로 읽힐 수 있다. 원문의 논증 취지(외형적 유사성보다 제정된 방식 자체가 중요하다는 논지)를 정확히 담았는지는 앞뒤 문맥과 함께 판단이 필요하다.

**[METADATA PROVENANCE]**
```
metadata_schema_version: 1.1.0
source_id: BAP-CHURCH-DAGG-001
author_id: dagg_john_l
work_id: WORK-DAGG-CHURCH-ORDER-001
edition_id: WORK-DAGG-CHURCH-ORDER-001-1871
volume_id: null
publication_year: 1871
source_type: reference
copyright_status: public_domain
usage_permission: research
access_control: public
tsu_access: full
category: null
category_status: AUTHORITATIVE_SOURCE_MISSING
citation_policy: null
citation_policy_status: AUTHORITATIVE_SOURCE_MISSING
metadata_provenance.crosswalk_id: f914f6c442983e59
```

**[REVIEW QUESTIONS]**
1. Claim Fidelity: 반어법적 답변 문장 하나만으로 "빵을 먹는 것이 더 적절하다"는 claim이 원문의 논증 취지를 정확히 담고 있는가?
2. Theological Accuracy: 성찬의 상징(sign)과 그림(image) 사용에 대한 개신교/침례교 관점(우상 금지 원칙 포함)과 부합하는가?
3. Doctrine Classification: Lord's Supper 분류가 정확한가?
4. Evidence: citation/scripture 없이 이 claim만으로 충분한 근거가 되는가?
5. Scripture/Citation: 성찬 제정 관련 성경 구절(마 26:26-28, 고전 11:23-26 등)이 이 claim에 연결되어야 하는가?

**[FLAGS]**
`CONTEXT_LOSS` — 반론에 대한 답변 구조의 결론부만 추출되어, 원 논증의 전체 취지 확인이 필요함 · `EVIDENCE_INSUFFICIENT` — scripture/citation 모두 없음

**[REVIEW DECISION]**
PENDING

---

==================================================
PILOT TSU REVIEW #04
==================================================
**TSU ID:** TSU-0000033
**SOURCE:** BAP-CHURCH-DAGG-001
**WORK:** WORK-DAGG-CHURCH-ORDER-001

**[ORIGINAL TEXT]**
(문단 시작 — 이전 문장 없음)
**(claim 원문) "A powerful motive, to love and obey Christ, is drawn from the love which he has manifested in dying for us."**
(뒤 문장) Paul felt this in an overpowering degree, when he said, "..."(다음 문장은 바울 인용으로 이어짐 — TSU 레코드 범위 밖)

**[THEOLOGICAL CLAIM]**
그리스도의 사랑과 복종의 강력한 동기는 우리를 위해 죽으신 그분의 사랑에서 비롯됩니다.

**[DOCTRINE]**
Soteriology

**[SCRIPTURE]**
(비어 있음)

**[CITATION]**
(비어 있음)

**[EVIDENCE ASSESSMENT]**
원문 문장과 claim이 거의 1:1로 대응하는 직접 재진술이다. 다음 문장이 바울의 발언(성경 인용으로 추정)으로 이어지지만 이번 TSU 레코드 범위에는 포함되지 않았다.

**[METADATA PROVENANCE]**
```
metadata_schema_version: 1.1.0
source_id: BAP-CHURCH-DAGG-001
author_id: dagg_john_l
work_id: WORK-DAGG-CHURCH-ORDER-001
edition_id: WORK-DAGG-CHURCH-ORDER-001-1871
volume_id: null
publication_year: 1871
source_type: reference
copyright_status: public_domain
usage_permission: research
access_control: public
tsu_access: full
category: null
category_status: AUTHORITATIVE_SOURCE_MISSING
citation_policy: null
citation_policy_status: AUTHORITATIVE_SOURCE_MISSING
metadata_provenance.crosswalk_id: f914f6c442983e59
```

**[REVIEW QUESTIONS]**
1. Claim Fidelity: 원문과 claim이 사실상 동일한 의미인가?
2. Theological Accuracy: "그리스도의 사랑이 순종의 동기"라는 진술이 대리속죄 신학과 일관되는가?
3. Doctrine Classification: Soteriology가 적절한가, 아니면 Sanctification(성화의 동기 부여)이 더 정확한가?
4. Evidence: 원문 문장 자체 외 추가 근거가 필요한가?
5. Scripture/Citation: 다음 문장의 바울 인용(추정 로마서/고린도후서 등)을 이 TSU에 함께 반영해야 하는가?

**[FLAGS]**
`NO_OBJECTION`(claim이 원문과 직접 대응, 다만 doctrine 이중분류 가능성은 검토자 판단 필요)

**[REVIEW DECISION]**
PENDING

---

==================================================
PILOT TSU REVIEW #05
==================================================
**TSU ID:** TSU-0000025
**SOURCE:** BAP-CHURCH-DAGG-001
**WORK:** WORK-DAGG-CHURCH-ORDER-001

**[ORIGINAL TEXT]**
(문단 시작 — 이전 문장 없음)
**(claim 원문) "To love God with all the heart is the sum of all duty."**
(뒤 문장) Love must be exercised according to the relations which we sustain...(이하 생략)

**[THEOLOGICAL CLAIM]**
하나님을 전심으로 사랑하는 것이 모든 의무의 총합이다.

**[DOCTRINE]**
Sanctification

**[SCRIPTURE]**
(비어 있음)

**[CITATION]**
(비어 있음)

**[EVIDENCE ASSESSMENT]**
원문 문장은 마태복음 22:37-38(대계명)의 명백한 반향(echo)이나, 직접 인용 표기는 없다. claim은 원문을 정확히 재진술했다.

**[METADATA PROVENANCE]**
```
metadata_schema_version: 1.1.0
source_id: BAP-CHURCH-DAGG-001
author_id: dagg_john_l
work_id: WORK-DAGG-CHURCH-ORDER-001
edition_id: WORK-DAGG-CHURCH-ORDER-001-1871
volume_id: null
publication_year: 1871
source_type: reference
copyright_status: public_domain
usage_permission: research
access_control: public
tsu_access: full
category: null
category_status: AUTHORITATIVE_SOURCE_MISSING
citation_policy: null
citation_policy_status: AUTHORITATIVE_SOURCE_MISSING
metadata_provenance.crosswalk_id: f914f6c442983e59
```

**[REVIEW QUESTIONS]**
1. Claim Fidelity: 원문과 claim이 정확히 대응하는가?
2. Theological Accuracy: "사랑 = 모든 의무의 총합"이라는 진술이 율법과 복음의 관계에서 균형 잡혀 있는가?
3. Doctrine Classification: Sanctification이 적절한가, 아니면 다른 범주(예: 대계명 관련 별도 범주)가 필요한가?
4. Evidence: 원문 자체 외 추가 근거가 필요한가?
5. Scripture/Citation: 마태복음 22:37-38(대계명)과의 명백한 연관성에도 `scriptures`가 비어 있는 것이 적절한가?

**[FLAGS]**
`SCRIPTURE_MISMATCH` — 대계명(마 22:37-38)의 명백한 반향인데 `scriptures` 필드 비어 있음(원문 자체가 직접 인용 표기를 하지 않아 파서가 감지하지 못한 것으로 추정, 임의 보충 안 함)

**[REVIEW DECISION]**
PENDING

---

==================================================
PILOT TSU REVIEW #06
==================================================
**TSU ID:** TSU-0003524
**SOURCE:** BAP-CHURCH-HISCOX
**WORK:** WORK-HISCOX-STANDARD-MANUAL-001 (Edward T. Hiscox, *The Standard Manual for Baptist Churches*, 1890)

**[ORIGINAL TEXT]**
(앞 문장) Church members are supposed to be regenerate persons bearing the fruits of the Spirit...(전체 문맥은 원문 참고)
**(claim 원문) "The evil passions of even good men may triumph over piety, and partisan strife may destroy the peace and the prosperity of the body of Christ."**
(뒤 문장) All this should, if possible, be avoided.

**[THEOLOGICAL CLAIM]**
선한 사람들의 악한 정서가 경건을 이길 수 있고, 당파적인 분쟁이 그리스도의 몸의 평화와 번영을 파괴할 수 있다.

**[DOCTRINE]**
Ecclesiology

**[SCRIPTURE]**
(비어 있음)

**[CITATION]**
`["5. Because that a case of discipline undertaken under excitement is almost certain"]`(각주 조각)

**[EVIDENCE ASSESSMENT]**
원문 문장을 거의 1:1로 재진술했다. 다음 문장("All this should, if possible, be avoided")이 다음 순번 TSU(#08, TSU-0003525)의 claim과 직접 이어진다 — 두 TSU가 원문 상 인접 문장임을 확인.

**[METADATA PROVENANCE]**
```
metadata_schema_version: 1.1.0
source_id: BAP-CHURCH-HISCOX
author_id: hiscox_edward_t
work_id: WORK-HISCOX-STANDARD-MANUAL-001
edition_id: WORK-HISCOX-STANDARD-MANUAL-001-1890
volume_id: null
publication_year: 1890
source_type: reference
copyright_status: public_domain
usage_permission: research
access_control: public
tsu_access: full
category: null
category_status: AUTHORITATIVE_SOURCE_MISSING
citation_policy: null
citation_policy_status: AUTHORITATIVE_SOURCE_MISSING
metadata_provenance.crosswalk_id: 260d31b2331a3f8b
```

**[REVIEW QUESTIONS]**
1. Claim Fidelity: 원문과 claim이 정확히 대응하는가?
2. Theological Accuracy: "선한 사람도 악한 정서에 굴복할 수 있다"는 진술이 성도의 죄성/성화 교리와 일관되는가?
3. Doctrine Classification: Ecclesiology가 적절한가, 아니면 Church Discipline(다음 TSU #08과 동일 주제군)이 더 정확한가?
4. Evidence: citation 각주가 잘려 있는 상태에서도 충분한가?
5. Scripture/Citation: 교회 내 분쟁/화평 관련 성경 구절(빌 4:2-3, 약 3:16 등)을 연결할 필요가 있는가?

**[FLAGS]**
`NO_OBJECTION`(claim이 원문과 직접 대응) · 참고: 다음 TSU(#08)와 원문상 인접 문장(같은 문단, 연속된 논증) — 두 TSU를 함께 검토 권고

**[REVIEW DECISION]**
PENDING

---

==================================================
PILOT TSU REVIEW #07
==================================================
**TSU ID:** TSU-0003661
**SOURCE:** BAP-CHURCH-HISCOX
**WORK:** WORK-HISCOX-STANDARD-MANUAL-001

**[ORIGINAL TEXT]**
(앞 문장) Acts 11:38.(각주/구절 참조 표기)
**(claim 원문) "Then Peter said unto them, Repent, and be baptized every one of you in the name of Jesus Christ for the remission of sins."**
(뒤 문장) Acts 16:30, 31.(다음 참조 표기)

**[THEOLOGICAL CLAIM]**
예수 그리스도의 이름으로 죄의 사함을 받기 위해 각자가 회개하고 세례를 받아야 한다.

**[DOCTRINE]**
Baptism

**[SCRIPTURE]**
(비어 있음)

**[CITATION]**
`["18. Then hath God also to the Gentiles granted repentance"]`(각주 조각)

**[EVIDENCE ASSESSMENT]**
원문 문장은 **사도행전 2:38의 직접 인용**이다. claim이 이를 정확히 재진술했으나, `scriptures` 필드는 비어 있다 — 앞뒤 문장이 다른 성경 구절 참조 표기("Acts 11:38", "Acts 16:30,31")인 것으로 보아 이 부분은 저자가 성경 구절들을 나열한 목록의 일부일 가능성이 있다(회개+세례 관련 구절 모음).

**[METADATA PROVENANCE]**
```
metadata_schema_version: 1.1.0
source_id: BAP-CHURCH-HISCOX
author_id: hiscox_edward_t
work_id: WORK-HISCOX-STANDARD-MANUAL-001
edition_id: WORK-HISCOX-STANDARD-MANUAL-001-1890
volume_id: null
publication_year: 1890
source_type: reference
copyright_status: public_domain
usage_permission: research
access_control: public
tsu_access: full
category: null
category_status: AUTHORITATIVE_SOURCE_MISSING
citation_policy: null
citation_policy_status: AUTHORITATIVE_SOURCE_MISSING
metadata_provenance.crosswalk_id: 260d31b2331a3f8b
```

**[REVIEW QUESTIONS]**
1. Claim Fidelity: 사도행전 2:38 인용을 "회개+세례+죄사함"으로 재진술한 것이 정확한가?
2. Theological Accuracy: 세례와 죄사함의 관계(침례교 신학에서 세례는 죄사함의 "상징"이지 "수단"이 아님) — claim이 이 구분을 흐리지 않는가?
3. Doctrine Classification: Baptism이 적절한가?
4. Evidence: 원문이 성경 직접 인용이므로 evidence는 충분하다고 볼 수 있는가?
5. Scripture/Citation: `scriptures` 필드에 "Acts 2:38"이 반드시 채워져야 하는가(현재 누락) — 앞뒤 참조 구절(Acts 11:38, Acts 16:30-31)도 함께 확인 필요한가?

**[FLAGS]**
`SCRIPTURE_MISMATCH` — 원문이 사도행전 2:38 직접 인용인데 `scriptures` 필드가 비어 있음 · `DOCTRINE_MISMATCH` 가능성 — claim이 "세례로 죄사함을 받는다"로 읽힐 경우 침례교의 상징적 세례관과 문구가 어긋날 수 있음(신학적 정밀 검토 필요)

**[REVIEW DECISION]**
PENDING

---

==================================================
PILOT TSU REVIEW #08
==================================================
**TSU ID:** TSU-0003525
**SOURCE:** BAP-CHURCH-HISCOX
**WORK:** WORK-HISCOX-STANDARD-MANUAL-001

**[ORIGINAL TEXT]**
(앞 문장) The evil passions of even good men may triumph over piety, and partisan strife may destroy the peace and the prosperity of the body of Christ.(= TSU-0003524의 claim 원문과 동일 문장)
**(claim 원문) "All this should, if possible, be avoided."**
(뒤 문장) Corrective discipline seeks to heal offenses; but it is better...(이하 생략)

**[THEOLOGICAL CLAIM]**
교회에서 일어날 수 있는 악한 정서와 파당적인 분쟁을 가능한 한 피해야 한다.

**[DOCTRINE]**
Church Discipline

**[SCRIPTURE]**
(비어 있음)

**[CITATION]**
`["5. Because that a case of discipline undertaken under excitement is almost certain"]`(TSU-0003524와 동일 각주 — 인접 문장이므로 동일 각주 범위에 속함)

**[EVIDENCE ASSESSMENT]**
원문 자체가 매우 짧고("All this should, if possible, be avoided") 지시대명사 "All this"가 가리키는 대상은 **직전 TSU(#06, TSU-0003524)의 내용**이다. 이 TSU 단독으로는 의미가 불완전하며, 반드시 앞 문맥(#06)과 함께 읽어야 한다.

**[METADATA PROVENANCE]**
```
metadata_schema_version: 1.1.0
source_id: BAP-CHURCH-HISCOX
author_id: hiscox_edward_t
work_id: WORK-HISCOX-STANDARD-MANUAL-001
edition_id: WORK-HISCOX-STANDARD-MANUAL-001-1890
volume_id: null
publication_year: 1890
source_type: reference
copyright_status: public_domain
usage_permission: research
access_control: public
tsu_access: full
category: null
category_status: AUTHORITATIVE_SOURCE_MISSING
citation_policy: null
citation_policy_status: AUTHORITATIVE_SOURCE_MISSING
metadata_provenance.crosswalk_id: 260d31b2331a3f8b
```

**[REVIEW QUESTIONS]**
1. Claim Fidelity: 지시대명사 "All this"를 "악한 정서와 파당적 분쟁"으로 명시적으로 풀어 쓴 것이 정확한가(원문 자체는 이를 명시하지 않음)?
2. Theological Accuracy: 권징(discipline)에서 "피해야 한다"는 소극적 진술이 교회 권징의 적극적 의무와 균형을 이루는가?
3. Doctrine Classification: Church Discipline이 적절한가?
4. Evidence: TSU 단독으로 evidence가 불완전하지 않은가(§상단 참고)?
5. Scripture/Citation: 교회 권징 관련 성경 구절(마 18:15-17, 갈 6:1 등)이 필요한가?

**[FLAGS]**
`CONTEXT_LOSS` — 지시대명사("All this")가 가리키는 내용이 TSU-0003524(#06)에만 있고 이 TSU 자체에는 없어, 단독으로는 의미 파악이 어려움. 두 TSU를 세트로 검토 권고

**[REVIEW DECISION]**
PENDING

---

==================================================
PILOT TSU REVIEW #09
==================================================
**TSU ID:** TSU-0003893
**SOURCE:** BAP-CHURCH-HISCOX
**WORK:** WORK-HISCOX-STANDARD-MANUAL-001

**[ORIGINAL TEXT]**
(앞 문장) The one prevailing argument with them is sympathy.
**(claim 원문) "To them it seems kindly and fraternal to invite all who say they love our common Lord and Saviour to unite in commemorating his death in the Supper."**
(뒤 문장) Even if they have not been baptized, they themselves believe...(이하 생략, "개방 성찬"을 주장하는 이들에 대한 서술로 이어짐)

**[THEOLOGICAL CLAIM]**
일부 사람들은 주님의 만찬에서 죽으신 주님을 기념하는 것을 모든 사람들이 함께 할 수 있도록 초청하는 것이 친절하고 형제적인 행동이라고 생각한다.

**[DOCTRINE]**
Lord's Supper

**[SCRIPTURE]**
(비어 있음)

**[CITATION]**
`["3. They do not invite immersed members"]`(각주 조각)

**[EVIDENCE ASSESSMENT]**
원문의 "To them"("그들에게는")은 **저자(Hiscox)가 아니라 개방 성찬(open communion)을 주장하는 제3자의 입장**을 가리키는 것으로 읽힌다("the one prevailing argument **with them**" — 앞 문장에서 이미 특정 집단을 지시). claim은 "일부 사람들은 ~라고 생각한다"로 이 3인칭 서술을 정확히 반영했으나, **저자 본인의 입장(폐쇄/제한 성찬)인지 아니면 저자가 소개·비판하는 타인의 입장인지**를 검토자가 명확히 구분해야 한다.

**[METADATA PROVENANCE]**
```
metadata_schema_version: 1.1.0
source_id: BAP-CHURCH-HISCOX
author_id: hiscox_edward_t
work_id: WORK-HISCOX-STANDARD-MANUAL-001
edition_id: WORK-HISCOX-STANDARD-MANUAL-001-1890
volume_id: null
publication_year: 1890
source_type: reference
copyright_status: public_domain
usage_permission: research
access_control: public
tsu_access: full
category: null
category_status: AUTHORITATIVE_SOURCE_MISSING
citation_policy: null
citation_policy_status: AUTHORITATIVE_SOURCE_MISSING
metadata_provenance.crosswalk_id: 260d31b2331a3f8b
```

**[REVIEW QUESTIONS]**
1. Claim Fidelity: "일부 사람들은 ~라고 생각한다"는 표현이 원문의 3인칭 서술(타인의 견해 소개)을 정확히 반영하는가?
2. Theological Accuracy: 개방 성찬(open communion) 논쟁에서 저자의 실제 입장(전통적 침례교는 폐쇄/제한 성찬 지지)과 claim이 혼동을 일으키지 않는가?
3. Doctrine Classification: Lord's Supper가 적절한가?
4. Evidence: 앞뒤 문맥(§상단) 없이 이 claim만 보면 저자 자신의 견해로 오독될 위험이 있는가?
5. Scripture/Citation: 성찬 참여 자격 관련 성경적 근거가 이 논쟁의 어느 편에 인용되어야 하는가?

**[FLAGS]**
`AMBIGUOUS` — claim이 저자 본인의 신학적 입장인지, 저자가 소개(및 통상 비판)하는 타 진영의 견해인지 이 TSU만으로는 명확하지 않음(원문 문맥상 후자로 추정) — **오독 위험이 있어 검토자의 명확한 판단이 특히 중요**

**[REVIEW DECISION]**
PENDING

---

==================================================
PILOT TSU REVIEW #10
==================================================
**TSU ID:** TSU-0003647
**SOURCE:** BAP-CHURCH-HISCOX
**WORK:** WORK-HISCOX-STANDARD-MANUAL-001

**[ORIGINAL TEXT]**
(앞 문장) 2 Acts 17:30.(구절 참조 표기)
**(claim 원문) "And the times of this ignorance God winked at, but now commandeth all men everywhere to repent."**
(뒤 문장) Rom. 16:26; Mark 1:15; Rom. 1:15-17.(다음 참조 표기 목록)

**[THEOLOGICAL CLAIM]**
하나님은 이전에는 무지한 시대를 용납하셨지만 이제는 모든 사람에게 어디서나 회개할 것을 명령하시고 계심

**[DOCTRINE]**
Soteriology

**[SCRIPTURE]**
(비어 있음)

**[CITATION]**
`["18. Then hath God also to the Gentiles granted repentance"]`(각주 조각)

**[EVIDENCE ASSESSMENT]**
원문 문장은 **사도행전 17:30의 직접 인용**(KJV)이다. 앞뒤 문장도 "Acts 17:30", "Rom. 16:26; Mark 1:15; Rom. 1:15-17" 등 성경 구절 참조 목록으로, 저자가 회개 명령에 관한 성경 구절들을 나열한 목록의 일부로 판단된다. claim은 인용을 정확히 재진술했으나 `scriptures` 필드는 비어 있다.

**[METADATA PROVENANCE]**
```
metadata_schema_version: 1.1.0
source_id: BAP-CHURCH-HISCOX
author_id: hiscox_edward_t
work_id: WORK-HISCOX-STANDARD-MANUAL-001
edition_id: WORK-HISCOX-STANDARD-MANUAL-001-1890
volume_id: null
publication_year: 1890
source_type: reference
copyright_status: public_domain
usage_permission: research
access_control: public
tsu_access: full
category: null
category_status: AUTHORITATIVE_SOURCE_MISSING
citation_policy: null
citation_policy_status: AUTHORITATIVE_SOURCE_MISSING
metadata_provenance.crosswalk_id: 260d31b2331a3f8b
```

**[REVIEW QUESTIONS]**
1. Claim Fidelity: 사도행전 17:30 인용을 "이전 무지 시대 용납 → 이제 모든 사람에게 회개 명령"으로 재진술한 것이 정확한가?
2. Theological Accuracy: "하나님이 무지를 용납했다"는 표현이 일반은총/특별계시 교리와 정확히 조화되는가(오해 소지 여부)?
3. Doctrine Classification: Soteriology가 적절한가, 아니면 별도로 "회개(Repentance)" 세부 분류가 필요한가?
4. Evidence: 성경 직접 인용이므로 evidence 자체는 충분한가?
5. Scripture/Citation: `scriptures` 필드에 "Acts 17:30"이 반드시 채워져야 하는가(현재 누락) — 앞뒤 참조 목록(Rom 16:26, Mark 1:15, Rom 1:15-17)도 함께 확인 필요한가?

**[FLAGS]**
`SCRIPTURE_MISMATCH` — 원문이 사도행전 17:30 직접 인용인데 `scriptures` 필드가 비어 있음(TSU-0003661과 동일 유형 문제 — 회개+성경목록형 문장에서 파서가 scripture를 감지하지 못하는 패턴으로 추정, 검토자 확인 권고)

**[REVIEW DECISION]**
PENDING

---

## Human Review Summary Table

| # | TSU ID | Source | Doctrine | Claim(요약) | Evidence | Flags | Decision |
|---|---|---|---|---|---|---|---|
| 1 | TSU-0000713 | Dagg | Ecclesiology | 초기 교회 간 독립성과 인사 교환 | 원문 2문장(빌 4:15 인용 포함), citation 1 | SCRIPTURE_MISMATCH | PENDING |
| 2 | TSU-0000199 | Dagg | Baptism | baptizō는 과정을 의미하지 않음 | 원문 1문장, citation 조각(잘림) | AMBIGUOUS | PENDING |
| 3 | TSU-0000330 | Dagg | Lord's Supper | 성찬에서 빵으로 그리스도 죽음을 기억함이 적절 | 원문 1문장(반론-답변 구조 결론부) | CONTEXT_LOSS, EVIDENCE_INSUFFICIENT | PENDING |
| 4 | TSU-0000033 | Dagg | Soteriology | 그리스도의 사랑이 순종의 강력한 동기 | 원문 1문장(직접 대응) | NO_OBJECTION | PENDING |
| 5 | TSU-0000025 | Dagg | Sanctification | 하나님을 전심으로 사랑함이 모든 의무의 총합 | 원문 1문장(마 22:37 반향) | SCRIPTURE_MISMATCH | PENDING |
| 6 | TSU-0003524 | Hiscox | Ecclesiology | 선한 이의 악한 정서가 경건을 이길 수 있음 | 원문 1문장, citation 조각 | NO_OBJECTION | PENDING |
| 7 | TSU-0003661 | Hiscox | Baptism | 회개+세례로 죄사함(행 2:38 인용) | 원문=성경 직접 인용 | SCRIPTURE_MISMATCH, DOCTRINE_MISMATCH(가능성) | PENDING |
| 8 | TSU-0003525 | Hiscox | Church Discipline | 악한 정서·분쟁을 가능한 한 피해야 함 | 원문 1문장(지시대명사, #06 의존) | CONTEXT_LOSS | PENDING |
| 9 | TSU-0003893 | Hiscox | Lord's Supper | (제3자 견해) 모두를 성찬에 초청함이 형제적 | 원문 1문장(타인 견해 소개 추정) | AMBIGUOUS | PENDING |
| 10 | TSU-0003647 | Hiscox | Soteriology | 이제 모든 사람에게 회개 명령(행 17:30 인용) | 원문=성경 직접 인용 | SCRIPTURE_MISMATCH | PENDING |

---

## Safety Verification(Read-only, 작업 후 재확인)

```
$ shasum -a 256 NAE/corpus/tsu/Dagg_Church_Order/tsu.json NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json
(작업 시작 시점과 동일 — 변경 없음)

$ review_status 분포: {'generated': 4117}
$ indexer.index_all(dry_run=True) -> indexed=0

generated = 4,117
verified  = 0
eligible  = 0
indexed   = 0

Production TSU modified = 0
Review Promotion = 0
Embedding = 0
Qdrant calls = 0
Git changes = 0
```

---

## Regression

이번 작업은 문서(Review Package) 생성만 수행했고 코드를 전혀 수정하지
않았으므로, 전체 회귀 스위트를 다시 실행하지 않았다(직전 작업에서
이미 확인된 상태 그대로 유지 — 1,967 passed / 2 failed(기존 무관
baseline)). 아래 target/Validator만 재확인했다:

```
Target tests(관련 스위트): 104 passed(변경 없음, 재실행으로 재확인)
Validator Drift: source=89/0/0, manifest=138/0/0, authority=128/26/0(baseline 일치)
신규 regression: 0
DRIFT: 0
```

---

## 완료 조건 체크리스트

```
[x] 10개 Pilot TSU 포함
[x] Dagg 5 + Hiscox 5
[x] 실제 Original Text 포함(canonical.json에서 직접 발췌, 요약/재구성 없음)
[x] Claim 포함
[x] Doctrine 포함
[x] Evidence 포함
[x] Scripture/Citation 포함(없는 경우 "비어 있음"으로 명시, 임의 생성 없음)
[x] Metadata Provenance 포함
[x] 5개 Review Question 포함(TSU마다)
[x] Flags 표시(10건 전부)
[x] 모든 Decision = PENDING
[x] generated = 4,117
[x] verified = 0
[x] eligible = 0
[x] indexed = 0
[x] Production TSU 변경 = 0
[x] Embedding = 0
[x] Qdrant = 0
[x] Git commit/push = 0
[x] 최종 Review Package 생성(본 문서)
```

---

## 최종 상태

```
READY_FOR_PASTORAL_HUMAN_REVIEW
```
