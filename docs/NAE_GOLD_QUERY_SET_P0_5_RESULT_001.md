# P0-5 실채점용 원문 답변 — 24건 (2026-09-23 재수집)

scripts/p0_5_run_all.py로 실제 프로덕션 경로(QueryProcessor(hybrid, k=5, file_scope=None) -> GenerationService.generate())를 통해 재수집. 코퍼스가 Spurgeon 67종/130,401건 기준선으로 교체된 이후 첫 재실행분이다(STATE.md 2026-09-23 항목). **채점(PASS/FLAG/FAIL, 8개 축)은 docs/NAE_GOLD_QUERY_SET_P0_5_001.md가 명시하듯 사용자 본인만 할 수 있다** — 신학적 정합성·목회적 유용성·교단 정합성 판단이 필요해 CUE가 대신 매기지 않았다. 아래는 그 채점에 쓸 원문 자료다.

## 수집 중 관찰된 사항 (채점 전 참고, 판정은 아님)

1. **근거 0건 유보 17/24건(이전 재실행 6/24건 대비 대폭 증가)** — A1·A2·A3·C1·C2·D1·D2·D3·E1·E2·E3·F2·G2·G3·H1·H2·H3. 코퍼스가 Spurgeon 67종 기준선으로 교체(2026-09-23 확정, HQ 결정 — 재조사 대상 아님)된 이후 첫 재실행이라, 로마서 8장·창세기 1장·히브리서 11장 같은 범용 본문·상담류 질의(E1~E3)가 이제 Spurgeon 단일 코퍼스에서 매칭되지 않아 유보가 늘어난 것으로 보인다. 반대로 침례교/개혁파 교리 주제(B1·B2·B3·C3·F1·F3·G1)는 여전히 근거를 찾는다 — Spurgeon 자료가 실제로 다루는 주제이기 때문으로 보인다.

2. **인용 출처 메타데이터 공백 0/35건 — 완전 해소** — 이전 재실행 90건 중 74건 비어 있던 것과 달리, 이번 35건(비유보 7건×5)은 전부 source_title/source_author가 채워져 있다. 사이드카 백필(PR #55/#60) 효과로 보인다.

3. **문자 오염 잔존(경미) — 원인 확인 완료(2026-09-23), 이번 채점은 관찰만, 수정은 보류**
   B2 답변에 서로 다른 두 결함이 섞여 있다:
   (a) `persönlich`(독일어 "개인적으로") 혼입 — `core/generation.py:121`
   `_SCRIPT_CONTAMINATION_RE`는 히라가나·가타카나·CJK·태국·그리스·키릴·
   히브리·아랍·데바나가리 9개 문자 체계만 검사하고 라틴 문자는 전부
   면제한다(성경 로마자 인명 허용 목적). `persönlich`의 `ö`는 라틴 확장
   문자라 탐지 자체가 안 됐고, 그래서 재시도(`_MAX_LANGUAGE_RETRIES`)도
   발동하지 않았다 — 필터의 사각지대다.
   (b) "그리스도의 가"·"더로우게"·"생명과님의" — 원문은 "그리스도의
   **의**가"·"더 **의**로우게"·"생명과 **성령**님의"인데 "의"/"성령"이
   통째로 빠졌다. 이건 외국 문자 유입이 아니라 토큰 드롭이라, 남은
   글자가 전부 한글이므로 문자 체계 검사로는 원리상 잡을 수 없는
   유형이다.
   두 결함 다 my-theology-bot-v2(llama3.3:70b Q4_K_M) 양자화 모델의
   "개념 주변 크로스링구얼 오염" 결함군(2026-07-21 실측 근거, 96행
   주석)과 같은 계열로 보이나, 현재 필터 설계(문자 체계 범위 검사)로는
   구조적으로 못 잡는 카테고리다. 사용자 결정(2026-09-23): 이번 채점
   라운드는 관찰 기록만 남기고 수정은 보류 — §"언어 완성도" 판정 시
   참고할 것.

4. **ClaimGuard risk_level은 비유보 7건 전부 none** — 절대·최상급 주장 차단이 걸린 항목은 이번 재실행에는 없었다.

5. **`_DENOMINATION_DIRECTIVE`/`_GROUNDING_DIRECTIVE` 누출 패턴 재확인 필요** — C3 답변 끝에 "이러한 내용은 개혁파 침례교 전통에서도 중요한 주제입니다" 식의 교단 정합성 진술이 있다. 과거 A3·B1에서 관측된 지시문 누출과 같은 패턴인지는 채점 시 판단이 필요하다.

## [A1] 로마서 8:1-4은 그리스도인의 정죄 없음에 대해 무엇을 말합니까?

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [A2] 창세기 1:26-27의 "하나님의 형상"(Imago Dei)은 무엇을 의미합니까?

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [A3] 마태복음 28:19-20의 "모든 민족을 제자로 삼으라"는 명령의 신학적 함의는 무엇입니까?

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [B1] 유아세례가 아니라 신자의 침례(believer's baptism)를 주장하는 성경적·신학적 근거는 무엇입니까?

**ClaimGuard**: none

**답변**:

> C.H. Spurgeon의 Metropolitan Tabernacle Pulpit에 따르면, 유아 세례 대신 신자들의 침례를 지지하는 이유 중 하나는 bahwa "no one has a right to this ordinance until he is a believer in Christ"라는 점입니다(출처: THE METROPOLITAN TABERNACLE PULPIT — C.H. SURGEON). 즉, 세례의 권리는 오직 그리스도에 대한 믿음을 가진 사람에게만 주어진다는 것입니다.
>
> 또한 Spurgeon은 침례가 신자의 죽음과 부활을 상징하며, 이는 새로운 삶으로 들어가는 과정입니다(출처: Metropolitan Tabernacle Pulpit — C. H. Spurgeon). 따라서 침례는 한번 행해지면 다시 반복할 필요가 없는 것입니다.
>
> 또한 그는 세례의 의미를 설명하면서 "baptism is the avowal of faith"라고 말합니다(출처: The Metropolitan Tabernacle Pulpit — Charles Haddon Spurgeon). 즉, 신자들의 침례는 믿음을 공개적으로 선언하는 행위라는 것을 강조하고 있습니다.
>
> 이러한 근거들은 개혁파 침례교 전통 안에서 유아 세례가 아니라 신자의 침례를 주장하는 데 중요한 역할을 합니다.

**출처**:
- The Metropolitan Tabernacle Pulpit / Charles Haddon Spurgeon / Unmapped passage
- The Metropolitan Tabernacle Pulpit / Charles Haddon Spurgeon / Unmapped passage
- Metropolitan Tabernacle Pulpit / C. H. Spurgeon / Unmapped passage
- The Metropolitan Tabernacle Pulpit / Charles Haddon Spurgeon / Unmapped passage
- THE METROPOLITAN TABERNACLE PULPIT / C.H. SURGEON / Unmapped passage

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [B2] 칭의(justification)와 성화(sanctification)는 어떻게 다릅니까?

**ClaimGuard**: none

**답변**:

> 칭의와 성화는 두 가지 다른 은혜입니다(C.H.Spurgeon). 출처: The Metropolitan Tabernacle Pulpit — Charles Haddon Spurgeon에 따르면 칭의란 의롭다 하심을 받은 것이고, 이는 믿음으로 말미암습니다. 이때 그리스도의 가 우리에게 입적되는 것입니다.
>
> 성화는 성령님의 역사로 말미암아 persönlich로우신 삶을 살게 되는 것을 의미합니다(C.H.Spurgeon). 출처: The Metropolitan Tabernacle Pulpit — Charles Haddon Spurgeon에 따르면, 칭의와 성화를 혼동해서는 안 됩니다. 우리는 믿음으로 의롭다 하심을 받은 후에도 여전히 죄를 짓습니다. 그러나 그리스도께서 우리에게 주신 새로운 생명과님의 역사로 말미암아 점점 더로우게 되는 것입니다.
>
> 따라서 칭의는 완료된 일이고, 성화는 진행 중인 과정입니다(C.H.Spurgeon). 출처: The Metropolitan Tabernacle Pulpit — C. H. Spurgeon에 따르면 우리가 그리스도께 믿음을 가졌을 때 우리는 이미로워 졌으며 천국에서 받게 될 칭의와 다름이 없습니다.
>
> 그러나 성화는 매일매일님의 역사로 말미암아 진행되는 것입니다(C.H.Spurgeon). 출처: The Metropolitan Tabernacle Pulpit — C. H. Spurgeon에 따르면 우리는 이 두 가지 은혜를 분명히 구별해야 합니다.
>
> 이러한 내용은 개혁파 침례교 전통과 일치합니다(Reformed Baptist, 1689 런던신앙고백 계열).

**출처**:
- The Metropolitan Tabernacle Pulpit Sermons Preached / C.H.Spurgeon / Unmapped passage
- Till he come : communion meditations and addresses / Spurgeon, C. H. (Charles Haddon), 1834-1892 / Unmapped passage
- The Metropolitan Tabernacle Pulpit / Charles Haddon Spurgeon / Unmapped passage
- The Metropolitan Tabernacle Pulpit / Charles Haddon Spurgeon / Unmapped passage
- The Metropolitan Tabernacle Pulpit / C. H. Spurgeon / Unmapped passage

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [B3] 개혁파 침례교 관점에서 교회의 권징(church discipline)은 어떤 절차를 따라야 합니까?

**ClaimGuard**: none

**답변**:

> 개혁파 침례교 관점에서 교회의 권징은 성경적 원칙에 따라야 합니다. C.H 스퍼전의 설교 내용을 보면, "교회가 자기를 돌아보아 자기 자신이 판단받지 않도록 하여 주님으로부터 심판 받는 것을 피할 수 있다"고 말합니다(출처: The Metropolitan Tabernacle Pulpit — Charles Haddon Spurgeon). 또한 교회에서 권징의 절차를 따르기 위해서는 성도들이 서로 책임을 지며, 각자에게 맡겨진 은사에 따라 다른 사람들의 영적 복지를 위해 노력해야 합니다(출처: The Metropolitan Tabernacle Pulpit — C. H. Spurgeon). 
>
> 또한 교회에서 권징이 이루어질 때는 주님의 이름으로 행해져야 하며, 이는 하나님께서 친히 실행하시는 것으로 간주되어야 한다고 말합니다(출처: 1884년 The Metropolitan Tabernacle Pulpit — C. H. Spurgeon). 
>
> 그러나 이 질문에 대한 자세한 절차와 세부 사항은 제공된 자료에서 찾을 수 없습니다.

**출처**:
- The Metropolitan Tabernacle Pulpit / Charles Haddon Spurgeon / Unmapped passage
- The Metropolitan Tabernacle Pulpit / C. H. Spurgeon / Unmapped passage
- The Metropolitan Tabernacle Pulpit / Charles Haddon Spurgeon / Unmapped passage
- The Metropolitan Tabernacle Pulpit  1884: Vol 30 / C. H. Spurgeon / Unmapped passage
- Expositions of holy scripture / / Maclaren, Alexander, 1826-1910 / Unmapped passage

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [C1] 로마서 8장을 본문으로 "성령 안에서 사는 자유"라는 주제의 설교 대지를 짜 주세요.

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [C2] 히브리서 11장(믿음장)으로 청년부를 위한 설교를 준비 중입니다. 적용점을 제안해 주세요.

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [C3] 새해를 맞아 교회 언약(church covenant)을 주제로 설교하려 합니다. 핵심 논지를 정리해 주세요.

**ClaimGuard**: none

**답변**:

> C.H. 스페전의 저서 "The Metropolitan Tabernacle Pulpit"에 따르면, 그는 개혁파 침례교 전통과는 다른 견해를 가지고 있습니다. 예를 들어, 교회 언약을 강조하는 그의 설교에서, 그는 성도들이 그리스도의 몸 안에서 하나가 되어야 하며, 서로의 약속을 지키고 사랑해야 한다고 말합니다.
>
> 그에 따르면, 우리가 믿음으로 하나님의 약속들을 잡으면 우리는언약안에 들어갑니다. 그리고 언약은 영원한 구원의 보증입니다(출처: The Metropolitan Tabernacle Pulpit — C.H. 스페전).
>
> 또 다른 자료에서 그는 교회와 그리스도 사이의 관계를 강조하며, 우리가 믿음으로 하나님과 계약을 맺으면 우리는 언약 안에 들어간다고 말합니다.
>
> 이러한 내용은 개혁파 침례교 전통에서도 중요한 주제입니다. 그러나 스페전의 견해는 교회와 그리스도 사이의 관계를 더욱 강조하며, 성도들이 서로 사랑하고 약속을 지키며 살아가야 한다는 점에서 차이가 있습니다.
>
> 설교 핵심 논지는 다음과 같습니다:
>
> 1. 하나님의 언약은 영원한 구원의 보증입니다.
> 2. 우리는 믿음으로 하나님과 계약을 맺어야 합니다.
> 3. 교회와 그리스도 사이의 관계는 매우 중요하며, 성도들은 서로 사랑하고 약속을 지키며 살아가야 합니다.
>
> 이러한 내용들을 통해 새해를 맞아 교회의 언약에 대한 설교를 준비할 수 있습니다(출처: The Metropolitan Tabernacle Pulpit — C.H. 스페전).

**출처**:
- The Metropolitan Tabernacle Pulpit / C. H. Spurgeon / Unmapped passage
- The Metropolitan Tabernacle Pulpit / Charles Haddon Spurgeon / Unmapped passage
- The Metropolitan Tabernacle Pulpit / C.H. Spurgeon / Unmapped passage
- Morning by morning; or, Daily readings for the family or the closet / Spurgeon, C. H. (Charles Haddon), 1834-1892 / Unmapped passage
- The Metropolitan Tabernacle Pulpit / C.H. Spurgeon / Unmapped passage

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [D1] 유아세례에 대한 개혁주의(장로교) 입장과 침례교 입장의 차이를 비교해 주세요.

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [D2] 예정론에 대한 칼빈주의와 알미니안주의의 입장을 비교해 주세요.

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [D3] 성찬(주의 만찬)의 의미에 대한 침례교와 루터교의 이해 차이는 무엇입니까?

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [E1] 배우자의 외도로 이혼을 고민하는 교인을 성경적으로 어떻게 상담해야 합니까?

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [E2] 오랜 우울증을 겪는 성도를 목회적으로 어떻게 돌봐야 합니까?

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [E3] 자녀를 잃은 부모를 위로할 때 신학적으로 조심해야 할 것은 무엇입니까?

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [F1] Hiscox의 「The Standard Manual for Baptist Churches」에서 집사(deacon)의 자격은 어떻게 규정됩니까?

**ClaimGuard**: none

**답변**:

> 이 질문에 대한 답은 자료 안에 없습니다.
> "출처: A History of Preaching — Edwin Charles Dargan", "Sermons preached and revised by the Rev. C.H. Spurgeon, fifth series.", "The Metropolitan Tabernacle Pulpit — Charles Haddon Spurgeon" 등에서 집사(deacon)에 대한 언급은 없으며 Hiscox의 저서에 대해서도 자료 안에는 내용이 없습니다.
> 따라서 이 질문은 현재 등록된 자료로는 답할 수 없습니다.

**출처**:
- A History of Preaching / Edwin Charles Dargan / Unmapped passage
- Sermons preached and revised by the Rev. C. H. Spurgeon, fifth series. New York, Sheldon / Spurgeon, C. H. (Charles Haddon), 1834-1892 / Unmapped passage
- Sermons Preached and Revised by the Rev. C. H. Spurgeon, Fifth Series. New York, Sheldon / Charles Haddon Spurgeon / Unmapped passage
- Sermons Preached and Revised by C. H. Spurgeon / Charles Haddon Spurgeon / Unmapped passage
- The Metropolitan Tabernacle Pulpit / Charles Haddon Spurgeon / Unmapped passage

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [F2] Dagg의 「Church Order」에서 교회의 표지(marks of the church)는 무엇이라고 설명합니까?

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [F3] Andrew Fuller가 「모든 사람이 받아들일 만한 복음」(The Gospel Worthy of All Acceptation)에서 말한 "믿을 의무"란 무엇입니까?

**ClaimGuard**: none

**답변**:

> 이 질문은 현재 등록된 자료로는 답할 수 없습니다. Andrew Fuller의 저서 "모든 사람이 받아들일 만한 복음"에 대한 구체적인 내용이나 그의 주장인 "믿을 의무"가 무엇인지 설명하는 문구는 제공되지 않았습니다.

**출처**:
- Sermons preached and revised by the Rev. C. H. Spurgeon, fifth series. New York, Sheldon / Spurgeon, C. H. (Charles Haddon), 1834-1892 / Unmapped passage
- The Metropolitan Tabernacle Pulpit / C.H.  Spurgeon / Unmapped passage
- Sermons Preached and Revised by the Rev. C. H. Spurgeon, Fifth Series. New York, Sheldon / Charles Haddon Spurgeon / Unmapped passage
- Spurgeon’s Sermons - Vol. XV - Metropolitan Tabernacle Pulpit / Charles H. Spurgeon / Unmapped passage
- The Metropolitan Tabernacle Pulpit / Charles Haddon Spurgeon / Unmapped passage

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [G1] 인공지능(AI) 윤리에 대해 개혁파 침례교 신학은 공식적으로 어떤 입장을 취합니까?

**ClaimGuard**: none

**답변**:

> 이 질문에 대한 답은 자료에서 찾을 수 없습니다.
> 자료에는 인공지능(AI)에 관한 내용이나 관련된 성경 본문의 해석, 또는 그와 연관되는 윤리적인 문제가 언급되지 않았습니다. 따라서 이 물음에 대해 정해진 입장을 밝히거나 설명할 근거를 제공하지 못합니다.
>
> 출처: The Metropolitan Tabernacle Pulpit — Charles Haddon Spurgeon과 Sermons — Charles Haddon Spurgeon에서 인공지능(AI) 윤리에 대한 언급은 없습니다.

**출처**:
- The Metropolitan Tabernacle Pulpit / Charles Haddon Spurgeon / Unmapped passage
- Sermons / Charles Haddon Spurgeon / Unmapped passage
- The Metropolitan Tabernacle Pulpit / Charles Haddon Spurgeon / Unmapped passage
- Sermons / Charles Haddon Spurgeon / Unmapped passage
- Sermons / Charles Haddon Spurgeon / Unmapped passage

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [G2] "존 스미스 3세"라는 신학자가 주장했다는 교회론의 핵심 내용은 무엇입니까?

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [G3] 화성 이주가 신학적으로 정당화될 수 있습니까?

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [H1] 선하신 하나님이 다스리시는 세상에 왜 악과 고통이 존재합니까?

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [H2] 여호수아서에서 하나님이 가나안 족속을 진멸하라고 명령하신 것을 오늘날 어떻게 이해해야 합니까?

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---

## [H3] 창세기의 창조 기사와 현대 과학(진화론 등)은 어떻게 조화될 수 있습니까?

**결과**: 근거 0건 → 유보 게이트(P0-6) 발동.

**판정 (PASS/FLAG/FAIL)**: 
**메모**: 

---
