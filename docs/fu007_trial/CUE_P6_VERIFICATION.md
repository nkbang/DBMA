# P0-5 FU-007 — P6 CUE Independent Verification

기준일 2026-09-30. 대상: `/Users/David/DBMA_wt/_c1_audit/C1_P0_5_GROUNDING_AUDIT.md` (475줄, 22,945B) 및 `scan_*.py` 3개.
기준: HQ [P0-5 FU-007 여정·범위·품질보호 최종 고정 명령]. 작업은 read-only로 했다. 코드 변경, 재생성, Ollama 호출, MAIN·워크트리 git 쓰기는 하지 않았다.

재현 자료(이 폴더):
- `cue_verify.py` / `cue_verify.out` — 상한 없는 단어 경계 코퍼스 스캔
- `c1_scan_corpus_rerun.out`, `c1_scan_types_rerun.out` — C1 스크립트를 수정 없이 재실행한 출력

## 0. 요약

| 구분 | 결과 |
|---|---|
| 무결성(HEAD·해시 4종·119,595줄·`matches_appindex_sources` 24/24) | **확인** |
| MAIN(`828c250d`, 미커밋 17) / fu007(`e5ee8f97`, clean) 불변 | **확인** |
| C1 코퍼스 검색 기록 | **재현 불가 6건** — C1 자신의 스크립트 출력과 보고서 수치가 다름(H2 근거 오귀속 판정은 CUE가 정정해 철회) |
| C1 스크립트 방법 | `max_hits=10`에서 break → "10건"은 **상한값**이지 실제 개수가 아님. 부분 문자열 일치(단어 경계 없음) |
| 사례 배정 오류 | **G3 절이 H2(가나안) 내용** — G3(화성 이주) 리뷰는 수행되지 않음 |
| 유형 분류 | 보고서 표(11/8/5)와 C1 분류 스크립트 출력이 불일치하고, 기준 문장과도 모순(PARTIAL "<200자"인데 D2 504자) |
| "evidence content 불완전"(C1·C2·E1) | **사실 아님** — 근거 전문 278~969자가 제공됨. 리뷰 미수행 |
| 자기모순 | D3: 9절에서 전환구 누출을 적발해 놓고 7절에서 "CORRECT abstention", 13절에서 "CLEAN" |

**판단**: C1 audit 파일은 현 상태로는 P0-5의 evidence record로 쓸 수 없다. 아래 1~3절의 CUE 기록이 이를 대체하거나 보정한다.

## 1. C1 주장 검증표

| C1 주장 | CUE 검증 | 증거 |
|---|---|---|
| A1 근거 [3] tsu `…02dd6090…_chunk_01715`에 Romans viii. 1 | **확인** | 근거 전문 rank 1·3·4·5에 "There is therefore now no condemnation" |
| A2 "HALLUCINATION", `image of God` 등 **모두 0건** | **반증** | A2 답변은 36자 유보뿐이라 날조할 내용이 없다. `\bimage of God\b` **82건**(예 `…7c3ffe52…_chunk_00427`). → A2는 **상위 5건에 관련 근거 없음 + 코퍼스에는 존재**(검색 누락형 유보) |
| A3 근거 [1] "willing subjects" | 인용 **확인** | rank 1 |
| B1 답변 인용문·근거 [2] | **확인** | 답변에 해당 문장 있음, rank 2에 "none have the right to approach his table" |
| B2 근거 [2] "run away to Moses…" | **확인** | rank 2 |
| C3 근거 [1]·[3] | **확인** | rank 1 "foot of Sinai", rank 3 "new covenant" |
| E3 근거 [1] | **확인** | rank 1·4 |
| H1 근거 [1] | **확인** | rank 1 |
| H2 근거 [1] Joshua xvii. 18 | **확인** | rank 1 |
| H2 근거 [4] "utterly exterminate those condemned races" | **확인** (CUE 1차 판정 정정) | rank 4에 있음. "utterly"와 "exterminate" 사이에 쪽 머리글("1096 ClassicChristianLibrary.com 1690 Chariots of Iron — Judges 1:19-20")이 끼어 있어 CUE의 단순 문자열 검색이 놓쳤다 |
| H2 핵심 주장 "세계의 도덕을 위한 처분" | **CUE 확인** | rank 1: "It was necessary for the purity of the world that ancient races … should be removed" |
| D1 근거 "top-5 모두 preaching/sympathy, 교단 세례 무관" | **반증** | rank 1·2·4에 infant baptism, rank 3에 Presbyterian(역사 서술 문맥) |
| D1 코퍼스 `infant baptism`/`paedobaptism`/`1689` **모두 0건** | **반증** | infant baptism **28**, pedobaptis 1, presbyterian 113, 1689 **27**, "London Confession" 0 |
| D1 결론(교단별 신학 논거·1689 신앙고백 예시는 근거에 없음) | **결론은 유지** | 근거의 infant baptism 언급은 역사 서술(재세례파 논쟁, 감독제 편향)이다. 답변의 "언약이 가족 전체에 적용", "1689 런던신앙고백은 신자 세례만" 서술은 근거 5건에 없다 |
| F2 `Dagg`·`Church Order` **0건** → 부재 | **근거 반증 / 결론 유지** | C1 스크립트 재실행 시 Dagg 10(상한), Church Order 10(상한). 단어 경계로는 Dagg 2건 — 둘 다 출판사 광고의 저서 목록("J. L. Dagg … Elements of Moral Science"). church order 11건은 일반 용례. 『Church Order』 본문은 없음 |
| G1 AI 윤리 0건 | **확인** | `\bartificial intelligence\b` 0 |
| G2 John Smith 4건(무관), Smith III 0 | **확인** | 4 / 0 |
| "G3" 가나안 검색 실패 | **사례 오배정** | G3 질문은 "화성 이주". 해당 절은 H2 내용이다. `drive out the Canaanites`도 보고서 0 ↔ 실제 10 |
| H3 문장 분석(근거 [1] evolution doctrine) | **확인** | rank 1 원문 일치. 문장 3("창세기 기사와 더 일치") 근거 없음 판단에 동의 |
| 전환구 정규식 적중 D3·E1·H3 | **재현** | 동일 |
| F2 진단본 비교(진단본에만 누출) | **확인** | — |
| 13절 leakage scan "D1만 누출, 나머지 CLEAN" | **반증** | D3는 9절에서 적발된 누출(아래 2절) |

## 2. C1이 수행하지 않았거나 틀린 사례 — CUE 최소 확인

| 사례 | 관찰 | 증거 |
|---|---|---|
| **G3** (화성 이주) | 유보. 코퍼스에 화성 이주 관련 자료 없음. `\bMars\b` 81건은 "bishop of Mars", "mars the force" 등 무관한 용례. "other worlds" 8건은 Spurgeon의 다른 세계 사변(이주와 무관). 유보 뒤 "개혁파 침례교 전통 안에서 이해될 수 있습니다"라는 교단 틀 문장 1개는 근거에 없음 | `cue_verify.out` |
| **D3** (성찬, 침례교 vs 루터교) | **누출.** "루터교의 견해는 자료에 직접 언급되어 있지 않습니다. **그러나 일반적인 신학적 관점에서는 루터교가 성찬을 상징으로 이해하지만…**" — 근거에 없는 내용을 사실처럼 제시. C1은 이를 abstention/CLEAN으로 분류 | 답변 원문, 전환구 정규식 |
| **E1** (외도·이혼 상담) | 유보 뒤 인용 2개가 rank 1에 **원문 그대로** 있음("Causeth her to commit adultery … without sufficient cause", "saving for the cause of fornication"). 해석도 근거와 일치. 전환구 적중이지만 **근거 있는 덧붙임** | rank 1 |
| **C1** (롬 8장 설교 대지) | 대지 내용(8:9 성령 받음, 8:1-4 해방, 8:5-11 육신/영)은 근거 본문에 없다. 근거에는 설교 제목·구절 표기만 있음(rank 1 "A FATAL DEFICIENCY — ROM. 8:9", rank 2 Romans viii 낭독, rank 4 8:18-39 강해 시작부). 성경 본문 지식이 출처 표기와 함께 제시됨 | rank 1~5 |
| **C2** (히 11장 적용점) | 답변이 드는 구절(11:4-7, 11:13-16, 11:35-38)과 적용점이 근거에 없음. 근거에 있는 요셉(11:22)·모세(11:24)·아브라함(11:9-10)·라합(11:31)은 답변에 쓰이지 않음. 끝에 일괄 출처 1개 | rank 1~5 |
| **F3** (Fuller 믿을 의무) | 유보. 『Gospel Worthy of All Acceptation』은 코퍼스에 **서적 목록 2건**뿐, 본문 없음. "duty-faith" 류 언급 4건은 Fuller 본문이 아님 | `cue_verify` 추가 스캔 |

## 3. P0-5 grounding 관찰 (CUE 확정분, APPINDEX 기준)

근거에 없는 내용을 사실처럼 제시한 사례:
- **D1**: 교단별 신학 논거, 1689 신앙고백
- **D3**: "그러나 일반적인 신학적 관점에서" 루터교 설명
- **H3**: 유보 뒤 "창세기 기사와 더 일치" 문장
- **C1**: 로마서 8장 대지 내용
- **C2**: 히브리서 11장 적용점과 구절

근거로 뒷받침되는 덧붙임: **E1**(인용 2개 원문 일치).

유보가 코퍼스 부재와 일치하는 사례: G1·G2·G3·F1(Hiscox 목록 1건만)·F2·F3.

유보이지만 코퍼스에는 관련 자료가 있는 사례(검색 누락형): **A2**(image of God 82건).

**답변형 9건 문장 대조 (HQ 선택 (a), 2026-09-30 추가)**

| 사례 | 근거로 확인된 진술 | 근거에 없는 진술 |
|---|---|---|
| A3 | 제자 삼기·종의 사역(r1), 교회의 섬김과 에너지(r4), 세례 후 가르침(r2), 'them' 남성형 해석(r3) | "개혁파 침례교 신학에서 중요한 역할"(교단 틀). 'them' 해석은 r3 Maclaren 것인데 Spurgeon 출처로 표기(출처 오귀속) |
| B1 | 믿음 없는 유아세례는 하나님 앞에서 죄(r1), 신자만의 규례(r2), 거듭남 없이는 천국 불가(r5) | **따옴표 직접 인용 형식의 둘째 문장**("… 구원에 대한 확신을 약화시키게 됩니다") — 근거에 없음. "개혁파 침례교 전통" 교단 틀 문장 |
| B2 | 칭의=그리스도 의의 전가, 성화=성령의 사역(r3), 모세 인용(r2), 둘 다 같은 근원(r4) | 성화를 "속죄를 위하여"라고 한 표현(근거와 불일치) |
| C3 | 언약을 기억, 시내산 언약과 망각(r1·r4), 성찬과 새 언약(r2), 언약 이해가 신학의 기초(r3) | **넷째 논지** "새로운 마음과 영을 주시고 … 법에 따라 행하게"(겔 36 계열) |
| D2 | Spurgeon "decree of his predestination"(r2·r4·r5)만 | **칼빈주의·알미니안주의 정의 전부**. 출처로 단 Broadus(r1)는 "Calvinism은 깊이 생각하게 한다"뿐이다(출처 오귀속). 비교 부분은 유보 |
| E2 | 그리스도의 모든 속성(r2), 설교자의 공감(r4), 목회자·성도 유대(r4), 염려를 맡김(r1) | 없음. 우울증 자체에 대한 조언은 유보 |
| E3 | 직접 인용이 r2의 충실한 번역 | 없음. 단 질문(자녀를 **잃은** 부모)이 아니라 악한 자녀를 둔 부모에 대한 답 — **질문 불일치** |
| H1 | 두 문장 모두 r1과 거의 같은 문장 | 없음 |
| H2 | 세계의 순결을 위한 제거, 멸망 판정(r1), 멸절 대상(r4) | "단순히 학살로 볼 수 없다"(해석, 근거에 명시 없음). 오늘날 이해는 유보 |

**APPINDEX 24건 종합 관찰 (CUE 확정)**
- 근거에 없는 내용을 사실처럼 제시한 진술이 있는 사례: **D1, D2, D3, H3, C1, C2, C3(1개 논지), B1(직접 인용 형식 1문장), A3(교단 틀 1문장)**
- 출처 오귀속: A3(Maclaren→Spurgeon), D2(Broadus)
- 근거로 뒷받침되는 답변: B2(표현 1곳 제외), E1, E2, E3(단 질문 불일치), H1, H2(해석 1문장 제외)
- 유보가 코퍼스 부재와 일치: G1, G2, G3, F1, F2, F3
- 코퍼스에 자료가 있는데 검색 상위 5건에 들지 못한 유보: A2
- 반복 양상(관찰만): 교단 틀 문장("개혁파 침례교 전통/신학") 덧붙임 — A3, B1, G3

**미확인**: B3의 코퍼스 존재 여부. C1이 근거를 기록하지 않았고, B3는 유보 사례라 grounding 결론에는 영향이 없다고 판단해 확인하지 않았다.

## 4. P0-5 STOP 조건 점검

| 조건 | 상태 |
|---|---|
| C1 audit 완료 | 완료 |
| C1 evidence record 확보 | 확보. 단 부적합 판정 — 이 문서가 보정 |
| CUE independent verification 완료 | 완료(1~3절, 답변형 9건 포함) |
| 주요 observation 근거 확인 | 완료(tag + rank 또는 tsu_id, 재현 스크립트) |
| unresolved 분류 | B3 코퍼스 존재 여부 1건(결론 영향 없음) |
| 결론을 훼손하는 미검증 문제 | 없음 |
| 추가 작업의 직접 필요성 | 없음 → **P7 HQ Decision 가능** |

BACKLOG 후보(이번 관찰에서 파생, 조사하지 않음): 교단 틀 문장 덧붙임, 출처 오귀속, 따옴표 직접 인용 형식의 비근거 문장, 질문 불일치(E3), 쪽 머리글이 청크 본문에 섞이는 문제(코퍼스 정제).
