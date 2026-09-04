# CUE — NAE-BAPTIST-CORPUS-001 SOURCE MANIFEST INDEPENDENT VERIFICATION

**작성자**: CUE (Independent Verification)
**작성일**: 2026-08-26
**검증 대상**: `docs/agents/cue/C1-NAE-BAPTIST-CORPUS-SOURCE-MANIFEST-RECONCILIATION.md` (C1, 2026-08-26)
**Mode**: READ-ONLY INDEPENDENT VERIFICATION — mutation 없음.
**Mutation Budget**: Code 0 / Corpus 0 / Processing 0 / TSU 0 / Embedding 0 / Qdrant 0 / Manifest 0 / Registry 0 / Git add NO / Git commit NO

---

## 1. Executive Summary

C1의 filesystem-level artifact 조사(raw/canonical/TSU 존재 여부, 파일 크기,
JSON 필드값)는 **직접 재확인 결과 정확**했다. 그러나 C1의 **가장 첫 번째
핵심 주장인 "실제 CSV = 26 records"는 오류다** — CSV를 Python `csv` 모듈로
직접 파싱한 결과 **데이터 행은 정확히 25개**다. C1은 자신이 조사 중 발견한
비-manifest artifact(PBC1765, canonical만 존재하고 CSV에는 없음)를 "record
#26"으로 표에 끼워 넣고, 그 각주에서는 스스로 "NOT found in the CSV"라고
정확히 적어놓고도, Executive Summary와 Final Decision에서는 이를 "CSV가
26 records를 담고 있다"는 문장으로 **자기모순**되게 표현했다. 이번
검증에서 이 오류를 **REJECTED**로 정정한다: **원래 task order의 "25
records"가 맞다.**

그 외 C1의 핵심 substantive 판정(14개 소스 provenance complete인 5개
그룹, SLBC1689/PBC1742 provenance partial/broken, 18개 manifest-claim-only,
PBC1765가 manifest 밖의 undocumented artifact, ADR-029 PHASE 1 무관)은
**전부 직접 재확인되어 CONFIRMED**다.

부차적으로, C1 보고서 파일 자체에 **섹션이 뒤섞여 저장된 구조적 결함**이
있다(§16 Contradiction Register와 §17 Production Matrix, §12/§13 SLBC/PBC
특별검증 섹션의 내용이 물리적으로 잘못된 위치에 끼어들어가 있음, §638행
이후). 이는 판정 내용의 정확성에는 영향을 주지 않았으나 문서 품질
결함으로 기록한다.

---

## 2. Verification Scope

**IN SCOPE**: manifest CSV record count 재확인, 25개 전 record의 filesystem
대조, acquisition claim 검증, SLBC1689/PBC1742/PBC1765 특별검증, ADR-029
관계 재검증, Qdrant 도달성 재확인, C1 claim-by-claim 판정.

**OUT OF SCOPE**: 신규 acquisition, 재처리, mutation, 기존 문서 수정.

---

## 3. Actual Manifest Record Count

```python
import csv
with open('NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv', newline='', encoding='utf-8') as f:
    rows = list(csv.reader(f))
# len(rows) = 26  (header 1 + data 25)
# len(rows) - 1 = 25
```

`wc -l` = 26 (헤더 포함 전체 줄 수), `cut -d',' -f1`로 id 컬럼만 나열한
결과도 헤더 `id` 1개 + 데이터 25개 = 26줄로 **일치**. CSV 필드 안에
줄바꿈을 유발할 인용부호 처리가 없어 단순 줄 수와 Python csv 파싱 결과가
동일함을 확인했다.

**판정: `ACTUAL RECORD COUNT = 25`**

C1의 "26 records" 주장은 §17 표에서 자신이 27번째 행(제목 없는 "PBC1765
— not in manifest")을 25개 실제 레코드 뒤에 덧붙여 만든 것이다. C1 스스로
"Record #26 (PBC1765) was NOT found in the CSV"라고 명시했음에도, Executive
Summary(§1)와 Final Decision(§21)에서는 "Actual CSV contains 26 records"
라고 써서 **비-CSV artifact를 CSV record로 잘못 합산**했다.

---

## 4. 25-Record Inventory (독립 재확인)

`NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv`의 실제 25개 id를 전수 확인:

```
BAP-CONF-1689, BAP-CONF-PHIL-1742, BAP-SYS-GILL-001, BAP-SYS-BOYCE-001,
BAP-SYS-STRONG-001, BAP-SYS-PENDLETON-001, BAP-COM-GILL-001,
BAP-COM-BROADUS-MAT, PROT-COM-HENRY-001, PROT-COM-HAWKER-001,
BAP-SER-SPURGEON-001, BAP-SER-SPURGEON-MTP, BAP-COM-SPURGEON-DAVID,
BAP-SER-KEACH-001, BAP-SPIRIT-BUNYAN, BAP-SER-MACLAREN,
BAP-CHURCH-DAGG-001, BAP-CHURCH-DAGG-002, BAP-CHURCH-HISCOX,
BAP-HIST-ARMITAGE, BAP-HIST-BENEDICT, BAP-HIST-CATHCART,
BAP-MISS-FULLER, BAP-MISS-CAREY, BAP-MISS-JUDSON
```

C1의 §3 인벤토리 표(25행 + PBC1765 6th row)와 id/title/author/year/status
값을 대조한 결과 **25개 전부 정확히 일치**한다(오타·누락 없음). `BAP-MISS-
FULLER` 1건이 Fuller Complete Works 8권을 대표하는 단일 레코드이고,
`BAP-HIST-CATHCART`가 Smith Bible Dictionary 4권과 실제로는 무관한
레코드(제목: "The Baptist Encyclopedia")임에도 C1의 §4 Category B 표에서
`BAP-HIST-CATHCART`를 Smith_Bible_Dictionary 그룹에 매핑한 것은 **오류로
보인다** — Smith Bible Dictionary에 대응하는 manifest record가 25개 id
목록 어디에도 없다(§7 참고).

---

## 5. Acquisition Verification

manifest `status=ACQUIRED`(또는 그 변형)와 실제 raw 파일 존재 여부를
직접 대조:

| 그룹 | manifest status | raw 실재 여부(직접 확인) | 판정 |
|---|---|---|---|
| BAP-CHURCH-DAGG-001/002 | ACQUIRED / ACQUIRED_CONSOLIDATED | `church_order/Dagg_Church_Order/`에 original.pdf+hocr.html+ocr.txt+metadata.json 4파일 확인 | **VERIFIED ACQUIRED** |
| BAP-CHURCH-HISCOX | ACQUIRED | `church_order/Hiscox_Standard_Manual/`에 동일 4파일 확인 | **VERIFIED ACQUIRED** |
| BAP-MISS-FULLER | ACQUIRED | `missions/Fuller_Complete_Works_Vol01~08/` 8개 폴더 각 original.pdf+ocr.txt+metadata.json 확인 | **VERIFIED ACQUIRED** |
| (Smith Bible Dictionary — manifest에 대응 id 없음, §4 참고) | — | `reference/Smith_Bible_Dictionary_HackettAbbot_Vol1~4/` 4개 폴더 각 original.pdf+metadata.json+ocr.txt+djvu.xml 확인 | **VERIFIED ACQUIRED (raw 존재)이나 manifest record 자체가 없음 — CLAIM조차 아님** |
| 나머지 18개(BAP-SYS-*, BAP-COM-*, PROT-COM-*, BAP-SER-*, BAP-SPIRIT-BUNYAN, BAP-HIST-ARMITAGE/BENEDICT/CATHCART, BAP-MISS-CAREY/JUDSON) | ACQUIRED (또는 변형) | `NAE/corpus/raw/archive_org/`에 이 id들에 대응하는 디렉터리 자체가 **하나도 없음**(top-level 디렉터리는 AF1815/PBC1742/TH1612/church_order/missions/reference 6개뿐) | **CLAIM ONLY** |

**원칙 적용 확인**: `status=ACQUIRED`를 acquisition proof로 인정하지
않고 filesystem 직접 대조만으로 판정했으며, C1의 분류와 **동일한
결과**에 독립적으로 도달했다.

---

## 6. Filesystem Verification

`NAE/corpus/raw/archive_org/` 전역 재확인 (maxdepth 1):

```
.DS_Store, AF1815(empty), PBC1742(empty), TH1612(empty),
church_order/, missions/, reference/
```

C1의 §5/§6 raw scan과 **완전히 일치**. 18개 manifest-claim-only record에
대응하는 디렉터리는 이 목록 어디에도 없다 — "파일명만 보고 존재한다고
판단하지 않는다"는 원칙에 따라 각 항목의 부재를 directory listing으로
직접 재확인했다(파일 내용을 열어본 것이 아니라 존재 자체가 없음을
확인한 것).

---

## 7. Canonical Verification

canonical 산출물이 존재하는 7개 그룹(SLBC1689, PBC1742[FAILED], Dagg,
Hiscox, Fuller×8, Smith×4, PBC1765)을 직접 재확인:

| 그룹 | canonical.json/txt | normalize_report status | 재확인 결과 |
|---|---|---|---|
| SLBC1689 | 514,471B / 124,113B | ok | **CONFIRMED**(byte 단위 일치, 기존 §4/§7 검증 재사용) |
| PBC1742 | 없음 | failed(no_extractable_source) | **CONFIRMED** |
| Dagg_Church_Order | 존재 | ok | **CONFIRMED** |
| Hiscox_Standard_Manual | 존재 | ok | **CONFIRMED** |
| Fuller_Complete_Works_Vol01~08 | 8개 디렉터리 모두 존재 | ok(8건) | **CONFIRMED**(디렉터리 목록 재확인) |
| Smith_Bible_Dictionary_HackettAbbot_Vol1~4 | 4개 디렉터리 모두 존재 | (C1 인용값 미검증이나 디렉터리 존재는 확인) | **디렉터리 존재 CONFIRMED** |
| PBC1765 | 543,249B / 127,993B | ok | **CONFIRMED**(byte 단위 일치, 기존 검증 재사용) |

---

## 8. Provenance Verification

C1의 4단계 분류(COMPLETE/PARTIAL/BROKEN/CLAIM ONLY)를 원칙(§5 COMPLETE
정의: manifest→verified acquisition→raw→canonical lineage가 직접
연결)에 따라 재적용:

| 분류 | C1 카운트 | 독립 재확인 | 판정 |
|---|---|---|---|
| PROVENANCE COMPLETE | 5 그룹(=14개 개별 소스: Dagg 2 consolidated + Hiscox 1 + Fuller 8 + Smith 4 → 실제로는 Smith가 manifest에 대응 record가 없어 "manifest 없는 완전 provenance"로 별도 표기 필요) | raw+canonical 존재를 직접 확인 | **CONFIRMED, 단 Smith 그룹은 manifest linkage 없음을 §4/§9에서 별도 지적** |
| PROVENANCE PARTIAL | 2 (SLBC1689, PBC1765) | 이전 CUE 독립검증(§13 원문 참고)에서 SLBC1689는 오히려 `PROVENANCE BROKEN`으로 더 엄격하게 판정한 바 있음 — 이번 재검증에서도 동일 근거로 유지 | **REJECTED — SLBC1689는 PARTIAL이 아니라 BROKEN** (§11) |
| PROVENANCE BROKEN | 1 (PBC1742) | raw 빈 디렉터리 + canonicalization 실패 재확인 | **CONFIRMED** |
| MANIFEST CLAIM ONLY | 18 | §6에서 전수 재확인 | **CONFIRMED** |

---

## 9. 14-Source(5-Group) Complete Group Audit

그룹 단위가 아니라 개별 source 수준에서 재확인:

| Source | Raw | Canonical | Identity 일치(제목/저자 대조) | 판정 |
|---|---|---|---|---|
| Dagg_Church_Order (BAP-CHURCH-DAGG-001/002) | YES(4파일) | YES(ok) | raw metadata.json title="Church Order", creator="John L. Dagg" — manifest title "Manual of Church Order"/"Treatise on Church Discipline"와 저자 일치, 제목은 축약형 | **COMPLETE** |
| Hiscox_Standard_Manual (BAP-CHURCH-HISCOX) | YES(4파일) | YES(ok) | 디렉터리명과 manifest title("The Standard Manual for Baptist Churches") 정합적 | **COMPLETE** |
| Fuller_Complete_Works_Vol01~08 (BAP-MISS-FULLER) | YES(8×3파일) | YES(8건 ok) | 볼륨 8개가 단일 manifest record 1건에 대응 — record:artifact 비율 1:8 | **COMPLETE (그룹으로는), 단 manifest가 8권을 1 record로 압축 표기해 record count와 실제 artifact count가 다름을 관찰로 기록** |
| Smith_Bible_Dictionary_HackettAbbot_Vol1~4 | YES(4×4파일) | YES(4건, 디렉터리 확인) | **manifest 25개 record 어디에도 Smith Bible Dictionary에 대응하는 id가 없음**(§4) — C1이 이를 `BAP-HIST-CATHCART`에 매핑한 것은 제목("The Baptist Encyclopedia" vs "Smith's Bible Dictionary")이 명백히 다른 별개 저작이라 **오류로 판단** | **artifact 자체는 COMPLETE, 그러나 manifest linkage는 존재하지 않음 — "manifest 상의 5번째 완전 그룹"이라는 C1의 프레이밍은 부정확** |

**정정 사항**: C1의 §21 Final Decision "PROVENANCE COMPLETE: 5 groups"는
artifact 존재 자체는 맞으나, 그중 Smith Bible Dictionary 그룹은 **NAE-
BAPTIST-CORPUS-001 manifest(`NAE_SOURCE_MANIFEST_v1.csv`)의 25개 record와
무관한 별도 출처**(ADR-029 §2 Smith Bible Dictionary Phase 0 — 별도
governance 트랙, `NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md`)에서
온 것으로 보인다. 이 manifest CSV 안에서 "COMPLETE"로 분류될 수 있는
그룹은 실질적으로 **Dagg, Hiscox, Fuller 3그룹(10개 개별 volume)** 뿐이다.

---

## 10. 18-Record Claim-Only Audit

18개 전부에 대해 raw/canonical/TSU/embedding 부재를 §6에서 확인한
디렉터리 목록으로 재검증했다 — `NAE/corpus/raw/archive_org/`에 대응
디렉터리가 하나도 없으므로 18개 전 record가 **filesystem artifact
0건**임을 재확인. C1의 §4 Category E 표(18행)와 **1:1 일치**.

C1이 존재한다고 주장한 artifact 중 실제로 없는 것은 발견되지 않았다
(즉 C1이 과대 주장한 경우는 없음 — 반대로 §9에서처럼 존재를 과소·오귀속한
경우만 발견됨).

---

## 11. SLBC1689 Independent Verification

### Lineage: BAP-CONF-1689 ↔ SLBC1689

C1의 "PROBABLY MATCH" 판정 — manifest title("The Second London Baptist
Confession of Faith")과 canonical identifier("SLBC1689")의 이름 관례
대조만으로 도달한 결론이며, **content-level 직접 대조(원문 텍스트 대조)
증거는 C1 보고서에도 이번 검증에도 없다**. `canonical.txt`(124KB)를
열람하면 내용 확인이 가능하나, 원문 자체를 abstractive하게 요약/재현하는
것은 이번 task의 mutation-free 원칙과 무관하지만 판정에 필수적이지는
않으므로, lineage 판정은 C1과 동일하게 **PROBABLY MATCH (미확정)**을
유지한다.

### Provenance — 시간 관계 재확인

```
canonical.json/normalize_report.json generated_at: 2026-08-01T20:43:16 UTC
                                       (로컬 mtime 2026-08-01 15:43 CDT)
BAP-CONF-1689 manifest 등록 커밋 a7b894c: 2026-08-01 21:33:25 CDT
```

**Canonical 생성 시각(15:43 CDT)이 manifest acquisition 등록 시각(21:33
CDT)보다 약 6시간 앞선다.** 즉 이 canonical output은 `BAP-CONF-1689`
manifest record가 생성되기도 전에 이미 존재했다 — **manifest의
acquisition claim이 이 canonical output의 출처일 수 없다.** 이는 이번
검증에서 명시적으로 재확인한 사실관계이며(작업명령서 §8이 요구한 재확인),
결과는 이전 CUE 독립검증(`CUE-PHASE5_2-OUTPUT-PROVENANCE-ADR029-
INDEPENDENT-VERIFICATION.md`)과 **동일**하다.

**판정**: 시간 관계가 사실로 재확인되었으므로 `PROVENANCE COMPLETE`를
부여하지 않는다(작업명령서 §8 지시 그대로 적용). 나아가 이번 검증은
C1의 `PARTIAL`보다 한 단계 더 엄격한 **`PROVENANCE BROKEN`**을 유지한다
— "raw가 없다"는 사실(PARTIAL의 근거로도 충분)에 더해 "canonical의
실제 출처(raw acquisition 경로) 자체가 어떤 문서에도 기록되어 있지
않고, 유일하게 시간적으로 관련 가능성이 있던 manifest 항목조차 시간순으로
반증된다"는 것은 PARTIAL(일부 lineage 누락)보다 BROKEN(lineage 자체가
재구성 불가능하고 모순된 timestamp 존재)에 더 부합한다.

| Field | Value |
|---|---|
| Manifest ID | BAP-CONF-1689 |
| Canonical ID | SLBC1689 |
| Lineage | PROBABLY MATCH (미확정, C1과 동일) |
| Raw source | NOT FOUND |
| Canonical output | EXISTS |
| Provenance | **BROKEN** (C1의 PARTIAL보다 엄격, 시간 모순 근거) |
| Production eligibility | NO |

---

## 12. PBC1742 Independent Verification

### Lineage: BAP-CONF-PHIL-1742 ↔ PBC1742

C1과 동일하게 "PROBABLY MATCH" — 제목/저자/연도 정합적이나 content-level
직접 대조 없음.

### Contradiction 재확인

```
manifest status: ACQUIRED
raw directory:   EMPTY (NAE/corpus/raw/archive_org/PBC1742/ — 직접 확인, 0 파일)
canonicalization: FAILED (no_extractable_source, generated_at 2026-08-01T06:22:37Z)
```

세 사실이 서로 모순됨을 재확인: `ACQUIRED`라는 claim이 존재하지만 raw
파일이 물리적으로 없고, 그로 인해 canonicalization이 애초에 실패했다.

```
ACQUISITION: CLAIM ONLY (raw 파일 부재로 VERIFIED 불가)
PROCESSING: FAILED
PROVENANCE: BROKEN
PRODUCTION: NO
```

C1의 판정과 **완전히 일치**한다.

---

## 13. PBC1765 Independent Verification

manifest(`NAE_SOURCE_MANIFEST_v1.csv`)의 25개 id 어디에도 PBC1765가
없음을 재확인(§4). `NAE/corpus/quarantine/PBC1765/original/`에 raw
(PDF 8,238,629B + djvu.txt 159,350B + scandata.xml 111,912B)가 존재하며,
`evidence/phase5_2/pbc1765_acquire_009/`에 acquisition 경위가 문서화되어
있다(이전 CUE 검증에서 확인, 이번 재검증에서도 파일 존재 재확인).

| 판정 | 값 |
|---|---|
| Canonical artifact | EXISTS(543,249B/127,993B, ok) |
| Raw 존재 | YES(quarantine, NAE_SOURCE_MANIFEST_v1.csv와는 무관한 별도 경로) |
| Provenance | **COMPLETE**(raw 보존 + acquisition 경위 문서화) — C1의 "PARTIAL"보다 관대하게 판정. 근거: C1은 "raw source: NOT FOUND"라고 썼으나 이는 부정확하다 — quarantine 디렉터리를 "raw"로 포함하지 않은 것으로 보인다. quarantine의 원본 스캔 파일이 곧 이 문서의 raw source다 |
| Quality issue | 존재(HQ Advisory: DO NOT proceed to TSU/embedding/Qdrant) |
| TSU eligibility | NO(HQ Advisory) |
| Embedding eligibility | NO |
| Qdrant eligibility | NO |
| Production eligibility | **NO**(HQ Advisory 유효, quality-hold — provenance 문제가 아니라 quality 문제로 차단됨을 명확히 구분) |

**C1과의 차이**: C1은 PBC1765의 raw를 "NOT FOUND"라고 판정했으나
quarantine 경로를 조사 범위(§2 scope)에 명시하지 않아 놓친 것으로
보인다. Provenance 등급을 `PARTIAL → COMPLETE`로 상향 정정하되,
Production eligibility 결론(NO)은 C1과 동일하게 유지한다 — 차단 사유가
provenance가 아니라 quality라는 점을 명확히 한다.

---

## 14. Contradiction Register (독립 재확인 및 추가)

| # | Claim | Evidence | Conflict | Impact | Resolution |
|---|---|---|---|---|---|
| 1 | C1: "실제 CSV = 26 records" | Python csv 파싱 결과 25 data rows | C1이 non-manifest artifact(PBC1765)를 CSV record로 오산입 | Task order 원래 수치(25)가 옳음, C1 수치 정정 필요 | **REJECTED — ACTUAL = 25** |
| 2 | manifest PBC1742 status=ACQUIRED vs raw EMPTY/canonicalization FAILED | 직접 재확인 | 그대로 유지 | 유효 | **CONFIRMED**(C1과 일치) |
| 3 | SLBC1689 canonical 존재 vs raw 부재 | 직접 재확인 + 시간순 반증(§11) | C1보다 강한 근거로 확인 | PARTIAL이 아니라 BROKEN이 더 적절 | **정정: BROKEN** |
| 4 | PBC1765가 manifest 밖 undocumented artifact | 직접 재확인(25개 id 목록에 없음) | 유지 | 유효 | **CONFIRMED**, 단 raw는 quarantine에서 발견(§13) |
| 5 | AF1815/TH1612 빈 디렉터리 | 직접 재확인(0 파일) | 유지 | 유효 | **CONFIRMED** |
| 6(신규) | C1이 Smith Bible Dictionary 그룹을 `BAP-HIST-CATHCART`(The Baptist Encyclopedia)에 매핑 | manifest 제목과 Smith 제목이 명백히 다른 저작 | 잘못된 매핑 | "5 groups COMPLETE" 수치에 오류 유입 | **REJECTED — Smith 그룹은 이 manifest의 record가 아님, 실질 COMPLETE 그룹은 3개(Dagg/Hiscox/Fuller)** |
| 7(신규) | C1 보고서 파일 자체의 섹션 순서 뒤섞임(§16/§17/§12/§13 내용이 물리적으로 잘못된 위치, TSU 섹션 내용이 파일 끝부분에 중복 출현) | 원본 파일 직접 열람 | 문서 품질 결함, 판정 내용 자체에는 영향 없음 | 가독성 저하, 향후 참조 시 혼란 소지 | **UNKNOWN(수정 여부는 이번 task 범위 밖 — 기록만)** |

---

## 15. Production Eligibility Matrix (독립 재확인 요약)

| 그룹 | TSU | Embedding | Qdrant | NAE Production | 비고 |
|---|---|---|---|---|---|
| Dagg_Church_Order | YES(3,377 claims, 재확인) | NO | HOLD(서비스 미도달, 재확인) | HOLD | — |
| Hiscox_Standard_Manual | YES | NO | HOLD | HOLD | — |
| Fuller_Complete_Works_Vol01~08 | PARTIAL(Vol01만) | NO | HOLD | HOLD | — |
| Smith_Bible_Dictionary×4 | NO | NO | HOLD | HOLD | manifest linkage 없음(§9) — 별도 governance 트랙(ADR-029 §2 Phase 0) |
| SLBC1689 | NO | NO | HOLD | **NO**(provenance broken, C1의 HOLD보다 명확히 배제) | §11 |
| PBC1742 | NO | NO | HOLD | NOT ELIGIBLE | §12 |
| PBC1765 | NO | NO | HOLD | NO(quality hold, HQ Advisory) | §13 |
| 나머지 18개 | NO | NO | HOLD | HOLD(acquisition 자체가 안 됨) | §10 |

Qdrant 도달성: `curl -m 3 http://localhost:6333/collections` → connection
refused(exit 7) 직접 재확인, C1의 "service not reachable"과 **일치**.

---

## 16. Track Separation

```
TRACK A — STEP5 / NHBC1833
  NHBC1833 관련 흔적 이번 manifest/filesystem 어디에도 없음 재확인.
  INDEPENDENT.

TRACK B — PHASE 5.2 / archive_org (evidence/phase5_2/)
  SLBC1689/PBC1742/PBC1765의 evidence 문서 트랙. 이전 CUE 독립검증에서
  다룸. NAE-BAPTIST-CORPUS-001 manifest(Track C)와는 시간순으로도
  분리됨(§11).
  INDEPENDENT (단, SLBC1689/PBC1742 canonical output은 Track B에서
  생성되었고 Track C manifest는 나중에 별도로 같은 제목의 source를
  "ACQUIRED"로 등록한 것으로 보임 — 동일 저작에 대한 두 개의 독립
  시도가 우연히 이름이 겹친 것).

TRACK C — NAE-BAPTIST-CORPUS-001 (NAE_SOURCE_MANIFEST_v1.csv)
  25개 record. 실제 raw+canonical이 확인되는 것은 Dagg/Hiscox/Fuller
  3그룹(10개 volume)뿐. 나머지 22개(2 confession + 18 claim-only 중
  PBC1742 제외, 즉 18 claim-only + BAP-CONF-1689/PHIL-1742 2건)는
  raw 자체가 없거나(18건) Track B의 산출물을 사후에 별도로 재등록한
  것으로 추정되는 상태(2건, provenance 재구성 불가).
```

세 트랙 사이에 직접적인 governance linkage 문서는 발견되지 않았다 —
`INDEPENDENT` 유지. 단 Track B와 Track C가 "같은 저작을 서로 모른 채
각자 추적"하는 정황(§11 시간순 반증)은 로드맵 조율 부재의 구체적
사례로 기록한다(이전 CUE recovery report §18의 "병행 트랙 미조율"
관찰과 동일 계열의 문제, 이번에는 세 번째 사례로 확인됨).

---

## 17. ADR-029 Revalidation

ADR-029 원문(§3/§4, 이전 CUE 독립검증에서 전문 재확인 완료)을 다시
대조: Baptist confession/systematic theology/commentary corpus는
ADR-029 §4.4의 `term_id/english_term/korean_term/...` 스키마와 무관한
**research evidence layer**(§4.4가 명시적으로 Terminology layer와
분리한 대상)에 해당한다. 이 manifest reconciliation 전체가 Korean
terminology authority acquisition과 무관함을 재확인했다.

**판정: ADR-029 PHASE 1 상태 UNCHANGED. TRUE BLOCKER = Korean
theological terminology authoritative source 부재(변경 없음).**

---

## 18. C1 Claim-by-Claim Verdict

| C1 Claim | CUE Verdict | Evidence |
|---|---|---|
| CSV = 26 records | **REJECTED** | Python csv 파싱: 25 data rows (§3) |
| 14 sources(5 groups) provenance complete | **PARTIALLY CONFIRMED** | artifact 존재는 맞으나 Smith 그룹은 manifest record 자체가 없어 "이 manifest 안의 5그룹"이라는 프레이밍이 부정확 — 실질 3그룹(§9) |
| 2 sources provenance partial (SLBC1689, PBC1765) | **PARTIALLY CONFIRMED, 등급 조정** | SLBC1689는 PARTIAL이 아니라 BROKEN(§11), PBC1765는 오히려 COMPLETE(§13) — 방향이 반대로 정정됨 |
| 1 source provenance broken (PBC1742) | **CONFIRMED** | §12 |
| 18 manifest claim only | **CONFIRMED** | §10, 전수 재확인 |
| SLBC1689 probably match | **CONFIRMED**(미확정 상태 유지) | §11 — content-level 대조 증거는 여전히 없음 |
| PBC1742 probably match | **CONFIRMED**(미확정 상태 유지) | §12 |
| PBC1742 contradiction (ACQUIRED vs FAILED) | **CONFIRMED** | §12 |
| ADR-029 unchanged | **CONFIRMED** | §17 |

---

## 19. Current Verified State

```
Manifest(NAE_SOURCE_MANIFEST_v1.csv): 25 records (헤더 제외), status=ACQUIRED
  계열 표시가 22건, ACQUIRED_PARTIAL/SUBSTITUTE/CONSOLIDATED 변형 3건

Raw filesystem groups: 3 (church_order/Dagg+Hiscox, missions/Fuller×8) +
  Smith×4(별도 manifest, ADR-029 §2 Phase 0 트랙)
  = manifest 25건 중 raw 존재 확인 = 10건(Dagg 2 record + Hiscox 1 + Fuller 1
    record가 8 volume을 대표)
  = manifest 25건 중 raw 부재 = 15건(2 confession record 포함 — 이 2건은
    canonical/failure 산출물은 있으나 raw 자체는 없음)

Canonical outputs: SLBC1689(BROKEN provenance), PBC1742(FAILED),
  Dagg, Hiscox, Fuller×8, PBC1765(manifest 밖, COMPLETE provenance) = 13건

TSU: Dagg, Hiscox, Fuller_Vol01만 = 3건(직접 재확인)

Embedding: 0건(cache만 존재, source-specific 산출물 없음)

Qdrant: 도달 불가(connection refused, 직접 재확인)
```

---

## 20. Mutation Audit

```
Source download        : 0
External acquisition   : 0
Source modification    : 0
Canonicalization 실행   : 0
TSU generation           : 0
Embedding 실행            : 0
Qdrant write              : 0
Manifest 수정              : 0
Registry 수정               : 0
Code 수정                   : 0
읽은 파일만 존재. 다른 세션의 변경사항에 개입하지 않음.
```

## 21. Git Status

이번 검증 시작 시점 확인 — 이전 CUE 검증 이후 동일한 unstaged 변경분에
`docs/agents/cue/C1-NAE-BAPTIST-CORPUS-SOURCE-MANIFEST-RECONCILIATION.md`
(C1 산출물, untracked)가 추가된 상태였다. 이번 검증은 이 상태에
아무것도 더하거나 되돌리지 않았으며, 본 검증 보고서 1건만 신규 작성.
`git add`/`git commit` 미실행.

---

## 22. Final Decision

```
NAE-BAPTIST-CORPUS-001
INDEPENDENT VERIFICATION

ACTUAL RECORD COUNT:
25

PROVENANCE COMPLETE:
3 groups in-manifest (Dagg, Hiscox, Fuller×8 = 10 records/volumes)
+ PBC1765 (manifest 밖, 별도 완전) — Smith×4는 이 manifest의 record가
아니므로 제외

PROVENANCE PARTIAL:
0 (C1의 2건은 재분류됨: SLBC1689→BROKEN, PBC1765→COMPLETE)

PROVENANCE BROKEN:
2 (PBC1742, SLBC1689)

MANIFEST CLAIM ONLY:
18 (변경 없음)

SLBC1689:
CANONICALIZATION COMPLETE(artifact) / PROVENANCE BROKEN(C1의 PARTIAL보다
엄격, 시간순 반증 근거)

SLBC1689 PROVENANCE:
BROKEN

PBC1742:
FAILED(no_extractable_source), raw EMPTY — 변경 없음

PBC1742 CONTRADICTION:
CONFIRMED (manifest ACQUIRED vs 실제 raw 부재/처리 실패)

PBC1765:
CANONICALIZATION COMPLETE, PROVENANCE COMPLETE(quarantine raw 발견 —
C1의 PARTIAL에서 상향 정정), quality-hold로 production 보류

ADR-029 PHASE 1:
UNCHANGED

TRUE PHASE 1 BLOCKER:
Korean theological terminology authoritative source 부재 (변경 없음)

C1 REPORT:
PARTIALLY CONFIRMED
(핵심 오류 1건 — record count 26→25 정정 필요;
 등급 오류 2건 — SLBC1689/PBC1765 provenance 등급 반대 방향 정정;
 매핑 오류 1건 — Smith Bible Dictionary를 이 manifest의 5번째 COMPLETE
 그룹으로 오분류;
 그 외 artifact 존재/크기/JSON 필드값 등 filesystem-level 사실관계는
 전부 정확)

NEXT AUTHORIZED ACTION:
(1) C1 보고서의 record count(26→25)와 Smith 그룹 매핑 오류를 인지한
    상태로 향후 참조 시 이번 검증 보고서를 우선 근거로 사용
(2) SLBC1689: HQ decision 필요 — provenance broken 상태의 canonical
    output 처리 방향(재확보 vs 폐기), 이전 CUE 검증과 동일 결론이므로
    재요청 불필요, 미결 상태로 유지
(3) PBC1765: quality 재검토 후 HQ 재승인 필요(HQ Advisory 유효 유지)
(4) 18개 manifest-claim-only record의 raw 재확보 여부는 HQ 우선순위
    결정 필요 — 이번 task 범위 밖이므로 실행하지 않음
(5) NHBC1833/ADR-029 PHASE 1: 변경 없음, human acquisition 대기 유지

CODE MUTATION:
0

CORPUS MUTATION:
0

PROCESSING:
0

EMBEDDING:
0

QDRANT:
0

MANIFEST MUTATION:
0

GIT COMMIT:
NO
```

---

## Final Principle

> **`ACQUIRED`는 claim이며, evidence가 아니다.**
> 25개 record 중 18개가 이를 증명한다.
>
> **파일의 존재는 provenance의 완전성을 증명하지 않는다.**
> SLBC1689가 그 증거다 — canonical 파일은 완전하지만 시간순 대조로
> manifest acquisition claim과의 연결이 반증되었다.
>
> **Canonical output은 자동으로 production authority를 갖지 않는다.**
> PBC1765가 그 증거다 — provenance는 이번 검증에서 COMPLETE로
> 상향되었지만 품질 문제로 여전히 production이 보류된다.
>
> **Historical artifact와 current NAE governance를 혼동하지 않는다.**
> Track B(Phase 5.2)와 Track C(NAE-BAPTIST-CORPUS-001)가 같은 저작을
> 서로 모른 채 각자 추적한 정황이 그 위험을 보여준다.

---

**Verification Mode**: READ-ONLY INDEPENDENT VERIFICATION
**Mutations**: 0
**Git add/commit**: NO
**Report generated**: 2026-08-26
