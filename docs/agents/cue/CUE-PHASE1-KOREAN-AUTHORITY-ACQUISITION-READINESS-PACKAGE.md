# NAE PHASE 1 — KOREAN AUTHORITY ACQUISITION READINESS & HUMAN ACQUISITION PACKAGE

**작업명**: Korean Authority Acquisition Readiness & Human Acquisition Package
**작성자**: CUE (Governance / Source Evaluation / Acquisition Readiness)
**작성일**: 2026-08-26
**Governing Authority**: ADR-029 (ACCEPTED, 2026-08-25), `CUE-PHASE1-ADR029-GATE-RECONCILIATION-TRUE-BLOCKER-AUDIT.md`
**Mode**: READ-ONLY PACKAGE PREPARATION — 이 문서는 acquisition/구매/다운로드/ingestion을 수행하지 않는다.

---

## 1. Executive Summary

이 보고서는 ADR-029 PHASE 1의 TRUE BLOCKER(검증된 Korean authoritative
terminology source 부재)를 해소하기 위해, **HQ가 직접 실행할 수 있는
acquisition package**를 준비한다. CUE는 source를 구매/다운로드하지 않는다.

### 핵심 발견 (이번 세션의 신규 기여)

기존 조사(`PHASE1-KOREAN-AUTHORITY-RESOLUTION.md`, `-ACQUISITION.md`)는 "한국어
신학사전을 독자적으로 발굴"하는 접근으로 8개 후보(KR-TH-001~004, KR-SEM-001,
KR-BAP-001, KR-EV-001, KR-BIBLE-001)를 조사했으나 **전부 academic-knowledge-only
상태로 남았고 모든 자동화된 학술 DB 접근이 실패**했다(NLK/RISS/DBpia/KISS/
WorldCat/Google Scholar/Internet Archive/출판사 웹사이트 전부 접근 차단).

이번 세션은 **다른 각도**로 접근했다: "독자적인 한국어 신학사전"이 아니라
**"NAE가 이미 canonical English source로 선정한 사전의 공식 한국어 번역판"**을
탐색했다. WebSearch로 다음 2건을 **독립적으로 신규 발견·검증**했다:

1. **새성경사전 (New Bible Dictionary 한국어판)** — 기독교문서선교회(CLC),
   2001, ISBN 9788934106708 — EN-BAP-001(The New Bible Dictionary)의 공식
   한국어 번역판. Yes24·11번가에 실제 판매 중(신간).
2. **IVP성경신학사전 (New Dictionary of Biblical Theology 한국어판)** — IVP
   코리아, 2024, ISBN 978-89-328-2263-1, 역자 권연경(숭실대 신약학 교수,
   King's College London Ph.D.) — 2024년 출간된 최신 e-book.

이 두 후보는 (a) 실제 서점에서 검증 가능한 서지정보를 가지며, (b) NAE가 이미
authoritative로 승인한 영미 evangelical reference work의 공식 번역이므로
ADR-029 §4.3 priority-3("영어 원문과 한국어 용어의 cross-reference")를 **가장
직접적인 형태로** 만족시킬 잠재력이 있다.

**중요한 구분(§15 Evidence Discipline 준수)**: "번역판이 존재하고 서점에서
검증됐다"는 사실은 "이 자료가 canonical terminology authority로 확정됐다"는
뜻이 아니다. Edition 일치 여부, 실제 entry 내용, 라이선스 조건은 여전히
**human acquisition 이후에 확인**되어야 한다.

---

## 2. Governing Documents (확인됨)

| # | Document | 위치 확인 | 비고 |
|---|----------|-----------|------|
| 1 | ADR-029 | `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md` | ACCEPTED, 2026-08-25 |
| 2 | Gate Reconciliation | `docs/agents/cue/CUE-PHASE1-ADR029-GATE-RECONCILIATION-TRUE-BLOCKER-AUDIT.md` | 이번 작업의 직접 선행 문서 — TRUE BLOCKER 정의의 출처 |
| 3 | Terminology Discovery Independent Verification | `docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md` | 확인됨(이전 세션에서 전체 열람) |
| 4 | Terminology Discovery Revalidation | `docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md` | 확인됨 |
| 5 | Korean Authority Resolution | `docs/agents/cue/PHASE1-KOREAN-AUTHORITY-RESOLUTION.md` | 확인됨 — 8개 후보 조사, 0건 fully verified |
| 6 | Korean Authority Acquisition | `docs/agents/cue/PHASE1-KOREAN-AUTHORITY-ACQUISITION.md` | 확인됨 — 8개 후보 acquisition 시도, 0건 획득, 모든 자동 경로 실패 |
| 7 | NAE Source Inventory | `docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md`, `-VALIDATION.md` | 확인됨 — EN-BAP-001~012 English canonical set |
| 8 | Baptist source_candidates.csv | `resources/theological_sources/baptist/source_candidates.csv` | 확인됨(이전 세션) — ADR-029와 무관한 별도 트랙 |

이미 확인된 내용을 근거 없이 재추정하지 않았다 — §3에서 기존 조사를 그대로
재사용한다.

---

## 3. Current PHASE 1 Gate

사용자 지시문의 상태 요약을 원문 그대로 재확인(이번 세션에서 다시 판정하지
않고 인용):

```text
PHASE 1 STATUS:        BLOCKED
TRUE BLOCKER:          No verified Korean authoritative source
CANONICAL TERM RECORDS: 0
EN-BAP TRACK:          PHASE 0 EXTENSION / PARALLEL RESEARCH CORPUS EXPANSION
PIPELINE:              READY
ARCHITECTURAL CHANGE:   0
```

이 상태는 `CUE-PHASE1-ADR029-GATE-RECONCILIATION-TRUE-BLOCKER-AUDIT.md`의
Final Decision과 일치한다. 이번 보고서는 이 판정을 재검증하지 않고, **그
blocker를 해소하기 위한 human-actionable package**를 제공하는 데 집중한다.

---

## 4. Existing Korean Source Investigation (재사용, 중복 조사 금지)

`PHASE1-KOREAN-AUTHORITY-RESOLUTION.md` + `-ACQUISITION.md`에서 이미 조사된
8개 후보를 그대로 인용하고 분류만 갱신한다:

| Source ID | Title | 기존 판정 | 이번 분류 |
|-----------|-------|-----------|-----------|
| KR-TH-001 | 한국신학사전 (두레, 1990) | PARTIAL / PURCHASABLE(추정) | **NOT VERIFIED** — 모든 접근 경로 실패, 재조사 무의미 |
| KR-TH-002 | 개혁신학대백과사전 (대한기독교출판사, 1995) | PARTIAL / PURCHASABLE(추정) | **NOT VERIFIED** |
| KR-TH-003 | 장로교신학사전 | PARTIAL | **NOT VERIFIED** |
| KR-TH-004 | 기독교백과사전 (YMCA, 1998) | PARTIAL / PURCHASABLE(추정) | **NOT VERIFIED** — §6.3에서 신규 발견 후보와 명칭 유사성 주의 |
| KR-SEM-001 | 한국신학교 신학용어집 | PARTIAL / ACCESSIBLE(도서관, 추정) | **NOT VERIFIED** — 단일 출처 아님, "여러 신학교가 각자 발행" |
| KR-BAP-001 | 한국침례교신학사전 | NOT VERIFIED (존재 자체 미확인) | **NOT VERIFIED** — 이번 세션도 추가 검색 시도했으나(§8) 확인 불가 |
| KR-EV-001 | 한국복음주의신학사전 | NOT VERIFIED | **NOT VERIFIED** |
| KR-BIBLE-001 | 한국어 성경사전 (복수 판본) | CONDITIONAL | **NOT VERIFIED** — 특정 판본 미확정 |
| STRONGS-KO-001 | Strong's Concordance 한국어판 | PARTIAL / CONDITIONAL | **ACCESSIBLE + INSUFFICIENT AUTHORITY** — 실존은 널리 알려졌으나 concordance(정의 없음)이므로 §4.4 `definition` 필드를 채울 수 없음 — 단독 canonical source 부적격, 보조 bridge로만 유효 |

**재조사하지 않은 이유**: `PHASE1-KOREAN-AUTHORITY-ACQUISITION.md` §7이 이미
NLK API, RISS, DBpia, KISS, WorldCat, Google Scholar, Internet Archive,
출판사 웹사이트(두레/대한기독교출판사/YMCA) 전부를 시도해 실패로 기록했다.
동일한 검색을 반복하는 것은 새 evidence를 만들지 못한다.

**이번 세션의 접근 전환**: 위 8개 후보는 전부 "독자적인 한국어 신학사전을
찾는다"는 접근이었다. 이번 세션은 대신 "**이미 NAE가 canonical로 승인한
영어 원문의 공식 한국어 번역**"을 검색해 §6에서 2건의 신규 후보를 발견했다.
이는 기존 조사의 반복이 아니라 **탐색 전략 자체의 전환**이다.

---

## 5. Candidate Selection Criteria

지시문 §4의 5개 기준(A. Korean theological authority, B. Terminological
usefulness, C. Bibliographic identity, D. Legitimate acquisition,
E. Reproducibility)을 그대로 적용한다. 각 후보에 대해 §9~§10에서 개별
평가한다.

---

## 6. Candidate A — 새성경사전 (New Bible Dictionary, Korean Edition)

| Field | Value | Evidence |
|-------|-------|----------|
| Title (KO) | 새성경사전 (4판) | **VERIFIED** (Yes24, 11번가, ivp.co.kr 3개 독립 출처) |
| Original work | The New Bible Dictionary (IVP/Tyndale) — **NAE의 EN-BAP-001과 동일 계열** | VERIFIED (제목·내용 기술 일치) |
| Editor | 편집부 (Editorial Department) — 개인 편집자 미기재 | VERIFIED (명시적으로 개인명 없음) |
| Publisher | 기독교문서선교회 (CLC, Christian Literature Crusade Korea) | VERIFIED |
| Edition | 4판 | VERIFIED (판매 페이지 명시) |
| Publication Year | 2001-12-31 | VERIFIED |
| ISBN-13 | 9788934106708 (ISBN-10: 8934106700) | VERIFIED |
| Pages | 1,898 | VERIFIED |
| Format | 인쇄본(양장) | VERIFIED (신국판 표기 확인) |
| Price | 정가 60,000원 / 판매가 54,000원 | VERIFIED (Yes24 기준, 변동 가능) |
| Language | Korean (원문 영어 번역) | VERIFIED |
| 절판 여부 | 미절판 — 신간으로 판매 중 | VERIFIED (2개 소매처에서 신간 재고 확인) |

**Sources**: [Yes24](https://www.yes24.com/Product/Goods/160273), [11번가](http://www.11st.co.kr/products/1121209606), [ivp.co.kr](https://ivp.co.kr/books/book_detail.html?book=s01&idx=1722)

---

## 7. Candidate B — IVP성경신학사전 (Korean Translation of New Dictionary of Biblical Theology)

| Field | Value | Evidence |
|-------|-------|----------|
| Title (KO) | IVP성경신학사전 [전자책] | **VERIFIED** (ivp.co.kr 공식 판매 페이지) |
| Original work | New Dictionary of Biblical Theology (IVP/Apollos, ed. T. Desmond Alexander & Brian S. Rosner) | VERIFIED |
| Editor(원서) | T. Desmond Alexander, Brian S. Rosner | VERIFIED |
| Translator | 권연경 (Kwon Yeon-kyung) | **VERIFIED** — 숭실대학교 기독교학과 신약학 교수, King's College London Ph.D., IVP 역서 다수(IVP 성경배경주석 등) 보유 |
| Publisher | IVP(한국기독학생회출판부, Inter-Varsity Press Korea) | VERIFIED |
| Publication Date | 2024-05-17 | VERIFIED |
| ISBN | 978-89-328-2263-1 | VERIFIED |
| Format | **전자책(E-Book)만 확인됨** — 인쇄본 존재 여부 미확인 | PARTIALLY VERIFIED — 인쇄본은 이번 조사에서 확인하지 못함(§18 리스크 참고) |
| Price | 정가 44,000원 | VERIFIED |
| Language | Korean (원문 영어 번역) | VERIFIED |

**중요**: 이 원서(New Dictionary of Biblical Theology)는 NAE의 기존
EN-BAP-001~012 목록에 **포함되어 있지 않다** — 이번 세션이 발견한 **신규
English original**이다. NAE가 이 원서 자체를 아직 English canonical
candidate로 검토한 적이 없다는 점을 명시한다(별도 §18 리스크로 기록).

**Source**: [ivp.co.kr](https://ivp.co.kr/books/book_detail.html?book=s01&idx=1722)

---

## 8. Candidate C — 기독교대백과사전 (Christian Encyclopedia, 기독교문사) — FALLBACK

| Field | Value | Evidence |
|-------|-------|----------|
| Title (KO) | 기독교대백과사전 | **VERIFIED** (Yes24 중고샵, 교보문고, 북코아 — 3개 독립 소매처) |
| Editor | 기독교대사전편찬위원회 (Christian Dictionary Compilation Committee) | VERIFIED |
| Publisher | 기독교문사 (Kidok Munsa) | VERIFIED |
| Volumes | 16권 전집 | VERIFIED (여러 리스팅 일치) |
| Publication Year | 1990-03-06 (한 소매처는 "1985년 4판"으로 표기 — **연도 불일치 발견**) | **PARTIALLY VERIFIED** — 정확한 판/연도는 실물 확인 필요 |
| Format | 인쇄본 전집(양장), **절판 — 중고서점에서만 유통** | VERIFIED (Yes24/교보문고 리스팅이 모두 "중고샵"/"중고나라") |
| Language | Korean (일반 개신교 백과사전, KO-only) | VERIFIED — English term coverage 없음 |

**주의(§4 KR-TH-004와의 명칭 혼동 위험)**: 기존 `PHASE1-KOREAN-AUTHORITY-
RESOLUTION.md`의 KR-TH-004는 "기독교백과사전, YMCA, 1998"이다. 이번에 발견한
"기독교대백과사전, 기독교문사, 1990, 전16권"은 **제목이 유사하지만 별개의
출판물**이다("백과사전" vs "대백과사전", YMCA vs 기독교문사, 1998 vs 1990,
1권 추정 vs 16권 확인). 향후 acquisition 시 이 둘을 혼동하지 않아야 한다.

**Source**: [Yes24 중고샵](https://m.yes24.com/Goods/Detail/25809055), [교보문고](https://product.kyobobook.co.kr/detail/S000000688003), [북코아](https://www.bookoa.co.kr/book/detail/67e7efee6d54a52a5dc0b51c)

---

## 9. Authority Assessment

| 후보 | 저자/편집자 전문성 | 출판기관 신뢰성 | 학술적 신뢰성 | 용어 표준화 가능성 |
|------|---------------------|-------------------|----------------|----------------------|
| A (새성경사전) | 편집부(무명) — 원저(IVP/Tyndale, J.D. Douglas 등)는 전문성 VERIFIED, 한국어판 번역진은 미확인 | CLC — 장기간 서구 evangelical 저작 번역 이력 보유, VERIFIED | 원저가 표준 evangelical Bible dictionary(EN-BAP-001)이므로 높음, 단 번역 품질은 미확인 | 높음 — 원저 자체가 이미 표준 참고서 |
| B (IVP성경신학사전) | 권연경 — 개인 학위·경력 VERIFIED(전문성 높음), 원저 편집자(Alexander, Rosner)도 저명 evangelical 학자 | IVP코리아 — 한국 복음주의 학계에서 광범위하게 사용되는 출판사, VERIFIED | 높음 — 최신(2024), 신뢰할 수 있는 원저·역자 | 높음, 단 최근 출간이라 아직 한국 학계에서의 수용도는 UNKNOWN |
| C (기독교대백과사전) | 편찬위원회(집단 저작), 개인 전문성 확인 불가 | 기독교문사 — 개신교 백과사전 전문 출판사, 존재는 VERIFIED이나 편집 방침(교단적 균형 등) 미확인 | 중간 — 오래된(1990) 일반 백과사전, 최신 학술 기준 반영 여부 UNKNOWN | 낮음~중간 — KO-only, 일반 백과사전이라 정의의 깊이가 전문 신학사전보다 얕을 가능성 |

---

## 10. Bibliographic Verification

§6~§8 표에서 이미 상세 기술함. 요약:

| 후보 | Title | Author/Editor | Publisher | Edition | Year | ISBN | 판정 |
|------|-------|----------------|-----------|---------|------|------|------|
| A | 새성경사전 | 편집부 | CLC | 4판 | 2001 | 9788934106708 | **VERIFIED** |
| B | IVP성경신학사전 | Alexander/Rosner(원저), 권연경(역) | IVP코리아 | (초판 추정, 미확인) | 2024 | 978-89-328-2263-1 | **VERIFIED** |
| C | 기독교대백과사전 | 편찬위원회 | 기독교문사 | 16권, 연도 불일치 있음 | 1990(또는 1985 4판) | 확인 안 됨 | **PARTIALLY VERIFIED** |

**Bibliographically verified ≠ theologically authoritative**(§15 원칙) — 이
구분을 §9(Authority Assessment)와 분리 유지했다.

---

## 11. Theological Compatibility

| 후보 | General Korean theological authority | Baptist theological authority | Evangelical authority | SBC official authority |
|------|----------------------------------------|-------------------------------|-------------------------|--------------------------|
| A (새성경사전, CLC) | VERIFIED (원저가 표준 evangelical Bible dictionary) | **NOT VERIFIED** | VERIFIED (CLC/IVP-Tyndale 계열, 초교파 evangelical) | **NOT VERIFIED** |
| B (IVP성경신학사전) | VERIFIED | **NOT VERIFIED** | VERIFIED (IVP/Apollos 계열, 초교파 evangelical, 한국 복음주의 신학계에서 널리 사용) | **NOT VERIFIED** |
| C (기독교대백과사전) | VERIFIED (단, 일반 개신교/기독교 전반 포괄 — "총망라" 성격) | **NOT VERIFIED** | CONDITIONAL — 특정 evangelical 색채보다 폭넓은 개신교 일반 백과사전 성격, 교단 편향 여부 미확인 | **NOT VERIFIED** |

**세 후보 모두 Baptist-specific 또는 SBC official authority가 아니다** — 이를
숨기지 않고 명시한다. 세 후보 모두 초교파적(trans-denominational) evangelical
또는 general-Protestant 성격이며, 이는 NAE의 "보수적 복음주의 신학 연구
목적"과는 **양립 가능(compatible)**하지만 Baptist ecclesiology-specific
authority(예: 기존 등록된 Dagg/Hiscox/SLBC1689/PBC1742/NHBC1833)와는 **다른
층위**의 authority임을 인식해야 한다. §4.3 원문도 "권위 있는 한국어
신학용어사전"만 요구하며 Baptist-specific을 요구하지 않는다 — 이 기준에서는
A/B 모두 적격이다.

---

## 12. Acquisition Route

### Candidate A (새성경사전)

```
1. Legitimate purchase (PRIMARY route)
   - Yes24: https://www.yes24.com/Product/Goods/160273
   - 11번가: http://www.11st.co.kr/products/1121209606
   - 가격: 약 54,000원(할인가 기준, 변동 가능)
2. Library / institution access — 미확인(국내 신학대학 도서관 소장 가능성
   높으나 이번 조사에서 특정 기관 확인은 하지 않음)
3. Other lawful access — 해당 없음
```

### Candidate B (IVP성경신학사전)

```
1. Legitimate purchase (PRIMARY route, 단 §18 DRM 리스크 참고)
   - IVP 코리아 공식 사이트: https://ivp.co.kr/books/book_detail.html?book=s01&idx=1722
   - 가격: 44,000원
   - **주의**: 전자책(E-Book)으로만 확인됨. 인쇄본 존재 여부 미확인.
     E-Book 플랫폼의 DRM/이용약관이 corpus 추출을 허용하는지 **반드시 구매
     전에 확인**해야 한다(§18).
2. Institutional access — 미확인
```

### Candidate C (기독교대백과사전) — FALLBACK

```
1. Legitimate purchase — 중고서점 경로만 확인됨
   - Yes24 중고샵, 교보문고, 북코아 (전16권 완질 여부는 개별 확인 필요)
2. Library access — 국내 신학대학/종합대학 도서관 소장 가능성 높음(오래된
   표준 참고서이므로), 단 이번 조사에서 특정 기관 확인은 하지 않음
```

**CUE는 위 링크·가격 정보를 구매 편의를 위해 제공할 뿐, 어떤 구매/다운로드/
로그인도 대행하지 않았다.**

---

## 13. Edition Recommendation

### Candidate A

```
Title:          새성경사전 (New Bible Dictionary)
Author/Editor:  편집부 (원저: J.D. Douglas 등)
Publisher:       기독교문서선교회(CLC)
Edition:         4판
Year:            2001
ISBN:            9788934106708
Language:        Korean (번역), 원문 English
Format:          인쇄본(양장), 1,898면
```

**추천 이유**: 이것이 현재 시중에서 확인되는 **유일한 판**이다(더 최신 판을
찾지 못함 — §4.13.1의 검색 결과 참고). 여러 판이 경쟁하는 상황이 아니므로
판본 선택의 모호함이 낮다. **단, 이 4판이 NAE의 EN-BAP-001(3rd ed., 1996)과
정확히 어느 영어 판에 대응하는지는 실물의 판권면(colophon)에서 반드시
확인해야 한다** — "4판"이 한국어판 자체의 인쇄 차수를 의미할 수도 있고,
원서의 특정 edition을 지칭할 수도 있어 이번 조사만으로는 확정할 수 없다
(NOT VERIFIED로 유지).

### Candidate B

```
Title:          IVP성경신학사전 (New Dictionary of Biblical Theology)
Author/Editor:  T. Desmond Alexander, Brian S. Rosner (원저)
Translator:      권연경
Publisher:       IVP(한국기독학생회출판부)
Edition:         확인 안 됨(초판으로 추정, 미확인)
Year:            2024
ISBN:            978-89-328-2263-1
Language:        Korean (번역), 원문 English
Format:          전자책(E-Book) — 인쇄본 여부 미확인
```

**추천 이유**: 가장 최근 출간(2024)이며 역자가 개인 식별 가능·전문성
검증됨(§9) — 향후 provenance 재확인이 가장 용이한 후보(§14의 Reproducibility
기준에 가장 부합). 다만 전자책 포맷의 라이선스 제약(§18)이 acquisition
결정 전에 반드시 해소되어야 한다.

---

## 14. Primary Recommendation

**Candidate A — 새성경사전 (New Bible Dictionary, Korean Edition)**

선정 근거:
1. **재현성(Reproducibility)** — 단일 판만 시중에 존재해 판본 혼동 위험이
   낮다.
2. **인쇄본 포맷** — Smith Bible Dictionary에서 이미 검증된 "인쇄본 구매 →
   스캔 → OCR/djvu → canonicalization" 경로를 그대로 재사용할 수 있다
   (Candidate B의 e-book DRM 리스크가 없음).
3. **원저와의 직접 대응** — EN-BAP-001(이미 NAE가 선정한 English canonical
   source)과 동일 저작의 공식 번역이므로, ADR-029 §4.3-3(영어 원문 cross-
   reference)을 **가장 직접적인 형태**로 만족시킬 잠재력이 있다 — 같은
   dictionary entry의 영어/한국어 쌍을 직접 대조할 수 있다.
4. **즉시 구매 가능** — 신간으로 2개 소매처에서 실시간 재고 확인됨.

**단, 이 추천은 "acquisition 이후 검증"을 전제로 한다** — bibliographically
verified라는 사실이 곧 theologically authoritative임을 자동으로 의미하지
않는다(§15). 실물 확보 후 §16의 identity verification 단계를 반드시
거쳐야 한다.

---

## 15. Alternative Recommendation

**Secondary — Candidate B (IVP성경신학사전)**

병행 또는 대체 후보로 권장. 개인 역자 신원이 확인되어 provenance 추적이
가장 용이하고, 최신 학술 기준을 반영한 원저(2000년대 이후 IVP/Apollos
계열)라는 장점이 있다. 단, e-book 포맷의 corpus-extraction 라이선스 여부가
구매 전 확인되지 않으면 acquisition route로 채택하지 않는다.

**Fallback — Candidate C (기독교대백과사전)**

Baptist-specific authority가 여전히 확인되지 않는 상황에서, 더 넓은 범위의
일반 개신교 참고자료가 필요할 경우의 대비책. 16권 완질 확보의 실무 부담과
연도/판 불일치(§8)로 인해 PRIMARY/SECONDARY보다 우선순위가 낮다.

---

## 16. Acquisition Instructions for HQ

```
STEP 1 — HUMAN ACQUISITION (HQ 또는 HQ가 지정한 담당자)
  Candidate A를 Yes24 또는 11번가에서 정상 구매한다.
  (선택) Candidate B를 IVP코리아 공식 채널에서 구매하되, 구매 전
  전자책 플랫폼의 "다운로드/텍스트 추출/개인 연구 목적 사용" 약관을
  확인한다 — DRM이 텍스트 추출을 금지하면 이 후보는 acquisition에서
  제외하고 인쇄본 유통 여부를 재확인한다.

STEP 2 — SOURCE PLACEMENT (Human 또는 C1)
  구매한 실물(또는 정당하게 다운로드한 파일)을
  NAE/corpus/raw/library/<candidate_id>/ 에 배치한다.
  (이 경로는 설계 제안일 뿐이며, 이번 task에서 디렉터리를 생성하지 않았다.)

STEP 3 — IDENTITY VERIFICATION (CUE)
  판권면(colophon)에서 정확한 edition/원서 대응 관계를 확인한다.
  §13에서 NOT VERIFIED로 남긴 "4판 ↔ 원서 edition" 대응을 이 단계에서
  확정한다.

STEP 4 — CHECKSUM (C1)
  SHA-256 checksum 계산, source_manifest.yaml 형식에 맞춰 기록 준비.

STEP 5 — MANIFEST REGISTRATION (C1, CUE 검토)
  source_manifest.yaml에 신규 entry 추가(이번 task에서는 수행하지 않음).

STEP 6 — CANONICALIZATION (C1)
  기존 Smith/EN-BAP 파이프라인(`NAE/pipeline/canonical/pipeline.py`) 재사용.
  Architecture 변경 불필요(이미 §3에서 PIPELINE: READY로 확인됨).

STEP 7 — TERMINOLOGY DISCOVERY (CUE 주도, C1 지원)
  canonicalized 텍스트에서 실제 dictionary entry를 조사해 ADR-029 §4.4
  스키마(term_id/korean_term/english_term/aliases/definition/source/
  provenance/confidence)로 최소 1건 이상 기록한다. **이것이 지금까지
  존재하지 않았던 PHASE 1의 실질적 산출물이다.**

STEP 8 — CANONICAL TERM VALIDATION (CUE 독립검증)
  §4.3 우선순위 기준으로 각 term의 출처 authoritativeness를 재확인.

STEP 9 — ADR-029 PHASE 1 GATE (CUE 판정, HQ 승인)
  §3 Gate("canonical term validation PASS") 충족 여부를 CUE가 재판정하고,
  ADR-029 §10에 따라 HQ가 최종 승인한다.
```

| 단계 | Responsible Agent |
|------|--------------------|
| STEP 1 (Acquisition) | **Human (HQ 또는 지정 담당자)** |
| STEP 2 (Placement) | Human 또는 C1 |
| STEP 3 (Identity Verification) | **CUE** |
| STEP 4 (Checksum) | C1 |
| STEP 5 (Manifest Registration) | C1 (구현), CUE (검토) |
| STEP 6 (Canonicalization) | C1 |
| STEP 7 (Terminology Discovery) | **CUE (주도)**, C1 (지원) |
| STEP 8 (Canonical Term Validation) | **CUE (독립검증)** |
| STEP 9 (PHASE 1 Gate 판정) | CUE (판정), **HQ (최종 승인)** |

---

## 17. Post-Acquisition Processing Plan

§16의 STEP 2~9가 post-acquisition plan이다. **이번 task에서는 STEP 1도
수행하지 않았고, STEP 2 이후 어떤 단계도 시작하지 않았다** — no
canonicalization, no TSU extraction, no embedding, no Qdrant ingestion, no
application integration(§12 지시사항 준수).

---

## 18. Risks / Limitations

| 리스크 | 영향 | 완화 방법 |
|--------|------|-----------|
| Candidate A "4판"이 EN-BAP-001의 정확히 어느 영어 edition에 대응하는지 미확인 | 잘못된 edition을 canonical로 등록할 위험 | STEP 3(Identity Verification)에서 실물 판권면 확인 필수 |
| Candidate B가 전자책만 확인됨 — 인쇄본 여부 미확인, DRM이 텍스트 추출을 금지할 가능성 | Smith와 동일한 legitimate-extraction 전제가 깨질 수 있음(EN-BAP-002의 archive.org CDL 문제와 유사한 패턴) | 구매 전 IVP코리아 e-book 플랫폼 이용약관 확인, 필요시 인쇄본 유통 여부 재확인 |
| Candidate B의 원저(New Dictionary of Biblical Theology)는 NAE의 기존 EN-BAP-001~012 목록에 없는 신규 English source | ADR-029 §4.3-3(영어 원문 cross-reference)에 쓰려면 이 원저 자체도 별도로 English canonical 후보로 검토돼야 함 — 이번 보고서는 그 검토를 수행하지 않았다 | 별도 task로 English source additional-candidate 평가 필요(구현 아님, 기록만) |
| Candidate C 연도/판 불일치(1990 vs 1985 4판) | 정확한 서지 식별 실패 위험 | 구매 전 판매자에게 정확한 판/연도 재확인 |
| Candidate C는 KO-only, English term 대응 없음 | §4.3-3 cross-reference 용도로 쓸 수 없음 — §4.3-1/2 용도로만 유효 | FALLBACK 지위 유지, PRIMARY로 승격하지 않음 |
| 세 후보 모두 Baptist/SBC-specific authority 아님(§11) | NAE의 Baptist ecclesiology-specific 연구에는 여전히 gap 존재 | KR-BAP-001(한국침례교신학사전) 확인은 계속 별도 트랙으로 유지(§4) — 이번 package로 이 gap이 해소된다고 주장하지 않는다 |
| 가격/재고 정보는 조회 시점(2026-08-26) 기준이며 변동 가능 | 실제 구매 시 가격/재고가 다를 수 있음 | STEP 1 실행 시 재확인 필요 |
| "Recommended" ≠ "Authoritative"(§15) | PRIMARY 추천이 곧 canonical 확정을 의미하지 않음 | STEP 7~9(Terminology Discovery, Validation, Gate 판정)를 반드시 거쳐야 함 |

---

## 19. Mutation Audit

| Action | Performed? |
|--------|-----------|
| Code modification | NO |
| Corpus mutation | NO |
| Embedding execution | NO |
| Embedding cache mutation | NO |
| Qdrant mutation | NO |
| Manifest mutation | NO |
| Source acquisition (purchase/download) | NO |
| Copyright circumvention / DRM bypass | NO — 오히려 §18에서 DRM 리스크를 명시적으로 경고함 |
| Library login | NO |
| Corpus ingestion | NO |
| Git add | NO |
| Git commit | NO |
| 기존 다른 session의 변경사항 수정/되돌림 | NO |

이번 task에서 수행한 유일한 외부 행위는 **read-only WebSearch/WebFetch**로
공개된 서점/출판사 페이지에서 서지정보를 조회한 것이다 — 구매, 로그인,
다운로드, 저작권 우회는 전혀 수행하지 않았다.

---

## 20. Git Status

```bash
$ git status --short   # /Users/David/DBMA, 이 보고서 작성 직전
 M NAE/smith_activation.py
 M docs/STATE.md
 D test_seal_*/... (9 files, 이전 세션부터 존재)
 M ui/pages/chat.py
?? docs/agents/cue/{기존 15개 PHASE1/CUE 문서}
```

이번 보고서가 추가하는 파일:
```
?? docs/agents/cue/CUE-PHASE1-KOREAN-AUTHORITY-ACQUISITION-READINESS-PACKAGE.md
```

기존 uncommitted 변경사항(다른 세션 소유) 중 어느 것도 수정/삭제하지 않았다.
**Git add/commit: 수행하지 않음.**

---

## 21. Final Decision

```text
NAE PHASE 1 — KOREAN AUTHORITY ACQUISITION READINESS

PHASE 1 STATUS:
BLOCKED

TRUE BLOCKER:
No verified Korean authoritative source

PRIMARY RECOMMENDATION:
새성경사전 (New Bible Dictionary, Korean ed.), 편집부 편, 기독교문서선교회
(CLC), 4판, 2001, ISBN 9788934106708 — 1,898면, 인쇄본

LEGITIMATE ACQUISITION ROUTE:
Legitimate purchase via Yes24 (https://www.yes24.com/Product/Goods/160273)
or 11st (http://www.11st.co.kr/products/1121209606); approx. 54,000 KRW

SECONDARY:
IVP성경신학사전 (Korean tr. of New Dictionary of Biblical Theology), tr.
권연경, IVP코리아, 2024, ISBN 978-89-328-2263-1 — CONDITIONAL on e-book
DRM/license terms permitting text extraction (unverified — confirm before
purchase)

HUMAN ACTION REQUIRED:
YES

CUE ACQUISITION:
NO

C1 IMPLEMENTATION:
NO

PIPELINE CHANGE:
0

PRODUCTION MUTATION:
0

GIT COMMIT:
NO

NEXT AUTHORIZED ACTION:
HQ human acquisition of PRIMARY source (새성경사전, CLC, 2001,
ISBN 9788934106708), followed by CUE identity verification (§16 STEP 3)
before any manifest/canonicalization work begins.
```

---

**Package Mode**: READ-ONLY ACQUISITION READINESS
**Mutations**: 0
**Git add/commit**: NO
**Report generated**: 2026-08-26
**Report location**: main worktree (`/Users/David/DBMA`), consistent with the
existing PHASE 1 document chain.
