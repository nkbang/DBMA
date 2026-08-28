"""
test_corpus_admissions.py — ADR-030 v2.1 §12 M-3 governance test

Verifies:
  1. corpus_admissions.jsonl has exactly 6 records
  2. All source_ids are unique
  3. No Fuller Vol.1–8 admission records
  4. decided_by = "David / HQ" for all 6
  5. date = "2026-08-28" for all 6
  6. Smith (reference track) has reference_quality_confirmed = true
  7. Dagg/Hiscox (tsu track) do NOT have reference_quality_confirmed key
  8. Missing metadata keys (theological_category, tradition) = key omission (not null/[]/"")
  9. Snapshot ↔ M2 classification match
 10. All evidence_refs paths exist
"""

import json
import os
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADMISSIONS_FILE = ROOT / "NAE" / "governance" / "corpus_admissions.jsonl"
M2_FILE = ROOT / "NAE" / "pipeline" / "registration" / "state" / "source_manifest.yaml"


@pytest.fixture(scope="module")
def records():
    """Load all non-empty lines from corpus_admissions.jsonl as parsed JSON."""
    assert ADMISSIONS_FILE.exists(), f"{ADMISSIONS_FILE} must exist"
    lines = [l for l in ADMISSIONS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [json.loads(l) for l in lines]


# ── 1. Record count ──────────────────────────────────────────────────────────

class TestRecordCount:
    def test_exactly_six_records(self, records):
        assert len(records) == 6, f"Expected 6 records, got {len(records)}"


# ── 2. Unique source_ids ─────────────────────────────────────────────────────

class TestUniqueIds:
    def test_all_unique(self, records):
        ids = [r["source_id"] for r in records]
        assert len(set(ids)) == len(ids) == 6

    def test_expected_sources(self, records):
        ids = sorted(r["source_id"] for r in records)
        expected = [
            "BAP-CHURCH-DAGG-001",
            "BAP-CHURCH-HISCOX",
            "BAP-REF-SMITH-VOL01",
            "BAP-REF-SMITH-VOL02",
            "BAP-REF-SMITH-VOL03",
            "BAP-REF-SMITH-VOL04",
        ]
        assert ids == expected


# ── 3. No Fuller records ─────────────────────────────────────────────────────

class TestNoFuller:
    def test_no_fuller_source_id(self, records):
        ids = [r["source_id"] for r in records]
        assert not any(i.startswith("BAP-MISS-FULLER") for i in ids), \
            "Fuller Vol.1–8 must NOT have admission records"


# ── 4. decided_by = "David / HQ" ─────────────────────────────────────────────

class TestDecidedBy:
    def test_all_david_hq(self, records):
        assert all(r["decided_by"] == "David / HQ" for r in records), \
            "All records must have decided_by = 'David / HQ'"


# ── 5. date = "2026-08-28" ──────────────────────────────────────────────────

class TestDate:
    def test_all_2026_08_28(self, records):
        assert all(r["date"] == "2026-08-28" for r in records), \
            "All records must have date = '2026-08-28'"


# ── 6. reference_quality_confirmed rules ─────────────────────────────────────

class TestReferenceQualityConfirmed:
    def test_smith_has_rqc_true(self, records):
        smith = [r for r in records if r["track"] == "reference"]
        assert len(smith) == 4, f"Expected 4 reference track records, got {len(smith)}"
        assert all(r.get("reference_quality_confirmed") is True for r in smith), \
            "All Smith (reference) records must have reference_quality_confirmed = true"

    def test_tsu_no_rqc_key(self, records):
        tsu = [r for r in records if r["track"] == "tsu"]
        assert len(tsu) == 2, f"Expected 2 tsu track records, got {len(tsu)}"
        assert all("reference_quality_confirmed" not in r for r in tsu), \
            "TSU track records must NOT have reference_quality_confirmed key"


# ── 7. Missing metadata = key omission (not null/[]/"") ─────────────────────

class TestMissingMetadataKeyOmission:
    def test_smith_no_theological_category_key(self, records):
        smith = [r for r in records if r["track"] == "reference"]
        for r in smith:
            assert "theological_category" not in r, \
                f"{r['source_id']}: theological_category must be omitted (key absent)"

    def test_smith_no_tradition_key(self, records):
        smith = [r for r in records if r["track"] == "reference"]
        for r in smith:
            assert "tradition" not in r, \
                f"{r['source_id']}: tradition must be omitted (key absent)"

    def test_tsu_has_required_meta(self, records):
        tsu = [r for r in records if r["track"] == "tsu"]
        for r in tsu:
            assert "theological_category" in r and r["theological_category"] not in (None, [], ""), \
                f"{r['source_id']}: theological_category must be present and non-empty"
            assert "tradition" in r and r["tradition"] not in (None, "", []), \
                f"{r['source_id']}: tradition must be present and non-empty"



# ── 8. Snapshot ↔ M2 classification match ────────────────────────────────────

class TestSnapshotMatchesM2:
    """Admission record classification values must match M2 (SSOT) at the time of decision."""

    @pytest.fixture(scope="module")
    def m2_sources(self):
        """Load M2 source_manifest.yaml and index by source_id."""
        import yaml
        assert M2_FILE.exists(), f"{M2_FILE} must exist"
        data = yaml.safe_load(M2_FILE.read_text(encoding="utf-8"))
        return {s["source_id"]: s for s in data["sources"]}

    def test_dagg_authority_class(self, records, m2_sources):
        rec = next(r for r in records if r["source_id"] == "BAP-CHURCH-DAGG-001")
        m2 = m2_sources["BAP-CHURCH-DAGG-001"]
        assert rec["authority_class"] == m2["authority_class"], \
            f"Dagg authority_class mismatch: admission={rec['authority_class']}, M2={m2['authority_class']}"

    def test_dagg_content_genre(self, records, m2_sources):
        rec = next(r for r in records if r["source_id"] == "BAP-CHURCH-DAGG-001")
        m2 = m2_sources["BAP-CHURCH-DAGG-001"]
        assert set(rec["content_genre"]) == set(m2["content_genre"]), \
            f"Dagg content_genre mismatch"

    def test_hiscox_authority_class(self, records, m2_sources):
        rec = next(r for r in records if r["source_id"] == "BAP-CHURCH-HISCOX")
        m2 = m2_sources["BAP-CHURCH-HISCOX"]
        assert rec["authority_class"] == m2["authority_class"]

    def test_hiscox_content_genre(self, records, m2_sources):
        rec = next(r for r in records if r["source_id"] == "BAP-CHURCH-HISCOX")
        m2 = m2_sources["BAP-CHURCH-HISCOX"]
        assert set(rec["content_genre"]) == set(m2["content_genre"])

    def test_smith_authority_class(self, records, m2_sources):
        for vol in range(1, 5):
            sid = f"BAP-REF-SMITH-VOL{vol:02d}"
            rec = next(r for r in records if r["source_id"] == sid)
            m2 = m2_sources[sid]
            assert rec["authority_class"] == m2["authority_class"], \
                f"{sid} authority_class mismatch"

    def test_smith_content_genre(self, records, m2_sources):
        for vol in range(1, 5):
            sid = f"BAP-REF-SMITH-VOL{vol:02d}"
            rec = next(r for r in records if r["source_id"] == sid)
            m2 = m2_sources[sid]
            assert set(rec["content_genre"]) == set(m2["content_genre"]), \
                f"{sid} content_genre mismatch"



# ── 9. evidence_refs paths all exist ─────────────────────────────────────────

class TestEvidenceRefsExist:
    def test_all_evidence_refs_exist(self, records):
        """Every path in every record's evidence_refs must exist on disk."""
        for rec in records:
            for ref in rec["evidence_refs"]:
                ref_path = ROOT / ref
                assert ref_path.exists() or pathlib.Path(ref).is_dir(), \
                    f"{rec['source_id']}: evidence_ref '{ref}' does not exist"


# ── 10. Required fields present ──────────────────────────────────────────────

class TestRequiredFields:
    REQUIRED_KEYS = {"source_id", "decided_by", "date", "track", "authority_class",
                     "content_genre", "rationale", "evidence_refs"}

    def test_all_required_keys_present(self, records):
        for rec in records:
            missing = self.REQUIRED_KEYS - set(rec.keys())
            assert not missing, f"{rec['source_id']}: missing required keys: {missing}"

    def test_track_enum(self, records):
        valid_tracks = {"tsu", "reference"}
        for rec in records:
            assert rec["track"] in valid_tracks, \
                f"{rec['source_id']}: track must be 'tsu' or 'reference', got {rec['track']}"

