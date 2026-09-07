# CUE — ADR-030 §12 M-3 확장 · Fuller Vol01–08 admission-with-processing-HOLD — DRAFT

**작성자**: CUE(쳗) · **작성일**: 2026-09-02 · **상태**: **DRAFT** — HQ 비준 대기 (§9 open items)
**대상**: `NAE/governance/corpus_admissions.jsonl` 스키마 확장 + Fuller 8건 항목 + `tests/test_corpus_admissions.py` 개정 + ADR-030 문서 정합
**baseline**: `dev/dbma-engine` @ `9c617b6` · 선행 커밋 `31ac18f` (doc-only N-9 기록, PR nkbang/DBMA#4)
**근거**: ADR-030 v2.1 §11 (Human Eligibility Governance), §12 MUST M-3 / N-9, `CUE-ADR-030-M3-CORPUS-ADMISSIONS.md` (RATIFIED)

> 진행: ① 본 DRAFT → ② HQ 비준(§9) → ③ M-3-EXT EXEC (C1, §10) → ④ 쳗 독립검증 → 커밋.
> **본 문서 mutation = 0.** 파일 생성·수정·테스트 실행 없음. 설계만.

---

## 1. 문제 — 현행 모델에 "admission 하되 처리 HOLD" 상태가 없다

`CUE-ADR-030-M3-CORPUS-ADMISSIONS.md` §5 게이트:

> `corpus_admissions.jsonl` 에 `source_id` 항목이 **없는** source 는 TSU 생성 / reference chunking 을 시작하지 않는다.

즉 현행 모델에서 **admission 기록 존재 = §5 수기 게이트 통과 = TSU review→embedding 진행 가능**. 이진(binary)이다.

HQ 결정(2026-09-02, PR #4): **Fuller Vol01–08 admission-in-principle 승인**, 그러나 TSU generation / TSU
verification / human review / embedding / production ingestion **전부 HOLD**.

→ 현행 모델로는 표현 불가. Fuller가 지금 처리에서 막혀 있는 유일한 이유가 "admission 기록 없음"이므로,
HOLD 장치 없이 Fuller 항목만 추가하면 **HQ가 유지하려는 그 차단을 오히려 해제**하게 된다.
따라서 스키마에 명시적 HOLD 필드를 추가하는 것이 이 확장의 핵심이다.

---

## 2. 스키마 확장 — `processing_status`

`CUE-ADR-030-M3-CORPUS-ADMISSIONS.md` §2 스키마에 **1개 optional 필드** 추가. 그 외 필드·정합 규칙 전부 불변.

| 필드 | 타입 | 필수 | 값 | 의미 |
|---|---|---|---|---|
| `processing_status` | string | ✖ | `"HOLD"` \| `"RELEASED"` | **키 생략 = RELEASED (레거시 기본값).** `"HOLD"` = admission 결정은 기록됐으나 §5 게이트 **미개방** — TSU 생성/검수/human review/embedding/ingestion 전면 금지. HQ만 `"RELEASED"` 로 전환(별도 append 또는 in-place 갱신 결정은 §9 OPEN-5). |

- 기존 6개 레코드: `processing_status` 키 없음 → RELEASED 로 해석. 이미 처리 완료 상태와 정합. **6줄 무변경.**
- Fuller 8개 레코드: `processing_status: "HOLD"`.

### §5 게이트 의미 확장 (문구 교체)

OLD (`CUE-ADR-030-M3-CORPUS-ADMISSIONS.md` §5 규칙 첫 줄):
> `corpus_admissions.jsonl` 에 `source_id` 항목이 없는 source 는 TSU 생성 또는 reference chunking 을 시작하지 않는다.

NEW:
> `corpus_admissions.jsonl` 에 `source_id` 항목이 **없거나**, 항목의 `processing_status == "HOLD"` 인 source 는
> TSU 생성 / TSU 검수 / human review / reference chunking / embedding / production ingestion 을 시작하지 않는다.
> `processing_status` 키가 없거나(레거시=RELEASED) `== "RELEASED"` 인 경우에만 다음 단계로 진행한다.
> HOLD→RELEASED 전환은 HQ 결정 사항이다 (코드 강제 = ADR-030 S-4).

---

## 3. `volume` 키 — 채택하지 않음

일부 검증 draft(PHASE 7 스크립트)가 `record["volume"] == "V01".."V08"` 를 가정하나:

- 기존 6개 레코드 · M2 `source_manifest.yaml` · `scripts/nae_corpus_reconcile.py` (GC-1/2/3) · 현행 test 전부
  **`source_id` 를 키로 사용**한다. `volume` 키 도입은 스키마 이중화이며 정합 규칙(M2 SSOT)과 무관한 신규 축이다.
- 권고: **`source_id` 유지** (`BAP-MISS-FULLER-VOL01` … `-VOL08`). 사람이 읽을 권 번호는 `rationale` 문장에 포함.
- PHASE 7 스크립트의 `volume` / `date 2026-08-29` 전제는 **비정규(draft artifact)** 로 간주. §9 OPEN-1/2.

---

## 4. Fuller 8건 — `corpus_admissions.jsonl` append (verbatim, M-3-EXT EXEC 소비)

기존 6줄 **뒤에** 아래 8줄 append. 총 14줄, 파일 끝 개행 1개. 값은 전부 M2 / evidence 에서 그대로.

```jsonl
{"source_id": "BAP-MISS-FULLER-VOL01", "decided_by": "David / HQ", "date": "2026-09-02", "track": "tsu", "authority_class": "historical_witness", "content_genre": ["theology"], "theological_category": ["soteriology"], "tradition": "Particular Baptist", "processing_status": "HOLD", "rationale": "HQ admission-in-principle 2026-09-02 (ADR-030 v2.1 §12 N-9). Registration QUALITY_PASSED; no TSU verified, no embedding, no reprocessing. TSU generation/verification, human review, embedding, production ingestion all HOLD pending ADR-029 PHASE order.", "evidence_refs": ["NAE/pipeline/registration/state/source_manifest.yaml", ".automation/evidence/NAE-REG-BAP-MISS-FULLER-VOL01.jsonl", "docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md"]}
{"source_id": "BAP-MISS-FULLER-VOL02", "decided_by": "David / HQ", "date": "2026-09-02", "track": "tsu", "authority_class": "historical_witness", "content_genre": ["theology"], "theological_category": ["soteriology"], "tradition": "Particular Baptist", "processing_status": "HOLD", "rationale": "HQ admission-in-principle 2026-09-02 (ADR-030 v2.1 §12 N-9). Registration QUALITY_PASSED; no TSU verified, no embedding, no reprocessing. TSU generation/verification, human review, embedding, production ingestion all HOLD pending ADR-029 PHASE order.", "evidence_refs": ["NAE/pipeline/registration/state/source_manifest.yaml", ".automation/evidence/NAE-REG-BAP-MISS-FULLER-VOL02.jsonl", "docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md"]}
{"source_id": "BAP-MISS-FULLER-VOL03", "decided_by": "David / HQ", "date": "2026-09-02", "track": "tsu", "authority_class": "historical_witness", "content_genre": ["theology"], "tradition": "Particular Baptist", "processing_status": "HOLD", "rationale": "HQ admission-in-principle 2026-09-02 (ADR-030 v2.1 §12 N-9). Registration QUALITY_PASSED; no TSU verified, no embedding, no reprocessing. TSU generation/verification, human review, embedding, production ingestion all HOLD pending ADR-029 PHASE order.", "evidence_refs": ["NAE/pipeline/registration/state/source_manifest.yaml", ".automation/evidence/NAE-REG-BAP-MISS-FULLER-VOL03.jsonl", "docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md"]}
{"source_id": "BAP-MISS-FULLER-VOL04", "decided_by": "David / HQ", "date": "2026-09-02", "track": "tsu", "authority_class": "historical_witness", "content_genre": ["theology"], "tradition": "Particular Baptist", "processing_status": "HOLD", "rationale": "HQ admission-in-principle 2026-09-02 (ADR-030 v2.1 §12 N-9). Registration QUALITY_PASSED; no TSU verified, no embedding, no reprocessing. TSU generation/verification, human review, embedding, production ingestion all HOLD pending ADR-029 PHASE order.", "evidence_refs": ["NAE/pipeline/registration/state/source_manifest.yaml", ".automation/evidence/NAE-REG-BAP-MISS-FULLER-VOL04.jsonl", "docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md"]}
{"source_id": "BAP-MISS-FULLER-VOL05", "decided_by": "David / HQ", "date": "2026-09-02", "track": "tsu", "authority_class": "historical_witness", "content_genre": ["commentary"], "tradition": "Particular Baptist", "processing_status": "HOLD", "rationale": "HQ admission-in-principle 2026-09-02 (ADR-030 v2.1 §12 N-9). Registration QUALITY_PASSED; no TSU verified, no embedding, no reprocessing. TSU generation/verification, human review, embedding, production ingestion all HOLD pending ADR-029 PHASE order.", "evidence_refs": ["NAE/pipeline/registration/state/source_manifest.yaml", ".automation/evidence/NAE-REG-BAP-MISS-FULLER-VOL05.jsonl", "docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md"]}
{"source_id": "BAP-MISS-FULLER-VOL06", "decided_by": "David / HQ", "date": "2026-09-02", "track": "tsu", "authority_class": "historical_witness", "content_genre": ["commentary"], "tradition": "Particular Baptist", "processing_status": "HOLD", "rationale": "HQ admission-in-principle 2026-09-02 (ADR-030 v2.1 §12 N-9). Registration QUALITY_PASSED; no TSU verified, no embedding, no reprocessing. TSU generation/verification, human review, embedding, production ingestion all HOLD pending ADR-029 PHASE order.", "evidence_refs": ["NAE/pipeline/registration/state/source_manifest.yaml", ".automation/evidence/NAE-REG-BAP-MISS-FULLER-VOL06.jsonl", "docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md"]}
{"source_id": "BAP-MISS-FULLER-VOL07", "decided_by": "David / HQ", "date": "2026-09-02", "track": "tsu", "authority_class": "historical_witness", "content_genre": ["sermon"], "tradition": "Particular Baptist", "processing_status": "HOLD", "rationale": "HQ admission-in-principle 2026-09-02 (ADR-030 v2.1 §12 N-9). Registration QUALITY_PASSED; no TSU verified, no embedding, no reprocessing. TSU generation/verification, human review, embedding, production ingestion all HOLD pending ADR-029 PHASE order.", "evidence_refs": ["NAE/pipeline/registration/state/source_manifest.yaml", ".automation/evidence/NAE-REG-BAP-MISS-FULLER-VOL07.jsonl", "docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md"]}
{"source_id": "BAP-MISS-FULLER-VOL08", "decided_by": "David / HQ", "date": "2026-09-02", "track": "tsu", "authority_class": "historical_witness", "content_genre": ["theology", "sermon", "mission"], "theological_category": ["missions"], "tradition": "Particular Baptist", "processing_status": "HOLD", "rationale": "HQ admission-in-principle 2026-09-02 (ADR-030 v2.1 §12 N-9). Registration QUALITY_PASSED; no TSU verified, no embedding, no reprocessing. TSU generation/verification, human review, embedding, production ingestion all HOLD pending ADR-029 PHASE order.", "evidence_refs": ["NAE/pipeline/registration/state/source_manifest.yaml", ".automation/evidence/NAE-REG-BAP-MISS-FULLER-VOL08.jsonl", "docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md"]}
```

**정합 확인 (M2 SSOT):** authority_class = `historical_witness` (8/8). content_genre: VOL01–04 `[theology]`,
VOL05–06 `[commentary]`, VOL07 `[sermon]`, VOL08 `[theology, sermon, mission]`. theological_category:
VOL01/02 `[soteriology]`, VOL08 `[missions]`, **VOL03–07 = M2에 키 없음 → 레코드에서도 키 생략**
(`null`/`[]` 금지, M3-4 원칙). tradition = `"Particular Baptist"` (8/8).

---

## 5. `tests/test_corpus_admissions.py` — 개정 명세 (C1 EXEC 소비, verbatim 수준)

현행 210줄. 아래 항목만 변경. 그 외 클래스·헬퍼 무변경.

| # | 현행 | 개정 |
|---|---|---|
| T-1 | `TestRecordCount.test_exactly_six_records`: `len(records) == 6` | `== 14` (메서드명 `test_exactly_fourteen_records`). 상단 docstring "exactly 6 records" → "6 legacy + 8 Fuller-HOLD = 14". |
| T-2 | `TestUniqueIds.test_all_unique`: `len(set(ids)) == len(ids) == 6` | `== 14` |
| T-3 | `TestUniqueIds.test_expected_sources`: 6-id 리스트 | 리스트에 `BAP-MISS-FULLER-VOL01`…`-VOL08` 8개 추가 (정렬 유지) |
| T-4 | `TestNoFuller.test_no_fuller_source_id` (Fuller 금지) | **클래스 교체** → `TestFullerAdmissionHold`: (a) `BAP-MISS-FULLER-VOL0[1-8]` 정확히 8건 존재, (b) 8건 전부 `track == "tsu"`, (c) 8건 전부 `processing_status == "HOLD"`, (d) legacy 6건은 `"processing_status" not in rec`. |
| T-5 | `TestDate.test_all_2026_08_28`: 전 레코드 `date == "2026-08-28"` | cohort 분리: legacy 6건(`processing_status` 키 없음) `== "2026-08-28"`; Fuller 8건(`processing_status == "HOLD"`) `== "2026-09-02"` (§9 OPEN-1). |
| T-6 | `TestReferenceQualityConfirmed.test_tsu_no_rqc_key`: `len(tsu) == 2` | `== 10`. "no rqc key" 단언은 유지(Fuller tsu track도 `reference_quality_confirmed` 키 없음). |
| T-7 | `TestReferenceQualityConfirmed.test_smith_has_rqc_true`: `len(reference) == 4` | 무변경 (reference track 여전히 4). |
| T-8 | `TestMissingMetadataKeyOmission.test_tsu_has_required_meta`: tsu track은 `theological_category` present & non-empty **필수** | **완화**: tsu track `theological_category` = "있으면 non-empty, 없으면 키 생략 허용" (M2 SSOT 반영 — Fuller VOL03–07은 M2에 키 없음). `tradition` present & non-empty 요구는 유지(8/8 존재). 신규 메서드 `test_tsu_theological_category_optional_but_wellformed`. |
| T-9 | `TestSnapshotMatchesM2` | Fuller 루프 추가: `for v in 1..8` → `BAP-MISS-FULLER-VOL0{v}` 레코드의 `authority_class` == M2, `set(content_genre)` == `set(M2 content_genre)`. theological_category는 M2에 있을 때만(VOL01/02/08) 일치 확인. |
| T-10 | `TestEvidenceRefsExist.test_all_evidence_refs_exist` | 무변경 (Fuller evidence_refs 3경로 전부 실존 확인 완료). |
| T-11 | `TestRequiredFields` | 무변경 (`REQUIRED_KEYS` 8개 그대로; Fuller 레코드 8키 전부 보유). `test_track_enum` 무변경. |
| T-12 | (신규) `TestProcessingStatus` | `processing_status` 값 ∈ {`"HOLD"`, `"RELEASED"`} (키 있을 때만). HOLD 레코드는 `track` 무관하게 §5 게이트 차단 대상임을 문서화하는 주석 포함. |

---

## 6. `scripts/nae_corpus_reconcile.py` (M-4, read-only) 영향

- **GC-1** (admission source_id ⊆ M2): Fuller 8건 전부 M2 존재 → PASS, 변화 없음.
- **GC-2** (verified TSU 있는데 admission 없음 = DRIFT): Fuller verified TSU = 0 → 트리거 안 됨.
- **GC-3** (tsu-track admission인데 TSU 디렉터리 없음 = **INFO only**): Fuller VOL02–08은 TSU 디렉터리 없음
  → GC-3 INFO 라인 7건 발생. **실패 아님(INFO)**. 
  - 권고(비필수, §9 OPEN-3): GC-3에 `processing_status == "HOLD"` 인 tsu-admission은
    "expected: HOLD" 로 라벨(INFO 문구만 조정, 로직·exit code 불변). 별도 S-item으로 분리 가능.
- `--apply` 없음, mutation 0 — 불변.

---

## 7. ADR-030 문서 정합 (M-3-EXT EXEC에 포함)

| 위치 | 변경 |
|---|---|
| §11.3 스키마 표 (line ~153) | 항목 스키마에 `processing_status?` 추가: `{… , tradition, reference_quality_confirmed?, processing_status?: "HOLD"\|"RELEASED", rationale, evidence_refs[]}` |
| §12 N-9 행 (커밋 `31ac18f`에서 갱신됨) | "admission-in-principle … ledger 기입 + 수기 게이트 활성화는 M3 모델 확장 후" → "admission 기록 완료(`corpus_admissions.jsonl`, `processing_status=HOLD`, 2026-09-02). TSU/verify/review/embedding/ingestion HOLD 유지. HOLD→RELEASED = HQ 별도 결정." |
| §13 Migration Policy | 1줄 추가: "`corpus_admissions.jsonl` Fuller 8건은 `processing_status=HOLD` append — 재처리·embedding·Qdrant 접촉 아님. 기존 6줄·3,319 TSU 무변경." |
| `CUE-ADR-030-M3-CORPUS-ADMISSIONS.md` §2/§5 | §2 스키마 표에 `processing_status` 행 추가, §5 게이트 규칙 문구를 본 문서 §2 NEW로 교체, §3.3을 "Fuller admission = 2026-09-02 기록, processing_status=HOLD"로 갱신. |

---

## 8. 이 확장이 **하지 않는** 것

- TSU 생성·검수, human review, embedding, Qdrant/production ingestion — 전부 HOLD, 접촉 0.
- 기존 6개 admission 레코드 — 무변경.
- 3,319 production TSU / `nae_tsu_v1` / `nae_ref_v1` / `incremental_state.json` / state store — 무접촉.
- M2 `source_manifest.yaml` — 읽기만 (VOL03–07 `theological_category` backfill은 **안 함**; §9 OPEN-4).
- 코드 게이트(ADR-019 `TSU_ELIGIBLE`) — 여전히 S-4 deferred. §5는 수기 게이트.
- `config.yaml` / runtime — 무변경.

---

## 9. HQ 비준 대기 — OPEN ITEMS

| # | 항목 | CUE 권고 |
|---|---|---|
| **OPEN-1** | Fuller admission `date` = `2026-09-02` (HQ 결정일, PR #4에 이미 기록) vs `2026-08-29` (PHASE 7 스크립트) | **`2026-09-02`**. `2026-08-29`는 근거 미확인 — 채택 시 HQ가 근거 명시 필요. |
| **OPEN-2** | `volume` 스키마 키 도입 여부 | **도입 안 함.** `source_id` 유지 (기존 전 계층과 정합). |
| **OPEN-3** | HOLD 표현 = `processing_status: "HOLD"` 필드 (본안) vs 별도 파일/enum | **`processing_status` optional 필드.** 키 생략 = RELEASED(레거시). |
| **OPEN-4** | Fuller VOL03–07 `theological_category` — test 완화(키 생략 허용) vs M2 backfill | **test 완화.** M2가 SSOT이고 값을 지어내지 않음. backfill은 분류 권위(`CUE-ADR-030-A2B2-CLASSIFICATION-RULE`) 경유 별건. |
| **OPEN-5** | HOLD→RELEASED 전환 메커니즘 = 해당 레코드 in-place 갱신 vs 신규 append(supersede) | append-only 원칙상 **신규 append + `supersedes` 참조** 권고. 단 M-3-EXT 범위 아님 — 전환 실제 발생 시 별도 EXEC. |
| **OPEN-6** | `nae_corpus_reconcile.py` GC-3 문구 조정(HOLD 인지) 포함 여부 | 이번 EXEC에 **미포함** 권고(INFO라 무해). 원하면 S-item. |

---

## 10. M-3-EXT EXEC (차기 C1 명령서 범위 — 본 문서 아님)

HQ 비준 후 발부할 C1 EXEC ORDER가 수행:

1. `NAE/governance/corpus_admissions.jsonl` — 기존 6줄 뒤 §4의 8줄 append (14줄, 끝 개행 1개).
2. `tests/test_corpus_admissions.py` — §5 표 T-1~T-12 개정.
3. `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` — §7 표 4개 위치.
4. `docs/agents/cue/CUE-ADR-030-M3-CORPUS-ADMISSIONS.md` — §7 마지막 행(§2/§5/§3.3).
5. (OPEN-6 채택 시) `scripts/nae_corpus_reconcile.py` GC-3 INFO 문구.
6. C1: `pytest tests/test_corpus_admissions.py tests/test_nae_corpus_reconcile.py -q` PASS 확인. **commit 안 함.**
7. 쳗 독립검증(5-invariant + pytest) → HQ 승인 → commit `M-3-EXT: Fuller Vol01–08 admission (processing_status=HOLD)`.

**금지(EXEC)**: TSU/Qdrant/state store 접촉, M2 backfill, 기존 6줄 수정, `config.yaml`, 무관 파일, push 전 commit.

---

## 11. Mutation

```text
본 DRAFT 산출물: 1 file (docs/agents/cue/CUE-ADR-030-M3-EXT-FULLER-ADMISSION-HOLD.md)
production / qdrant / tsu / canonical / config mutation: 0
corpus_admissions.jsonl: 미변경 (6 lines)
3,319 production TSUs: UNCHANGED
```

END OF DRAFT — HQ 비준 대기 (§9)
