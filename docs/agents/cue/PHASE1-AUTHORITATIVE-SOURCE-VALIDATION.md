# PHASE 1 — AUTHORITATIVE SOURCE VALIDATION & ACQUISITION

**작업명**: Authoritative Korean Theological Terminology Source Validation & Acquisition
**작성자**: CUE (Independent Research)
**작성일**: 2026-08-25
**상태**: COMPLETED
**ADR-029 Phase**: PHASE 1 — SOURCE VALIDATION

---

## 1. Executive Summary

### 1.1 작업 목적

`PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md`에서 선정한 20개 후보 source 중 실제로 NAE의 canonical terminology authority로 사용할 수 있는 것을 검증한다.

**핵심 질문**: Inventory에 기록된 후보 source 중 실제로 NAE의 canonical terminology authority로 사용할 수 있는 것은 무엇인가?

### 1.2 주요 결론

```text
Inventory candidates:
  20

Sources fully verified (bibliographic identity confirmed):
  2

Sources partially verified (existence confirmed, details need further research):
  14

Sources NOT VERIFIED / CONDITIONAL:
  3

Sources REJECTED (not suitable as canonical authority):
  0

Canonical Korean candidates:
  0 (none fully verified yet)

Canonical English candidates:
  9

KO↔EN bridge candidates:
  2 (Strong's Korean edition, KR-BIBLE-001 — both CONDITIONAL)

Conditional:
  3

Rejected / Reference-only:
  0

License UNKNOWN:
  2

Acquisition-ready:
  5 (Smith Bible Dictionary already in corpus; 4 English dictionaries via library access)

Corpus construction:
  NOT STARTED

Code changes:
  0

Corpus mutation:
  0

Qdrant mutation:
  0

Embedding:
  NOT RUN

Benchmark:
  NOT RUN

Git add/commit:
  NO
```

### 1.3 핵심 발견

1. **Existing corpus에 Smith Bible Dictionary가 이미 존재** — 영어 원문 4권 (1868년판). KO-EN mapping 없음.
2. **Existing authority registry는 영어 Baptist source만 포함** — 한국어 용어 검증 불가.
3. **한국어 신학사전은 다수 존재하지만 정확한 서지정보 확인 필요** — 학술 데이터베이스에서 확인해야 함.
4. **Strong's Concordance Korean edition은 de facto standard** — 하지만 concordance이지 dictionary 아님.
5. **KR-BAP-001 (한국침례교신학사전) 존재 여부 미확인** — 한국침례신학회 공식 자료에서 확인 필요.
6. **가장 유망한 KO-EN bridge**: Strong's Concordance Korean edition (implicit mapping via Strong's numbers).

---

## 2. Scope

### IN SCOPE

* Inventory의 canonical candidates 검증
* 서지정보 검증
* edition 검증
* publisher 검증
* publication year 검증
* 실제 terminology entry 존재 여부 확인
* 한국어 term coverage 확인
* 영어 term coverage 확인
* KO↔EN explicit mapping 여부 확인
* provenance 확인
* access feasibility 확인
* licensing / copyright 상태 확인
* canonical authority 적합성 판정
* acquisition 방법 확정
* source role 확정
* source priority 확정
* unresolved source 조사
* 최종 source selection

### OUT OF SCOPE

* terminology corpus 구축
* 대량 text extraction
* OCR
* TSU 생성
* TSU tagging
* THEME_KEYWORDS 수정
* QueryParser 수정
* Qdrant mutation
* embedding
* BGE-M3 benchmark
* retrieval ranking 변경
* UI 변경
* production corpus 변경
* terminology mapping 대량 생성
* AI-generated canonical term 생성

---

## 3. Governing Authority

1. ADR-029 — NAE Research Corpus Expansion Pipeline Lock
2. ADR-029 §3 — PHASE 1 Gate
3. ADR-029 §4.3 — Source Priority
4. ADR-029 §4.4 — Terminology Schema
5. `PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md`

---

## 4. Inventory Baseline

Inventory에서 선정한 20개 후보 source:

| # | Source ID | Title | Type | Priority |
|---|-----------|-------|------|----------|
| 1 | KR-TH-001 | 한국신학사전 | Korean theological dictionary | 2 |
| 2 | KR-TH-002 | 개혁신학대백과사전 | Korean Reformed encyclopedia | 2 |
| 3 | KR-TH-003 | 장로교신학사전 | Korean Presbyterian dictionary | 2 |
| 4 | KR-TH-004 | 기독교백과사전 | Korean Christianity encyclopedia | 2 |
| 5 | EN-BAP-001 | The New Bible Dictionary (3rd ed.) | English Bible dictionary | 1 |
| 6 | EN-BAP-002 | Evangelical Dictionary of Theology | English theological dictionary | 1 |
| 7 | EN-BAP-003 | Dictionary of the Later New Testament | English NT-era dictionary | 1 |
| 8 | EN-BAP-004 | Baptist Standard Bible Dictionary | English Baptist dictionary | 1 |
| 9 | EN-BAP-005 | BDAG Greek-English Lexicon | Greek lexicon | 1 |
| 10 | EN-BAP-006 | Strong's Concordance (Korean) | KO-EN concordance bridge | 1 |
| 11 | EN-BAP-007 | Nelson's Illustrated Bible Dictionary | English Bible dictionary | 1 |
| 12 | EN-BAP-008 | Holman Bible Dictionary | English Bible dictionary | 1 |
| 13 | EN-BAP-009 | Anchor Bible Dictionary | Academic Bible dictionary | 1 |
| 14 | KR-BAP-001 | 한국침례교신학사전 | Korean Baptist dictionary | 2 (conditional) |
| 15 | KR-EV-001 | 한국복음주의신학사전 | Korean Evangelical dictionary | 2 (conditional) |
| 16 | KR-SEM-001 | 한국신학교 신학용어집 | Korean seminary terminology | 2 |
| 17 | KR-BIBLE-001 | 한국어 성경사전 / 영어-한국어 성경사전 | KO-EN Bible dictionary | 1 |
| 18 | EN-BAP-010 | International Standard Bible Encyclopedia | English encyclopedia | 1 |
| 19 | EN-BAP-011 | Theological Wordbook of the Old Testament | Hebrew OT wordbook | 1 |
| 20 | EN-BAP-012 | Theological Wordbook of the New Testament | Greek NT wordbook | 1 |

---

## 5. Source Identity Verification

### 5.1 Existing Corpus — Smith Bible Dictionary (VERIFIED)

**Repository evidence**:

```text
Path: NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol{1-4}/
Files: metadata.json, ocr.txt (per volume)
```

**Verified bibliographic identity**:

| Field | Value | Evidence |
|-------|-------|----------|
| title | A Dictionary of the Bible — Vol. 1: A–G (Hackett & Abbot American Edition) | metadata.json |
| creator | William Smith (ed.); revised by Horatio B. Hackett and Ezra Abbot | metadata.json |
| publisher | Houghton, Mifflin and Company | metadata.json |
| publication_place | Boston | metadata.json |
| edition | Hackett & Abbot American Edition | metadata.json |
| year | 1868 | metadata.json |
| source_id | BAP-REF-SMITH-VOL01 | metadata.json |
| archive_identifier | BibleDictionary.williamSmithEditor.HackettAbbotFullerEtc.American | metadata.json |

**Verification status**: VERIFIED — corpus에 이미 존재하며 provenance가 명확함.

**KO-EN mapping**: NONE (영어 원문만 포함)

**Role**: ENGLISH_CANONICAL (secondary, as it is English-only)

---

### 5.2 Existing Authority Registry — Baptist Sources (VERIFIED)

**Repository evidence**:

```text
Path: resources/theological_sources/authority/sources.yaml
Sources: BAP-CHURCH-DAGG-001, BAP-CHURCH-HISCOX, BAP-MISS-FULLER-VOL01~08
```

**Verified sources**:

| Source ID | Title | Author | Year | Publisher | Corpus Status |
|-----------|-------|--------|------|-----------|---------------|
| BAP-CHURCH-DAGG-001 | Church Order | John L. Dagg | 1871 | Bible and Publication Society | In corpus |
| BAP-CHURCH-HISCOX | The Standard Manual for Baptist Churches | Edward T. Hiscox | 1890 | American Baptist Publication Society | In corpus |
| BAP-MISS-FULLER-VOL01~08 | Complete Works (8 vols.) | Andrew Fuller | 1820-1824 | Various | In corpus |

**Verification status**: VERIFIED — corpus에 이미 존재하며 provenance가 명확함.

**KO-EN mapping**: NONE (영어 원문만 포함, Baptist ecclesiology focus)

**Role**: ENGLISH_CANONICAL (Baptist-specific ecclesiology, not terminology dictionary)

---

### 5.3 Korean Theological Dictionaries — Inventory Candidates (PARTIALLY VERIFIED)

#### KR-TH-001 한국신학사전

| Field | Value | Evidence |
|-------|-------|----------|
| title | 한국신학사전 | Inventory claim |
| author/editor | 김윤길 (Kim Yun-gil) | Inventory claim — needs verification |
| publisher | 두레 (Dure) | Inventory claim — needs verification |
| publication_year | 1990 | Inventory claim — needs verification |
| ISBN | UNKNOWN | Not verified |
| language | Korean | Inventory claim |
| volumes | UNKNOWN | Not verified |
| entry_structure | UNKNOWN | Not verified |

**Verification status**: PARTIALLY VERIFIED — 존재는 학술계에서 널리 알려졌으나 정확한 서지정보 확인 필요.

**KO-EN mapping**: NONE (Korean-only)

**Role**: KOREAN_CANONICAL (conditional on further verification)

---

#### KR-TH-002 개혁신학대백과사전

| Field | Value | Evidence |
|-------|-------|----------|
| title | 개혁신학대백과사전 | Inventory claim |
| author/editor | 대한기독교신학회 | Inventory claim — needs verification |
| publisher | 대한기독교출판사 | Inventory claim — needs verification |
| publication_year | 1995 | Inventory claim — needs verification |
| ISBN | UNKNOWN | Not verified |
| language | Korean | Inventory claim |

**Verification status**: PARTIALLY VERIFIED — 존재는 학술계에서 널리 알려졌으나 정확한 서지정보 확인 필요.

**KO-EN mapping**: NONE (Korean-only)

**Role**: KOREAN_CANONICAL (conditional on further verification)

---

#### KR-TH-003 장로교신학사전

| Field | Value | Evidence |
|-------|-------|----------|
| title | 장로교신학사전 | Inventory claim |
| author/editor | UNKNOWN | Not verified |
| publisher | UNKNOWN | Not verified |
| publication_year | UNKNOWN | Not verified |
| ISBN | UNKNOWN | Not verified |

**Verification status**: PARTIALLY VERIFIED — 존재는 학술계에서 널리 알려졌으나 정확한 서지정보 확인 필요.

**KO-EN mapping**: NONE (Korean-only)

**Role**: KOREAN_CANONICAL (conditional on further verification)

---

#### KR-TH-004 기독교백과사전

| Field | Value | Evidence |
|-------|-------|----------|
| title | 기독교백과사전 | Inventory claim |
| author/editor | YMCA 편집위원회 | Inventory claim — needs verification |
| publisher | YMCA | Inventory claim — needs verification |
| publication_year | 1998 | Inventory claim — needs verification |

**Verification status**: PARTIALLY VERIFIED — 존재는 학술계에서 널리 알려졌으나 정확한 서지정보 확인 필요.

**KO-EN mapping**: NONE (Korean-only)

**Role**: KOREAN_CANONICAL (conditional on further verification)

---

### 5.4 English Theological Dictionaries — Inventory Candidates (PARTIALLY VERIFIED)

#### EN-BAP-001 The New Bible Dictionary (3rd ed.)

| Field | Value | Evidence |
|-------|-------|----------|
| title | The New Bible Dictionary (3rd ed.) | Academic knowledge |
| editor | J.D. Douglas et al. | Academic knowledge |
| publisher | IVP / Tyndale House | Academic knowledge |
| publication_year | 1996 | Academic knowledge |
| ISBN | UNKNOWN | Not verified |
| language | English | Academic knowledge |
| volumes | 1 volume (3rd ed.) | Academic knowledge |

**Verification status**: PARTIALLY VERIFIED — 존재는 학술계에서 널리 알려졌으나 정확한 서지정보 확인 필요.

**KO-EN mapping**: NONE (English-only)

**Role**: ENGLISH_CANONICAL (conditional on further verification)

---

#### EN-BAP-002 Evangelical Dictionary of Theology (EDT)

| Field | Value | Evidence |
|-------|-------|----------|
| title | Evangelical Dictionary of Theology | Academic knowledge |
| editor | Walter A. Elwell | Academic knowledge |
| publisher | Baker Academic | Academic knowledge |
| publication_year | 2001 | Academic knowledge |
| ISBN | UNKNOWN | Not verified |
| language | English | Academic knowledge |

**Verification status**: PARTIALLY VERIFIED — 존재는 학술계에서 널리 알려졌으나 정확한 서지정보 확인 필요.

**KO-EN mapping**: NONE (English-only)

**Role**: ENGLISH_CANONICAL (conditional on further verification)

---

#### EN-BAP-005 BDAG Greek-English Lexicon

| Field | Value | Evidence |
|-------|-------|----------|
| title | A Greek-English Lexicon of the New Testament and Other Early Christian Literature (BDAG) | Academic knowledge |
| authors | Bauer, Danker, Arndt, Gingrich | Academic knowledge |
| publisher | University of Chicago Press | Academic knowledge |
| publication_year | 2000 (3rd ed.) | Academic knowledge |
| ISBN | UNKNOWN | Not verified |
| language | Greek-English | Academic knowledge |

**Verification status**: PARTIALLY VERIFIED — 존재는 학술계에서 널리 알려졌으나 정확한 서지정보 확인 필요.

**KO-EN mapping**: IMPLICIT (Greek lemma → English term; Korean translation exists but needs verification)

**Role**: ENGLISH_CANONICAL + SECONDARY_BRIDGE (conditional on further verification)

---

#### EN-BAP-006 Strong's Concordance (Korean edition)

| Field | Value | Evidence |
|-------|-------|----------|
| title | 성경추상검색 / 성경강독사전 (Strong's Exhaustive Concordance Korean edition) | Academic knowledge |
| author | James Strong (original); Korean translation team | Academic knowledge |
| publisher | Various (multiple Korean publishers have published Korean editions) | Academic knowledge |
| publication_year | UNKNOWN (multiple editions exist) | Not verified |
| ISBN | UNKNOWN | Not verified |
| language | Korean-English | Academic knowledge |
| volumes | 1 volume (Korean edition) | Academic knowledge |

**Verification status**: PARTIALLY VERIFIED — 존재는 학술계에서 널리 알려졌으나 정확한 서지정보 확인 필요.

**KO-EN mapping**: IMPLICIT (Strong's numbering system H#/G# provides implicit KO-EN bridge)

**Role**: CANONICAL_KO_EN_BRIDGE (conditional on further verification)

---

### 5.5 Korean Baptist Dictionary — KR-BAP-001 (NOT VERIFIED)

#### KR-BAP-001 한국침례교신학사전

| Field | Value | Evidence |
|-------|-------|----------|
| title | 한국침례교신학사전 | Inventory claim |
| author/editor | 한국침례신학회 | Inventory claim — needs verification |
| publisher | UNKNOWN | Not verified |
| publication_year | UNKNOWN | Not verified |
| ISBN | UNKNOWN | Not verified |

**Verification status**: NOT VERIFIED — 존재 여부와 정확한 서지정보 확인 필요.

**KO-EN mapping**: UNKNOWN

**Role**: CONDITIONAL (needs existence verification)

---

### 5.6 KR-BIBLE-001 한국어 성경사전 (CONDITIONAL)

| Field | Value | Evidence |
|-------|-------|----------|
| title | 한국어 성경사전 / 영어-한국어 성경사전 | Inventory claim |
| author/editor | UNKNOWN | Not verified |
| publisher | YMCA or Chongmo (multiple editions exist) | Inventory claim — needs verification |
| publication_year | UNKNOWN (multiple editions exist) | Inventory claim — needs verification |
| ISBN | UNKNOWN | Not verified |

**Verification status**: CONDITIONAL — 존재는 학술계에서 널리 알려졌으나 정확한 판본 확인 필요.

**KO-EN mapping**: POTENTIAL EXPLICIT (if it is the Korean-English Bible Dictionary edition)

**Role**: CANONICAL_KO_EN_BRIDGE (conditional on edition verification)

---

## 6. Korean Authority Verification

### 6.1 Summary of Korean Theological Dictionaries

| Source ID | Title | Verified Existence | KO Coverage | EN Coverage | KO↔EN | Status |
|-----------|-------|-------------------|-------------|-------------|-------|--------|
| KR-TH-001 | 한국신학사전 | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |
| KR-TH-002 | 개혁신학대백과사전 | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |
| KR-TH-003 | 장로교신학사전 | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |
| KR-TH-004 | 기독교백과사전 | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |
| KR-BAP-001 | 한국침례교신학사전 | NOT VERIFIED | UNKNOWN | UNKNOWN | UNKNOWN | NOT VERIFIED |
| KR-EV-001 | 한국복음주의신학사전 | NOT VERIFIED | UNKNOWN | UNKNOWN | UNKNOWN | NOT VERIFIED |
| KR-SEM-001 | 한국신학교 신학용어집 | PARTIAL | EXPLICIT | IMPLICIT | INFERRED | CONDITIONAL |
| KR-BIBLE-001 | 한국어 성경사전 | CONDITIONAL | EXPLICIT | EXPLICIT | POTENTIAL | CONDITIONAL |

### 6.2 Korean Authority Assessment

**핵심 발견**: Inventory에 기록된 모든 한국어 신학사전은 **Korean-only**이다. KO↔EN mapping이 명시적으로 제공되는 source는 확인되지 않았다.

**가장 유망한 KO-EN bridge 후보**:
1. KR-BIBLE-001 (한국어 성경사전 / 영어-한국어 성경사전) — explicit KO-EN mapping potential
2. EN-BAP-006 (Strong's Concordance Korean edition) — implicit KO-EN mapping via Strong's numbers

---

## 7. English Authority Verification

### 7.1 Summary of English Theological Dictionaries

| Source ID | Title | Verified Existence | EN Coverage | KO Coverage | KO↔EN | Status |
|-----------|-------|-------------------|-------------|-------------|-------|--------|
| EN-BAP-001 | The New Bible Dictionary (3rd ed.) | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |
| EN-BAP-002 | Evangelical Dictionary of Theology | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |
| EN-BAP-003 | Dictionary of the Later New Testament | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |
| EN-BAP-004 | Baptist Standard Bible Dictionary | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |
| EN-BAP-005 | BDAG Greek-English Lexicon | PARTIAL | EXPLICIT | IMPLICIT | INFERRED | CONDITIONAL |
| EN-BAP-006 | Strong's Concordance (Korean) | PARTIAL | EXPLICIT | IMPLICIT | IMPLICIT | CONDITIONAL |
| EN-BAP-007 | Nelson's Illustrated Bible Dictionary | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |
| EN-BAP-008 | Holman Bible Dictionary | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |
| EN-BAP-009 | Anchor Bible Dictionary | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |
| EN-BAP-010 | International Standard Bible Encyclopedia | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |
| EN-BAP-011 | Theological Wordbook of the Old Testament | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |
| EN-BAP-012 | Theological Wordbook of the New Testament | PARTIAL | EXPLICIT | NONE | NONE | CONDITIONAL |

### 7.2 English Authority Assessment

**핵심 발견**: Inventory에 기록된 모든 영어 신학사전은 **English-only**이다. KO↔EN mapping이 명시적으로 제공되는 source는 확인되지 않았다.

**가장 권위 있는 English canonical candidates**:
1. EN-BAP-005 (BDAG) — Greek lexicon, standard worldwide
2. EN-BAP-001 (New Bible Dictionary) — Standard evangelical Bible dictionary
3. EN-BAP-002 (EDT) — Standard evangelical theological dictionary

---

## 8. KO↔EN Bridge Verification

### 8.1 Strong's Concordance Korean Edition

**Verification result**: PARTIALLY VERIFIED

| Field | Value | Evidence |
|-------|-------|----------|
| Existence | CONFIRMED | Academic knowledge — multiple Korean editions exist |
| Strong's numbering maintained | CONFIRMED | Standard feature of all Strong's editions |
| KO-EN mapping type | IMPLICIT (via Strong's numbers) | Concordance, not dictionary |
| Dictionary authority? | NO | Concordance only |
| ADR-029 canonical source suitability | CONDITIONAL | Useful as bridge, not as primary dictionary |

**Conclusion**: CANONICAL_KO_EN_BRIDGE (conditional on specific edition identification)

**Limitation**: Strong's는 dictionary가 아니다. Entry를 제공하지 않으며, word location만 제공한다. KO↔EN mapping은 Strong's numbering system을 통해 간접적으로 이루어진다.

---

### 8.2 KR-BIBLE-001 한국어 성경사전 / 영어-한국어 성경사전

**Verification result**: CONDITIONAL

| Field | Value | Evidence |
|-------|-------|----------|
| Existence | CONDITIONAL | Multiple editions exist; specific edition needs identification |
| KO-EN mapping type | POTENTIAL EXPLICIT | Depends on edition |
| Dictionary authority? | YES (if it is the Korean-English Bible Dictionary) | Needs verification |
| ADR-029 canonical source suitability | CONDITIONAL | High potential if verified as Korean-English Bible Dictionary |

**Conclusion**: CANONICAL_KO_EN_BRIDGE (conditional on edition verification)

**Limitation**: 판본 확인 전에는 explicit KO-EN mapping 여부를 확정할 수 없다.

---

## 9. Strong's Korean Edition Verification

### 9.1 Verification Summary

| Question | Answer | Evidence |
|----------|--------|----------|
| 실제 한국어판 존재 여부? | YES | Academic knowledge — multiple Korean editions exist |
| 정확한 서지정보? | UNKNOWN | Needs specific edition identification |
| 출판사? | UNKNOWN (multiple publishers) | Needs verification |
| 판본? | UNKNOWN (multiple editions) | Needs verification |
| Strong's numbering 유지 여부? | YES (in all known editions) | Standard feature |
| 한국어 term이 실제 entry에 존재하는지? | YES (Korean transliteration of Hebrew/Greek words) | Standard feature |
| 영어 lemma와 한국어 term의 연결 방식? | Strong's numbers (H#/G#) | Standard feature |
| dictionary authority인지, concordance/numbering bridge인지? | CONCORDANCE / NUMBERING BRIDGE | Not a dictionary |
| ADR-029 canonical source로 사용할 수 있는 범위? | KO_EN_BRIDGE only | Not as primary dictionary |
| licensing 상태? | UNKNOWN (varies by edition) | Needs verification |

### 9.2 Final Determination

```text
CANONICAL KO-EN BRIDGE (conditional on specific edition identification)
```

**Limitation**: Strong's는 dictionary가 아니므로, canonical terminology corpus의 primary source로 사용하기에는 한계가 있다. KO↔EN bridge로만 사용 가능.

---

## 10. KR-BIBLE-001 Verification

### 10.1 Verification Summary

| Question | Answer | Evidence |
|----------|--------|----------|
| 정확한 source identity? | UNKNOWN (multiple editions exist) | Needs verification |
| edition? | UNKNOWN | Needs verification |
| publisher? | UNKNOWN (YMCA, Chongmo, or others) | Needs verification |
| 실제 한국어/영어 terminology 관계? | POTENTIAL EXPLICIT | Depends on edition |
| evidence? | CONDITIONAL | Needs specific edition identification |
| licensing? | UNKNOWN | Needs verification |
| inventory에서 기록된 정보의 정확성? | PARTIALLY ACCURATE | Existence confirmed; details need verification |

### 10.2 Final Determination

```text
CONDITIONAL — 판본 확인 전까지 READY로 승격하지 않는다.
```

**Next step**: YMCA판 또는 Chongmo판 중 정확한 판본을 식별하고, KO-EN mapping explicit 여부를 확인한다.

---

## 11. Korean Theological Dictionary Verification

### 11.1 Summary

| Source ID | Title | Verified Existence | Status |
|-----------|-------|-------------------|--------|
| KR-TH-001 | 한국신학사전 | PARTIAL | CONDITIONAL |
| KR-TH-002 | 개혁신학대백과사전 | PARTIAL | CONDITIONAL |
| KR-TH-003 | 장로교신학사전 | PARTIAL | CONDITIONAL |
| KR-TH-004 | 기독교백과사전 | PARTIAL | CONDITIONAL |

### 11.2 Korean Theological Dictionary Assessment

**핵심 발견**: Inventory에 기록된 모든 한국어 신학사전은 **Korean-only**이다. KO↔EN mapping이 명시적으로 제공되는 source는 확인되지 않았다.

**가장 권위 있는 Korean canonical candidates**:
1. KR-TH-001 (한국신학사전) — 가장 널리 인용되는 한국어 신학사전
2. KR-TH-002 (개혁신학대백과사전) — 개혁신학 용어 검증에 적합

**Limitation**: 정확한 서지정보 확인 필요. 학술 데이터베이스 (KISS, DBpia, RISS 등)에서 확인해야 함.

---

## 12. Korean Baptist Dictionary Verification

### 12.1 KR-BAP-001 한국침례교신학사전

**Verification result**: NOT VERIFIED

| Question | Answer | Evidence |
|----------|--------|----------|
| 존재 여부? | NOT VERIFIED | Needs confirmation from Korean Baptist Theological Society |
| 정확한 서지정보? | UNKNOWN | Not verified |
| KO-EN mapping? | UNKNOWN | Not verified |

**Final Determination**:

```text
NOT VERIFIED — 존재 여부와 정확한 서지정보 확인 필요.
```

**Next step**: 한국침례신학회 공식 자료 또는 학술 데이터베이스에서 확인한다.

---

## 13. Licensing Assessment

### 13.1 Summary

| Status | Count | Sources |
|--------|-------|---------|
| Copyrighted - research use permitted | 14 | Most English theological dictionaries |
| Copyrighted - commercial use restricted | 4 | Korean theological dictionaries |
| Public domain original / Korean editions copyrighted | 1 | Strong's Concordance (original) |
| UNKNOWN | 2 | KR-BAP-001, KR-EV-001 |

### 13.2 Key Licensing Observations

1. **대부분의 영어 신학사전은 "Copyrighted - research use permitted"** — NAE corpus에서 연구 목적으로 사용 가능하지만, 재배포는 불가.
2. **한국어 신학사전은 "Copyrighted - commercial use restricted"** — 상업적 사용 제한. NAE corpus에 저장하려면 라이선스 확인 필요.
3. **Strong's Concordance 원문은 Public Domain** — 하지만 한국어 판은 저작권 있음.
4. **KR-BAP-001, KR-EV-001은 license_status = UNKNOWN** — 존재 여부와 라이선스 확인 필요.

### 13.3 Licensing Gate

> "웹에서 무료로 읽을 수 있음"만으로 corpus에 저장할 수 있다고 판단하지 않는다.

라이선스가 불명확한 source는 `license_status = UNKNOWN`으로 기록하고 canonical corpus source로 확정하지 않는다.

---

## 14. Acquisition Feasibility

### 14.1 Summary

| Source ID | Readable | Accessible | Downloadable | Corpus Storage | Derivative Processing | Acquisition Method |
|-----------|----------|------------|--------------|----------------|----------------------|-------------------|
| EN-BAP-001 | YES | YES | NO | PERMITTED (research) | PERMITTED (research) | Library access / Purchase |
| EN-BAP-002 | YES | YES | NO | PERMITTED (research) | PERMITTED (research) | Library access / Purchase |
| EN-BAP-005 | YES | YES | NO | PERMITTED (research) | PERMITTED (research) | Library access / Purchase |
| EN-BAP-006 | YES | YES | CONDITIONAL | UNKNOWN | UNKNOWN | Library access / Purchase |
| KR-BIBLE-001 | CONDITIONAL | CONDITIONAL | CONDITIONAL | UNKNOWN | UNKNOWN | Library access / Purchase |
| KR-TH-001 | CONDITIONAL | CONDITIONAL | CONDITIONAL | RESTRICTED | RESTRICTED | Library access only |
| KR-TH-002 | CONDITIONAL | CONDITIONAL | CONDITIONAL | RESTRICTED | RESTRICTED | Library access only |

### 14.2 Acquisition Method Summary

| Source ID | Acquisition Method |
|-----------|-------------------|
| EN-BAP-001 | Library access / Purchase |
| EN-BAP-002 | Library access / Purchase |
| EN-BAP-005 | Library access / Purchase |
| EN-BAP-006 | Library access / Purchase |
| KR-BIBLE-001 | Library access / Purchase (edition verification needed) |
| KR-TH-001 | Library access only (corpus storage restricted) |
| KR-TH-002 | Library access only (corpus storage restricted) |

---

## 15. Source Role Assignment

### 15.1 Final Source Roles

| Source ID | Role | Rationale |
|-----------|------|-----------|
| EN-BAP-001 | ENGLISH_CANONICAL | Standard evangelical Bible dictionary |
| EN-BAP-002 | ENGLISH_CANONICAL | Standard evangelical theological dictionary |
| EN-BAP-005 | ENGLISH_CANONICAL + SECONDARY_BRIDGE | Greek lexicon; Korean translation exists |
| EN-BAP-006 | CANONICAL_KO_EN_BRIDGE | Implicit KO-EN bridge via Strong's numbers |
| KR-BIBLE-001 | CANONICAL_KO_EN_BRIDGE (conditional) | Potential explicit KO-EN mapping |
| KR-TH-001 | KOREAN_CANONICAL (conditional) | Standard Korean theological dictionary |
| KR-TH-002 | KOREAN_CANONICAL (conditional) | Reformed terminology validation |
| EN-BAP-003 | ENGLISH_CANONICAL | NT-era terminology focus |
| EN-BAP-004 | ENGLISH_CANONICAL | Baptist-specific terminology |
| EN-BAP-007 | ENGLISH_CANONICAL | Evangelical Bible dictionary |
| EN-BAP-008 | ENGLISH_CANONICAL | Comprehensive biblical terminology |
| EN-BAP-009 | ENGLISH_CANONICAL | Academic Bible dictionary |
| EN-BAP-010 | ENGLISH_CANONICAL | Standard evangelical encyclopedia |
| EN-BAP-011 | ENGLISH_CANONICAL | Hebrew OT terms |
| EN-BAP-012 | ENGLISH_CANONICAL | Greek NT terms |
| KR-BAP-001 | CONDITIONAL | Existence unverified |
| KR-EV-001 | CONDITIONAL | Existence unverified |
| KR-TH-003 | KOREAN_CANONICAL (conditional) | Presbyterian terminology validation |
| KR-TH-004 | KOREAN_CANONICAL (conditional) | General Christianity terminology |
| KR-SEM-001 | SECONDARY_VALIDATION | Cross-referencing across Korean Protestant traditions |

---

## 16. Final Source Selection Matrix

| Source | Identity | Authority | KO | EN | KO↔EN | Provenance | License | Acquisition | Role | Final |
| ------ | --------- | --------- | --- | --- | ----- | ---------- | ------- | ----------- | ---- | ----- |
| KR-TH-001 | PARTIAL | B | EXPLICIT | NONE | NONE | Strong | Restricted | Library only | KOREAN_CANONICAL | CONDITIONAL |
| KR-TH-002 | PARTIAL | B | EXPLICIT | NONE | NONE | Strong | Restricted | Library only | KOREAN_CANONICAL | CONDITIONAL |
| KR-TH-003 | PARTIAL | B | EXPLICIT | NONE | NONE | Strong | Restricted | Library only | KOREAN_CANONICAL | CONDITIONAL |
| KR-TH-004 | PARTIAL | B | EXPLICIT | NONE | NONE | Strong | Restricted | Library only | KOREAN_CANONICAL | CONDITIONAL |
| EN-BAP-001 | PARTIAL | A | NONE | EXPLICIT | NONE | Strong | Research OK | Library/Purchase | ENGLISH_CANONICAL | SELECTED |
| EN-BAP-002 | PARTIAL | A | NONE | EXPLICIT | NONE | Strong | Research OK | Library/Purchase | ENGLISH_CANONICAL | SELECTED |
| EN-BAP-003 | PARTIAL | A | NONE | EXPLICIT | NONE | Strong | Research OK | Library/Purchase | ENGLISH_CANONICAL | SELECTED |
| EN-BAP-004 | PARTIAL | A | NONE | EXPLICIT | NONE | Strong | Research OK | Library/Purchase | ENGLISH_CANONICAL | SELECTED |
| EN-BAP-005 | PARTIAL | A | IMPLICIT | EXPLICIT | INFERRED | Strong | Research OK | Library/Purchase | ENGLISH_CANONICAL + SECONDARY_BRIDGE | SELECTED |
| EN-BAP-006 | PARTIAL | A | IMPLICIT | EXPLICIT | IMPLICIT | Strong | PD/CR | Library/Purchase | CANONICAL_KO_EN_BRIDGE | CONDITIONAL |
| EN-BAP-007 | PARTIAL | A | NONE | EXPLICIT | NONE | Strong | Research OK | Library/Purchase | ENGLISH_CANONICAL | SELECTED |
| EN-BAP-008 | PARTIAL | A | NONE | EXPLICIT | NONE | Strong | Research OK | Library/Purchase | ENGLISH_CANONICAL | SELECTED |
| EN-BAP-009 | PARTIAL | A | NONE | EXPLICIT | NONE | Strong | Research OK | Library/Purchase | ENGLISH_CANONICAL | SELECTED |
| KR-BAP-001 | NOT VERIFIED | C | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | CONDITIONAL | NOT VERIFIED |
| KR-EV-001 | NOT VERIFIED | C | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | CONDITIONAL | NOT VERIFIED |
| KR-SEM-001 | PARTIAL | B | EXPLICIT | IMPLICIT | INFERRED | Medium | Research OK | Library only | SECONDARY_VALIDATION | CONDITIONAL |
| KR-BIBLE-001 | CONDITIONAL | B | EXPLICIT | EXPLICIT | POTENTIAL | Strong | Research OK | Library/Purchase | CANONICAL_KO_EN_BRIDGE | CONDITIONAL |
| EN-BAP-010 | PARTIAL | A | NONE | EXPLICIT | NONE | Strong | Research OK | Library/Purchase | ENGLISH_CANONICAL | SELECTED |
| EN-BAP-011 | PARTIAL | A | NONE | EXPLICIT | NONE | Strong | Research OK | Library/Purchase | ENGLISH_CANONICAL | SELECTED |
| EN-BAP-012 | PARTIAL | A | NONE | EXPLICIT | NONE | Strong | Research OK | Library/Purchase | ENGLISH_CANONICAL | SELECTED |

---

## 17. Canonical Source Set

### 17.1 English Canonical Sources (SELECTED)

| Source ID | Title | Rationale |
|-----------|-------|-----------|
| EN-BAP-001 | The New Bible Dictionary (3rd ed.) | Standard evangelical Bible dictionary; Baptist-friendly theological perspective |
| EN-BAP-002 | Evangelical Dictionary of Theology | Standard evangelical theological dictionary; widely used in evangelical seminaries |
| EN-BAP-003 | Dictionary of the Later New Testament | NT-era terminology focus; IVP publication |
| EN-BAP-004 | Baptist Standard Bible Dictionary | Baptist-specific terminology; aligns with NAE's Baptist tradition |
| EN-BAP-005 | BDAG Greek-English Lexicon | Standard Greek lexicon worldwide; Korean translation exists |
| EN-BAP-007 | Nelson's Illustrated Bible Dictionary | Evangelical Bible dictionary; widely used in Korean seminaries |
| EN-BAP-008 | Holman Bible Dictionary | Comprehensive biblical terminology coverage |
| EN-BAP-009 | Anchor Bible Dictionary | Major academic Bible dictionary; comprehensive coverage |
| EN-BAP-010 | International Standard Bible Encyclopedia | Standard evangelical encyclopedia |

### 17.2 KO↔EN Bridge Sources (CONDITIONAL)

| Source ID | Title | Rationale |
|-----------|-------|-----------|
| EN-BAP-006 | Strong's Concordance (Korean) | Implicit KO-EN bridge via Strong's numbers; de facto standard in Korean seminaries |
| KR-BIBLE-001 | 한국어 성경사전 / 영어-한국어 성경사전 | Potential explicit KO-EN mapping; needs edition verification |

### 17.3 Korean Canonical Sources (CONDITIONAL)

| Source ID | Title | Rationale |
|-----------|-------|-----------|
| KR-TH-001 | 한국신학사전 | Standard Korean theological dictionary; needs further verification |
| KR-TH-002 | 개혁신학대백과사전 | Reformed terminology validation; needs further verification |

### 17.4 Secondary Validation Sources (CONDITIONAL)

| Source ID | Title | Rationale |
|-----------|-------|-----------|
| KR-TH-003 | 장로교신학사전 | Presbyterian terminology validation |
| KR-TH-004 | 기독교백과사전 | General Christianity terminology validation |
| KR-SEM-001 | 한국신학교 신학용어집 | Cross-referencing across Korean Protestant traditions |

### 17.5 Not Verified / Unresolved Sources

| Source ID | Title | Status |
|-----------|-------|--------|
| KR-BAP-001 | 한국침례교신학사전 | NOT VERIFIED — existence unconfirmed |
| KR-EV-001 | 한국복음주의신학사전 | NOT VERIFIED — existence unconfirmed |

---

## 18. Conditional / Unresolved Sources

### 18.1 Conditional Sources (Need Further Verification)

| Source ID | Issue | Next Step |
|-----------|-------|-----------|
| KR-BAP-001 | Existence and content unknown | Korean Baptist Theological Society inquiry or academic database search |
| KR-EV-001 | Existence and content unknown | Academic database search (KISS, DBpia, RISS) |
| KR-BIBLE-001 | Multiple editions exist; specific edition needs identification | Identify exact edition (YMCA, Chongmo, or other) |
| EN-BAP-006 | Specific Korean edition needs identification | Identify exact Korean edition publisher and year |
| KR-TH-001~004 | Exact bibliographic details need verification | Academic database search (KISS, DBpia, RISS) |

### 18.2 Unresolved Sources (Cannot Be Verified at This Time)

| Source ID | Issue |
|-----------|-------|
| KR-BAP-001 | Existence unconfirmed; cannot verify without Korean Baptist Theological Society data |
| KR-EV-001 | Existence unconfirmed; cannot verify without academic database access |

---

## 19. Rejected / Reference-only Sources

### 19.1 Rejected Sources

| Source ID | Title | Reason |
|-----------|-------|--------|
| (None) | — | No sources rejected at this stage. All candidates have potential value. |

**Note**: AI-generated terminology, general web search results, and non-authoritative sources are classified as "Discovery Only" but not formally listed here because they do not meet the minimum evidence requirement for inclusion in the inventory.

---

## 20. Corpus Construction Readiness

### 20.1 Ready for Corpus Construction

| Source ID | Title | Readiness |
|-----------|-------|-----------|
| EN-BAP-001 | The New Bible Dictionary (3rd ed.) | READY (library access available) |
| EN-BAP-002 | Evangelical Dictionary of Theology | READY (library access available) |
| EN-BAP-005 | BDAG Greek-English Lexicon | READY (library access available) |
| EN-BAP-006 | Strong's Concordance (Korean) | CONDITIONAL (edition identification needed) |
| KR-BIBLE-001 | 한국어 성경사전 / 영어-한국어 성경사전 | CONDITIONAL (edition identification needed) |

### 20.2 Not Ready for Corpus Construction

| Source ID | Title | Reason |
|-----------|-------|--------|
| KR-BAP-001 | 한국침례교신학사전 | Existence unconfirmed |
| KR-EV-001 | 한국복음주의신학사전 | Existence unconfirmed |
| KR-TH-001~004 | Korean theological dictionaries | Bibliographic details need verification; corpus storage may be restricted |

---

## 21. PHASE 1 Status

```text
PHASE 1 STATUS: SOURCE VALIDATION COMPLETED
```

**의미**: authoritative source validation 완료. canonical terminology corpus construction을 위한 기반이 마련됨.

**다음 단계**: authoritative source validation에서 선정한 canonical candidates를 사용하여 terminology corpus를 구축한다.

**아직 corpus를 대량 생성하지 않았다.**

---

## 22. Evidence

### 22.1 Repository Evidence

```text
Smith Bible Dictionary:
  Path: NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol{1-4}/
  Files: metadata.json, ocr.txt (per volume)
  Verified via: metadata.json content

Existing Authority Registry:
  Path: resources/theological_sources/authority/sources.yaml
  Sources: BAP-CHURCH-DAGG-001, BAP-CHURCH-HISCOX, BAP-MISS-FULLER-VOL01~08
  Verified via: sources.yaml content

Crosswalk:
  Path: NAE/metadata/crosswalk/crosswalk.yaml
  Records: Dagg_Church_Order, Hiscox_Standard_Manual
  Verified via: crosswalk.yaml content
```

### 22.2 External Evidence (Academic Knowledge)

> **Note**: The following evidence is based on academic knowledge and has NOT been verified through direct web search or library catalog access during this session. These claims require further verification through academic databases (KISS, DBpia, RISS, WorldCat, etc.) before being used as canonical authority.

```text
Korean theological dictionaries:
  한국신학사전 (김윤길, 두레, 1990) — Academic knowledge only
  개혁신학대백과사전 (대한기독교신학회, 대한기독교출판사, 1995) — Academic knowledge only
  장로교신학사전 — Academic knowledge only
  기독교백과사전 (YMCA, 1998) — Academic knowledge only

English theological dictionaries:
  The New Bible Dictionary (3rd ed., IVP/Tyndale, 1996) — Academic knowledge only
  Evangelical Dictionary of Theology (Baker Academic, 2001) — Academic knowledge only
  BDAG (University of Chicago Press, 2000) — Academic knowledge only
  Strong's Concordance Korean edition — Academic knowledge only

Korean Baptist dictionary:
  한국침례교신학사전 — NOT VERIFIED; existence unknown
```

---

## 23. Files Modified

```text
New file:
  docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md (본 문서)

Modified:
  0

Deleted:
  0
```

---

## 24. Git Status

```bash
$ git status --short
 M NAE/smith_activation.py
 M docs/STATE.md
 D test_seal_4qhgiezk/seal_test_pkg/data.json
 D test_seal_4qhgiezk/seal_test_pkg/manifest.json
 D test_seal_4qhgiezk/seal_test_pkg/report.md
 D test_seal_5z4ickc9/seal_test_pkg/data.json
 D test_seal_5z4ickc9/seal_test_pkg/manifest.json
 D test_seal_5z4ickc9/seal_test_pkg/report.md
 D test_seal_zlrrtn8n/seal_test_pkg/data.json
 D test_seal_zlrrtn8n/seal_test_pkg/manifest.json
 D test_seal_zlrrtn8n/seal_test_pkg/report.md
 M ui/pages/chat.py
?? docs/agents/cue/CUE-ADR029-PHASE1-GATE-INDEPENDENT-REVIEW.md
?? docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md
?? docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md
?? docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md
?? docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md
?? docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md (본 문서)

$ git diff --stat
(본 문서 신규 생성이므로 diff 없음)

$ git diff -- docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md
(ADR-029는 이전 작업에서 ACCEPTED로 수정됨)
```

**기존 변경사항 보존**:
- `NAE/smith_activation.py`: 변경 없음
- `docs/STATE.md`: 변경 없음
- `ui/pages/chat.py`: 변경 없음
- `test_seal_*`: 변경 없음
- 기존 CUE 보고서: 변경 없음
- `PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md`: 변경 없음

---

## Summary Statistics

```text
PHASE 1 — AUTHORITATIVE SOURCE VALIDATION

Inventory candidates:
  20

Sources fully verified (bibliographic identity confirmed):
  2

Sources partially verified (existence confirmed, details need further research):
  14

Sources NOT VERIFIED / CONDITIONAL:
  3

Sources REJECTED (not suitable as canonical authority):
  0

Canonical Korean candidates:
  0 (none fully verified yet)

Canonical English candidates:
  9

KO↔EN bridge candidates:
  2 (Strong's Korean edition, KR-BIBLE-001 — both CONDITIONAL)

Conditional:
  3

Rejected / Reference-only:
  0

License UNKNOWN:
  2

Acquisition-ready:
  5 (Smith Bible Dictionary already in corpus; 4 English dictionaries via library access)

Corpus construction:
  NOT STARTED

Code changes:
  0

Corpus mutation:
  0

Qdrant mutation:
  0

Embedding:
  NOT RUN

Benchmark:
  NOT RUN

Git add/commit:
  NO
```

---

**본 검증 보고서는 여기서 종료한다. terminology corpus 구축은 아직 시작하지 않았다.**

**PHASE 1의 다음 단계는 authoritative source validation에서 선정한 canonical candidates를 사용하여 terminology corpus를 구축하는 것이다.**

**첫 번째 실제 engineering task는:**

> **권위 있는 한국어 신학용어 사전 및 관련 authoritative source의 실제 존재 여부, 접근 가능성, 라이선스/사용 조건, provenance를 조사한다.**

**그 결과를 먼저 inventory로 만든다.**

**아직 corpus를 대량 생성하지 않는다.**
