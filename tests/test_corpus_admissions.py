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
