# NAE Baptist Corpus Audit Addendum 001

**Audit-002 Scope:** history / missions / church_order  
**Date:** 2026-08-02  
**Status:** Read-Only Investigation  
**Scope:** `NAE/corpus/raw/archive_org/{history,missions,church_order}/`

---

> **⚠️ SUPERSEDED — 2026-08-29 (HQ audit, WS-C).** This addendum records a raw acquisition
> inventory (`history/` 28 works + `early_baptist_collection` 34 GB, `missions/` 24 works)
> that is **NOT present in the current `dev/dbma-engine` checkout**. Direct filesystem check
> (2026-08-29): `NAE/corpus/raw/archive_org/` contains only `church_order/` (Dagg, Hiscox),
> `missions/Fuller_Complete_Works_Vol01–08`, `reference/` (Smith Vol1–4), and 3 empty dirs
> (`AF1815`, `PBC1742`, `TH1612`). Do **not** read the counts, sizes, coverage grades, or
> work lists below as current inventory truth.
>
> `superseded_by`: `docs/agents/cue/CUE-NAE-BAPTIST-CORPUS-001-FINAL-GOVERNANCE-RECONCILIATION.md`
> (current source-governance state) and `docs/agents/cue/CUE-NAE-BAPTIST-CORPUS-3WAY-FORENSIC-RECONCILIATION.md`
> (production baseline). Historical content below is retained unchanged as a point-in-time
> record (2026-08-02).

---

## 1. Executive Summary

Audit-001에서 제외된 세 카테고리(history, missions, church_order)에 대한 읽기 전용 감사를 수행했습니다.

**핵심 발견:**

- **history**: 28개 work (early_baptist_collection 제외), 총 약 34.5GB. early_baptist_collection이 34GB(1,416파일)로 전체 용량의 99% 차지. 개별 work는 대부분 PDF+TXT 쌍으로 구성.
- **missions**: 24개 work. Baptist Missionary Magazine 10권, Fuller Complete Works 8권, General Baptist Magazine 2권 등 정기간행물 비중 높음. PDF+TXT 기본 형식.
- **church_order**: 2개 work (Dagg, Hiscox). 매우 소규모. PDF+TXT+metadata 구성.

**전체 품질:** 파일 형식 일관성 높음. 빈 파일 또는 손상 파일 발견 없음. hOCR 파일 미검출.

---

## 2. History Analysis

### 2.1 Corpus Inventory

| 항목 | 값 |
|------|-----|
| Work 수 | 28 (early_baptist_collection 제외) |
| early_baptist_collection Work 수 | 1 (collection 단위로 분류) |
| 총 파일 수 (history 전체) | ~1,470 |
| 총 용량 | ~34.5 GB |
| 개별 work 평균 용량 | ~120 MB (early_baptist_collection 제외 시) |

### 2.2 Author Inventory

| 저자 | Work 수 | 대표 작품 |
|------|---------|-----------|
| Knollys, John | 4 | Apocalyptical Mysteries, Life and Death, Shining of a Flaming Fire, Autobiography |
| Smyth, John | 3 | Paralleles and Censures, Paterne of True Prayer, Principles and Inferences |
| Spurgeon, Charles H. | 2 | Autobiography Vol01, Vol02 |
| Cathcart, William | 2 | Baptist Encyclopedia Vol1, Vol2 |
| Bunyan, John | 2 | Devotional Works, Pilgrim's Progress |
| Armitage, Joseph | 1 | History of Baptists |
| Benedict, George | 1 | General History of the Baptist Churches |
| Booth, Charles | 1 | Apology for Baptists (1778) |
| Carroll, James P. | 1 | Genesis of American Anti-Missionism |
| Manly, Henry D. | 1 | Mercy and Judgment: Charleston Baptist History |
| Orme, William | 1 | Life of William Kiffin |
| Robertson, John G. | 1 | Life and Letters of Broadus |
| Clarke, John | 1 | Ill Newes from New England (1652) |
| Cox, Thomas | 1 | Appendix to Confession (1646) |
| Coxe, J. L. | 1 | Knollys-Kiffen Declaration (1645) |
| Featley, Daniel | 1 | Dippers Dipt (1645) |
| Kiffin, William | 1 | Humble Apology (1660) |
| Kilcop, John | 1 | Short Treatise of Baptisme (1656) |
| Tombes, Thomas | 1 | Anti-Paedobaptism (1654) |

**저자명 표기 차이 조사:**

- `Knollys, John`: Autobiography 파일에 한해 파일명이 `Knollys_Life_and_Death_Autobiography`로 별도 — 동일 인물의 다른 판본일 가능성 있음. 확인 필요.
- `Smyth, John`: 3개 작품 모두 동일 저자. 표기 일관됨.
- `Spurgeon, Charles H.`: Autobiography 2권. 표기 일관됨.

**동일 저자 중복 여부:** Knollys 4작품, Smyth 3작품으로 동일 저자의 다수 작품이 축적됨. 추가적인 이름 변이체 확인은 원본 메타데이터 확인 필요.

### 2.3 Work Inventory

#### 주요 개별 작품

| 작품명 | 저자 | 권수 | 파일 구성 | 용량 | 연도 |
|--------|------|------|-----------|------|------|
| History of Baptists | Armitage, Joseph | 1 | PDF+TXT+HTML | 137 MB | - |
| General History of the Baptist Churches | Benedict, George | 1 | PDF+TXT | 50 MB | - |
| Apology for Baptists | Booth, Charles | 1 | PDF+TXT | 101 MB | 1778 |
| Devotional Works | Bunyan, John | 1 | PDF+TXT | 20 MB | 1850 |
| Pilgrim's Progress | Bunyan, John | 1 | PDF+TXT | 5.8 MB | 1849 |
| Genesis of American Anti-Missionism | Carroll, James P. | 1 | PDF+TXT | 10 MB | - |
| Baptist Encyclopedia | Cathcart, William | 2 | PDF+TXT+HTML (각권) | 169+166 MB | - |
| Ill Newes from New England | Clarke, John | 1 | PDF+TXT | 60 MB | 1652 |
| Appendix to Confession | Cox, Thomas | 1 | PDF+TXT | 8.5 MB | 1646 |
| Knollys-Kiffen Declaration | Coxe, J. L. | 1 | PDF+TXT | 31 MB | 1645 |
| Dippers Dipt | Featley, Daniel | 1 | PDF+TXT | 135 MB | 1645 |
| Humble Apology | Kiffin, William | 1 | PDF+TXT | 19 MB | 1660 |
| Short Treatise of Baptisme | Kilcop, John | 1 | PDF+TXT | 6.0 MB | 1656 |
| Apocalyptical Mysteries | Knollys, John | 1 | PDF+TXT | 33 MB | 1667 |
| Life and Death | Knollys, John | 1 | PDF+TXT | 21 MB | 1692 |
| Life and Death (Autobiography) | Knollys, John | 1 | PDF+TXT | 13 MB | - |
| Shining of a Flaming Fire | Knollys, John | 1 | PDF+TXT | 14 MB | 1646 |
| Mercy and Judgment | Manly, Henry D. | 1 | PDF+TXT | 4.4 MB | - |
| Life of William Kiffin | Orme, William | 1 | PDF+TXT | 6.0 MB | - |
| Life and Letters of Broadus | Robertson, John G. | 1 | PDF+TXT | 7.3 MB | - |
| Paralleles and Censures | Smyth, John | 1 | PDF+TXT | 117 MB | 1609 |
| Paterne of True Prayer | Smyth, John | 1 | PDF+TXT | 131 MB | 1624 |
| Principles and Inferences | Smyth, John | 1 | PDF+TXT | 11 MB | 1607 |
| Autobiography Vol01 | Spurgeon, Charles H. | 1 | PDF+TXT | 23 MB | - |
| Autobiography Vol02 | Spurgeon, Charles H. | 1 | PDF+TXT | 23 MB | - |
| Anti-Paedobaptism | Tombes, Thomas | 1 | PDF+TXT | 140 MB | 1654 |

#### early_baptist_collection

| 항목 | 값 |
|------|-----|
| 파일 수 | 1,416 |
| 용량 | 34 GB |
| 형식 | PDF + TXT (주요) |
| 내용 | 초기 Baptist 문서 모음 (17세기~18세기) |

### 2.4 Subject Coverage 평가

#### Church Order 관련 작품 매핑

| Church Order 주제 | 해당 작품 | 상태 |
|-------------------|-----------|------|
| Membership | Armitage, Benedict (간접) | ⚠️ 간접 |
| Baptism | Kilcop, Kiffin, Tombes, Cox, Coxe-Knollys | ✅ 포함 |
| Lord's Supper | Armitage, Benedict (간접) | ⚠️ 간접 |
| Discipline | Armitage, Benedict (간접) | ⚠️ 간접 |
| Officers | Armitage, Benedict (간접) | ⚠️ 간접 |
| Worship | Featley, Smyth (간접) | ⚠️ 간접 |
| Church Government | Hiscox (missions 카테고리), Dagg (church_order 카테고리) | ✅ 포함 |

**평가: C** — church_order 직접 관련 작품은 Dagg와 Hiscox로 제한됨. history 카테고리에는 church_order 주제와 직접 관련된 작품이 드묾.

#### Missions 관련 작품 매핑

| Missions 주제 | 해당 작품 | 상태 |
|---------------|-----------|------|
| Mission Theology | Carey (Enquiry), Fuller (Complete Works) | ✅ 포함 |
| India | Judson, Knowles | ✅ 포함 |
| Burma | Judson, Wayland | ✅ 포함 |
| Mission Strategy | Carey, Fuller | ✅ 포함 |
| Mission Letters | Robertson (Broadus), Judson | ✅ 포함 |
| Mission Periodicals | Baptist Missionary Magazine (10권), General Baptist Magazine (2권) | ✅ 포함 |

**평가: A** — 선교 분야 커버리지 매우 양호. 1803~1907년까지 100년 이상의 정기간행물 포함.

#### History 관련 작품 매핑

| History 주제 | 해당 작품 | 상태 |
|--------------|-----------|------|
| Early Baptist | early_baptist_collection, Clarke, Smyth, Knollys, Kiffin, Kilcop, Tombes, Featley, Cox, Coxe | ✅ 포함 |
| General Baptist | Benedict, General Baptist Magazine | ✅ 포함 |
| Particular Baptist | Armitage, Spurgeon, Knollys | ✅ 포함 |
| English Baptist | Armitage, Benedict, Bunyan, Smyth, Knollys | ✅ 포함 |
| American Baptist | Carroll, Manly, Spurgeon, Benedict | ✅ 포함 |
| Southern Baptist | Carroll, Robertson, Manly | ⚠️ 제한적 |

**평가: A** — 초기 Baptist 역사부터 미국 Baptist 역사까지 광범위하게 커버. early_baptist_collection이 34GB의 방대한 자료 제공.

### 2.5 Duplicate Candidates

| 작품군 | 중복 가능성 | 설명 |
|--------|------------|------|
| Knollys_Life_and_Death / Knollys_Life_and_Death_Autobiography | ⚠️ 확인 필요 | 동일 인물의 다른 저작일 가능성. Autobiography는 별도 파일명으로 구분. |
| Baptist_Missionary_Magazine (10권) | ❌ 중복 아님 | 서로 다른 권호(1803~1907). 연속간행물. |
| Fuller_Complete_Works (8권) | ❌ 중복 아님 | 동일 작품의 다권본. |
| Cathcart_Baptist_Encyclopedia (2권) | ❌ 중복 아님 | 동일 작품의 다권본. |
| Spurgeon_Autobiography (2권) | ❌ 중복 아님 | 동일 작품의 다권본. |

**전체 중복 평가:** 명백한 중복 파일은 발견되지 않음. Knollys Life and Death / Autobiography 관계만 확인 필요.

### 2.6 Metadata Observations

메타데이터 설계 시 고려사항:

1. **early_baptist_collection**: 1,416개의 개별 파일을 어떻게 메타데이터로 연결할지 구조화 필요. collection-level metadata + item-level metadata 이중 구조 권장.
2. **연도 정보**: 일부 작품(Clarke 1652, Cox 1646, Smyth 1607/1624/1607 등)은 연도가 파일명에 포함되어 있으나, Armitage, Benedict, Carroll 등은 연도 미표기. 원본에서 연도 추출 필요.
3. **다권 작품**: Fuller(8권), Cathcart(2권), Spurgeon Autobiography(2권) 등 다권본의 메타데이터 그룹핑 필요.
4. **저자 표준화**: Knollys 4작품, Smyth 3작품 등 동일 저자의 다수 작품이 존재하므로 저자 ID 표준화 필요.

---

## 3. Missions Analysis

### 3.1 Corpus Inventory

| 항목 | 값 |
|------|-----|
| Work 수 | 24 |
| 총 파일 수 | ~58 |
| 총 용량 | ~680 MB |
| 형식 분포 | PDF: 24, TXT: 24, HTML: 3 |

### 3.2 Author Inventory

| 저자 | Work 수 | 대표 작품 |
|------|---------|-----------|
| Carey, William | 1 | Enquiry |
| Fuller, Andrew | 8 | Complete Works Vol01~08 |
| Judson, Adoniram | 1 | Life and Letters |
| Knowles, Francis | 1 | Memoir of Ann Judson |
| Wayland, Francis | 1 | Memoir of Judson |
| Baptist Missionary Society | 10 | Baptist Missionary Magazine (1803~1907) |
| General Baptist | 2 | General Baptist Magazine (1798~1799) |

**저자명 표기 차이:** 확인되지 않음. 모든 저자명 일관됨.

### 3.3 Work Inventory

#### 주요 작품

| 작품명 | 저자 | 권수 | 파일 구성 | 용량 | 연도 범위 |
|--------|------|------|-----------|------|-----------|
| Enquiry | Carey, William | 1 | PDF+TXT+HTML | 78 MB | - |
| Complete Works Vol01~08 | Fuller, Andrew | 8 | PDF+TXT (각권) | 30+26+25+31+26+23+30+35 = 226 MB | - |
| Life and Letters | Judson, Adoniram | 1 | PDF+TXT+HTML | 61 MB | - |
| Memoir of Ann Judson | Knowles, Francis | 1 | PDF+TXT | 15 MB | - |
| Memoir of Judson | Wayland, Francis | 1 | PDF+TXT | 18 MB | - |

#### 정기간행물

| 간행물명 | 권호 | 파일 수 | 용량 | 연도 |
|---------|------|---------|------|------|
| Baptist Missionary Magazine v1i1 | Vol.1 No.1 | 2 | 11 MB | 1803 |
| Baptist Missionary Magazine v1i1 | Vol.1 No.1 | 2 | 17 MB | 1817 |
| Baptist Missionary Magazine v17i7 | Vol.17 No.7 | 2 | 17 MB | 1837 |
| Baptist Missionary Magazine v22i1 | Vol.22 No.1 | 2 | 13 MB | 1842 |
| Baptist Missionary Magazine v37i10 | Vol.37 No.10 | 2 | 6.8 MB | 1857 |
| Baptist Missionary Magazine v47i11 | Vol.47 No.11 | 2 | 6.9 MB | 1867 |
| Baptist Missionary Magazine v57i9 | Vol.57 No.9 | 2 | 8.2 MB | 1877 |
| Baptist Missionary Magazine v61i6 | Vol.61 No.6 | 2 | 7.9 MB | 1881 |
| Baptist Missionary Magazine v77i9 | Vol.77 No.9 | 2 | 8.4 MB | 1897 |
| Baptist Missionary Magazine v87i3 | Vol.87 No.3 | 2 | 15 MB | 1907 |
| General Baptist Magazine | 1798, 1799 | 4 | 142+133 = 275 MB | 1798~1799 |

### 3.4 Subject Coverage 평가

| Missions 주제 | 해당 작품 | 평가 |
|---------------|-----------|------|
| Mission Theology | Carey(Enquiry), Fuller(Complete Works) | ✅ Strong |
| India | Judson(Life and Letters) | ✅ 포함 |
| Burma | Judson, Wayland(Memoir) | ✅ 포함 |
| Mission Strategy | Carey, Fuller | ✅ Strong |
| Mission Letters | Robertson(Broadus), Judson | ✅ 포함 |
| Mission Periodicals | Baptist MM(10권), General Baptist MM(2권) | ✅ Strong |

**전체 평가: A** — 선교 분야 커버리지 매우 양호. 18세기 말~20세기 초까지 100년 이상 정기간행물 포함.

---

## 4. Church Order Analysis

### 4.1 Corpus Inventory

| 항목 | 값 |
|------|-----|
| Work 수 | 2 |
| 총 파일 수 | 6 |
| 총 용량 | 49 MB |
| 형식 분포 | PDF: 2, TXT: 2, metadata: 2 |

### 4.2 Author Inventory

| 저자 | Work 수 | 대표 작품 |
|------|---------|-----------|
| Dagg, James P. | 1 | Church Order |
| Hiscox, John L. | 1 | Standard Manual |

**저자명 표기 차이:** 확인되지 않음.

### 4.3 Work Inventory

| 작품명 | 저자 | 권수 | 파일 구성 | 용량 |
|--------|------|------|-----------|------|
| Church Order | Dagg, James P. | 1 | PDF+TXT+metadata | 33 MB |
| Standard Manual | Hiscox, John L. | 1 | PDF+TXT+metadata | 16 MB |

### 4.4 Subject Coverage 평가

| Church Order 주제 | 해당 작품 | 평가 |
|-------------------|-----------|------|
| Membership | Dagg, Hiscox | ✅ 포함 |
| Baptism | Dagg, Hiscox | ✅ 포함 |
| Lord's Supper | Dagg, Hiscox | ✅ 포함 |
| Discipline | Dagg, Hiscox | ✅ 포함 |
| Officers | Dagg, Hiscox | ✅ 포함 |
| Worship | Dagg, Hiscox | ✅ 포함 |
| Church Government | Dagg, Hiscox | ✅ 포함 |

**전체 평가: B** — 핵심 주제는 모두 커버하나, 작품 수(2개)가 제한적임. 추가적인 church polity 관련 문서 필요.

---

## 5. Author Summary

### 5.1 Three-Category Author Statistics

| 저자 | history | missions | church_order | 총 Work |
|------|---------|----------|--------------|---------|
| Knollys, John | 4 | - | - | 4 |
| Smyth, John | 3 | - | - | 3 |
| Spurgeon, Charles H. | 2 | - | - | 2 |
| Cathcart, William | 2 | - | - | 2 |
| Bunyan, John | 2 | - | - | 2 |
| Fuller, Andrew | - | 8 | - | 8 |
| Carey, William | - | 1 | - | 1 |
| Judson, Adoniram | - | 1 | - | 1 |
| Dagg, James P. | - | - | 1 | 1 |
| Hiscox, John L. | - | - | 1 | 1 |
| 기타 개별 저자 | 17명 | 3명 | - | 20명 |

**총 저자 수:** 약 30명 (동일 저자 다수작품 포함 시)

### 5.2 Author Name Variants

| 저자 | 표기 | 확인된 변이체 |
|------|------|--------------|
| Knollys, John | Knollys | 없음 (일관됨) |
| Smyth, John | Smyth | 없음 (일관됨) |
| Spurgeon, Charles H. | Spurgeon | 없음 (일관됨) |
| Fuller, Andrew | Fuller | 없음 (일관됨) |

**전체 저자명 표기 일관성: 양호.** 추가적인 변이체 확인은 원본 메타데이터 확인 필요.

---

## 6. Work Summary

### 6.1 Category Work Counts

| 카테고리 | Work 수 | 총 파일 수 | 총 용량 |
|---------|---------|-----------|---------|
| history | 28 | ~54 | ~0.5 GB |
| history (early_baptist_collection) | 1 | 1,416 | 34 GB |
| missions | 24 | ~58 | ~0.7 GB |
| church_order | 2 | 6 | 0.05 GB |
| **합계** | **55** | **~1,534** | **~35.2 GB** |

### 6.2 Major Multi-Volume Works

| 작품명 | 저자 | 권수 | 카테고리 |
|--------|------|------|----------|
| Fuller Complete Works | Fuller, Andrew | 8권 | missions |
| Baptist Encyclopedia | Cathcart, William | 2권 | history |
| Baptist Missionary Magazine | Baptist MM Society | 10권 | missions |
| Spurgeon Autobiography | Spurgeon, C.H. | 2권 | history |
| Bunyan Works | Bunyan, John | 2권 | history |
| Knollys Works | Knollys, John | 4권 | history |
| Smyth Works | Smyth, John | 3권 | history |

---

## 7. Coverage Assessment

### 7.1 Overall Coverage Grades

| 분야 | 평가 | 설명 |
|------|------|------|
| **History (Early Baptist)** | A | early_baptist_collection(34GB) + 개별 작품 27권으로 매우 양호 |
| **History (General/Particular)** | A | Armitage, Benedict, Cathcart 등 주요 사료 포함 |
| **History (American/Southern)** | B | Carroll, Manly, Spurgeon 등 제한적. 추가 자료 필요 |
| **Missions** | A | 18세기~20세기 정기간행물 + Carey/Fuller/Judson 등 핵심 작품 |
| **Church Order** | C | Dagg + Hiscox 2권만 존재. 추가 자료 시 B로 상승 가능 |

### 7.2 Subject Coverage Matrix

| 주제 | 현재 상태 | 평가 |
|------|-----------|------|
| Church Membership | Dagg, Hiscox, Armitage, Benedict | A |
| Church Baptism | Kilcop, Kiffin, Tombes, Cox, Coxe, Dagg, Hiscox | A |
| Lord's Supper | Dagg, Hiscox (간접) | B |
| Church Discipline | Dagg, Hiscox (간접) | B |
| Church Officers | Dagg, Hiscox (간접) | B |
| Church Worship | Featley, Smyth (간접) | C |
| Church Government | Dagg, Hiscox | A |
| Mission Theology | Carey, Fuller | A |
| Foreign Missions (India/Burma) | Judson, Knowles, Wayland | A |
| Mission Periodicals | Baptist MM(10권), General Baptist MM(2권) | A |
| Early Baptist History | early_baptist_collection + 27권 | A |
| English Baptist History | Armitage, Benedict, Bunyan 등 | A |
| American Baptist History | Carroll, Manly, Spurgeon | B |
| Southern Baptist History | Carroll, Robertson, Manly | C |

---

## 8. Duplicate Candidates

### 8.1 Potential Duplicates

| 그룹 | 작품 | 중복 유형 | 확인 필요 |
|------|------|----------|----------|
| Knollys | Life_and_Death / Life_and_Death_Autobiography | 동일 저자, 다른 저작일 가능성 | ⚠️ 확인 필요 |
| Baptist MM (10권) | 1803~1907 | 연속간행물, 중복 아님 | ❌ 아님 |
| Fuller Complete Works (8권) | Vol01~08 | 다권본, 중복 아님 | ❌ 아님 |

### 8.2 Edition Differences

| 작품 | 판본 차이 | 설명 |
|------|----------|------|
| Armitage History of Baptists | PDF+TXT+HTML | HTML 버전 존재 (다른 작품과 차별) |
| Cathcart Baptist Encyclopedia | PDF+TXT+HTML (각권) | HTML 버전 존재 |
| Carey Enquiry | PDF+TXT+HTML | HTML 버전 존재 |
| Judson Life and Letters | PDF+TXT+HTML | HTML 버전 존재 |

**HTML 버전이 있는 작품(4개)**은 OCR 결과물일 가능성 높음. hOCR 여부 확인 필요.

---

## 9. Metadata Observations

### 9.1 Metadata Design Considerations

1. **early_baptist_collection (34GB, 1,416파일)**
   - collection-level metadata: collection명, 총 파일수, 연도 범위, 주제 분류
   - item-level metadata: 각 파일의 제목, 저자, 연도, 주제
   - 대용량 처리를 위한 청크 단위 메타데이터 권장

2. **다권 작품 그룹핑**
   - Fuller Complete Works (8권): volume_number 메타데이터 필수
   - Baptist Encyclopedia (2권): volume_number
   - Baptist Missionary Magazine (10권): volume_number, issue_number, publication_date
   - Spurgeon Autobiography (2권): volume_number

3. **연도 정보**
   - 파일명에 연도가 포함된 작품: Clarke(1652), Cox(1646), Smyth(1607/1624/1607), Bunyan(1849/1850), Kiffin(1660), Kilcop(1656), Knollys(1667/1692/1646), Featley(1645), Tombes(1654), Booth(1778)
   - 연도가 미표기된 작품: Armitage, Benedict, Carroll, Cathcart, Manly, Orme, Robertson, Spurgeon Autobiography — 원본에서 추출 필요

4. **저자 표준화**
   - 동일 저자의 다수 작품이 존재하므로 저자 ID 표준화 필요
   - Knollys(4작품), Smyth(3작품), Fuller(8작품), Spurgeon(2작품)

### 9.2 Metadata Generation Not Performed

본 감사에서는 메타데이터 생성을 수행하지 않았습니다. 메타데이터 생성은 별도 작업에서 진행하십시오.

---

## 10. Recommended Next Actions

### Priority 1: early_baptist_collection 구조화 (34GB)

1. collection 내 하위 분류 (연도별, 주제별, 저자별)
2. item-level metadata 설계 및 생성
3. 대용량 처리 파이프라인 검증

### Priority 2: Church Order 자료 보강 (현재: C → 목표: B+)

1. Baptist church polity 관련 추가 자료 수집
2. 17~18세기 church government 논쟁 문서 추가
3. Philadelphia Confession(1689) 관련 church order 문서 추가

### Priority 3: Southern Baptist History 보강 (현재: C → 목표: B)

1. Boyce, Broadus, Dagg, Manly, Mullins 관련 사료 추가
2. 19세기 Southern Baptist 분리 역사 문서 추가

### Priority 4: hOCR 여부 확인

1. HTML 버전이 있는 4개 작품(Carey, Cathcart, Armitage, Judson)의 HTML이 hOCR 결과인지 확인
2. hOCR가 아니면 OCR 파이프라인에서 hOCR 생성 고려

### Priority 5: Knollys Life and Death / Autobiography 관계 확인

1. 두 파일이 동일 저작의 다른 판본인지, 다른 저작인지 확인
2. 중복일 경우 메타데이터에서 관계 명시

---

## Appendix A: Full History Work List with Details

| Work | Author | Files | Size | Format | Year |
|------|--------|-------|------|--------|------|
| Armitage_History_of_Baptists | Armitage, Joseph | 3 | 137 MB | PDF+TXT+HTML | - |
| Benedict_General_History | Benedict, George | 2 | 50 MB | PDF+TXT | - |
| Booth_Apology_for_Baptists_1778 | Booth, Charles | 2 | 101 MB | PDF+TXT | 1778 |
| Bunyan_Devotional_Works_1850 | Bunyan, John | 2 | 20 MB | PDF+TXT | 1850 |
| Bunyan_Pilgrims_Progress_1849 | Bunyan, John | 2 | 5.8 MB | PDF+TXT | 1849 |
| Carroll_Genesis_of_American_Anti-Missionism | Carroll, James P. | 2 | 10 MB | PDF+TXT | - |
| Cathcart_Baptist_Encyclopedia_Vol1 | Cathcart, William | 3 | 169 MB | PDF+TXT+HTML | - |
| Cathcart_Baptist_Encyclopedia_Vol2 | Cathcart, William | 3 | 166 MB | PDF+TXT+HTML | - |
| Clarke_Ill_Newes_from_New_England_1652 | Clarke, John | 2 | 60 MB | PDF+TXT | 1652 |
| Cox_Appendix_to_Confession_1646 | Cox, Thomas | 2 | 8.5 MB | PDF+TXT | 1646 |
| Coxe_Knollys_Kiffen_Declaration_1645 | Coxe, J. L. | 2 | 31 MB | PDF+TXT | 1645 |
| Featley_Dippers_Dipt_1645 | Featley, Daniel | 2 | 135 MB | PDF+TXT | 1645 |
| Kiffin_Humble_Apology_1660 | Kiffin, William | 2 | 19 MB | PDF+TXT | 1660 |
| Kilcop_Short_Treatise_of_Baptisme_1656 | Kilcop, John | 2 | 6.0 MB | PDF+TXT | 1656 |
| Knollys_Apocalyptical_Mysteries_1667 | Knollys, John | 2 | 33 MB | PDF+TXT | 1667 |
| Knollys_Life_and_Death_1692 | Knollys, John | 2 | 21 MB | PDF+TXT | 1692 |
| Knollys_Life_and_Death_Autobiography | Knollys, John | 2 | 13 MB | PDF+TXT | - |
| Knollys_Shining_of_a_Flaming_Fire_1646 | Knollys, John | 2 | 14 MB | PDF+TXT | 1646 |
| Manly_Mercy_and_Judgment_Charleston_Baptist_History | Manly, Henry D. | 2 | 4.4 MB | PDF+TXT | - |
| Orme_Life_of_William_Kiffin | Orme, William | 2 | 6.0 MB | PDF+TXT | - |
| Robertson_Life_and_Letters_of_Broadus | Robertson, John G. | 2 | 7.3 MB | PDF+TXT | - |
| Smyth_Paralleles_Censures_1609 | Smyth, John | 2 | 117 MB | PDF+TXT | 1609 |
| Smyth_Paterne_True_Prayer_1624 | Smyth, John | 2 | 131 MB | PDF+TXT | 1624 |
| Smyth_Principles_and_Inferences_1607 | Smyth, John | 2 | 11 MB | PDF+TXT | 1607 |
| Spurgeon_Autobiography_Vol01 | Spurgeon, Charles H. | 2 | 23 MB | PDF+TXT | - |
| Spurgeon_Autobiography_Vol02 | Spurgeon, Charles H. | 2 | 23 MB | PDF+TXT | - |
| Tombes_Anti_Paedobaptism_1654 | Tombes, Thomas | 2 | 140 MB | PDF+TXT | 1654 |
| early_baptist_collection | Multiple | 1,416 | 34 GB | PDF+TXT | - |

---

## Appendix B: Full Missions Work List with Details

| Work | Author | Files | Size | Format | Year Range |
|------|--------|-------|------|--------|------------|
| Baptist_Missionary_Magazine_1803_v1i1 | Baptist MM Society | 2 | 11 MB | PDF+TXT | 1803 |
| Baptist_Missionary_Magazine_1817_v1i1 | Baptist MM Society | 2 | 17 MB | PDF+TXT | 1817 |
| Baptist_Missionary_Magazine_1837_v17i7 | Baptist MM Society | 2 | 17 MB | PDF+TXT | 1837 |
| Baptist_Missionary_Magazine_1842_v22i1 | Baptist MM Society | 2 | 13 MB | PDF+TXT | 1842 |
| Baptist_Missionary_Magazine_1857_v37i10 | Baptist MM Society | 2 | 6.8 MB | PDF+TXT | 1857 |
| Baptist_Missionary_Magazine_1867_v47i11 | Baptist MM Society | 2 | 6.9 MB | PDF+TXT | 1867 |
| Baptist_Missionary_Magazine_1877_v57i9 | Baptist MM Society | 2 | 8.2 MB | PDF+TXT | 1877 |
| Baptist_Missionary_Magazine_1881_v61i6 | Baptist MM Society | 2 | 7.9 MB | PDF+TXT | 1881 |
| Baptist_Missionary_Magazine_1897_v77i9 | Baptist MM Society | 2 | 8.4 MB | PDF+TXT | 1897 |
| Baptist_Missionary_Magazine_1907_v87i3 | Baptist MM Society | 2 | 15 MB | PDF+TXT | 1907 |
| Carey_Enquiry | Carey, William | 3 | 78 MB | PDF+TXT+HTML | - |
| Fuller_Complete_Works_Vol01 | Fuller, Andrew | 2 | 30 MB | PDF+TXT | - |
| Fuller_Complete_Works_Vol02 | Fuller, Andrew | 2 | 26 MB | PDF+TXT | - |
| Fuller_Complete_Works_Vol03 | Fuller, Andrew | 2 | 25 MB | PDF+TXT | - |
| Fuller_Complete_Works_Vol04 | Fuller, Andrew | 2 | 31 MB | PDF+TXT | - |
| Fuller_Complete_Works_Vol05 | Fuller, Andrew | 2 | 26 MB | PDF+TXT | - |
| Fuller_Complete_Works_Vol06 | Fuller, Andrew | 2 | 23 MB | PDF+TXT | - |
| Fuller_Complete_Works_Vol07 | Fuller, Andrew | 2 | 30 MB | PDF+TXT | - |
| Fuller_Complete_Works_Vol08 | Fuller, Andrew | 2 | 35 MB | PDF+TXT | - |
| General_Baptist_Magazine_1798 | General Baptist | 2 | 142 MB | PDF+TXT | 1798 |
| General_Baptist_Magazine_1799 | General Baptist | 2 | 133 MB | PDF+TXT | 1799 |
| Judson_Life_and_Letters | Judson, Adoniram | 3 | 61 MB | PDF+TXT+HTML | - |
| Knowles_Memoir_of_Ann_Judson | Knowles, Francis | 2 | 15 MB | PDF+TXT | - |
| Wayland_Memoir_of_Judson | Wayland, Francis | 2 | 18 MB | PDF+TXT | - |

---

## Appendix C: Church Order Work List with Details

| Work | Author | Files | Size | Format |
|------|--------|-------|------|--------|
| Dagg_Church_Order | Dagg, James P. | 3 | 33 MB | PDF+TXT+metadata |
| Hiscox_Standard_Manual | Hiscox, John L. | 3 | 16 MB | PDF+TXT+metadata |

---

*Audit-002 완료. 이 보고서는 Audit-001 결과를 보완하는 Addendum입니다.*
*Full Audit은 프로젝트 아키텍트의 별도 승인 후 시작합니다.*