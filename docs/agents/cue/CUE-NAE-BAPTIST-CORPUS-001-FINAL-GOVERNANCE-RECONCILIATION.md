# CUE — NAE-BAPTIST-CORPUS-001 FINAL GOVERNANCE RECONCILIATION

**작성자**: CUE
**작성일**: 2026-08-26
**통합 대상**:
1. `docs/agents/cue/C1-NAE-BAPTIST-CORPUS-SOURCE-MANIFEST-RECONCILIATION.md` (C1)
2. `docs/agents/cue/CUE-NAE-BAPTIST-CORPUS-001-26-RECORD-INDEPENDENT-VERIFICATION.md` (CUE)
3. `docs/agents/cue/CUE-PHASE5_2-OUTPUT-PROVENANCE-ADR029-INDEPENDENT-VERIFICATION.md` (CUE, 선행 검증)
4. `docs/agents/cue/CUE-THEOLOGY-CORPUS-RESUME-POINT-RECOVERY.md` (CUE, 최초 recovery)

**Mode**: 신규 조사 없음 — 기존 3건의 독립 검증 결과를 하나의 authoritative
governance state로 고정하는 통합 문서.
**Mutation Budget**: Code 0 / Corpus 0 / Processing 0 / TSU 0 / Embedding 0 / Qdrant 0 / Manifest 0 / Registry 0 / Git add NO / Git commit NO

---

## 1. Executive Summary

`NAE_SOURCE_MANIFEST_v1.csv`(NAE-BAPTIST-CORPUS-001 batch)는 **25개
데이터 record**를 담고 있다. 이 중 실제 filesystem evidence로 뒷받침되는
것은 **4개 record(Dagg×2, Hiscox×1, Fuller×1 — 실질 3개 저작 그룹, raw+
canonical 존재)**뿐이며, **2개 record(BAP-CONF-1689/SLBC1689,
BAP-CONF-PHIL-1742/PBC1742)는 provenance가 깨져 있고**, 나머지
**19개 record는 manifest claim만 있을 뿐 filesystem에 어떤 흔적도
없다.** 이 manifest와 별개로 `NAE/corpus/quarantine/PBC1765/`에는
이 manifest에 등록되지 않은 완전한 provenance를 가진 canonical output이
존재한다.

**NHBC1833은 이번 reconciliation과 완전히 무관하며 `WAITING_FOR_SOURCE`
상태를 그대로 유지한다.** ADR-029 PHASE 1의 TRUE BLOCKER(Korean
theological terminology authoritative source 부재) 역시 변경되지 않는다.

---

## 2. Governing Evidence

우선순위(작업명령서 §1)에 따라 직접 재확인한 evidence만 authoritative로
채택한다. Prior agent report(C1)의 결론 중 direct filesystem evidence와
충돌하는 부분은 CUE의 두 차례 독립검증에서 이미 정정되었으며, 이 문서는
그 정정을 최종안으로 고정한다.

| Evidence 종류 | 소스 | 신뢰도 |
|---|---|---|
| Direct filesystem scan (`find`, `ls`, `stat`) | 이번 및 선행 CUE 검증 | 최상 |
| Direct manifest parsing (Python `csv`) | 이번 및 선행 CUE 검증 | 최상 |
| JSON 필드값 직접 열람(`normalize_report.json` 등) | 이번 및 선행 CUE 검증 | 최상 |
| Git log/show 직접 실행 | 선행 CUE 검증 | 최상 |
| Historical evidence 문서(`evidence/phase5_2/`) | 선행 CUE 검증에서 대조 | 중(문서 자체가 사후 미갱신 사례 존재 확인됨) |
| C1 보고서 | 참고, 상충 시 하위 | 부분 정정됨(§4, §11 참고) |

---

## 3. Manifest Record Count

```python
import csv
rows = list(csv.reader(open('NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv',
                             newline='', encoding='utf-8')))
len(rows)      # 26 (header 포함)
len(rows) - 1  # 25 (data record)
```

**HEADER ≠ RECORD 원칙 적용 결과: `DATA RECORD COUNT = 25`** (헤더
`id,title,author,year,category,source_url,archive_identifier,license,
file_format,sha256,status` 1행 + 데이터 25행). `wc -l`(26) 및
`cut -d',' -f1`로 나열한 id 목록(헤더 1개 + 25개)과도 100% 일치. CSV
필드 내 개행을 유발하는 quoting이 없어 단순 줄 수 계산과 Python csv
파싱 결과가 동일함을 재확인했다.

**PBC1765는 이 CSV의 record가 아니다** — 25개 id 목록 전수 재확인 결과
`PBC1765`라는 문자열은 `NAE_SOURCE_MANIFEST_v1.csv`에 존재하지 않는다.
이는 `NAE/corpus/canonical/PBC1765/`, `NAE/corpus/quarantine/PBC1765/`
경로에만 존재하는 **별도 filesystem artifact**이며, 이번 governance
matrix(§14)에서는 manifest 25건과 분리된 "부록 항목"으로 별도 표기한다.

**확정: 25 records.**

---

## 4. Final 25-Record Inventory

manifest의 25개 id를 그대로 나열(§3의 CSV 파싱 순서, 원본 순서 유지):

```
1  BAP-CONF-1689         11 BAP-SER-SPURGEON-001    21 BAP-HIST-BENEDICT
2  BAP-CONF-PHIL-1742    12 BAP-SER-SPURGEON-MTP    22 BAP-HIST-CATHCART
3  BAP-SYS-GILL-001       13 BAP-COM-SPURGEON-DAVID  23 BAP-MISS-FULLER
4  BAP-SYS-BOYCE-001      14 BAP-SER-KEACH-001       24 BAP-MISS-CAREY
5  BAP-SYS-STRONG-001     15 BAP-SPIRIT-BUNYAN       25 BAP-MISS-JUDSON
6  BAP-SYS-PENDLETON-001  16 BAP-SER-MACLAREN
7  BAP-COM-GILL-001       17 BAP-CHURCH-DAGG-001
8  BAP-COM-BROADUS-MAT    18 BAP-CHURCH-DAGG-002
9  PROT-COM-HENRY-001     19 BAP-CHURCH-HISCOX
10 PROT-COM-HAWKER-001    20 BAP-HIST-ARMITAGE
```

---

## 5. Acquisition Verification

`status` 필드 값과 실제 raw 파일 존재를 직접 대조(원칙: `ACQUIRED`
claim 자체는 증거로 인정하지 않음):

- **raw 실제 존재 확인된 id**: `BAP-CHURCH-DAGG-001`/`-002`(church_order/
  Dagg_Church_Order/ 4파일), `BAP-CHURCH-HISCOX`(church_order/
  Hiscox_Standard_Manual/ 4파일), `BAP-MISS-FULLER`(missions/
  Fuller_Complete_Works_Vol01~08/ 각 3파일×8)
- **raw 부재이나 canonical/failure 산출물 존재**: `BAP-CONF-1689`
  (SLBC1689 canonical 존재, raw 없음), `BAP-CONF-PHIL-1742`(raw 디렉터리
  존재하나 0파일, canonicalization FAILED)
- **raw/canonical 모두 부재(19건)**: 나머지 전부

---

## 6. Artifact Verification

`NAE/corpus/raw/archive_org/` top-level 실제 디렉터리(재확인):
`AF1815`(empty), `PBC1742`(empty), `TH1612`(empty), `church_order/`,
`missions/`, `reference/` — 이 6개 뿐. 25개 manifest id 중 이 목록의
하위에 실제로 대응하는 것은 `church_order/`(Dagg, Hiscox)와
`missions/`(Fuller×8) 뿐이다. `reference/`(Smith Bible Dictionary×4)는
**이 manifest의 25개 id 어디와도 대응하지 않는다**(§8).

---

## 7. Provenance Classification (기준 확정)

```
COMPLETE   : Acquisition evidence → Raw source → Canonical artifact
             의 lineage가 실제 evidence로 연결됨
PARTIAL    : lineage 일부만 확인, 전체 연결 미증명
BROKEN     : timestamp/checksum/identity/source lineage 등에서
             직접적 모순 존재
CLAIM ONLY : manifest claim은 있으나 supporting artifact/evidence 없음
```

이 기준으로 25개 record + 부록 1건(PBC1765)을 전수 재분류한다.

---

## 8. SLBC1689 Final State

```
Manifest record : BAP-CONF-1689 (status: ACQUIRED)
Canonical ID     : SLBC1689
Lineage          : PROBABLY MATCH (제목/저자/연도 정합적, content-level
                   직접 대조 증거 없음 — 미확정 상태 유지)
Raw source        : NOT FOUND (NAE/corpus/raw/archive_org/에 SLBC1689/
                   BAP-CONF-1689 대응 디렉터리 없음, git에도 없음)
Canonical artifact : EXISTS — canonical.json 514,471B, canonical.txt
                   124,113B, normalize_report.json status="ok",
                   157 pages, 1,202 paragraphs (직접 재확인, byte 단위
                   일치)
Timestamp 모순      : canonical 생성(2026-08-01 15:43 CDT / 20:43:16 UTC)
                   이 manifest record 등록 커밋 a7b894c(2026-08-01
                   21:33:25 CDT)보다 약 6시간 앞선다 — 이 canonical이
                   BAP-CONF-1689 manifest acquisition의 산출물일 수
                   없음을 시간순으로 직접 반증(재확인 완료)
```

**FINAL STATE: `SLBC1689 PROVENANCE = BROKEN`** (canonical artifact
존재는 기록하되, 그 존재가 production authority를 부여하지 않음 —
§4 원칙 그대로 적용).

```
TSU        : HOLD (미착수)
Embedding  : HOLD
Qdrant     : HOLD
Production : INELIGIBLE
```

---

## 9. PBC1742 Final State

```
Manifest record  : BAP-CONF-PHIL-1742 (status: ACQUIRED)
Canonical ID      : PBC1742
Lineage           : PROBABLY MATCH (미확정)
Raw source         : EMPTY 디렉터리(NAE/corpus/raw/archive_org/PBC1742/,
                    직접 재확인 0파일)
Canonicalization    : FAILED — normalize_report.json status="failed",
                    reason="no_extractable_source",
                    generated_at="2026-08-01T06:22:37Z"(직접 재확인)
Contradiction        : manifest ACQUIRED ↔ raw 부재 ↔ 처리 실패 —
                    3개 사실이 서로 모순, 근본 원인은 raw 자체가
                    확보되지 않았음(archive.org 에러 페이지를 실제
                    콘텐츠로 오인했을 가능성, evidence/phase5_2/
                    C1-SOURCE-IDENTITY-REGISTRY-006.md와 정합적)
```

**FINAL STATE: `PBC1742 PROVENANCE = BROKEN`, `PROCESSING = FAILED`,
`PRODUCTION = INELIGIBLE`.**

---

## 10. PBC1765 Final State

```
Manifest record  : 없음 — 25개 id 목록에 PBC1765 부재(재확인)
Raw source         : NAE/corpus/quarantine/PBC1765/original/에
                    confeo00phil.pdf(8,238,629B) + confeo00phil_djvu.txt
                    (159,350B) + confeo00phil_scandata.xml(111,912B)
                    존재(직접 재확인, git tracked)
Acquisition 경위     : evidence/phase5_2/pbc1765_acquire_008(FAILED,
                    404) → pbc1765_acquire_009(PASS, 7/7 조건,
                    content identity VERIFIED via direct grep)로
                    문서화됨
Canonical artifact   : EXISTS — canonical.json 543,249B, canonical.txt
                    127,993B, normalize_report.json status="ok",
                    114 pages, 1,046 paragraphs(직접 재확인)
Quality issue         : 존재 — 첫 60 paragraph의 약 62%가 OCR noise,
                    다수 chapter heading 미인식, scripture_references_
                    found=0. HQ Advisory(`HQ-ADVISORY-PBC1765-
                    CANONICAL-DECISION.md`, 2026-08-01)가 명시적으로
                    "DO NOT proceed to TSU/embedding/Qdrant" 지시
```

**FINAL STATE: `PBC1765 PROVENANCE = COMPLETE`** (raw 보존 + acquisition
경위 문서화 + canonical linkage 확인 — lineage 전체가 evidence로
연결됨). **단, Provenance COMPLETE와 Production Eligible을 동일시하지
않는다(작업명령서 §7 원칙)**:

```
TSU        : HOLD (HQ Advisory)
Embedding  : HOLD (HQ Advisory)
Qdrant     : HOLD (HQ Advisory)
Production : HOLD (quality 재검토 후 HQ 재승인 필요 — provenance
             문제가 아니라 quality 문제로 차단됨을 명확히 구분)
```

---

## 11. Dagg / Hiscox / Fuller Final State

각 record를 개별 재확인(그룹 일괄 PASS 금지 원칙 적용):

| Record | Raw | Canonical | TSU | Provenance | Production |
|---|---|---|---|---|---|
| BAP-CHURCH-DAGG-001 | YES(4파일, church_order/Dagg_Church_Order/) | YES(ok) | YES(3,377 claims, tsu_report.json 직접 확인) | **COMPLETE** | HOLD(embedding/Qdrant 미착수) |
| BAP-CHURCH-DAGG-002 | YES(001과 동일 소스로 consolidated, manifest note) | YES(001과 동일 canonical) | YES(001과 동일) | **COMPLETE** | HOLD |
| BAP-CHURCH-HISCOX | YES(4파일) | YES(ok, 192 pages/877 paragraphs) | YES(tsu.json/tsu_report.json/index_report.json 존재) | **COMPLETE** | HOLD |
| BAP-MISS-FULLER | YES(8볼륨×3파일, missions/Fuller_Complete_Works_Vol01~08/) | YES(8건 ok) | PARTIAL(Vol01만 tsu.json/tsu_report.json 존재, Vol02~08 없음) | **COMPLETE**(raw+canonical lineage 기준. TSU는 그룹 내 1/8만 진행된 상태를 별도 명시) | HOLD |

### Smith Bible Dictionary 오매핑 정정 (§8)

C1의 §21 "PROVENANCE COMPLETE: 5 groups (Dagg, Hiscox, Fuller×8, Smith
Dict×4)" 분류를 **폐기**한다. `NAE/corpus/raw/archive_org/reference/
Smith_Bible_Dictionary_HackettAbbot_Vol1~4/`는 실제로 존재하고 raw+
canonical이 완전하지만(§6), **이 manifest(`NAE_SOURCE_MANIFEST_v1.csv`)
의 25개 id 어디에도 대응 record가 없다.** C1이 이를 `BAP-HIST-CATHCART`
("The Baptist Encyclopedia", William Cathcart 저)에 매핑한 것은
제목/저작 자체가 명백히 다른 별개 문헌이므로 **오류**다. Smith Bible
Dictionary는 별도 governance 트랙(ADR-029 §2, `NAE_SMITH_BIBLE_
DICTIONARY_REGISTRATION_001.md` — PHASE 0)에 속하며, **이번 manifest의
final governance matrix에서 완전히 제외한다.**

`BAP-HIST-CATHCART`는 raw/canonical이 모두 없으므로 §12의 CLAIM ONLY로
재분류한다(원래 C1은 이를 Category E 18건 목록에서 제외했었음 — 이번
정정으로 19번째 CLAIM ONLY record가 됨).

**이번 manifest 안에서 확정되는 PROVENANCE COMPLETE 그룹은 Dagg, Hiscox,
Fuller 3개 저작(record 기준 4건: 001/002/HISCOX/FULLER)뿐이다.**

---

## 12. 18(→19) Claim-Only Records

BAP-HIST-CATHCART을 포함해 최종 19개 record가 CLAIM ONLY로 확정된다.
전부 raw/canonical/TSU/embedding 0건(§6 디렉터리 재확인 결과 대응
디렉터리 자체가 없음):

```
BAP-SYS-GILL-001, BAP-SYS-BOYCE-001, BAP-SYS-STRONG-001,
BAP-SYS-PENDLETON-001, BAP-COM-GILL-001, BAP-COM-BROADUS-MAT,
PROT-COM-HENRY-001, PROT-COM-HAWKER-001, BAP-SER-SPURGEON-001,
BAP-SER-SPURGEON-MTP, BAP-COM-SPURGEON-DAVID, BAP-SER-KEACH-001,
BAP-SPIRIT-BUNYAN, BAP-SER-MACLAREN, BAP-HIST-ARMITAGE,
BAP-HIST-BENEDICT, BAP-HIST-CATHCART, BAP-MISS-CAREY, BAP-MISS-JUDSON
```

`manifest says ACQUIRED ≠ acquisition verified` 원칙에 따라 19건 전부
`PROVENANCE = CLAIM ONLY`, `PRODUCTION = HOLD`(acquisition 자체 미완료로
production 판단 불가 상태이지 명시적 부적격은 아님).

---

## 13. Contradiction Register (최종본)

| # | Claim | Evidence | Conflict | Resolution |
|---|---|---|---|---|
| 1 | 원 task order 25 records vs C1 주장 26 records | Python csv 파싱 = 25 data rows | C1이 manifest 밖 PBC1765를 26번째로 오산입 | **25로 확정(§3)** |
| 2 | BAP-CONF-1689 manifest ACQUIRED vs SLBC1689 raw 부재 + 시간순 반증 | 직접 재확인(§8) | canonical이 manifest acquisition보다 먼저 존재 | **PROVENANCE BROKEN 확정** |
| 3 | BAP-CONF-PHIL-1742 manifest ACQUIRED vs raw EMPTY vs canonicalization FAILED | 직접 재확인(§9) | 3중 모순 | **PROVENANCE BROKEN, PROCESSING FAILED 확정** |
| 4 | C1 "PBC1765 raw NOT FOUND" | quarantine/PBC1765/original/ 실재 확인 | C1이 조사 범위에서 quarantine 누락 | **PROVENANCE COMPLETE로 상향 확정(§10)** |
| 5 | C1 "Smith Bible Dictionary = 이 manifest의 5번째 COMPLETE 그룹" | Smith 관련 id가 25개 목록에 없음, BAP-HIST-CATHCART는 다른 저작 | 오매핑 | **이 manifest의 record에서 완전 제외(§11)** |
| 6 | 19개(18+CATHCART) manifest ACQUIRED vs filesystem 0건 | 디렉터리 전수 재확인 | manifest overstate | **CLAIM ONLY 확정(§12)** |

---

## 14. Final Source Governance Matrix

**Manifest 25 records (authoritative):**

| # | Source ID | Manifest Status | Raw | Canonical | Provenance | Production |
|---|---|---|---|---|---|---|
| 1 | BAP-CONF-1689 | ACQUIRED | NO | YES (SLBC1689) | **BROKEN** | INELIGIBLE |
| 2 | BAP-CONF-PHIL-1742 | ACQUIRED | EMPTY | FAILED | **BROKEN** | INELIGIBLE |
| 3 | BAP-SYS-GILL-001 | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |
| 4 | BAP-SYS-BOYCE-001 | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |
| 5 | BAP-SYS-STRONG-001 | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |
| 6 | BAP-SYS-PENDLETON-001 | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |
| 7 | BAP-COM-GILL-001 | ACQUIRED_PARTIAL_6_VOLUMES | NO | NO | CLAIM ONLY | HOLD |
| 8 | BAP-COM-BROADUS-MAT | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |
| 9 | PROT-COM-HENRY-001 | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |
| 10 | PROT-COM-HAWKER-001 | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |
| 11 | BAP-SER-SPURGEON-001 | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |
| 12 | BAP-SER-SPURGEON-MTP | PARTIAL_31_OF_63 | NO | NO | CLAIM ONLY | HOLD |
| 13 | BAP-COM-SPURGEON-DAVID | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |
| 14 | BAP-SER-KEACH-001 | ACQUIRED_SUBSTITUTE | NO | NO | CLAIM ONLY | HOLD |
| 15 | BAP-SPIRIT-BUNYAN | ACQUIRED_SUBSTITUTE | NO | NO | CLAIM ONLY | HOLD |
| 16 | BAP-SER-MACLAREN | ACQUIRED_15_VOLUMES | NO | NO | CLAIM ONLY | HOLD |
| 17 | BAP-CHURCH-DAGG-001 | ACQUIRED | YES | YES | **COMPLETE** | HOLD |
| 18 | BAP-CHURCH-DAGG-002 | ACQUIRED_CONSOLIDATED | YES | YES | **COMPLETE** | HOLD |
| 19 | BAP-CHURCH-HISCOX | ACQUIRED | YES | YES | **COMPLETE** | HOLD |
| 20 | BAP-HIST-ARMITAGE | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |
| 21 | BAP-HIST-BENEDICT | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |
| 22 | BAP-HIST-CATHCART | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |
| 23 | BAP-MISS-FULLER | ACQUIRED | YES(×8) | YES(×8) | **COMPLETE** | HOLD |
| 24 | BAP-MISS-CAREY | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |
| 25 | BAP-MISS-JUDSON | ACQUIRED | NO | NO | CLAIM ONLY | HOLD |

**부록 — Manifest 밖 artifact (25건에 포함되지 않음):**

| Source ID | Manifest | Raw | Canonical | Provenance | Production |
|---|---|---|---|---|---|
| PBC1765 | 없음(NOT A RECORD) | YES(quarantine) | YES | **COMPLETE** | HOLD(quality) |

**집계**: PROVENANCE COMPLETE = 4 records(3그룹) / PROVENANCE BROKEN = 2
/ PROVENANCE CLAIM ONLY = 19 / 합계 25. (부록 PBC1765는 COMPLETE, 별도
집계.)

---

## 15. Track Separation

```
TRACK A — STEP5 / NHBC1833           : INDEPENDENT
TRACK B — PHASE 5.2 / archive_org    : INDEPENDENT
                                        (evidence/phase5_2/, SLBC1689/
                                        PBC1742/PBC1765 evidence 문서)
TRACK C — NAE-BAPTIST-CORPUS-001      : INDEPENDENT
                                        (NAE_SOURCE_MANIFEST_v1.csv,
                                        25 records)
```

Track B와 Track C는 SLBC1689/PBC1742라는 같은 제목의 저작을 시간순으로
서로 무관하게(Track B의 canonical 생성이 Track C의 manifest 등록보다
먼저) 각자 추적한 것으로 확인된다(§8) — governance linkage 문서가
없으므로 계속 `INDEPENDENT`로 유지하며, 어느 한 track의 artifact를
다른 track의 acquisition/provenance 증거로 사용하지 않는다.

---

## 16. ADR-029 Reconciliation

```
Baptist corpus acquisition (Track A/B/C 전체)
        ≠
Korean authority acquisition
        ≠
Korean-English canonical terminology (ADR-029 §4.4 스키마)
```

NAE-BAPTIST-CORPUS-001의 4개 COMPLETE record(§14)나 PBC1765의 COMPLETE
provenance(§10)가 존재한다는 사실은 ADR-029 §4.4가 요구하는 `term_id/
english_term/korean_term/...` 스키마 레코드와 무관하다 — Baptist
confession/systematic theology/commentary 원문 자체는 ADR-029가 명시적으로
분리한 "Dictionary/Commentary = research evidence layer"에 해당하며
"Terminology = authoritative terminology layer"가 아니다.

**ADR-029 PHASE 1 = UNCHANGED.**

---

## 17. NHBC1833 Status

이번 reconciliation 과정에서 NHBC1833(New Hampshire Confession of Faith,
1833)에 대한 어떤 filesystem artifact, manifest entry, acquisition
evidence도 발견되지 않았다(25개 manifest record, Track B evidence,
Track C 전체를 통틀어 재확인). Baptist corpus의 다른 source(SLBC1689,
PBC1765 등)가 다양한 상태로 존재한다는 사실이 NHBC1833의 acquisition
요구사항을 대체하지 않는다.

**`NHBC1833 = WAITING_FOR_SOURCE` — 변경 없음.**

---

## 18. Production Eligibility (요약)

```
ELIGIBLE   : 0
HOLD       : 23 record (COMPLETE 4건 — embedding/Qdrant 미착수 사유,
             CLAIM ONLY 19건 — acquisition 미완료 사유) + 부록 PBC1765
             (quality-hold)
INELIGIBLE : 2 record (SLBC1689/BAP-CONF-1689, PBC1742/BAP-CONF-
             PHIL-1742 — provenance broken)
UNKNOWN    : 0
```

TSU는 Dagg/Hiscox/Fuller-Vol01 3건만 존재(직접 재확인), embedding
artifact는 0건, Qdrant는 도달 불가(`curl -m 3 http://localhost:6333/
collections` → connection refused, exit 7, 직접 재확인) — 따라서
COMPLETE 등급이라도 현재 ELIGIBLE로 승격되는 record는 없다.

---

## 19. Current True Blocker

```
NAE-BAPTIST-CORPUS-001(Track C) 자체의 blocker:
  → 19개 CLAIM ONLY record의 실제 raw acquisition 미완료
  → SLBC1689/PBC1742(2건)의 provenance 재구성 불가(broken)

ADR-029 PHASE 1(별개 governance gate)의 blocker:
  → Korean theological terminology authoritative source 0건
    (변경 없음, 이번 reconciliation과 무관)

NHBC1833(Track A)의 blocker:
  → 원문 미확보 (변경 없음)
```

세 blocker는 서로 다른 track에 속하며 하나를 해결해도 다른 것이
자동으로 해결되지 않는다(§15).

---

## 20. Authorized Next Action

```
(1) SLBC1689/PBC1742: HQ decision 대기 — provenance broken canonical
    output을 폐기할지, BAP-CONF-1689/-PHIL-1742 identifier로 raw를
    재확보 시도할지 결정 필요. CUE/C1은 자체적으로 재처리하지 않는다.
(2) 19개 CLAIM ONLY record: HQ 우선순위 결정 필요 — 실제 acquisition을
    시도할 대상과 순서를 정해야 함. 이번 reconciliation은 실행하지
    않는다.
(3) PBC1765: quality 재검토 후 HQ 재승인이 있어야 TSU/embedding/Qdrant
    진행 가능(HQ Advisory 유효 유지).
(4) Dagg/Hiscox/Fuller(4 record, 3그룹): provenance COMPLETE이므로
    embedding/Qdrant 진행이 기술적으로는 가능하나, ADR-029 §3 Fixed
    Pipeline(Phase 0 Smith 완료 → Phase 1 Korean terminology) 순서
    원칙에 따라 별도 HQ 승인 없이 진행하지 않는다.
(5) NHBC1833: Human acquisition 대기 — 변경 없음.
(6) ADR-029 PHASE 1: Human acquisition of Korean authoritative
    terminology source 대기 — 변경 없음.
```

---

## 21. Mutation Audit

```
Canonicalization   : 0
TSU generation      : 0
Embedding            : 0
Qdrant ingestion      : 0
Source acquisition    : 0
Source deletion         : 0
Manifest modification   : 0
Registry modification    : 0
Code modification         : 0
```

읽은 파일만 존재. 다른 세션의 변경사항(NAE/smith_activation.py,
docs/STATE.md, ui/pages/chat.py 등)에 개입하지 않음.

## 22. Git Status

이번 통합 작업 시작 시점 — 선행 CUE 검증들과 동일한 unstaged 변경분
(다른 세션) + 이번까지의 CUE/C1 신규 보고서 4건(untracked)이 누적된
상태였다. 이번 문서 1건만 신규 작성하며 그 외 아무것도 더하거나
되돌리지 않았다. `git add`/`git commit` 미실행.

---

## 23. Final Decision

```
NAE-BAPTIST-CORPUS-001
FINAL GOVERNANCE RECONCILIATION

MANIFEST RECORDS:
25

PROVENANCE COMPLETE:
4 (BAP-CHURCH-DAGG-001, BAP-CHURCH-DAGG-002, BAP-CHURCH-HISCOX,
   BAP-MISS-FULLER — 실질 3개 저작 그룹)
   [+ 부록 PBC1765, manifest 밖, 별도 집계]

PROVENANCE PARTIAL:
0

PROVENANCE BROKEN:
2 (BAP-CONF-1689/SLBC1689, BAP-CONF-PHIL-1742/PBC1742)

MANIFEST CLAIM ONLY:
19 (BAP-HIST-CATHCART 포함, C1의 18건에서 1건 추가 정정)

SLBC1689:
CANONICALIZATION COMPLETE(artifact) / PROVENANCE BROKEN / PRODUCTION
INELIGIBLE

PBC1742:
CANONICALIZATION FAILED(no_extractable_source) / PROVENANCE BROKEN /
PRODUCTION INELIGIBLE

PBC1765:
CANONICALIZATION COMPLETE / PROVENANCE COMPLETE(quarantine raw 확인) /
PRODUCTION HOLD(quality, HQ Advisory 유효)

DAGG / HISCOX / FULLER:
PROVENANCE COMPLETE(4 records, 개별 검증 완료) / PRODUCTION HOLD
(embedding/Qdrant 미착수, ADR-029 §3 순서 원칙 적용)

SMITH BIBLE DICTIONARY:
NOT A RECORD IN THIS MANIFEST

NHBC1833:
WAITING_FOR_SOURCE — UNCHANGED

ADR-029 PHASE 1:
UNCHANGED

CURRENT TRUE BLOCKER:
Track A(NHBC1833): human acquisition 미완료.
Track C(NAE-BAPTIST-CORPUS-001): 19개 record 미확보 + 2개 record
provenance broken.
ADR-029 PHASE 1: Korean theological terminology authoritative source
0건. 세 blocker는 독립적이며 상호 대체되지 않는다.

EN-BAP TRACK:
PARALLEL / PHASE 0 EXTENSION — UNCHANGED (2026-08-26 HQ 승인 relabel
그대로 유지, 이번 reconciliation과 무관)

NEXT AUTHORIZED ACTION:
§20 (1)~(6) 참고 — 전부 HQ decision 대기, CUE/C1 자체 실행 없음

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

> **이 문서는 새로운 사실을 발견하기 위한 문서가 아니라, 이미 독립적으로
> 검증된 사실을 하나의 authoritative governance state로 고정하기 위한
> 문서다.**
>
> 불확실한 것은 없었다 — 이번 통합에서 `UNKNOWN`으로 남긴 항목은 0건이다
> (모든 25개 record + 부록 1건이 직접 evidence로 COMPLETE/BROKEN/CLAIM
> ONLY 중 하나로 확정됨).
>
> Provenance와 Production Eligibility는 분리되어 있다 — COMPLETE 4건
> 중 어느 것도 아직 ELIGIBLE이 아니다.
>
> Manifest와 실제 evidence가 충돌한 곳(SLBC1689, PBC1742, Smith
> 오매핑)은 전부 evidence를 우선해 정정했다.
>
> **이 reconciliation 이후, 같은 artifact를 반복 조사하지 않는다.**
> CUE는 본 보고서 제출로 이번 조사 계열을 종료하고 HQ의 다음 결정을
> 기다린다.

---

**Mode**: FINAL GOVERNANCE RECONCILIATION (신규 조사 없음)
**Mutations**: 0
**Git add/commit**: NO
**Report generated**: 2026-08-26
