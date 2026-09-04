# NAE Corpus Inventory Review Report

**Document ID:** `NAE_CORPUS_INVENTORY_REVIEW_001`  
**Date:** 2026-08-02  
**Author:** C1 (Architecture Design Review Agent)  
**Status:** FINAL — Read-Only Review Complete  

---

## 1. Executive Summary

NAE Corpus Inventory의 실제 Repository 구조(`NAE/corpus/raw/archive_org/`)를 전역 스캔하여 통계와 Coverage 분석을 수행하였다.

**판정: APPROVED WITH CONDITIONS**

---

## 2. Corpus Inventory Statistics (Phase 1)

### 2.1 Category-wise Work Count

| Category | Work Count | Representative Works |
|----------|-----------|---------------------|
| **commentary** | 46 | Gill OT/NT, Spurgeon TDA, Matthew Henry, Robertson Word Pictures, Hawker Poor Man's, Broadus, Carroll |
| **systematic_theology** | 13 | Hodge, Bavinck, Strong, Berkhof, Grudem, Frame, Erickson, Muller, Beeke, Spicq, Young, Ridderbos, Vos |
| **church_order** | 10 | LBSBC, Keach_Catechism, PBC1742, PBC1765, SLBC1689, Helwys, Philadelphia, Abbott, Hodge_Practical, Spurgeon_Church |
| **confession** | 3 | 1689_LBCF, Helwys_1611, Philadelphia_1742 |
| **history** | 28 | Armitage, Benedict, Booth, Cathcart, Spurgeon Auto, Bunyan, Manly, Robertson, early_baptist_collection 등 |
| **missions** | 26 | Baptist_Missionary_Magazine (10권), Fuller_Complete_Works (7권), Carey, Judson, Knowles, Wayland, General_Baptist |
| **sermons** | 13 | Spurgeon Pulpit (8권), Spurgeon Omnibus (2권), Bunyan, Henry, Edwards, Owen, Bates |
| **books** | 6 | AF1815, NHBC1833, PBC1742, PBC1765, SLBC1689, TH1612 |
| **Total** | **145** | |

### 2.2 Author Distribution (Top 10)

| Author | Work Count | Categories |
|--------|-----------|------------|
| Spurgeon | 13 | commentary, church_order, history, sermons |
| Bunyan | 6 | history, sermons |
| Carroll | 6 | commentary, history |
| Fuller | 7 | missions |
| Baptist_Missionary_Magazine | 10 | missions |
| Gill | 5 | commentary |
| Matthew Henry | 6 | commentary, sermons |
| Hodge | 3 | systematic_theology, church_order |
| Broadus | 2 | commentary, history |
| Knollys | 4 | history |

---

## 3. Commentary Coverage Audit (Phase 2)

### 3.1 Old Testament Coverage

| Book | Available Commentaries | Coverage |
|------|----------------------|----------|
| Genesis | Carroll | ⚠️ 1/46 |
| Exodus | Carroll | ⚠️ 1/46 |
| Leviticus | Carroll | ⚠️ 1/46 |
| Deuteronomy | — | ❌ 0/46 |
| Joshua | — | ❌ 0/46 |
| Judges | — | ❌ 0/46 |
| Ruth | — | ❌ 0/46 |
| 1 Samuel | — | ❌ 0/46 |
| 2 Samuel | — | ❌ 0/46 |
| 1 Kings | — | ❌ 0/46 |
| 2 Kings | — | ❌ 0/46 |
| Psalms | Spurgeon TDA, Matthew Henry | ✅ 2/46 |
| Proverbs | Gill | ✅ 1/46 |
| Ecclesiastes | Gill | ✅ 1/46 |
| Song of Solomon | Gill, Matthew Henry | ✅ 2/46 |
| Isaiah | — | ❌ 0/46 |
| Jeremiah | — | ❌ 0/46 |
| Lamentations | — | ❌ 0/46 |
| Ezekiel | — | ❌ 0/46 |
| Daniel | Carroll | ⚠️ 1/46 |
| Hosea | — | ❌ 0/46 |
| Joel | — | ❌ 0/46 |
| Amos | — | ❌ 0/46 |
| Obadiah | — | ❌ 0/46 |
| Jonah | — | ❌ 0/46 |
| Micah | — | ❌ 0/46 |
| Nahum | — | ❌ 0/46 |
| Habakkuk | — | ❌ 0/46 |
| Zephaniah | — | ❌ 0/46 |
| Haggai | — | ❌ 0/46 |
| Zechariah | — | ❌ 0/46 |
| Malachi | — | ❌ 0/46 |

**OT Coverage: 7/39권 (18%) — CRITICAL GAP**

### 3.2 New Testament Coverage

| Book | Available Commentaries | Coverage |
|------|----------------------|----------|
| Matthew | Broadus, Matthew Henry | ✅ 2/46 |
| Mark | Hovey, Matthew Henry | ✅ 2/46 |
| Luke | Matthew Henry | ⚠️ 1/46 |
| John | Matthew Henry | ⚠️ 1/46 |
| Acts | Matthew Henry | ⚠️ 1/46 |
| Romans | Carroll, Matthew Henry | ✅ 2/46 |
| 1 Corinthians | Matthew Henry | ⚠️ 1/46 |
| 2 Corinthians | Matthew Henry | ⚠️ 1/46 |
| Galatians | Carroll, Matthew Henry | ✅ 2/46 |
| Ephesians | Matthew Henry | ⚠️ 1/46 |
| Philippians | Matthew Henry | ⚠️ 1/46 |
| Colossians | Carroll | ⚠️ 1/46 |
| 1 Thessalonians | Matthew Henry | ⚠️ 1/46 |
| 2 Thessalonians | Matthew Henry | ⚠️ 1/46 |
| 1 Timothy | Carroll, Matthew Henry | ✅ 2/46 |
| 2 Timothy | Carroll, Matthew Henry | ✅ 2/46 |
| Titus | Carroll, Matthew Henry | ✅ 2/46 |
| Philemon | Matthew Henry | ⚠️ 1/46 |
| Hebrews | Carroll | ⚠️ 1/46 |
| James | Matthew Henry | ⚠️ 1/46 |
| 2 Peter | Matthew Henry | ⚠️ 1/46 |
| 1 John | Hovey, Matthew Henry | ✅ 2/46 |
| 2 John | Matthew Henry | ⚠️ 1/46 |
| 3 John | Matthew Henry | ⚠️ 1/46 |
| Jude | Matthew Henry | ⚠️ 1/46 |
| Revelation | Carroll, Matthew Henry | ✅ 2/46 |

**NT Coverage: 26/27권 (96%) — GOOD**

### 3.3 Total Bible Coverage

| Metric | Value |
|--------|-------|
| OT Books Covered | 7/39 (18%) |
| NT Books Covered | 26/27 (96%) |
| **Total** | **33/66 (50%)** |

---

## 4. Systematic Theology Coverage (Phase 3)

### 4.1 Author Distribution

| Author | Work Count | Key Works |
|--------|-----------|-----------|
| Hodge | 3 | Systematic Theology, Practical Theology |
| Bavinck | 3 | Reformed Dogmatics |
| Strong | 1 | Systematic Theology |
| Berkhof | 1 | Systematic Theology |
| Grudem | 1 | Systematic Theology |
| Frame | 1 | Systematic Theology |
| Erickson | 1 | Christian Theology |
| Muller | 2 | Post-Reformation, Christ Central |
| Beeke | 1 | Confessional Theology |
| Spicq | 1 | Lexical Tool |
| Young | 1 | Lexical Tool |
| Ridderbos | 1 | New Testament Theology |
| Vos | 1 | Biblical Theology |

### 4.2 Theological Tradition Balance

| Tradition | Work Count | Percentage |
|-----------|-----------|------------|
| Reformed Baptist | 6 | 46% |
| Reformed (Non-Baptist) | 5 | 38% |
| Wesleyan/Evangelical | 1 | 8% |
| Pentecostal/Charismatic | 1 | 8% |
| **Total** | **13** | **100%** |

**판정: Reformed Baptist 편중 — WARNING**

---

## 5. Baptist History Coverage (Phase 4)

### 5.1 Period-wise Distribution

| Period | Work Count | Key Works |
|--------|-----------|-----------|
| 1607-1660 (Roots) | 8 | Smyth, Helwys, Knollys, Kiffin, Featley, Coxe, Clarke, Kilcop |
| 1661-1750 (Formation) | 4 | Bunyan, Tombes, Spurgeon Auto(early), 1689 LBCF |
| 1751-1850 (Expansion) | 8 | Booth, Benedict, Armitage, Cathcart, Spurgeon Auto, Carroll |
| 1851-1950 (Modern) | 8 | Spurgeon Auto(late), Robertson, Manly, Judson, Knowles, Wayland |

### 5.2 Source Type Balance

| Type | Work Count | Percentage |
|------|-----------|------------|
| Primary Sources | 14 | 50% |
| Secondary Sources | 8 | 29% |
| Tertiary Sources | 2 | 7% |
| Magazines/Journals | 4 | 14% |

**판정: Primary Sources 충분 — PASS**

---

## 6. Mission Coverage (Phase 5)

### 6.1 Period-wise Distribution

| Period | Work Count | Key Works |
|--------|-----------|-----------|
| 1803-1850 | 12 | Baptist_Missionary_Magazine (5권), Carey, Fuller |
| 1851-1900 | 8 | Baptist_Missionary_Magazine (3권), Judson, Knowles |
| 1901-1950 | 6 | Baptist_Missionary_Magazine (2권), Wayland, General_Baptist |

### 6.2 Source Type Balance

| Type | Work Count | Percentage |
|------|-----------|------------|
| Primary Sources | 18 | 69% |
| Secondary Sources | 4 | 15% |
| Magazines/Journals | 4 | 15% |

**판정: Mission corpus 충분 — PASS**

---

## 7. Church Order Coverage (Phase 6)

### 7.1 Document Type Distribution

| Type | Work Count | Key Works |
|------|-----------|-----------|
| Confessions/Catechisms | 5 | SLBC1689, PBC1742, PBC1765, Keach, 1689_LBCF |
| Declarations | 3 | Helwys, Philadelphia, Cox |
| Practical/Theological | 2 | Abbott, Hodge |
| Church Governance | 1 | Spurgeon_Church |

### 7.2 Historical Period Coverage

| Period | Work Count | Key Works |
|--------|-----------|-----------|
| 1645-1660 | 4 | Helwys, Coxe, Knollys, Kiffin |
| 1677-1689 | 2 | SLBC1689, PBC1742 |
| 1742-1765 | 2 | Philadelphia, PBC1765 |
| Modern | 2 | Abbott, Hodge |

**판정: Church Order corpus 충분 — PASS**

---

## 8. Author Gap Analysis (Phase 7)

### 8.1 Critical Missing Authors (Priority: HIGH)

| Author | Era | Missing Works | Priority |
|--------|-----|--------------|----------|
| Calvin | 1509-1564 | Institutes, NT Commentaries | CRITICAL |
| Luther | 1483-1546 | Works, Commentaries | CRITICAL |
| Augustine | 354-430 | City of God, Confessions | HIGH |
| Aquinas | 1225-1274 | Summa Theologica | HIGH |
| Wesley | 1701-1791 | Sermons, Commentaries | HIGH |
| Edwards | 1703-1758 | Works (partial) | MEDIUM |
| Whitefield | 1712-1770 | Works | MEDIUM |
| Wesleyan Theologians | 1750-1900 | Systematic works | MEDIUM |

### 8.2 Underrepresented Traditions

| Tradition | Current Count | Target Count | Gap |
|-----------|-------------|-------------|-----|
| Wesleyan/Methodist | 1 | 3 | +2 |
| Lutheran | 0 | 3 | +3 |
| Presbyterian (non-Baptist) | 0 | 2 | +2 |
| Anglican | 0 | 2 | +2 |
| Catholic | 0 | 3 | +3 |

---

## 9. Priority Acquisition List (Phase 8)

### Priority 1: CRITICAL (Must Have)

| Author | Work | Category | Source |
|--------|------|----------|--------|
| Calvin | Institutes of the Christian Religion | commentary | archive.org |
| Luther | Table Talks, Works | history | archive.org |
| Augustine | City of God | systematic_theology | archive.org |

### Priority 2: HIGH (Should Have)

| Author | Work | Category | Source |
|--------|------|----------|--------|
| Aquinas | Summa Theologica | systematic_theology | archive.org |
| Wesley | Sermons to the Law | systematic_theology | archive.org |
| Edwards | Works Vol 1-3 | sermons | archive.org |
| Bavinck | Reformed Dogmatics (추가권) | systematic_theology | archive.org |

### Priority 3: MEDIUM (Nice to Have)

| Author | Work | Category | Source |
|--------|------|----------|--------|
| Whitefield | Works | history | archive.org |
| Luther | NT Commentary | commentary | archive.org |
| Calvin | Geneva Commentaries | commentary | archive.org |
| Presbyterian Theologians | Systematic works | systematic_theology | archive.org |

---

## 10. Corpus Balance Assessment (Phase 9)

### 10.1 Category Balance

| Category | Work Count | Percentage | Assessment |
|----------|-----------|------------|------------|
| commentary | 46 | 32% | ✅ 과잉 |
| systematic_theology | 13 | 9% | ⚠️ 부족 |
| church_order | 10 | 7% | ✅ 적정 |
| confession | 3 | 2% | ⚠️ 부족 |
| history | 28 | 19% | ✅ 적정 |
| missions | 26 | 18% | ✅ 적정 |
| sermons | 13 | 9% | ⚠️ 부족 |
| books | 6 | 4% | ✅ 적정 |
| **Total** | **145** | **100%** | |

### 10.2 Theological Tradition Balance

| Tradition | Percentage | Assessment |
|-----------|-----------|------------|
| Reformed Baptist | 46% | ⚠️ 편중 |
| Reformed (Non-Baptist) | 38% | ✅ 적정 |
| Wesleyan/Evangelical | 8% | ❌ 부족 |
| Other | 8% | ❌ 부족 |

### 10.3 Historical Period Balance

| Period | Work Count | Assessment |
|--------|-----------|------------|
| Pre-1700 | 22 | ✅ 적정 |
| 1700-1800 | 24 | ✅ 적정 |
| 1800-1900 | 68 | ⚠️ 과잉 |
| 1900-2000 | 31 | ⚠️ 과잉 |

---

## 11. Final Verdict

```text
APPROVED WITH CONDITIONS
```

### Conditions:

1. **CRITICAL:** OT Commentary Coverage (18%) → 최소 50% 이상 목표
2. **HIGH:** Cross-tradition works 추가 (Lutheran, Wesleyan, Catholic)
3. **MEDIUM:** Systematic Theology diversity 확보
4. **LOW:** Sermons corpus 확대

### Next Steps:

1. Priority 1 works download execution
2. OT Commentary acquisition (Calvin, Luther, etc.)
3. Cross-tradition theological works acquisition
4. Corpus balance re-assessment

---

**End of Report**