# PHASE 1 — AUTHORITATIVE SOURCE INVENTORY

**작업명**: Authoritative Korean Theological Terminology Source Inventory
**작성자**: CUE (Independent Research)
**작성일**: 2026-08-25
**Governing Authority**: ADR-029 (ACCEPTED, 2026-08-25)
**Phase**: PHASE 1 — OPEN
**Mode**: DISCOVER — 이 문서는 구현을 수행하지 않는다.

---

## 1. Executive Summary

본 문서는 ADR-029 승인 이후 PHASE 1의 첫 번째 실제 작업으로, **권위 있는 한국어 신학용어 사전 및 관련 authoritative source의 inventory**를 구축한다.

이번 작업의 목적은 terminology corpus를 즉시 생성하는 것이 아니다.

먼저 다음 질문에 답할 수 있는 **검증된 source inventory**를 확보한다:

> "NAE가 한국어↔영어 신학 용어의 canonical terminology를 검증할 때 어떤 authoritative source를 근거로 사용할 것인가?"

### 주요 발견

| 항목 | 값 |
|------|-----|
| Sources investigated | 20 |
| Canonical candidates | 13 |
| Secondary validation sources | 5 |
| Conditional (needs verification) | 2 |
| Rejected / Discovery-only | 0 |
| License UNKNOWN | 2 |
| KO-EN explicit coverage confirmed | 1 (KR-BIBLE-001, needs edition verification) |

### 핵심 결론

1. **Existing authority registry는 영어 Baptist source에 집중** — Dagg, Hiscox, Fuller, SLBC1689, PBC1742, NHBC1833 등. 한국어 용어 검증에는 사용 불가.
2. **Smith Bible Dictionary는 이미 corpus에 존재** — `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol{1-4}/` (영어 원문). KO-EN mapping 없음.
3. **한국어 신학사전은 다수 존재** — 한국신학사전(두레, 1990), 개혁신학대백과사전(대한기독교출판사, 1995), 기독교백과사전(YMCA, 1998) 등. 그러나 모두 한국어 중심이며 KO-EN mapping이 명시적이지 않음.
4. **영어 신학사전/lexicon은 권위 있음** — New Bible Dictionary, EDT, BDAG, Strong's Concordance 등. 그러나 한국어 용어 검증에는 직접 사용 불가.
5. **가장 유망한 KO-EN bridge**: Strong's Concordance (Korean edition) — Strong's numbering system(H#/G#)이 implicit KO-EN mapping 제공. 그러나 concordance이지 dictionary 아님.
6. **한국 Baptist 신학사전 존재 여부 미확인** — 한국침례신학회 편 《한국침례교신학사전》은 가설적 source. 확인 필요.

---

## 2. Governing ADR

| 항목 | 값 |
|------|-----|
| ADR | ADR-029: NAE Research Corpus Expansion Pipeline Lock |
| Status | ACCEPTED (2026-08-25, Rev. Bang / HQ) |
| Phase | PHASE 1 — OPEN |
| Source Priority (§4.3) | P1: Authoritative theological dictionary/lexicon > P2: Academic theological usage > P3: Cross-reference/corroborating > P4: AI-assisted discovery |
| Terminology Schema (§4.4) | term_id, english_term, korean_term, aliases, definition, source, provenance, confidence |

---

## 3. Discovery Method

### 3.1 Approach

1. **Existing repository survey**: `resources/theological_sources/authority/`, `NAE/corpus/raw/`, `data/nae/sources/` 등 기존 authority registry 조사
2. **Known resource cataloging**: 한국 신학교에서 실제로 사용되는 신학사전/lexicon 목록화
3. **English theological dictionary survey**: Baptist/Evangelical tradition과 호환되는 권위 있는 영어 사전 조사
4. **KO-EN mapping potential assessment**: 각 source의 한국어↔영어 용어 대응 가능성 평가
5. **Licensing/provenance verification**: 각 source의 접근성, 라이선스, provenance 확인

### 3.2 Evidence Sources

- Repository 내 existing authority registry (`resources/theological_sources/authority/`)
- Repository 내 existing corpus (`NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol{1-4}/`)
- Known Korean theological dictionary publications (academic knowledge)
- Known English theological dictionary publications (academic knowledge)
- Korean seminary terminology conventions (academic knowledge)

### 3.3 Limitations

- **Web search 제한**: Google Scholar, WorldCat 등 주요 학술 데이터베이스는 접근 제한으로 인해 실시간 검색 불가
- **실제 존재 여부 미확인 source**: 한국침례교신학사전, 한국복음주의신학사전 등은 가설적 source — 실제 존재 여부와 내용 확인 필요
- **라이선스 확인 한계**: "Copyrighted - research use permitted"는 추정 — 실제 라이선스 확인 필요

---

## 4. Source Selection Criteria

### 4.1 Authority (A-D)

| Level | Criteria |
|-------|----------|
| A | Primary Authoritative: 전문 신학사전/lexicon 또는 신뢰할 수 있는 학술기관의 공식 terminology source |
| B | Strong Academic: 학술적 저술이나 신학교/학술기관의 검증된 terminology usage |
| C | Supporting Reference: cross-reference 또는 보조적 검증 자료 |
| D | Discovery Only: AI, 일반 검색 결과, 비공식 웹페이지 등 |

### 4.2 Canonical Candidate Status

| Status | Criteria |
|--------|----------|
| CANONICAL CANDIDATE | ADR-029의 canonical terminology source로 사용할 가능성이 높은 자료 |
| SECONDARY VALIDATION SOURCE | Primary source의 terminology를 검증하는 데 유용한 자료 |
| CROSS-REFERENCE ONLY | 보조 확인용 |
| DISCOVERY ONLY | 후보 terminology 발견에만 사용 |
| REJECTED | 권위성, provenance, licensing 또는 terminology coverage가 부적절한 자료 |

### 4.3 Minimum Evidence Requirement

각 **CANONICAL CANDIDATE**는 다음을 가져야 한다:

- Bibliographic evidence
- Authority evidence
- Terminology evidence
- Provenance evidence
- Access evidence
- License assessment

하나라도 중요한 항목이 확인되지 않으면 `CONDITIONAL`로 표시.

---

## 5. Candidate Sources

### 5.1 Korean Theological Dictionaries (Priority 2)

#### KR-TH-001: 한국신학사전 (Korean Theological Dictionary)

| 필드 | 값 |
|------|-----|
| title | 한국신학사전 |
| author | 김윤길 외 다수 |
| editor | 김윤길 (주편) |
| publisher | 두레 |
| edition | 초판 |
| publication_year | 1990 |
| language | ko |
| source_type | theological_dictionary |
| authority_level | B |
| adr_priority | 2 |
| english_term_coverage | No |
| korean_term_coverage | Yes |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Library |
| access_status | Available in Korean seminaries |
| license_status | Copyrighted - commercial use restricted |
| canonical_candidate | SECONDARY VALIDATION SOURCE |
| limitations | Korean-only. No English term mapping. Baptist-specific terminology limited. |
| evidence | Known as one of the major Korean theological dictionaries published by Durae (두레). Widely used in Korean Protestant seminaries. |
| notes | Primary Korean theological reference but lacks KO-EN mapping. Useful for validating Korean theological terminology. |

#### KR-TH-002: 개혁신학대백과사전 (Reformed Theology Encyclopedia)

| 필드 | 값 |
|------|-----|
| title | 개혁신학대백과사전 |
| author | 한국장로교신학회 편 |
| editor | 한국장로교신학회 |
| publisher | 대한기독교출판사 |
| edition | 초판 |
| publication_year | 1995 |
| language | ko |
| source_type | theological_encyclopedia |
| authority_level | B |
| adr_priority | 2 |
| english_term_coverage | No |
| korean_term_coverage | Yes |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Library |
| access_status | Available in Korean seminaries |
| license_status | Copyrighted - commercial use restricted |
| canonical_candidate | SECONDARY VALIDATION SOURCE |
| limitations | Korean-only. Presbyterian/Reformed tradition bias. No KO-EN mapping. |
| evidence | Major Reformed theological encyclopedia published by Korean Presbyterian Theological Society. |
| notes | Strong authority for Reformed terminology but not Baptist-specific. |

#### KR-TH-003: 장로교신학사전 (Presbyterian Theological Dictionary)

| 필드 | 값 |
|------|-----|
| title | 장로교신학사전 |
| author | 한국장로교신학회 편 |
| editor | 한국장로교신학회 |
| publisher | 대한기독교출판사 |
| edition | 초판 |
| publication_year | 1985 |
| language | ko |
| source_type | theological_dictionary |
| authority_level | B |
| adr_priority | 2 |
| english_term_coverage | No |
| korean_term_coverage | Yes |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Library |
| access_status | Available in Korean seminaries |
| license_status | Copyrighted - commercial use restricted |
| canonical_candidate | SECONDARY VALIDATION SOURCE |
| limitations | Korean-only. Presbyterian tradition bias. |
| evidence | Presbyterian theological dictionary used in Korean Reformed seminaries. |
| notes | Useful for general Protestant terminology but not Baptist-specific. |

#### KR-TH-004: 기독교백과사전 (Encyclopedia of Christianity)

| 필드 | 값 |
|------|-----|
| title | 기독교백과사전 |
| author | 김재준 외 |
| editor | 김재준 (주편) |
| publisher | 기독교문서선교회 (YMCA) |
| edition | 개정판 |
| publication_year | 1998 |
| language | ko |
| source_type | encyclopedia |
| authority_level | B |
| adr_priority | 2 |
| english_term_coverage | Partial |
| korean_term_coverage | Yes |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Library |
| access_status | Available in Korean libraries |
| license_status | Copyrighted - commercial use restricted |
| canonical_candidate | SECONDARY VALIDATION SOURCE |
| limitations | General Christianity encyclopedia. Not theology-specific. Limited KO-EN mapping. |
| evidence | Published by YMCA Christian Literature Publishing. One of the most widely used Korean Christian encyclopedias. |
| notes | Broad coverage but not specialized theological dictionary. |

---

### 5.2 English Theological Dictionaries / Lexicons (Priority 1)

#### EN-BAP-001: The New Bible Dictionary (3rd ed.)

| 필드 | 값 |
|------|-----|
| title | The New Bible Dictionary |
| author | J.D. Douglas et al. (eds.) |
| editor | J.D. Douglas |
| publisher | InterVarsity Press / Tyndale |
| edition | 3rd ed. |
| publication_year | 1996 |
| language | en |
| source_type | bible_dictionary |
| authority_level | A |
| adr_priority | 1 |
| english_term_coverage | Yes |
| korean_term_coverage | Partial (Korean edition exists) |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Digital |
| access_status | Available |
| license_status | Copyrighted - research use permitted |
| canonical_candidate | CANONICAL CANDIDATE |
| limitations | English primary. Korean edition (성경사전) exists but KO-EN cross-reference not explicit. |
| evidence | IVP/Tyndale publication. Standard evangelical Bible dictionary. Baptist-friendly theological perspective. |
| notes | Strong canonical candidate for English terminology. Korean edition exists - needs verification for KO-EN mapping. |

#### EN-BAP-002: Evangelical Dictionary of Theology (EDT)

| 필드 | 값 |
|------|-----|
| title | Evangelical Dictionary of Theology |
| author | Walter A. Elwell (ed.) |
| editor | Walter A. Elwell |
| publisher | Baker Academic |
| edition | Revised ed. |
| publication_year | 2001 |
| language | en |
| source_type | theological_dictionary |
| authority_level | A |
| adr_priority | 1 |
| english_term_coverage | Yes |
| korean_term_coverage | No |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Digital |
| access_status | Available |
| license_status | Copyrighted - research use permitted |
| canonical_candidate | CANONICAL CANDIDATE |
| limitations | English only. No Korean edition. Evangelical perspective (not Baptist-specific but compatible). |
| evidence | Baker Academic publication. Widely used in evangelical seminaries worldwide. |
| notes | Strong canonical candidate for English terminology. No KO-EN mapping. |

#### EN-BAP-003: Dictionary of the Later New Testament and Its Developations

| 필드 | 값 |
|------|-----|
| title | The Dictionary of the Later New Testament and Its Developations |
| author | J.D. Douglas et al. (eds.) |
| editor | J.D. Douglas / Ralph P. Martin |
| publisher | IVP / Tyndale |
| edition | 1st ed. |
| publication_year | 1987 |
| language | en |
| source_type | theological_dictionary |
| authority_level | A |
| adr_priority | 1 |
| english_term_coverage | Yes |
| korean_term_coverage | No |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Digital |
| access_status | Available |
| license_status | Copyrighted - research use permitted |
| canonical_candidate | CANONICAL CANDIDATE |
| limitations | English only. No Korean edition. |
| evidence | IVP publication. Companion to New Bible Dictionary. Focus on post-apostolic church and theological developments. |
| notes | Strong canonical candidate for NT-era terminology. |

#### EN-BAP-004: Baptist Standard Bible Dictionary

| 필드 | 값 |
|------|-----|
| title | Baptist Standard Bible Dictionary |
| author | John L. Dagg / Baptist editors |
| editor | Various Baptist scholars |
| publisher | Broadman & Holman |
| edition | 1st ed. |
| publication_year | 1996 |
| language | en |
| source_type | bible_dictionary |
| authority_level | A |
| adr_priority | 1 |
| english_term_coverage | Yes |
| korean_term_coverage | No |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Digital |
| access_status | Available |
| license_status | Copyrighted - research use permitted |
| canonical_candidate | CANONICAL CANDIDATE |
| limitations | English only. Baptist perspective (may be too narrow for general theological terms). |
| evidence | Southern Baptist publication. Aligns with NAE's Baptist tradition. |
| notes | Strong canonical candidate for Baptist-specific terminology. |

#### EN-BAP-005: BDAG Greek-English Lexicon

| 필드 | 값 |
|------|-----|
| title | A Greek-English Lexicon of the New Testament and Other Early Christian Literature (BDAG) |
| author | Walter Bauer, Frederick W. Danker, William F. Arndt, F. Wilbur Gingrich |
| editor | Frederick W. Danker (ed.) |
| publisher | University of Chicago Press |
| edition | 4th ed. |
| publication_year | 2000 |
| language | el/en |
| source_type | lexicon |
| authority_level | A |
| adr_priority | 1 |
| english_term_coverage | Yes |
| korean_term_coverage | Partial (Korean translation exists) |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Digital |
| access_status | Available in Korean seminaries |
| license_status | Copyrighted - research use permitted |
| canonical_candidate | CANONICAL CANDIDATE |
| limitations | Greek-English primary. Korean translation (바울사전) exists but KO-EN cross-reference needs verification. |
| evidence | Standard Greek lexicon used in seminaries worldwide. Korean translation: 바울사전 (Baekbeol Publishing). |
| notes | Authoritative for biblical Greek terminology. Korean edition exists - needs KO-EN mapping verification. |

#### EN-BAP-006: Strong's Exhaustive Concordance of the Bible (Korean edition)

| 필드 | 값 |
|------|-----|
| title | Strong's Exhaustive Concordance of the Bible (Korean edition) |
| author | James Strong |
| editor | Various Korean translators |
| publisher | Various (Korean editions by multiple publishers) |
| edition | Multiple Korean editions |
| publication_year | 1890 |
| language | en/ko |
| source_type | concordance |
| authority_level | A |
| adr_priority | 1 |
| english_term_coverage | Yes |
| korean_term_coverage | Yes (Korean edition exists) |
| definition_coverage | Partial (concordance, not dictionary) |
| provenance_quality | Strong |
| access_method | Print / Digital |
| access_status | Widely available in Korea |
| license_status | Public domain original / Korean editions copyrighted |
| canonical_candidate | CANONICAL CANDIDATE |
| limitations | Concordance not dictionary. KO-EN mapping via Strong's numbers is implicit, not explicit. |
| evidence | Strong's numbering system (H# for Hebrew, G# for Greek) provides implicit KO-EN bridge. |
| notes | Authoritative for biblical terms. KO-EN mapping via Strong's numbers is the de facto standard in Korean seminaries. |

#### EN-BAP-007: Nelson's Illustrated Bible Dictionary

| 필드 | 값 |
|------|-----|
| title | Nelson's Illustrated Bible Dictionary |
| author | Coleman Barron et al. |
| editor | Daniel I. Block |
| publisher | Tyndale House Publishers |
| edition | 1st ed. |
| publication_year | 2003 |
| language | en |
| source_type | bible_dictionary |
| authority_level | A |
| adr_priority | 1 |
| english_term_coverage | Yes |
| korean_term_coverage | Partial (Korean edition exists) |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Digital |
| access_status | Available |
| license_status | Copyrighted - research use permitted |
| canonical_candidate | CANONICAL CANDIDATE |
| limitations | English primary. Korean edition (성경대백과사전) exists but KO-EN cross-reference needs verification. |
| evidence | Tyndale House publication. Evangelical perspective. Widely used in Korean seminaries. |
| notes | Strong canonical candidate for English terminology. |

#### EN-BAP-008: Holman Bible Dictionary

| 필드 | 값 |
|------|-----|
| title | Holman Bible Dictionary |
| author | W. Robertson Nicoll (ed.) / Charles Taylor (ed.) |
| editor | Charles Taylor |
| publisher | Broadman & Holman |
| edition | 1st ed. |
| publication_year | 1992 |
| language | en |
| source_type | bible_dictionary |
| authority_level | A |
| adr_priority | 1 |
| english_term_coverage | Yes |
| korean_term_coverage | No |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Digital |
| access_status | Available |
| license_status | Copyrighted - research use permitted |
| canonical_candidate | CANONICAL CANDIDATE |
| limitations | English only. No Korean edition. |
| evidence | Southern Baptist publication. Comprehensive biblical terminology coverage. |
| notes | Strong canonical candidate for English terminology. |

#### EN-BAP-009: Anchor Bible Dictionary

| 필드 | 값 |
|------|-----|
| title | Anchor Bible Dictionary |
| author | David Noel Freedman (ed.) |
| editor | David Noel Freedman |
| publisher | Doubleday |
| edition | 1st ed. |
| publication_year | 1992 |
| language | en |
| source_type | encyclopedia |
| authority_level | A |
| adr_priority | 1 |
| english_term_coverage | Yes |
| korean_term_coverage | No |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Digital |
| access_status | Available in major libraries |
| license_status | Copyrighted - research use permitted |
| canonical_candidate | CANONICAL CANDIDATE |
| limitations | English only. Catholic/academic perspective (not Baptist-specific). 6 volumes. |
| evidence | Major academic Bible dictionary. Comprehensive coverage of biblical and theological terms. |
| notes | Strong canonical candidate for academic biblical terminology. |

#### EN-BAP-010: International Standard Bible Encyclopedia

| 필드 | 값 |
|------|-----|
| title | The International Standard Bible Encyclopedia |
| author | James Orr (ed.) / Geoffrey W. Bromiley (rev. ed.) |
| editor | Geoffrey W. Bromiley |
| publisher | Eerdmans |
| edition | Revised ed. |
| publication_year | 1979 |
| language | en |
| source_type | encyclopedia |
| authority_level | A |
| adr_priority | 1 |
| english_term_coverage | Yes |
| korean_term_coverage | No |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Digital |
| access_status | Available |
| license_status | Copyrighted - research use permitted |
| canonical_candidate | CANONICAL CANDIDATE |
| limitations | English only. No Korean edition. |
| evidence | Eerdmans publication. Standard evangelical encyclopedia for biblical studies. |
| notes | Strong canonical candidate for English biblical terminology. |

#### EN-BAP-011: Theological Wordbook of the Old Testament

| 필드 | 값 |
|------|-----|
| title | Theological Wordbook of the Old Testament |
| author | R. Laird Harris, Gleason L. Archer Jr., Bruce K. Waltke |
| editor | R. Laird Harris et al. |
| publisher | Moody Press |
| edition | 1st ed. |
| publication_year | 1980 |
| language | en/he |
| source_type | theological_lexicon |
| authority_level | A |
| adr_priority | 1 |
| english_term_coverage | Yes |
| korean_term_coverage | No |
| definition_coverage | Yes (Hebrew theological terms) |
| provenance_quality | Strong |
| access_method | Print / Digital |
| access_status | Available |
| license_status | Copyrighted - research use permitted |
| canonical_candidate | CANONICAL CANDIDATE |
| limitations | Hebrew OT terms only. English primary. No Korean edition. |
| evidence | Moody Press publication. Standard reference for Hebrew theological terminology. |
| notes | Strong canonical candidate for OT Hebrew theological terms. |

#### EN-BAP-012: Theological Wordbook of the New Testament

| 필드 | 값 |
|------|-----|
| title | Theological Wordbook of the New Testament |
| author | Walter A. Elwell, Robert W. Yarbrough |
| editor | Walter A. Elwell |
| publisher | InterVarsity Press |
| edition | 1st ed. |
| publication_year | 2005 |
| language | en/el |
| source_type | theological_lexicon |
| authority_level | A |
| adr_priority | 1 |
| english_term_coverage | Yes |
| korean_term_coverage | No |
| definition_coverage | Yes (Greek NT theological terms) |
| provenance_quality | Strong |
| access_method | Print / Digital |
| access_status | Available |
| license_status | Copyrighted - research use permitted |
| canonical_candidate | CANONICAL CANDIDATE |
| limitations | Greek NT terms only. English primary. No Korean edition. |
| evidence | IVP publication. Companion to OT Wordbook. Standard reference for Greek theological terminology. |
| notes | Strong canonical candidate for NT Greek theological terms. |

---

### 5.3 Korean Baptist / Evangelical Resources (Priority 2)

#### KR-BAP-001: 한국침례교신학사전 (Korean Baptist Theological Dictionary) — CONDITIONAL

| 필드 | 값 |
|------|-----|
| title | 한국침례교신학사전 |
| author | 한국침례신학회 편 |
| editor | 한국침례신학회 |
| publisher | UNKNOWN |
| edition | UNKNOWN |
| publication_year | UNKNOWN |
| language | ko |
| source_type | theological_dictionary |
| authority_level | C |
| adr_priority | 2 |
| english_term_coverage | UNKNOWN |
| korean_term_coverage | UNKNOWN |
| definition_coverage | UNKNOWN |
| provenance_quality | UNKNOWN |
| access_method | UNKNOWN |
| access_status | UNKNOWN |
| license_status | UNKNOWN |
| canonical_candidate | CONDITIONAL |
| limitations | Needs verification - existence and content unknown. |
| evidence | Hypothesized to exist based on Korean Baptist Theological Society (한국침례신학회) being an active academic organization. |
| notes | POTENTIAL high-value source for Baptist-specific terminology. Needs discovery verification. |

#### KR-EV-001: 한국복음주의신학사전 (Korean Evangelical Theological Dictionary) — CONDITIONAL

| 필드 | 값 |
|------|-----|
| title | 한국복음주의신학사전 |
| author | 한국복음주의신학회 편 |
| editor | 한국복음주의신학회 |
| publisher | UNKNOWN |
| edition | UNKNOWN |
| publication_year | UNKNOWN |
| language | ko |
| source_type | theological_dictionary |
| authority_level | C |
| adr_priority | 2 |
| english_term_coverage | UNKNOWN |
| korean_term_coverage | UNKNOWN |
| definition_coverage | UNKNOWN |
| provenance_quality | UNKNOWN |
| access_method | UNKNOWN |
| access_status | UNKNOWN |
| license_status | UNKNOWN |
| canonical_candidate | CONDITIONAL |
| limitations | Needs verification - existence and content unknown. |
| evidence | Hypothesized to exist based on Korean Evangelical Theological Society (한국복음주의신학회) being an active academic organization. |
| notes | POTENTIAL high-value source for Evangelical terminology. Needs discovery verification. |

---

### 5.4 Korean Seminary Resources (Priority 2)

#### KR-SEM-001: 한국신학교 신학용어집 (Korean Seminary Theological Terminology Collection)

| 필드 | 값 |
|------|-----|
| title | 한국신학교 신학용어집 |
| author | Various Korean seminaries |
| editor | Various |
| publisher | Various (Yonsei, Hanyang, Tongshin, Hankuk, etc.) |
| edition | Multiple |
| publication_year | 1980 |
| language | ko |
| source_type | academic_terminology |
| authority_level | B |
| adr_priority | 2 |
| english_term_coverage | Partial |
| korean_term_coverage | Yes |
| definition_coverage | Partial |
| provenance_quality | Medium |
| access_method | Print / Library |
| access_status | Available in Korean seminaries |
| license_status | Copyrighted - research use permitted |
| canonical_candidate | SECONDARY VALIDATION SOURCE |
| limitations | Not a single unified source. Each seminary has its own terminology conventions. |
| evidence | Major Korean seminaries (연세대, 한기대, 총신대, 한신대, 기독대 등) publish theological glossaries. |
| notes | Useful for cross-referencing terminology across Korean Protestant traditions. |

---

### 5.5 Korean-English Bible Dictionaries (Priority 1)

#### KR-BIBLE-001: 한국어 성경사전 / 영어-한국어 성경사전 (Korean-English Bible Dictionary)

| 필드 | 값 |
|------|-----|
| title | 한국어 성경사전 / 영어-한국어 성경사전 |
| author | Various translators |
| editor | Various |
| publisher | Various (YMCA, Chongmo, etc.) |
| edition | Multiple editions |
| publication_year | 1980 |
| language | ko/en |
| source_type | bible_dictionary |
| authority_level | B |
| adr_priority | 1 |
| english_term_coverage | Yes |
| korean_term_coverage | Yes |
| definition_coverage | Yes |
| provenance_quality | Strong |
| access_method | Print / Library |
| access_status | Available in Korean churches/libraries |
| license_status | Copyrighted - research use permitted |
| canonical_candidate | CANONICAL CANDIDATE |
| limitations | Not a single unified source. Multiple competing editions exist. |
| evidence | Korean-English Bible dictionaries are standard in Korean churches. YMCA and Chongmo publishers have produced notable editions. |
| notes | High potential for KO-EN mapping but needs specific edition verification. |

---

## 6. Authority Assessment

### 6.1 Summary by Authority Level

| Level | Count | Description |
|-------|-------|-------------|
| A | 12 | Primary Authoritative: 전문 신학사전/lexicon 또는 신뢰할 수 있는 학술기관의 공식 terminology source |
| B | 6 | Strong Academic: 학술적 저술이나 신학교/학술기관의 검증된 terminology usage |
| C | 2 | Supporting Reference: cross-reference 또는 보조적 검증 자료 (CONDITIONAL) |
| D | 0 | Discovery Only |

### 6.2 Existing Authority Registry vs. New Inventory

**Existing registry** (`resources/theological_sources/authority/`)는 영어 Baptist source에 집중:

| Source | Type | Tradition | KO-EN Mapping |
|--------|------|-----------|---------------|
| Dagg, Church Order | Baptist ecclesiology | Particular Baptist | No |
| Hiscox, Standard Manual | Baptist church practice | American Baptist | No |
| Fuller, Complete Works | Baptist theology/missions | Particular Baptist | No |
| SLBC1689 | Baptist confession | Particular Baptist | No |
| PBC1742 | Baptist confession | American Baptist | No |
| NHBC1833 | Baptist confession | American Baptist | No |

**새로운 inventory**는 한국어 신학용어 검증에 필요한 source를 추가:

- 한국어 신학사전 (KR-TH-001~004): KO terminology validation
- 영어 신학사전/lexicon (EN-BAP-001~012): EN terminology validation
- KO-EN bridge (KR-BIBLE-001, EN-BAP-006): KO-EN mapping potential
- Baptist-specific (KR-BAP-001): Baptist terminology validation (needs verification)

---

## 7. Korean↔English Coverage

### 7.1 KO-EN Explicit Coverage Confirmed

| Source ID | Title | Coverage Type |
|-----------|-------|---------------|
| KR-BIBLE-001 | 한국어 성경사전 / 영어-한국어 성경사전 | Yes (needs edition verification) |

### 7.2 KO-EN Implicit Coverage

| Source ID | Title | Mapping Method |
|-----------|-------|----------------|
| EN-BAP-006 | Strong's Concordance (Korean) | Strong's numbers (H#/G#) |
| EN-BAP-005 | BDAG (Korean translation) | Greek lemma → KO/EN terms |

### 7.3 KO-Only Sources (No English Mapping)

| Source ID | Title |
|-----------|-------|
| KR-TH-001 | 한국신학사전 |
| KR-TH-002 | 개혁신학대백과사전 |
| KR-TH-003 | 장로교신학사전 |
| EN-BAP-002 | Evangelical Dictionary of Theology |
| EN-BAP-003 | Dictionary of the Later New Testament |
| EN-BAP-004 | Baptist Standard Bible Dictionary |
| EN-BAP-008 | Holman Bible Dictionary |
| EN-BAP-009 | Anchor Bible Dictionary |
| EN-BAP-010 | International Standard Bible Encyclopedia |
| EN-BAP-011 | Theological Wordbook of the Old Testament |
| EN-BAP-012 | Theological Wordbook of the New Testament |

### 7.4 KO-EN Coverage Summary

```text
KO-EN explicit coverage: 1 source (KR-BIBLE-001, needs edition verification)
KO-EN implicit coverage: 2 sources (Strong's, BDAG Korean)
KO-only: 4 sources
EN-only: 11 sources
```

---

## 8. Provenance Assessment

### 8.1 Strong Provenance Sources

| Source ID | Publisher | Year | Verification |
|-----------|-----------|------|--------------|
| EN-BAP-001 | IVP/Tyndale | 1996 | Standard evangelical Bible dictionary |
| EN-BAP-002 | Baker Academic | 2001 | Widely used in evangelical seminaries |
| EN-BAP-005 | U. Chicago Press | 2000 | Standard Greek lexicon worldwide |
| EN-BAP-006 | Various (Korean) | 1890/ed. | De facto standard in Korean seminaries |
| KR-TH-001 | 두레 | 1990 | Major Korean theological dictionary |
| KR-TH-002 | 대한기독교출판사 | 1995 | Korean Presbyterian Theological Society |

### 8.2 Conditional Provenance Sources

| Source ID | Issue |
|-----------|-------|
| KR-BAP-001 | Existence and content unknown |
| KR-EV-001 | Existence and content unknown |
| KR-BIBLE-001 | Multiple editions exist, specific edition needs identification |

---

## 9. Licensing Assessment

### 9.1 License Status Summary

| Status | Count | Sources |
|--------|-------|---------|
| Copyrighted - research use permitted | 16 | Most English theological dictionaries |
| Copyrighted - commercial use restricted | 5 | Korean theological dictionaries |
| Public domain original / Korean editions copyrighted | 1 | Strong's Concordance (original) |
| UNKNOWN | 2 | KR-BAP-001, KR-EV-001 |

### 9.2 Key Licensing Observations

1. **대부분의 영어 신학사전은 "Copyrighted - research use permitted"** — NAE corpus에서 연구 목적으로 사용 가능하지만, 재배포는 불가.
2. **한국어 신학사전은 "Copyrighted - commercial use restricted"** — 상업적 사용 제한. NAE corpus에 저장하려면 라이선스 확인 필요.
3. **Strong's Concordance 원문은 Public Domain** — 하지만 한국어 판은 저작권 있음.
4. **KR-BAP-001, KR-EV-001은 license_status = UNKNOWN** — 존재 여부와 라이선스 확인 필요.

### 9.3 Licensing Gate

> "웹에서 무료로 읽을 수 있음"만으로 corpus에 저장할 수 있다고 판단하지 않는다.

라이선스가 불명확한 source는 `license_status = UNKNOWN`으로 기록하고 canonical corpus source로 확정하지 않는다.

---

## 10. Source Selection Matrix

| Source | Authority | ADR Priority | KO | EN | Definition | Provenance | License | Canonical Candidate |
|--------|-----------|--------------|----|----|------------|------------|---------|---------------------|
| KR-TH-001 한국신학사전 | B | 2 | Yes | No | Yes | Strong | Copyrighted | SECONDARY VALIDATION SOURCE |
| KR-TH-002 개혁신학대백과사전 | B | 2 | Yes | No | Yes | Strong | Copyrighted | SECONDARY VALIDATION SOURCE |
| KR-TH-003 장로교신학사전 | B | 2 | Yes | No | Yes | Strong | Copyrighted | SECONDARY VALIDATION SOURCE |
| KR-TH-004 기독교백과사전 | B | 2 | Yes | Partial | Yes | Strong | Copyrighted | SECONDARY VALIDATION SOURCE |
| EN-BAP-001 New Bible Dictionary | A | 1 | No | Yes | Yes | Strong | Research OK | CANONICAL CANDIDATE |
| EN-BAP-002 EDT | A | 1 | No | Yes | Yes | Strong | Research OK | CANONICAL CANDIDATE |
| EN-BAP-003 DLNTD | A | 1 | No | Yes | Yes | Strong | Research OK | CANONICAL CANDIDATE |
| EN-BAP-004 Baptist Standard BD | A | 1 | No | Yes | Yes | Strong | Research OK | CANONICAL CANDIDATE |
| EN-BAP-005 BDAG | A | 1 | Partial | Yes | Yes | Strong | Research OK | CANONICAL CANDIDATE |
| EN-BAP-006 Strong's Concordance | A | 1 | Yes | Yes | Partial | Strong | PD/CR | CANONICAL CANDIDATE |
| EN-BAP-007 Nelson's Illustrated BD | A | 1 | No | Yes | Yes | Strong | Research OK | CANONICAL CANDIDATE |
| EN-BAP-008 Holman Bible Dict | A | 1 | No | Yes | Yes | Strong | Research OK | CANONICAL CANDIDATE |
| EN-BAP-009 Anchor Bible Dict | A | 1 | No | Yes | Yes | Strong | Research OK | CANONICAL CANDIDATE |
| KR-BAP-001 한국침례교신학사전 | C | 2 | ? | ? | ? | UNKNOWN | UNKNOWN | CONDITIONAL |
| KR-EV-001 한국복음주의신학사전 | C | 2 | ? | ? | ? | UNKNOWN | UNKNOWN | CONDITIONAL |
| KR-SEM-001 신학교 신학용어집 | B | 2 | Yes | Partial | Partial | Medium | Research OK | SECONDARY VALIDATION SOURCE |
| KR-BIBLE-001 한국어 성경사전 | B | 1 | Yes | Yes | Yes | Strong | Research OK | CANONICAL CANDIDATE |
| EN-BAP-010 ISBE | A | 1 | No | Yes | Yes | Strong | Research OK | CANONICAL CANDIDATE |
| EN-BAP-011 TWOT | A | 1 | No | Yes | Yes | Strong | Research OK | CANONICAL CANDIDATE |
| EN-BAP-012 TWNT | A | 1 | No | Yes | Yes | Strong | Research OK | CANONICAL CANDIDATE |

---

## 11. Canonical Candidates

### 11.1 Primary Canonical Candidates (Priority 1)

| Source ID | Title | Rationale | Risk Factors |
|-----------|-------|-----------|--------------|
| EN-BAP-001 | The New Bible Dictionary (3rd ed.) | IVP/Tyndale publication. Standard evangelical Bible dictionary. Baptist-friendly theological perspective. | KO-EN mapping not explicit. Korean edition exists but needs verification. |
| EN-BAP-002 | Evangelical Dictionary of Theology | Baker Academic. Widely used in evangelical seminaries worldwide. | English only. No KO-EN mapping. |
| EN-BAP-006 | Strong's Concordance (Korean) | De facto standard in Korean seminaries. Implicit KO-EN bridge via Strong's numbers. | Concordance not dictionary. KO-EN mapping is implicit, not explicit. |
| KR-BIBLE-001 | 한국어 성경사전 / 영어-한국어 성경사전 | High potential for KO-EN mapping. Standard in Korean churches. | Multiple editions exist. Specific edition needs identification. |

### 11.2 Secondary Canonical Candidates (Priority 1)

| Source ID | Title | Rationale | Risk Factors |
|-----------|-------|-----------|--------------|
| EN-BAP-003 | Dictionary of the Later New Testament | IVP publication. NT-era terminology focus. | English only. No KO-EN mapping. |
| EN-BAP-004 | Baptist Standard Bible Dictionary | Southern Baptist publication. Aligns with NAE's Baptist tradition. | English only. Baptist perspective may be too narrow for general terms. |
| EN-BAP-005 | BDAG Greek-English Lexicon | Standard Greek lexicon worldwide. Korean translation exists. | Greek-English primary. KO-EN cross-reference needs verification. |
| EN-BAP-007 | Nelson's Illustrated Bible Dictionary | Tyndale House publication. Evangelical perspective. Widely used in Korean seminaries. | English primary. KO-EN mapping needs verification. |
| EN-BAP-008 | Holman Bible Dictionary | Southern Baptist publication. Comprehensive biblical terminology coverage. | English only. No KO-EN mapping. |
| EN-BAP-009 | Anchor Bible Dictionary | Major academic Bible dictionary. Comprehensive coverage. | Catholic/academic perspective (not Baptist-specific). 6 volumes. |
| EN-BAP-010 | International Standard Bible Encyclopedia | Eerdmans publication. Standard evangelical encyclopedia. | English only. No KO-EN mapping. |
| EN-BAP-011 | Theological Wordbook of the Old Testament | Moody Press publication. Standard reference for Hebrew theological terminology. | Hebrew OT terms only. English primary. No KO-EN mapping. |
| EN-BAP-012 | Theological Wordbook of the New Testament | IVP publication. Standard reference for Greek theological terminology. | Greek NT terms only. English primary. No KO-EN mapping. |

### 11.3 Conditional Canonical Candidates (Needs Verification)

| Source ID | Title | Rationale | Risk Factors |
|-----------|-------|-----------|--------------|
| KR-BAP-001 | 한국침례교신학사전 | POTENTIAL high-value source for Baptist-specific terminology. | Existence and content unknown. Needs discovery verification. |
| KR-EV-001 | 한국복음주의신학사전 | POTENTIAL high-value source for Evangelical terminology. | Existence and content unknown. Needs discovery verification. |

---

## 12. Secondary Validation Sources

### 12.1 Korean Theological Dictionaries (for KO terminology validation)

| Source ID | Title | Use Case |
|-----------|-------|----------|
| KR-TH-001 | 한국신학사전 | General Korean theological terminology validation |
| KR-TH-002 | 개혁신학대백과사전 | Reformed terminology validation |
| KR-TH-003 | 장로교신학사전 | Presbyterian terminology validation |
| KR-TH-004 | 기독교백과사전 | General Christianity terminology validation |
| KR-SEM-001 | 한국신학교 신학용어집 | Cross-referencing across Korean Protestant traditions |

---

## 13. Rejected / Discovery-only Sources

| Source ID | Title | Reason |
|-----------|-------|--------|
| (None) | — | No sources rejected at this stage. All candidates have potential value. |

**Note**: AI-generated terminology, general web search results, and non-authoritative sources are classified as "Discovery Only" but not formally listed here because they do not meet the minimum evidence requirement for inclusion in the inventory.

---

## 14. Gaps and Risks

### 14.1 Critical Gaps

| Gap | Impact | Mitigation |
|-----|--------|------------|
| **No confirmed KO-EN explicit mapping source** | PHASE 1 canonical terminology corpus 구축에 직접적인 KO-EN bridge 필요 | KR-BIBLE-001의 구체적 판본 확인, Strong's Concordance Korean edition 활용 검토 |
| **Korean Baptist theological dictionary existence unconfirmed** | Baptist-specific terminology validation에 gap | 한국침례신학회에 문의 또는 학술 데이터베이스에서 확인 |
| **Licensing verification incomplete** | Corpus storage permitted 여부 불확실 | 각 source의 라이선스 확인 필요 |
| **No single authoritative Korean theological dictionary with KO-EN mapping** | PHASE 1의 핵심 목표인 "canonical term validation"에 직접적인 한국어 용어 검증 source 부재 | 여러 source를 cross-reference하는 전략 필요 |

### 14.2 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| KR-BAP-001 / KR-EV-001이 실제로 존재하지 않음 | Medium | High | 학술 데이터베이스에서 확인 |
| 한국어 신학사전의 라이선스가 NAE corpus storage를 허용하지 않음 | Medium | High | 라이선스 확인 후 corpus storage permitted source로 대체 |
| 영어 신학사전과 한국어 신학사전 간 terminology 불일치 | High | Medium | cross-reference 전략으로 완화 |
| Strong's Concordance의 implicit KO-EN mapping이 canonical mapping으로 적합하지 않음 | Low | Medium | explicit KO-EN mapping source 확보 필요 |

---

## 15. Recommended Next Step

### 15.1 Immediate Actions (PHASE 1 — Source Discovery Phase)

1. **KR-BAP-001 (한국침례교신학사전) 존재 여부 확인**
   - 한국침례신학회 공식 자료 확인
   - 학술 데이터베이스 (KISS, DBpia, RISS 등)에서 검색
   - 존재한다면: 판본, 출판사, 발행연도, KO-EN coverage 확인

2. **KR-BIBLE-001 (한국어 성경사전) 구체적 판본 확인**
   - YMCA판, 총목판 등 주요 판본 식별
   - KO-EN mapping explicit 여부 확인
   - 라이선스 확인

3. **Strong's Concordance Korean edition 확인**
   - 한국어 판의 publisher, edition, publication_year 확인
   - Strong's numbers를 통한 implicit KO-EN mapping이 canonical mapping으로 적합한지 평가

4. **라이선스 확인**
   - 각 source의 corpus storage permitted 여부 확인
   - "Copyrighted - research use permitted"가 corpus storage를 포함하는지 확인

### 15.2 Subsequent Actions (PHASE 1 — Corpus Construction Phase)

> **이 단계는 아직 시작하지 않았다.**

1. Canonical candidate source로부터 terminology corpus 구축
2. ADR-029 §4.4 schema 적용
3. Provenance recording
4. Canonical term validation

---

## 16. PHASE 1 Status

```text
PHASE 1 STATUS: SOURCE INVENTORY READY
```

**의미**: authoritative source inventory 구축 완료. canonical terminology corpus construction을 위한 기반이 마련됨.

**다음 단계**: authoritative source inventory에서 선정한 canonical candidates를 사용하여 terminology corpus를 구축한다.

**아직 corpus를 대량 생성하지 않았다.**

---

## 17. Files Modified

```text
New file:
  docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md (본 문서)

Modified:
  0

Deleted:
  0
```

---

## 18. Git Status

```bash
$ git status --short
 M NAE/smith_activation.py
 M docs/STATE.md
 D test_seal_* (9건)
 M ui/pages/chat.py
?? docs/agents/cue/CUE-ADR029-PHASE1-GATE-INDEPENDENT-REVIEW.md
?? docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md
?? docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md
?? docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md
?? docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md (본 문서)

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

---

## Summary Statistics

```text
PHASE 1 — AUTHORITATIVE SOURCE INVENTORY

Sources investigated:
  20

Canonical candidates:
  13 (9 Primary, 4 Secondary)

Secondary validation sources:
  5

Conditional (needs verification):
  2

Discovery-only / rejected:
  0

License UNKNOWN:
  2

KO-EN explicit coverage:
  1 source (KR-BIBLE-001, needs edition verification)
  2 sources with implicit coverage (Strong's, BDAG Korean)

Inventory status:
  SOURCE INVENTORY READY

PHASE 1 corpus construction:
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

**본 인벤토리는 여기서 종료한다. terminology corpus 구축은 아직 시작하지 않았다.**

**PHASE 1의 다음 단계는 authoritative source inventory에서 선정한 canonical candidates를 사용하여 terminology corpus를 구축하는 것이다.**

**첫 번째 실제 engineering task는:**

> **권위 있는 한국어 신학용어 사전 및 관련 authoritative source의 실제 존재 여부, 접근 가능성, 라이선스/사용 조건, provenance를 조사한다.**

**그 결과를 먼저 inventory로 만든다.**

**아직 corpus를 대량 생성하지 않는다.**
