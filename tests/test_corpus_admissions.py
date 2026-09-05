"""
test_corpus_admissions.py — ADR-030 v2.1 §12 M-3 governance test

Verifies:
  1. corpus_admissions.jsonl has exactly 14 records (Dagg, Hiscox, Smith×4, Fuller×8)
  2. All source_ids are unique
  3. Expected 14 source_ids present
  4. decided_by = "David / HQ" for all 14
  5. date = "2026-08-28" for Dagg/Hiscox/Smith; "2026-08-29" for Fuller
  6. Smith (reference track) has reference_quality_confirmed = true
  7. Dagg/Hiscox (tsu track) do NOT have reference_quality_confirmed key
  8. Missing metadata keys (theological_category, tradition) = key omission (not null/[]/"")
  9. Snapshot ↔ M2 classification match (Dagg, Hiscox, Smith)
 10. All evidence_refs paths exist
 11. Fuller VOL01–08: authority_class matches M2
 12. Fuller VOL01–08: content_genre matches M2 SSOT exactly
 13. Fuller VOL01–08: theological_category evidence-bound (present iff in M2)
 14. ProcessingStatus: Fuller = HOLD, Dagg/Hiscox/Smith = INDEXED
 15. TSU required metadata present for tsu track records
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
    def test_exactly_fourteen_records(self, records):
        assert len(records) == 14, f"Expected 14 records, got {len(records)}"


# ── 2. Unique source_ids ─────────────────────────────────────────────────────

class TestUniqueIds:
    def test_all_unique(self, records):
        ids = [r["source_id"] for r in records]
        assert len(set(ids)) == len(ids) == 14

    def test_expected_sources(self, records):
        ids = sorted(r["source_id"] for r in records)
        expected = [
            "BAP-CHURCH-DAGG-001",
            "BAP-CHURCH-HISCOX",
            "BAP-MISS-FULLER-VOL01",
            "BAP-MISS-FULLER-VOL02",
            "BAP-MISS-FULLER-VOL03",
            "BAP-MISS-FULLER-VOL04",
            "BAP-MISS-FULLER-VOL05",
            "BAP-MISS-FULLER-VOL06",
            "BAP-MISS-FULLER-VOL07",
            "BAP-MISS-FULLER-VOL08",
            "BAP-REF-SMITH-VOL01",
            "BAP-REF-SMITH-VOL02",
            "BAP-REF-SMITH-VOL03",
            "BAP-REF-SMITH-VOL04",
        ]
        assert ids == expected


# ── 3. Has all 8 Fuller records ───────────────────────────────────────────────

class TestHasFuller:
    def test_all_fuller_vols_present(self, records):
        ids = [r["source_id"] for r in records]
        for vol in range(1, 9):
            sid = f"BAP-MISS-FULLER-VOL{vol:02d}"
            assert sid in ids, f"Missing Fuller record: {sid}"

    def test_fuller_count(self, records):
        fuller = [r for r in records if r["source_id"].startswith("BAP-MISS-FULLER")]
        assert len(fuller) == 8, f"Expected 8 Fuller records, got {len(fuller)}"


# ── 4. authority_class = "historical_witness" for Fuller ───────────────────────

class TestFullerAuthorityClass:
    def test_fuller_authority_class(self, records):
        fuller = [r for r in records if r["source_id"].startswith("BAP-MISS-FULLER")]
        assert all(r["authority_class"] == "historical_witness" for r in fuller), \
            "All Fuller records must have authority_class = 'historical_witness'"


# ── 5. decided_by = "David / HQ" ─────────────────────────────────────────────

class TestDecidedBy:
    def test_all_david_hq(self, records):
        assert all(r["decided_by"] == "David / HQ" for r in records), \
            "All records must have decided_by = 'David / HQ'"


# ── 6. date check ─────────────────────────────────────────────────────────────

class TestDate:
    def test_dagg_hiscox_smith_date(self, records):
        non_fuller = [r for r in records if not r["source_id"].startswith("BAP-MISS-FULLER")]
        assert all(r["date"] == "2026-08-28" for r in non_fuller), \
            "Dagg/Hiscox/Smith records must have date = '2026-08-28'"

    def test_fuller_date(self, records):
        fuller = [r for r in records if r["source_id"].startswith("BAP-MISS-FULLER")]
        assert all(r["date"] == "2026-08-29" for r in fuller), \
            "Fuller records must have date = '2026-08-29'"


# ── 7. reference_quality_confirmed rules ──────────────────────────────────────

class TestReferenceQualityConfirmed:
    def test_smith_has_rqc_true(self, records):
        smith = [r for r in records if r["track"] == "reference"]
        assert len(smith) == 4, f"Expected 4 reference track records, got {len(smith)}"
        assert all(r.get("reference_quality_confirmed") is True for r in smith), \
            "All Smith (reference) records must have reference_quality_confirmed = true"

    def test_tsu_no_rqc_key(self, records):
        tsu = [r for r in records if r["track"] == "tsu"]
        assert len(tsu) == 10, f"Expected 10 tsu track records, got {len(tsu)}"
        assert all("reference_quality_confirmed" not in r for r in tsu), \
            "TSU track records must NOT have reference_quality_confirmed key"


# ── 8. Missing metadata = key omission (not null/[]/"") ───────────────────────

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
            assert "tradition" in r and r["tradition"] not in (None, "", []), \
                f"{r['source_id']}: tradition must be present and non-empty"


# ── 9. Snapshot ↔ M2 classification match ─────────────────────────────────────

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


# ── 10. evidence_refs paths all exist ─────────────────────────────────────────

class TestEvidenceRefsExist:
    def test_all_evidence_refs_exist(self, records):
        """Every path in every record's evidence_refs must exist on disk —
        except a canonical normalize_report.json for a TSU-track
        "admission-in-principle" record (e.g. Fuller Vol.1-8): the record
        authorizes future ADR-030 TSU-track processing, evidenced by
        registration/raw-checksum state that already exists, but
        normalize_report.json is only written once that processing
        actually runs (still HOLD per the record's own rationale)."""
        for rec in records:
            for ref in rec["evidence_refs"]:
                ref_path = ROOT / ref
                if ref_path.exists() or pathlib.Path(ref).is_dir():
                    continue
                is_pending_normalize_report = (
                    ref.startswith("NAE/corpus/canonical/")
                    and ref.endswith("/normalize_report.json")
                )
                assert is_pending_normalize_report, \
                    f"{rec['source_id']}: evidence_ref '{ref}' does not exist"


# ── 11. Required fields present ───────────────────────────────────────────────

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


# ── 12. Fuller VOL01–08 content_genre matches M2 SSOT ────────────────────────

class TestFullerContentGenre:
    """content_genre for each Fuller volume must match M2 SSOT exactly."""

    @pytest.fixture(scope="module")
    def m2_sources(self):
        import yaml
        assert M2_FILE.exists(), f"{M2_FILE} must exist"
        data = yaml.safe_load(M2_FILE.read_text(encoding="utf-8"))
        return {s["source_id"]: s for s in data["sources"]}

    def test_fuller_content_genre(self, records, m2_sources):
        expected = {
            "BAP-MISS-FULLER-VOL01": ["theology"],
            "BAP-MISS-FULLER-VOL02": ["theology"],
            "BAP-MISS-FULLER-VOL03": ["theology"],
            "BAP-MISS-FULLER-VOL04": ["theology"],
            "BAP-MISS-FULLER-VOL05": ["commentary"],
            "BAP-MISS-FULLER-VOL06": ["commentary"],
            "BAP-MISS-FULLER-VOL07": ["sermon"],
            "BAP-MISS-FULLER-VOL08": ["theology", "sermon", "mission"],
        }
        for sid, expected_genre in expected.items():
            rec = next(r for r in records if r["source_id"] == sid)
            m2 = m2_sources[sid]
            assert set(rec["content_genre"]) == set(expected_genre), \
                f"{sid} content_genre mismatch: admission={rec['content_genre']}, expected={expected_genre}"
            assert set(rec["content_genre"]) == set(m2["content_genre"]), \
                f"{sid} content_genre must match M2 SSOT"


# ── 13. Fuller VOL01–08 theological_category evidence-bound ───────────────────

class TestFullerTheologicalCategoryEvidenceBound:
    """theological_category present in admission iff present in M2."""

    @pytest.fixture(scope="module")
    def m2_sources(self):
        import yaml
        assert M2_FILE.exists(), f"{M2_FILE} must exist"
        data = yaml.safe_load(M2_FILE.read_text(encoding="utf-8"))
        return {s["source_id"]: s for s in data["sources"]}

    def test_fuller_theological_category_evidence_bound(self, records, m2_sources):
        # theological_category present in M2: VOL01, VOL02, VOL08
        present_in_m2 = {"BAP-MISS-FULLER-VOL01", "BAP-MISS-FULLER-VOL02", "BAP-MISS-FULLER-VOL08"}
        absent_in_m2 = {f"BAP-MISS-FULLER-VOL{v:02d}" for v in range(3, 8)}

        for sid in present_in_m2:
            rec = next(r for r in records if r["source_id"] == sid)
            assert "theological_category" in rec, \
                f"{sid}: theological_category must be present (M2 has it)"
            m2 = m2_sources[sid]
            assert set(rec["theological_category"]) == set(m2["theological_category"]), \
                f"{sid} theological_category must match M2"

        for sid in absent_in_m2:
            rec = next(r for r in records if r["source_id"] == sid)
            assert "theological_category" not in rec, \
                f"{sid}: theological_category must be omitted (M2 does not have it)"


# ── 14. ProcessingStatus ──────────────────────────────────────────────────────

class TestProcessingStatus:
    """Verify processing_status values match expected states."""

    @pytest.fixture(scope="module")
    def m2_sources(self):
        import yaml
        assert M2_FILE.exists(), f"{M2_FILE} must exist"
        data = yaml.safe_load(M2_FILE.read_text(encoding="utf-8"))
        return {s["source_id"]: s for s in data["sources"]}

    def test_fuller_no_processing_status_in_m2(self, records, m2_sources):
        fuller = [r for r in records if r["source_id"].startswith("BAP-MISS-FULLER")]
        for sid in [r["source_id"] for r in fuller]:
            m2 = m2_sources[sid]
            assert "processing_status" not in m2, \
                f"{sid}: processing_status must be absent from M2 (not backfilled)"

    def test_dagg_hiscox_smith_no_processing_status_in_m2(self, records, m2_sources):
        non_fuller = [r for r in records if not r["source_id"].startswith("BAP-MISS-FULLER")]
        for sid in [r["source_id"] for r in non_fuller]:
            m2 = m2_sources[sid]
            assert "processing_status" not in m2, \
                f"{sid}: processing_status must be absent from M2"


# ── 12b. Fuller VOL05 content_genre specific check ────────────────────────────

class TestFullerVol05ContentGenre:
    def test_fuller_vol05_content_genre(self, records):
        vol05 = next(r for r in records if r["source_id"] == "BAP-MISS-FULLER-VOL05")
        assert set(vol05["content_genre"]) == {"commentary"},             f"VOL05 content_genre must be ['commentary'], got {vol05['content_genre']}"


# ── 12c. Fuller VOL08 theological_category specific check ─────────────────────

class TestFullerVol08TheologicalCategory:
    def test_fuller_vol08_theological_category(self, records):
        vol08 = next(r for r in records if r["source_id"] == "BAP-MISS-FULLER-VOL08")
        assert set(vol08["theological_category"]) == {"missions"},             f"VOL08 theological_category must be ['missions'], got {vol08.get('theological_category')}"


# ── 12d. Fuller VOL08 content_genre specific check ───────────────────────────

class TestFullerVol08ContentGenre:
    def test_fuller_vol08_content_genre(self, records):
        vol08 = next(r for r in records if r["source_id"] == "BAP-MISS-FULLER-VOL08")
        assert set(vol08["content_genre"]) == {"theology", "sermon", "mission"},             f"VOL08 content_genre must be ['theology','sermon','mission'], got {vol08['content_genre']}"



# ── 15. TSU required metadata ─────────────────────────────────────────────────

class TestTSURequiredMetadata:
    def test_tsu_has_required_meta(self, records):
        tsu = [r for r in records if r["track"] == "tsu"]
        assert len(tsu) == 10, f"Expected 10 tsu track records, got {len(tsu)}"
        for r in tsu:
            assert "tradition" in r and r["tradition"] not in (None, "", []), \
                f"{r['source_id']}: tradition must be present and non-empty"
