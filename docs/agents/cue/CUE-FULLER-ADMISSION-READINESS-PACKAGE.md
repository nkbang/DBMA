# CUE — Fuller Vol.01–08 Admission Readiness Package

**작성자**: CUE (Architecture / Governance / Independent Verification)
**작성일**: 2026-08-29
**Governing Authority**: ADR-030 v2.1 §11 (Human Eligibility Governance / Admission Decision), ADR-029 (Research Corpus Pipeline Lock)
**Mode**: GOVERNANCE ARTIFACT — 이 문서는 admission record를 재해석하지 않는다. HQ authoritative values를 그대로 반영한다.
**Mutation Budget**: Code 0 / Corpus 0 / RAW 0 / Canonical 0 / TSU 0 / Embedding 0 / Qdrant 0 / Registration-state 0 / Manifest 0 / Config 0

---

## 0. Status

| | |
|---|---|
| **Fuller Vol.01–08** | **ADMITTED** (`NAE/governance/corpus_admissions.jsonl` lines 7–14, committed `6b77df6`) |
| **Processing** | **HOLD** — TSU generation / verification / human review / embedding / Qdrant ingestion / production integration |
| **Admission date** | 2026-08-29 (HQ authoritative) |
| **CUE readiness finding** | GREEN — evidence sufficient for admission |
| **3,319 production baseline** | FROZEN / UNCHANGED |

> **ADMITTED ≠ PROCESSED.** 이 문서·admission record는 Fuller가 향후 ADR-030 TSU track으로 처리될 대상임을 공식 기록할 뿐, TSU가 생성/검수/검증/임베딩/인덱싱/production 편입되었음을 의미하지 않는다.

---

## 1. Fuller Vol.01–08 Identity

| 항목 | 값 |
|---|---|
| author | Andrew Fuller (`author_id: fuller_andrew`) |
| collection | *The Works of the Rev. Andrew Fuller, in Eight Volumes* |
| license | `public_domain` |
| archive_source | `archive_org` |
| source identity 분리 | 8권 각각 고유 `work_id` / `edition_id` / `year` / `raw_checksum` (M2 `NAE/pipeline/registration/state/source_manifest.yaml`) |

확인된 권별 title (M2 직접 인용, 대표 3권):

- **Vol.01** — *The Gospel Worthy of All Acceptation: The Duty of Sinners to Believe in Jesus Christ* (1820, Charlestown)
- **Vol.05** — *Expository Discourses on the Book of Genesis* (1824, New Haven)
- **Vol.08** — *Miscellanies: Magazine Papers, Sketches of Sermons, Association Letters, Tracts* (1824, New Haven)

Vol.02–04, 06, 07 title/edition은 M2 source_manifest.yaml이 authority.

---

## 2. Source / Provenance Evidence

### 2.1 Raw 무결성 — 3-way MATCH (8/8)

`shasum -a 256 original.pdf` = M2 `raw_checksum` = `raw_checksum_ledger.jsonl` — 3자간 전량 일치.

| Vol | raw_checksum (SHA-256, 앞 8) | 3-way |
|---|---|---|
| Vol.01 | `74416a8f…` | MATCH |
| Vol.02 | `352d7edf…` | MATCH |
| Vol.03 | `787e185c…` | MATCH |
| Vol.04 | `8f4ba47e…` | MATCH |
| Vol.05 | `20da331a…` | MATCH |
| Vol.06 | `95b2fe11…` | MATCH |
| Vol.07 | `78cd86c9…` | MATCH |
| Vol.08 | `bc66c821…` | MATCH |

- `checksum_target` = `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol0x/original.pdf`
- `raw_path` (canonical 생성에 실제 사용) = `.../Vol0x/ocr.txt`
- Vol.01 / Vol.05 / Vol.08은 CUE가 직접 재계산·재대조. 나머지는 C1 evidence collection + 3-way FORENSIC RECONCILIATION(`CUE-NAE-BAPTIST-CORPUS-3WAY-FORENSIC-RECONCILIATION.md` §3.3 "MATCH ×8")와 정합.

### 2.2 Registration

`NAE/pipeline/registration/state/registration_state.json` — Vol.01–08 전량 `QUALITY_PASSED` (updated 2026-08-15). ADR-021 파이프라인 통과.

---

## 3. Canonical Readiness Status

| Vol | status | source | page_count | paragraph_count | scripture_refs | footnotes | verse_para | canonical.json / .txt |
|---|---|---|---|---|---|---|---|---|
| Vol.01 | ok | ocr | 1 | 2,250 | 2 | 0 | 0 | 존재 / 존재 |
| Vol.02 | ok | ocr | 1 | 2,040 | 3 | 0 | 0 | 존재 / 존재 |
| Vol.03 | ok | ocr | 1 | 2,526 | 0 | 0 | 0 | 존재 / 존재 |
| Vol.04 | ok | ocr | 1 | 2,268 | 3 | 0 | 0 | 존재 / 존재 |
| Vol.05 | ok | ocr | 1 | 1,890 | 1 | 0 | 1 | 존재 / 존재 |
| Vol.06 | ok | ocr | 1 | 2,756 | 1 | 0 | 0 | 존재 / 존재 |
| Vol.07 | ok | ocr | 1 | 2,103 | 0 | 0 | 0 | 존재 / 존재 |
| Vol.08 | ok | ocr | 1 | 2,769 | 1 | 0 | 0 | 존재 / 존재 |

**Provenance limitation (disclosure, admission blocker 아님):**

- `source = ocr`, `page_count = 1` → **page-level citation provenance 미확보** (모든 paragraph가 page 1)
- `footnotes_extracted = 0` (8/8)
- `verse_paragraph_count = 0` (Vol.05만 1)
- `scripture-reference detection` = 제한적·권별 편차, **Vol.03 / Vol.07 = 0**

이 limitation은 `authority_class = historical_witness`(claim이 저작에 귀속되며 page-level scholarly citation certification이 목적이 아님)에서 수용 가능하다. 단 향후 retrieval/citation 사용 시 이 한계가 존재한다는 사실을 8개 admission record의 `rationale`에 명시했다.

---

## 4. Admission Decision

**HQ decision (2026-08-29):**

```
Fuller Vol.01–08   ADMISSION  = ADMITTED
Fuller Vol.01–08   PROCESSING = HOLD
```

기록 위치: `NAE/governance/corpus_admissions.jsonl` lines 7–14 (append-only, 기존 6줄 무접촉). Commit `6b77df6` "Record Fuller Vol.01-08 corpus admission".

Admission은 ADR-030 §11 Admission Decision 요건을 충족하며, TSU track 배정만 authorize한다.

---

## 5. Authoritative Metadata Classification

M2 RATIFIED v1.1 값을 그대로 반영 (임의 분류 추가·변경·normalization 없음):

| Vol | content_genre | theological_category | authority_class | tradition | track |
|---|---|---|---|---|---|
| Vol.01 | `["theology"]` | `["soteriology"]` | historical_witness | Particular Baptist | tsu |
| Vol.02 | `["theology"]` | `["soteriology"]` | historical_witness | Particular Baptist | tsu |
| Vol.03 | `["theology"]` | *(key 생략)* | historical_witness | Particular Baptist | tsu |
| Vol.04 | `["theology"]` | *(key 생략)* | historical_witness | Particular Baptist | tsu |
| Vol.05 | `["commentary"]` | *(key 생략)* | historical_witness | Particular Baptist | tsu |
| Vol.06 | `["commentary"]` | *(key 생략)* | historical_witness | Particular Baptist | tsu |
| Vol.07 | `["sermon"]` | *(key 생략)* | historical_witness | Particular Baptist | tsu |
| Vol.08 | `["theology","sermon","mission"]` | `["missions"]` | historical_witness | Particular Baptist | tsu |

Vol.03–07의 `theological_category`는 M2에서 RATIFIED v1.1상 required로 승격되지 않았으며, admission record에서도 **key 자체를 생략**한다 (`[]` 미사용).

---

## 6. TSU Status

### Vol.01

| 항목 | 값 |
|---|---|
| builder_version | 3.0.0 |
| model | `my-theology-bot-v2:latest` |
| generated_at | 2026-08-16T11:44:46Z |
| candidates_evaluated / total | 5,452 / 5,452 |
| **claims_extracted** | **3,643** |
| llm_errors | 1 |
| partial | false |
| review_status 분포 | `generated: 3,643` (verified 0 / rejected 0 / empty 0) |
| unique id | 3,643 |
| doctrine_breakdown | Soteriology 2,314 · Sanctification 279 · Justification 271 · Providence 204 · Election 165 · Ecclesiology 98 · Scripture/Authority 73 · Eschatology 61 · Trinity 21 · Other 10 · Baptism 9 · Confession 2 |
| **human review** | **PENDING** |

### Vol.02–08

```
TSU = NOT GENERATED  (NAE/corpus/tsu/ 에 Fuller_Complete_Works_Vol02..08 디렉터리 부재)
```

### Embedding gate

`NAE/pipeline/tsu/review_gate.py` — `EMBEDDING_ELIGIBLE_STATUSES = {verified}`. Fuller Vol.01의 3,643 claim은 전량 `generated` → **embedding-eligible = 0**.

---

## 7. Processing HOLD Decision

Fuller Vol.01–08은 admission 이후에도 다음 상태를 유지한다 (8개 record `rationale`에 명시):

```
TSU generation        = HOLD   (Vol.02–08)
TSU verification      = HOLD
Human review          = HOLD   (Vol.01의 3,643 generated → verified 승격 금지)
Embedding             = HOLD
Qdrant ingestion      = HOLD
Production integration = HOLD
```

후속 진행은 별도 HQ authorization을 요구한다. Admission은 이 HOLD를 해제하지 않는다.

---

## 8. Qdrant / Production Mutation Audit

| 대상 | 상태 |
|---|---|
| Qdrant `nae_tsu_v1` | **3,319** (Dagg 2,958 + Hiscox 361) — UNCHANGED |
| Qdrant `nae_ref_v1` | **34,948** (Smith Vol1–4) — UNCHANGED |
| `nae_tsu_v1` identifier = `Fuller_Complete_Works_Vol0x` | **0 / 8** (Fuller 미인덱싱) |
| production corpus / raw / canonical | 무접촉 |
| `registration_state.json` / `incremental_state.json` | 무접촉 |
| `NAE/manifest/*` / M2 source_manifest.yaml | 무접촉 |
| `config.yaml` / runtime code | 무접촉 |

```
Production mutation = 0
Qdrant mutation     = 0
TSU mutation        = 0
```

3,319 production baseline은 이번 admission 작업 전 구간에서 **FROZEN / UNCHANGED**.

---

## 9. CUE Forensic Correction History

Admission record 최초 append(C1)는 CUE 독립 검증에서 **REJECTED**되었다. HQ authoritative verbatim 8줄과의 불일치:

| 필드 | Authoritative | C1 최초 append | 판정 |
|---|---|---|---|
| `track` | `tsu` ×8 | `reference` ×8 | WRONG |
| `authority_class` | `historical_witness` ×8 | `reference` ×8 | WRONG |
| `content_genre` | 권별 (theology / commentary / sermon / mix) | `["missions"]` ×8 | WRONG |
| `theological_category` | Vol.01·02 `[soteriology]`, Vol.08 `[missions]`, Vol.03–07 생략 | 8줄 전부 생략 | WRONG |
| `rationale` | provenance disclosure + processing HOLD + ADR-029 독립 | Smith 보일러플레이트 + 허위 주장 ("M2 confirms category=missions, source_type=reference" — M2에 두 필드 다 없음) | WRONG |
| `evidence_refs` | M2 SSOT + ledger + normalize_report + package | legacy pilot manifest + self-reference | WRONG |
| `date` | `2026-08-29` | `2026-09-02` | 불일치 |

**CUE 직접 correction (forensic):** `corpus_admissions.jsonl` lines 7–14를 HQ authoritative verbatim 8줄로 교체. 기존 lines 1–6은 byte 보존 — SHA-256 `00257d066773ee5ecd925345f8b0331adea48339620349c139bc0375ffac37b6` (correction 전후 동일). `git reset` / `git restore` / `git checkout` / `git clean` 미사용.

---

## 10. CUE Independent Verification Result

byte-level verification (HQ addendum PHASE 1–8) — 전량 GREEN:

| Check | 결과 |
|---|---|
| Lines 1–6 `cmp` | `cmp_exit = 0` (byte identical vs HEAD) |
| Lines 1–6 SHA-256 | HEAD == WT (`00257d06…ac37b6`) |
| Lines 7–14 full-object | 8/8 — track / authority_class / tradition / decided_by / date + 권별 content_genre + theological_category present/absent + `volume` key 부재 확인 |
| Line count | 14 |
| JSONL parse | 14 / 14 PASS |
| Line endings | LF only (CR 0), final byte `0a` |
| Diff | `+8 / -0`, numstat `8␉0` |
| Staged (correction 단계) | 없음 |

**Commits (unpushed):**

```
6b77df6  Record Fuller Vol.01-08 corpus admission     (corpus_admissions.jsonl, +8/-0)
5cc0119  Update ADR-030 Fuller N-9 governance status   (ADR-030 §12 N-9, +1/-1)
```

두 commit 모두 별도(combined 아님). `origin/dev/dbma-engine` 대비 unpushed. HQ 승인 전 push 없음.

---

## 11. ADR-030 N-9 Relationship

`5cc0119`로 ADR-030 §12 N-9를 갱신:

- **이전**: `| N-9 | Fuller Vol01–08 TSU/embedding, M3 CLAIM-ONLY 19건 acquisition | backlog, ADR-029 PHASE 순서 |`
- **현재**: `| N-9 | Fuller Vol01–08 TSU/embedding (admitted 2026-08-29, corpus_admissions.jsonl lines 7–14 — processing HOLD); M3 CLAIM-ONLY 19건 acquisition | Fuller: HQ HOLD (admission 완료, TSU/review/embedding 후속 승인 대기). M3 19건: backlog |`

Governance fact:

1. ADR-029 §3 Fixed Pipeline은 research-corpus sequence (PHASE 1 Korean Terminology → PHASE 2 → PHASE 3 NAC …).
2. **Fuller는 이 pipeline에 속하지 않는다** — ADR-030 Baptist 신학/설교 corpus의 TSU track.
3. ADR-029 PHASE 0은 CLOSED (2026-08-29).
4. Fuller admission은 ADR-029 PHASE 1과 **독립**적으로 허용되었다.
5. 이것은 ADR-029 PHASE 1을 우회·종료시키는 결정이 **아니다.** ADR-029 PHASE 1(Korean Terminology)은 기존 governance대로 유지된다.

N-9의 이전 blocking rationale("ADR-029 PHASE 순서")는 PHASE 0 종료 + Fuller의 track 독립성 확인으로 더 이상 admission을 막지 않는다. 처리(TSU/embedding)는 여전히 HQ HOLD.

---

## 12. ADMITTED ≠ PROCESSED (명시)

```
Fuller Vol.01–08 = ADMITTED for future ADR-030 TSU-track processing.

이것이 의미하지 않는 것:
  × TSU가 생성되었다        (Vol.02–08 = NOT GENERATED)
  × TSU가 검수/검증되었다   (Vol.01 = 3,643 generated / 0 verified, review PENDING)
  × 임베딩되었다
  × Qdrant에 인덱싱되었다
  × production corpus에 편입되었다

모든 처리는 후속 HQ authorization 전까지 HOLD.
3,319 production baseline은 이 admission의 영향을 받지 않는다.
```

---

## Evidence References

- `NAE/governance/corpus_admissions.jsonl` (lines 7–14, commit `6b77df6`)
- `NAE/pipeline/registration/state/source_manifest.yaml` (M2 SSOT)
- `NAE/pipeline/registration/state/raw_checksum_ledger.jsonl`
- `NAE/pipeline/registration/state/registration_state.json`
- `NAE/corpus/canonical/Fuller_Complete_Works_Vol01..08/normalize_report.json`
- `NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu_report.json`, `tsu.json`
- `NAE/pipeline/tsu/review_gate.py` (`EMBEDDING_ELIGIBLE_STATUSES`)
- `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` §11, §12 N-9 (commit `5cc0119`)
- `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md` §3
- `docs/agents/cue/CUE-NAE-BAPTIST-CORPUS-3WAY-FORENSIC-RECONCILIATION.md`
- `docs/agents/cue/CUE-NAE-BAPTIST-CORPUS-001-FINAL-GOVERNANCE-RECONCILIATION.md`

## Final Verification State

```
Fuller Vol.01–08          = ADMITTED (6b77df6)
Processing                = HOLD
ADR-030 N-9               = updated (5cc0119)
Existing 3,319 baseline   = FROZEN / UNCHANGED
Production mutation        = 0
Qdrant mutation            = 0
TSU mutation               = 0
Unrelated WIP              = untouched
This package               = separate commit
Push                       = NO (HQ approval pending)
```

---

**Mode**: GOVERNANCE ARTIFACT (admission record 재해석 없음)
**Mutations**: 0
**Report generated**: 2026-08-29
