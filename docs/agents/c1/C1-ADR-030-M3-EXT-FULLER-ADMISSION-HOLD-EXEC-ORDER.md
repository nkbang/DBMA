# 쳗 → C1 EXEC ORDER — ADR-030 M-3-EXT · Fuller Vol01–08 admission (processing_status=HOLD)

> **baseline**: worktree `claude/fuller-admission-n9-docs` (dev/dbma-engine 계열) @ `31ac18f`.
> **권위**: HQ RATIFICATION 2026-09-02 — `docs/agents/cue/CUE-ADR-030-M3-EXT-FULLER-ADMISSION-HOLD.md` §9 = RATIFIED.
> 설계 = 그 문서. **C1 은 governance/schema 를 해석하지 않는다.** 아래 verbatim 블록만 적용한다.
> **운영**: single EXEC. **commit 금지 · push 금지.** pytest 는 실행한다.
> **작성**: 쳗 · 2026-09-02

---

## 0. Workspace Verification Gate

```bash
pwd                                   # …/.claude/worktrees/…/fuller-admission-n9-docs
git rev-parse --abbrev-ref HEAD       # claude/fuller-admission-n9-docs
git rev-parse --short HEAD            # 31ac18f
git status --porcelain               # 기대: ?? docs/agents/c1/... , ?? docs/agents/cue/CUE-ADR-030-M3-EXT-... 만
grep -c . NAE/governance/corpus_admissions.jsonl   # 기대: 6
```

하나라도 불일치 → 편집 금지, 즉시 중단·보고.
무관 미커밋 항목 발견 시 stage·revert·수정 금지, 그대로 둔다.

---

## 1. MANDATE — 정확히 4개 대상

| # | 파일 | 조치 |
|---|---|---|
| A | `NAE/governance/corpus_admissions.jsonl` | 기존 6줄 **뒤에** §2의 8줄 append. 총 14줄. 파일 끝 개행 1개. 기존 6줄 **1바이트도 수정 금지**. |
| B | `tests/test_corpus_admissions.py` | §3 전문으로 **전체 덮어쓰기**. |
| C | `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` | §4의 치환 C-1 / C-2 / C-3. |
| D | `docs/agents/cue/CUE-ADR-030-M3-CORPUS-ADMISSIONS.md` | §5의 치환 D-1 / D-2 / D-3 / D-4. |

OLD 블록이 파일에서 정확히 일치하지 않으면 **조정하지 말고 STOP·보고**.

---

## 2. 대상 A — `corpus_admissions.jsonl` append (8줄 verbatim)

기존 6줄 다음 줄부터 아래를 그대로 붙인다. 순서·공백·키 순서 변경 금지.

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

**주의**: VOL03–07 에는 `theological_category` 키가 **없다** (M2에 없음 — RATIFIED §4). 임의 추가 금지.

---

## 3. 대상 B — `tests/test_corpus_admissions.py` 전체 덮어쓰기 (verbatim)

```python
"""
test_corpus_admissions.py — ADR-030 v2.1 §12 M-3 / M-3-EXT governance test

Verifies:
  1. corpus_admissions.jsonl has exactly 14 records (6 legacy + 8 Fuller HOLD)
  2. All source_ids are unique; expected id set
  3. Fuller Vol01–08 present, all track=tsu, all processing_status=HOLD;
     legacy 6 carry no processing_status key
  4. decided_by = "David / HQ" for all
  5. date cohort: key-omitted/RELEASED = 2026-08-28; HOLD = 2026-09-02
  6. reference_quality_confirmed: reference track true; tsu track never has the key
  7. Missing metadata = key omission (never null/[]/"")
     - reference track: theological_category + tradition omitted
     - tsu track: tradition required non-empty; theological_category optional, non-empty when present
  8. Snapshot <-> M2 classification match (Dagg, Hiscox, Smith x4, Fuller x8)
  9. All evidence_refs paths exist
 10. Required fields present; track enum
 11. processing_status enum + gate semantics (ADR-030 M-3-EXT §2, RATIFIED 2026-09-02)
"""

import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADMISSIONS_FILE = ROOT / "NAE" / "governance" / "corpus_admissions.jsonl"
M2_FILE = ROOT / "NAE" / "pipeline" / "registration" / "state" / "source_manifest.yaml"

FULLER_IDS = [f"BAP-MISS-FULLER-VOL{v:02d}" for v in range(1, 9)]
LEGACY_IDS = [
    "BAP-CHURCH-DAGG-001",
    "BAP-CHURCH-HISCOX",
    "BAP-REF-SMITH-VOL01",
    "BAP-REF-SMITH-VOL02",
    "BAP-REF-SMITH-VOL03",
    "BAP-REF-SMITH-VOL04",
]


@pytest.fixture(scope="module")
def records():
    assert ADMISSIONS_FILE.exists(), f"{ADMISSIONS_FILE} must exist"
    lines = [l for l in ADMISSIONS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [json.loads(l) for l in lines]


def _fuller(records):
    return [r for r in records if r["source_id"].startswith("BAP-MISS-FULLER")]


def _legacy(records):
    return [r for r in records if not r["source_id"].startswith("BAP-MISS-FULLER")]


# -- 1. Record count ---------------------------------------------------------

class TestRecordCount:
    def test_exactly_fourteen_records(self, records):
        assert len(records) == 14, f"Expected 14 records (6 legacy + 8 Fuller), got {len(records)}"


# -- 2. Unique source_ids --------------------------------------------------

class TestUniqueIds:
    def test_all_unique(self, records):
        ids = [r["source_id"] for r in records]
        assert len(set(ids)) == len(ids) == 14

    def test_expected_sources(self, records):
        ids = sorted(r["source_id"] for r in records)
        assert ids == sorted(LEGACY_IDS + FULLER_IDS)


# -- 3. Fuller admission = ADMITTED + HOLD --------------------------------

class TestFullerAdmissionHold:
    def test_fuller_eight_present(self, records):
        assert sorted(r["source_id"] for r in _fuller(records)) == FULLER_IDS

    def test_fuller_all_tsu_track(self, records):
        assert all(r["track"] == "tsu" for r in _fuller(records))

    def test_fuller_all_hold(self, records):
        assert all(r.get("processing_status") == "HOLD" for r in _fuller(records))

    def test_legacy_no_processing_status_key(self, records):
        for r in _legacy(records):
            assert "processing_status" not in r, \
                f"{r['source_id']}: legacy record must omit processing_status (key omitted = RELEASED)"


# -- 4. decided_by --------------------------------------------------------

class TestDecidedBy:
    def test_all_david_hq(self, records):
        assert all(r["decided_by"] == "David / HQ" for r in records)


# -- 5. date cohorts ----------------------------------------------------

class TestDate:
    def test_released_cohort_date(self, records):
        for r in records:
            if "processing_status" not in r:
                assert r["date"] == "2026-08-28", \
                    f"{r['source_id']}: released/legacy date must be 2026-08-28"

    def test_hold_cohort_date(self, records):
        for r in records:
            if r.get("processing_status") == "HOLD":
                assert r["date"] == "2026-09-02", \
                    f"{r['source_id']}: HOLD date must be 2026-09-02"


# -- 6. reference_quality_confirmed rules -------------------------------

class TestReferenceQualityConfirmed:
    def test_smith_has_rqc_true(self, records):
        smith = [r for r in records if r["track"] == "reference"]
        assert len(smith) == 4, f"Expected 4 reference track records, got {len(smith)}"
        assert all(r.get("reference_quality_confirmed") is True for r in smith)

    def test_tsu_no_rqc_key(self, records):
        tsu = [r for r in records if r["track"] == "tsu"]
        assert len(tsu) == 10, f"Expected 10 tsu track records (2 legacy + 8 Fuller), got {len(tsu)}"
        assert all("reference_quality_confirmed" not in r for r in tsu)


# -- 7. Missing metadata = key omission (never null/[]/"") -------------

class TestMissingMetadataKeyOmission:
    def test_reference_no_theological_category_key(self, records):
        for r in [x for x in records if x["track"] == "reference"]:
            assert "theological_category" not in r, \
                f"{r['source_id']}: theological_category must be omitted (key absent)"

    def test_reference_no_tradition_key(self, records):
        for r in [x for x in records if x["track"] == "reference"]:
            assert "tradition" not in r, \
                f"{r['source_id']}: tradition must be omitted (key absent)"

    def test_tsu_tradition_required(self, records):
        for r in [x for x in records if x["track"] == "tsu"]:
            assert "tradition" in r and r["tradition"] not in (None, "", []), \
                f"{r['source_id']}: tsu-track tradition must be present and non-empty"

    def test_tsu_theological_category_optional_but_wellformed(self, records):
        # ADR-030 M-3-EXT RATIFICATION 4 (2026-09-02): tsu-track theological_category
        # is evidence-bound -- present & non-empty when M2 carries it, key omitted
        # otherwise. null / [] / "" are never allowed.
        for r in [x for x in records if x["track"] == "tsu"]:
            if "theological_category" in r:
                assert r["theological_category"] not in (None, [], ""), \
                    f"{r['source_id']}: theological_category present but empty/null"


# -- 8. Snapshot <-> M2 classification match --------------------------

class TestSnapshotMatchesM2:
    """Admission record classification values must match M2 (SSOT) at decision time."""

    @pytest.fixture(scope="module")
    def m2_sources(self):
        import yaml
        assert M2_FILE.exists(), f"{M2_FILE} must exist"
        data = yaml.safe_load(M2_FILE.read_text(encoding="utf-8"))
        return {s["source_id"]: s for s in data["sources"]}

    def test_dagg_authority_class(self, records, m2_sources):
        rec = next(r for r in records if r["source_id"] == "BAP-CHURCH-DAGG-001")
        assert rec["authority_class"] == m2_sources["BAP-CHURCH-DAGG-001"]["authority_class"]

    def test_dagg_content_genre(self, records, m2_sources):
        rec = next(r for r in records if r["source_id"] == "BAP-CHURCH-DAGG-001")
        assert set(rec["content_genre"]) == set(m2_sources["BAP-CHURCH-DAGG-001"]["content_genre"])

    def test_hiscox_authority_class(self, records, m2_sources):
        rec = next(r for r in records if r["source_id"] == "BAP-CHURCH-HISCOX")
        assert rec["authority_class"] == m2_sources["BAP-CHURCH-HISCOX"]["authority_class"]

    def test_hiscox_content_genre(self, records, m2_sources):
        rec = next(r for r in records if r["source_id"] == "BAP-CHURCH-HISCOX")
        assert set(rec["content_genre"]) == set(m2_sources["BAP-CHURCH-HISCOX"]["content_genre"])

    def test_smith_authority_class(self, records, m2_sources):
        for vol in range(1, 5):
            sid = f"BAP-REF-SMITH-VOL{vol:02d}"
            rec = next(r for r in records if r["source_id"] == sid)
            assert rec["authority_class"] == m2_sources[sid]["authority_class"], f"{sid} authority_class"

    def test_smith_content_genre(self, records, m2_sources):
        for vol in range(1, 5):
            sid = f"BAP-REF-SMITH-VOL{vol:02d}"
            rec = next(r for r in records if r["source_id"] == sid)
            assert set(rec["content_genre"]) == set(m2_sources[sid]["content_genre"]), f"{sid} content_genre"

    def test_fuller_authority_class(self, records, m2_sources):
        for sid in FULLER_IDS:
            rec = next(r for r in records if r["source_id"] == sid)
            assert rec["authority_class"] == m2_sources[sid]["authority_class"], f"{sid} authority_class"

    def test_fuller_content_genre(self, records, m2_sources):
        for sid in FULLER_IDS:
            rec = next(r for r in records if r["source_id"] == sid)
            assert set(rec["content_genre"]) == set(m2_sources[sid]["content_genre"]), f"{sid} content_genre"

    def test_fuller_theological_category_evidence_bound(self, records, m2_sources):
        for sid in FULLER_IDS:
            rec = next(r for r in records if r["source_id"] == sid)
            m2_val = m2_sources[sid].get("theological_category")
            if m2_val:
                assert set(rec.get("theological_category", [])) == set(m2_val), \
                    f"{sid}: theological_category mismatch vs M2"
            else:
                assert "theological_category" not in rec, \
                    f"{sid}: M2 has no theological_category -> record must omit the key"


# -- 9. evidence_refs paths all exist --------------------------------

class TestEvidenceRefsExist:
    def test_all_evidence_refs_exist(self, records):
        for rec in records:
            for ref in rec["evidence_refs"]:
                ref_path = ROOT / ref
                assert ref_path.exists() or pathlib.Path(ref).is_dir(), \
                    f"{rec['source_id']}: evidence_ref '{ref}' does not exist"


# -- 10. Required fields present -----------------------------------

class TestRequiredFields:
    REQUIRED_KEYS = {"source_id", "decided_by", "date", "track", "authority_class",
                     "content_genre", "rationale", "evidence_refs"}

    def test_all_required_keys_present(self, records):
        for rec in records:
            missing = self.REQUIRED_KEYS - set(rec.keys())
            assert not missing, f"{rec['source_id']}: missing required keys: {missing}"

    def test_track_enum(self, records):
        for rec in records:
            assert rec["track"] in {"tsu", "reference"}, \
                f"{rec['source_id']}: bad track {rec['track']}"


# -- 11. processing_status enum + gate semantics -----------------

class TestProcessingStatus:
    """ADR-030 M-3-EXT §2 (RATIFIED 2026-09-02).

    Gate rule:  admission record absent  OR  processing_status == "HOLD"
                -> processing PROHIBITED (TSU gen/verify, human review,
                   reference chunking, embedding, production ingestion).
                key omitted (legacy) or == "RELEASED" -> may proceed.
    HOLD -> RELEASED requires a separate explicit HQ decision.
    """

    def test_enum_when_present(self, records):
        for r in records:
            if "processing_status" in r:
                assert r["processing_status"] in {"HOLD", "RELEASED"}, \
                    f"{r['source_id']}: processing_status must be HOLD or RELEASED"

    def test_hold_records_are_exactly_fuller_tsu(self, records):
        hold = [r for r in records if r.get("processing_status") == "HOLD"]
        assert {r["source_id"] for r in hold} == set(FULLER_IDS)
        assert all(r["track"] == "tsu" for r in hold)

    def test_no_released_value_yet(self, records):
        assert not any(r.get("processing_status") == "RELEASED" for r in records), \
            "No HOLD -> RELEASED transition is authorized under M-3-EXT"
```

---

## 4. 대상 C — `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md`

### 치환 C-1 — §6.1 Admission Decision 스키마 행

OLD:
```
| 기록 위치 | `NAE/governance/corpus_admissions.jsonl` (append-only, 신규 — §12 MUST M-3). 항목: `{source_id, decided_by, date, track: "tsu"\|"reference", authority_class, content_genre[], theological_category[], tradition, reference_quality_confirmed?, rationale, evidence_refs[]}` |
```
NEW:
```
| 기록 위치 | `NAE/governance/corpus_admissions.jsonl` (append-only, 신규 — §12 MUST M-3). 항목: `{source_id, decided_by, date, track: "tsu"\|"reference", authority_class, content_genre[], theological_category[], tradition, reference_quality_confirmed?, processing_status?: "HOLD"\|"RELEASED", rationale, evidence_refs[]}`. M-3-EXT(2026-09-02, RATIFIED): `processing_status?` 추가 — 키 생략 = RELEASED(레거시 기본값), `"HOLD"` = admission 기록됨·§5 게이트 미개방. HOLD→RELEASED = 별도 HQ 결정. |
```

### 치환 C-2 — §12 N-9 행

OLD:
```
| N-9 | Fuller Vol01–08 TSU/embedding, M3 CLAIM-ONLY 19건 acquisition | admission-in-principle 승인 (HQ, 2026-09-02) — TSU generation / TSU verification / human review / embedding / production ingestion 전부 HOLD 유지. corpus_admissions.jsonl ledger 기입 + 수기 게이트 활성화는 M3 모델 확장(별도 CUE 단계) 후. provenance: `docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md`. backlog, ADR-029 PHASE 순서 |
```
NEW:
```
| N-9 | Fuller Vol01–08 TSU/embedding, M3 CLAIM-ONLY 19건 acquisition | admission 기록 완료 (HQ RATIFIED 2026-09-02) — `corpus_admissions.jsonl` 8건, `processing_status="HOLD"`, `date="2026-09-02"`. §5 확장 게이트상 HOLD = 미개방 → TSU generation / TSU verification / human review / embedding / production ingestion 전부 차단 유지. HOLD→RELEASED = 별도 HQ 결정. design: `docs/agents/cue/CUE-ADR-030-M3-EXT-FULLER-ADMISSION-HOLD.md`. provenance: `docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md`. backlog(처리): ADR-029 PHASE 순서 |
```

### 치환 C-3 — §13 Migration Policy (bullet 1개 뒤에 bullet 1개 추가)

OLD:
```
- **`corpus_admissions.jsonl`**: 신규 파일. 기존 3,319 + Smith는 back-fill **기록**만(재처리 아님, §11.4).
```
NEW:
```
- **`corpus_admissions.jsonl`**: 신규 파일. 기존 3,319 + Smith는 back-fill **기록**만(재처리 아님, §11.4).
- **`corpus_admissions.jsonl` M-3-EXT (2026-09-02, RATIFIED)**: Fuller Vol01–08 admission 8줄 append, `processing_status="HOLD"`. 기존 6줄·3,319 TSU 무변경. 재처리·embedding·Qdrant·state store 접촉 없음. TSU 생성/검수·human review·ingestion 은 HOLD 게이트로 차단.
```

---

## 5. 대상 D — `docs/agents/cue/CUE-ADR-030-M3-CORPUS-ADMISSIONS.md`

### 치환 D-1 — §1 "만들지 않는다" 의 Fuller 항목

OLD:
```
- Fuller Vol01–08 항목 — **넣지 않는다** (§3.3).
```
NEW:
```
- Fuller Vol01–08 항목 — M-3 시점에는 넣지 않았으나 **M-3-EXT(2026-09-02, RATIFIED)에서 `processing_status="HOLD"` 로 8건 추가** (§3.3, `docs/agents/cue/CUE-ADR-030-M3-EXT-FULLER-ADMISSION-HOLD.md`).
```

### 치환 D-2 — §2 스키마 표 (`reference_quality_confirmed` 행과 `rationale` 행 사이에 1행 삽입)

OLD:
```
| `reference_quality_confirmed` | bool | reference track만 | `true` (indexed·운영 중). tsu track 은 **키 생략** |
| `rationale` | string | ✔ | 이 admission 이 성립하는 근거 (한 문장) |
```
NEW:
```
| `reference_quality_confirmed` | bool | reference track만 | `true` (indexed·운영 중). tsu track 은 **키 생략** |
| `processing_status` | string | ✖ | `"HOLD"` \| `"RELEASED"`. **키 생략 = RELEASED (레거시 기본값).** `"HOLD"` = admission 기록됨, §5 게이트 미개방. HOLD→RELEASED = 별도 HQ 결정 (M-3-EXT, 2026-09-02 RATIFIED). |
| `rationale` | string | ✔ | 이 admission 이 성립하는 근거 (한 문장) |
```

### 치환 D-3 — §5 게이트 규칙 첫 bullet

OLD:
```
- **규칙**: `corpus_admissions.jsonl` 에 `source_id` 항목이 없는 source 는 TSU 생성(TSU Builder) 또는
  reference chunking 을 **시작하지 않는다.** 현재는 작업 착수 시 **수기 확인** (담당자가 이 파일을 대조).
```
NEW:
```
- **규칙**: `corpus_admissions.jsonl` 에 `source_id` 항목이 **없거나**, 항목의 `processing_status == "HOLD"` 인
  source 는 TSU 생성(TSU Builder) / TSU 검수 / human review / reference chunking / embedding /
  production ingestion 을 **시작하지 않는다.** `processing_status` 키가 없거나(레거시 = RELEASED) 또는
  `== "RELEASED"` 인 경우에만 다음 단계로 진행한다. HOLD→RELEASED 는 HQ 결정.
  현재는 작업 착수 시 **수기 확인** (담당자가 이 파일을 대조).
```

### 치환 D-4 — §3.3 말미 (마지막 bullet 뒤에 bullet 1개 추가)

OLD:
```
- 결과: admission 기록 없는 source(Fuller ×8)는 §5 수기 게이트에 의해 TSU review→embedding 으로 진행 불가 —
  이것이 게이트가 의도대로 동작한다는 증거.
```
NEW:
```
- 결과: admission 기록 없는 source(Fuller ×8)는 §5 수기 게이트에 의해 TSU review→embedding 으로 진행 불가 —
  이것이 게이트가 의도대로 동작한다는 증거.
- **UPDATE (M-3-EXT, 2026-09-02 RATIFIED)**: HQ가 Fuller Vol01–08 admission-in-principle 을 비준
  (`docs/agents/cue/CUE-ADR-030-M3-EXT-FULLER-ADMISSION-HOLD.md`). 8건이 `corpus_admissions.jsonl` 에
  `processing_status="HOLD"`, `date="2026-09-02"` 로 기록됨. §5 확장 규칙상 HOLD = 게이트 미개방이므로
  TSU 생성/검수·human review·embedding·ingestion 은 계속 차단. HOLD→RELEASED = 별도 HQ 결정.
```

---

## 6. VERIFY (C1 self-check)

```bash
grep -c . NAE/governance/corpus_admissions.jsonl          # 기대: 14
git diff --stat                                           # 기대: A/B/C/D 4파일만
python -m pytest tests/test_corpus_admissions.py tests/test_nae_corpus_reconcile.py -q
```

- pytest: `tests/test_corpus_admissions.py` 전부 PASS, `tests/test_nae_corpus_reconcile.py` 회귀 없음.
- `git status --porcelain` 에 A/B/C/D + 기존 `?? docs/agents/c1/...` `?? docs/agents/cue/CUE-ADR-030-M3-EXT-...` 외 항목 없음.
- 하나라도 불일치·FAIL → STOP, 값 자체 수정 금지, REPORT 로 보고.

---

## 7. DO NOT

TSU generation·verification · human review · embedding · reference chunking ·
Qdrant mutation · production/state store mutation · 3,319 baseline 변경 ·
`NAE/pipeline/registration/state/source_manifest.yaml` (M2) 편집 — **읽기 전용** ·
VOL03–07 `theological_category` 임의 backfill ·
기존 6개 admission 레코드 수정 ·
`scripts/nae_corpus_reconcile.py` 편집 ·
`config.yaml` / runtime ·
무관 미커밋 항목 stage·revert·수정 ·
**commit · push**.

HOLD→RELEASED 전환 금지. `processing_status="RELEASED"` 레코드 생성 금지.

---

## 8. REPORT (아래 형식만)

```text
C1 RESULT — M-3-EXT

STATUS: GREEN / BLOCKED

FILES:
- NAE/governance/corpus_admissions.jsonl        (6 -> 14 lines, +8 Fuller)
- tests/test_corpus_admissions.py               (full rewrite)
- docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md   (C-1/C-2/C-3)
- docs/agents/cue/CUE-ADR-030-M3-CORPUS-ADMISSIONS.md         (D-1/D-2/D-3/D-4)

PYTEST:
test_corpus_admissions.py     = <passed N>
test_nae_corpus_reconcile.py  = <passed N / no regression>

ADMISSION:
Fuller Vol.01–08 = ADMITTED, processing_status = HOLD

PROCESSING:
TSU generation = HOLD
TSU verification = HOLD
human review = HOLD
embedding = HOLD
production ingestion = HOLD

MUTATION:
production = 0
qdrant = 0
tsu = 0
M2 source_manifest = 0
existing 6 admission records = 0
config = 0
reconcile.py = 0
unrelated WIP = 0

BASELINE:
3,319 production TSUs = UNCHANGED
corpus_admissions.jsonl legacy 6 lines = UNCHANGED

GIT:
commit = NO
push = NO
diff = EXPECTED (4 files) / UNEXPECTED

EXCEPTION:
NONE / <one-line>
```
