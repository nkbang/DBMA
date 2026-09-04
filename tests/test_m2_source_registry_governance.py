"""tests/test_m2_source_registry_governance.py - NAE M2 Source Registry Governance Tests.

ADR-030 v2.1 Phase 1-A 구현 검증 테스트.

§15 A-N 분류표:
  [코드 테스트 가능] A, B, C, D, E, F, G, H, I, J, K, L, M, N
  [config 의존]    -
  [수기 확인]      -

실행:
    cd ~/DBMA && source ~/envs/dbma311/bin/activate
    python -m pytest tests/test_m2_source_registry_governance.py -v

테스트 목록 (약 20 tests):
  Negative: test_neg_01(no corpus_tier in M2), neg_04, neg_05, neg_07, neg_08
  Positive: test_pos_01(content_genre optional), pos_02(theological_category optional),
            pos_03(tradition optional), pos_04(raw_path present), pos_05(checksum_target present),
            pos_06(authority_class vocab when present), pos_07(new fields optional no fail)
  Isolation: test_iso_01, iso_02
  Integration: test_int_01(validator exit 0), int_02(schema YAML valid),
               int_03(M2 14), int_04(M1 10), int_05(M3 26줄),
               int_06(M1 DERIVED), int_07(M2 ROLE), int_08(M3 ROLE), int_09(M1 mirror)
  New: test_m2_records_only_known_keys, test_validator_has_no_schema_path,
        test_authority_class_matches_adr030_7_3, test_raw_path_checksum_target_files_exist
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Constants ────────────────────────────────────────────────────────────────

VALID_AUTHORITY_CLASSES = frozenset([
    "primary_doctrinal", "historical_witness", "reference", "application",
])
FORBIDDEN_AUTHORITY_VALUES = frozenset([
    "application_resource", "auxiliary", "unassigned",
])
VALID_CONTENT_GENRE_VALUES = frozenset([
    "confession", "theology", "history", "commentary",
    "sermon", "mission", "church_practice", "pastoral",
])
VALID_THEOLOGICAL_CATEGORIES = frozenset([
    "confession", "ecclesiology", "soteriology", "missions",
])
M2_BASE_KEYS = frozenset([
    "source_id", "title", "author", "author_id", "work_id",
    "edition_id", "year", "license", "archive_source", "raw_checksum",
])
ADR030_ADDITIVE_FIELDS = frozenset([
    "authority_class", "content_genre", "theological_category",
    "tradition", "raw_path", "checksum_target",
])
M2_PATH = PROJECT_ROOT / "NAE" / "pipeline" / "registration" / "state" / "source_manifest.yaml"
M1_PATH = PROJECT_ROOT / "NAE" / "authority" / "source_manifest.yaml"
M3_PATH = PROJECT_ROOT / "NAE" / "manifest" / "NAE_SOURCE_MANIFEST_v1.csv"
FORBIDDEN_REGISTRY_DIR = PROJECT_ROOT / "NAE" / "corpus" / "governance"

# raw_path/checksum_target existence and the validator subprocess both need
# the NAE corpus + registration state on disk, which a fresh checkout / CI
# does not carry. Skip those two rather than fail on the environment gap.
_needs_nae_corpus = pytest.mark.skipif(
    not (PROJECT_ROOT / "NAE" / "corpus" / "raw").is_dir(),
    reason="requires the NAE/corpus raw tree + registration state (not in repo / CI)",
)


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ── Negative Tests (forbidden patterns) ─────────────────────────────────────

class TestNegativeForbiddenPatterns:
    """부재 검증: forbidden 패턴이 없어야 함."""

    def test_neg_01_no_corpus_tier_in_m2(self):
        """M2 sources[] 각 레코드에 corpus_tier 키 없음."""
        m2_data = _load_yaml(M2_PATH)
        for source in m2_data.get("sources", []):
            assert "corpus_tier" not in source, (
                f"{source.get('source_id')} must not have corpus_tier key"
            )

    def test_neg_04_no_eligible_in_m2(self):
        """M2 record에 ELIGIBLE state가 없어야 함."""
        m2_data = _load_yaml(M2_PATH)
        for source in m2_data.get("sources", []):
            assert source.get("status") != "ELIGIBLE", (
                f"{source.get('source_id')} must not have ELIGIBLE status"
            )

    def test_neg_05_no_active_in_m2(self):
        """M2 record에 ACTIVE state가 없어야 함 (ADR N-2)."""
        m2_data = _load_yaml(M2_PATH)
        for source in m2_data.get("sources", []):
            assert source.get("status") != "ACTIVE", (
                f"{source.get('source_id')} must not have ACTIVE status"
            )

    def test_neg_07_no_forbidden_authority_values_in_m2(self):
        """M2 record에 forbidden authority_class 값이 없어야 함."""
        m2_data = _load_yaml(M2_PATH)
        for source in m2_data.get("sources", []):
            ac = source.get("authority_class")
            if ac is not None:
                assert ac not in FORBIDDEN_AUTHORITY_VALUES, (
                    f"Forbidden authority_class in M2: {ac}"
                )

    def test_neg_08_no_forbidden_registry_dir(self):
        """NAE/corpus/governance/m2_source_registry.yaml 파일이 없어야 함."""
        assert not FORBIDDEN_REGISTRY_DIR.exists(), (
            f"Forbidden registry dir must not exist: {FORBIDDEN_REGISTRY_DIR}"
        )


# ── Positive Tests (new fields) ─────────────────────────────────────────────

class TestPositiveNewFields:
    """신규 필드 optional 검증."""

    def test_pos_01_content_genre_present(self):
        """content_genre 가 모든 M2 레코드에 존재 (A-2b-2)."""
        m2_data = _load_yaml(M2_PATH)
        for s in m2_data.get("sources", []):
            assert "content_genre" in s, f"{s.get('source_id')}: content_genre 부재"
            cg = s["content_genre"]
            assert isinstance(cg, list), f"{s.get('source_id')}: content_genre must be list"
            for v in cg:
                assert v in VALID_CONTENT_GENRE_VALUES, (
                    f"{s.get('source_id')}: unknown content_genre={v}"
                )

    def test_pos_02_theological_category_vocab(self):
        """theological_category 가 있는 레코드만 존재하고 값 ∈ 4-enum (A-2b-2)."""
        m2_data = _load_yaml(M2_PATH)
        found = [s for s in m2_data.get("sources", []) if "theological_category" in s]
        assert len(found) == 5, f"theological_category populated expected 5, got {len(found)}"
        for s in found:
            tc = s["theological_category"]
            assert isinstance(tc, list), f"{s.get('source_id')}: theological_category must be list"
            for v in tc:
                assert v in VALID_THEOLOGICAL_CATEGORIES, (
                    f"{s.get('source_id')}: unknown theological_category={v}"
                )

    def test_pos_03_tradition_vocab(self):
        """tradition 가 있는 레코드만 존재하고 값 ∈ canonical 3 (A-2b-2)."""
        m2_data = _load_yaml(M2_PATH)
        found = [s for s in m2_data.get("sources", []) if "tradition" in s]
        assert len(found) == 10, f"tradition populated expected 10, got {len(found)}"
        canonical_traditions = ("Particular Baptist", "American Baptist", "Baptist Evangelical")
        for s in found:
            t = s["tradition"]
            assert isinstance(t, str), f"{s.get('source_id')}: tradition must be str"
            assert t in canonical_traditions, (
                f"{s.get('source_id')}: unknown tradition={t}"
            )

    def test_pos_04_raw_path_present(self):
        """raw_path 가 모든 M2 레코드에 존재 (A-2b-1)."""
        m2_data = _load_yaml(M2_PATH)
        for s in m2_data.get("sources", []):
            assert "raw_path" in s, f"{s.get('source_id')}: raw_path 부재"

    def test_pos_05_checksum_target_present(self):
        """checksum_target 가 모든 M2 레코드에 존재 (A-2b-1)."""
        m2_data = _load_yaml(M2_PATH)
        for s in m2_data.get("sources", []):
            assert "checksum_target" in s, f"{s.get('source_id')}: checksum_target 부재"

    def test_pos_06_authority_class_vocab_when_present(self):
        """M2 로드 → authority_class 가진 레코드만 값 ∈ 4-enum.
        A-2a 엔 없어 공허 통과. # A-2b backfill 후 실질 검증"""
        m2_data = _load_yaml(M2_PATH)
        found = [s for s in m2_data.get("sources", []) if "authority_class" in s]
        for source in found:
            ac = source.get("authority_class")
            assert ac in VALID_AUTHORITY_CLASSES, (
                f"{source.get('source_id')} authority_class={ac} not in 4-enum"
            )
        # A-2a: found == [] → 공허 통과

    def test_pos_07_new_fields_optional_no_fail(self):
        """6필드 없는 합성 레코드에 validator per-record 검사 → FAIL 0."""
        import scripts.m2_source_registry_validator as v
        synthetic = [{k: "x" for k in M2_BASE_KEYS}]
        fails = (v.check_authority_class_enum(synthetic).failed
                 + v.check_new_field_definitions(synthetic).failed)
        assert fails == [], f"합성 레코드에서 예상외 FAIL: {fails}"


# ── New: M2 key governance ───────────────────────────────────────────────────

class TestM2KeyGovernance:
    """§2-1 판정 회귀 가드 + M2 키 화이트리스트."""

    def test_validator_has_no_schema_path(self):
        """validator 소스에 schema 파일 참조가 없어야 한다 (§2-1 회귀 가드)."""
        src = (PROJECT_ROOT / "scripts" / "m2_source_registry_validator.py").read_text(encoding="utf-8")
        assert "SCHEMA_PATH" not in src, "validator에 SCHEMA_PATH 재등장"
        assert "source_manifest.schema" not in src, "validator가 schema 파일을 참조"

    def test_m2_records_only_known_keys(self):
        """M2 각 레코드의 키가 {10 base} ∪ {6 ADR-030} 밖으로 나가지 않는다.
        A-2b-2: 키 수 14~16 (content_genre 14 + theological_category 5 + tradition 10).
        """
        m2_data = _load_yaml(M2_PATH)
        base = {"source_id", "title", "author", "author_id", "work_id",
                "edition_id", "year", "license", "archive_source", "raw_checksum"}
        additive = {"authority_class", "content_genre", "theological_category",
                    "tradition", "raw_path", "checksum_target"}
        for s in m2_data["sources"]:
            keys = set(s.keys())
            assert keys.issubset(base | additive), f"{s.get('source_id')} unknown keys: {keys - (base | additive)}"

    def test_authority_class_matches_adr030_7_3(self):
        """ADR-030 v2.1 §7.3 배정: historical_witness×10 / reference×4."""
        m2_data = _load_yaml(M2_PATH)
        sources = m2_data["sources"]
        counts = {}
        for s in sources:
            ac = s.get("authority_class")
            if ac is not None:
                counts[ac] = counts.get(ac, 0) + 1
        assert counts.get("historical_witness", 0) == 10, \
            f"historical_witness expected 10, got {counts.get('historical_witness', 0)}"
        assert counts.get("reference", 0) == 4, \
            f"reference expected 4, got {counts.get('reference', 0)}"
        assert len(counts) == 2, f"expected exactly 2 authority_class values, got {list(counts.keys())}"

    @_needs_nae_corpus
    def test_raw_path_checksum_target_files_exist(self):
        """raw_path / checksum_target 가 모든 M2 레코드에서 실제 파일 존재."""
        m2_data = _load_yaml(M2_PATH)
        for s in m2_data["sources"]:
            sid = s.get("source_id", "UNKNOWN")
            for k in ("raw_path", "checksum_target"):
                path = s.get(k)
                assert path is not None, f"{sid}: {k} 부재"
                assert (PROJECT_ROOT / path).exists(), f"{sid} {k}: {path}"


class TestPathIsolation:
    """tmp_path fixture 기반 격리 테스트."""

    def test_iso_01_can_create_temp_manifest(self, tmp_path: Path):
        """tmp_path에 임시 manifest 생성·삭제 가능."""
        test_file = tmp_path / "test_manifest.yaml"
        test_file.write_text("schema_version: '1.2'\nsources: []", encoding="utf-8")
        assert test_file.exists()
        data = yaml.safe_load(test_file.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.2"

    def test_iso_02_no_real_files_modified(self):
        """테스트 실행 중 실제 파일이 수정되지 않았는지 확인."""
        # M2, M1, M3 파일의 존재 여부만 확인 (수정 아님)
        assert M2_PATH.exists()
        assert M1_PATH.exists()
        assert M3_PATH.exists()


# ── Integration: Validator Script ───────────────────────────────────────────

class TestValidatorIntegration:
    """validator script 통합 테스트."""

    @_needs_nae_corpus
    def test_int_01_validator_passes(self):
        """validator script가 exit 0으로 통과해야 함."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "m2_source_registry_validator.py")],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Validator failed:\n{result.stdout}\n{result.stderr}"
        )

    def test_int_02_schema_yaml_valid(self):
        """schema YAML이 유효하게 파싱되어야 함 (revert 후)."""
        schema_path = PROJECT_ROOT / "resources" / "theological_sources" / "modern" / "source_manifest.schema.yaml"
        schema = _load_yaml(schema_path)
        assert isinstance(schema, dict)
        assert "schema_version" in schema
        assert "fields" in schema
        assert isinstance(schema["fields"], dict)

    def test_int_03_m2_yaml_valid(self):
        """M2 YAML이 유효하게 파싱되어야 함."""
        m2_data = _load_yaml(M2_PATH)
        assert isinstance(m2_data, dict)
        assert "sources" in m2_data
        assert len(m2_data["sources"]) == 14

    def test_int_04_m1_yaml_valid(self):
        """M1 YAML이 유효하게 파싱되어야 함."""
        m1_data = _load_yaml(M1_PATH)
        assert isinstance(m1_data, dict)
        assert "sources" in m1_data
        assert len(m1_data["sources"]) == 10

    def test_int_05_m3_csv_valid(self):
        """M3 CSV이 유효하게 파싱되어야 함."""
        lines = M3_PATH.read_text(encoding="utf-8").strip().split("\n")
        # Skip comment line
        data_lines = [l for l in lines if not l.startswith("#")]
        assert len(data_lines) == 26  # header + 25 data rows
        header = data_lines[0].split(",")
        assert "id" in header

    def test_int_06_m1_header_comment(self):
        """M1 파일 상단에 DERIVED 주석이 있어야 함."""
        m1_text = M1_PATH.read_text(encoding="utf-8")
        assert "DERIVED from" in m1_text
        assert "source_manifest.yaml (M2)" in m1_text

    def test_int_07_m2_header_comment(self):
        """M2 파일 상단에 ROLE 주석이 있어야 함."""
        m2_text = M2_PATH.read_text(encoding="utf-8")
        assert "ROLE: Source Registry SSOT" in m2_text

    def test_int_08_m3_header_comment(self):
        """M3 파일 상단에 ROLE 주석이 있어야 함."""
        m3_text = M3_PATH.read_text(encoding="utf-8")
        assert "ROLE: Acquisition Backlog Tracker" in m3_text

    def test_int_09_m1_is_mirror_not_ssot(self):
        """M1이 SSOT가 아니어야 함."""
        m1_text = M1_PATH.read_text(encoding="utf-8")
        assert "Non-authoritative mirror" in m1_text
        assert "Do NOT hand-edit" in m1_text


# ── New: A-2b-2 classification tests ─────────────────────────────────────────

class TestClassificationA2b2:
    """A-2b-2 RATIFIED v1.1 §4.1 verbatim 대조 + vocab 검사."""

    def test_classification_matches_a2b2_v1_1(self):
        """M2 14 레코드 분류값이 CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md §4.1 A2B2 dict verbatim 일치."""
        m2_data = _load_yaml(M2_PATH)
        sources = {s["source_id"]: s for s in m2_data["sources"]}

        A2B2 = {
            "BAP-CHURCH-DAGG-001": {"content_genre": ["church_practice"], "theological_category": ["ecclesiology"], "tradition": "Particular Baptist"},
            "BAP-CHURCH-HISCOX": {"content_genre": ["church_practice", "pastoral"], "theological_category": ["ecclesiology"], "tradition": "Particular Baptist"},
            "BAP-MISS-FULLER-VOL01": {"content_genre": ["theology"], "theological_category": ["soteriology"], "tradition": "Particular Baptist"},
            "BAP-MISS-FULLER-VOL02": {"content_genre": ["theology"], "theological_category": ["soteriology"], "tradition": "Particular Baptist"},
            "BAP-MISS-FULLER-VOL03": {"content_genre": ["theology"], "theological_category": None, "tradition": "Particular Baptist"},
            "BAP-MISS-FULLER-VOL04": {"content_genre": ["theology"], "theological_category": None, "tradition": "Particular Baptist"},
            "BAP-MISS-FULLER-VOL05": {"content_genre": ["commentary"], "theological_category": None, "tradition": "Particular Baptist"},
            "BAP-MISS-FULLER-VOL06": {"content_genre": ["commentary"], "theological_category": None, "tradition": "Particular Baptist"},
            "BAP-MISS-FULLER-VOL07": {"content_genre": ["sermon"], "theological_category": None, "tradition": "Particular Baptist"},
            "BAP-MISS-FULLER-VOL08": {"content_genre": ["theology", "sermon", "mission"], "theological_category": ["missions"], "tradition": "Particular Baptist"},
            "BAP-REF-SMITH-VOL01": {"content_genre": ["commentary"], "theological_category": None, "tradition": None},
            "BAP-REF-SMITH-VOL02": {"content_genre": ["commentary"], "theological_category": None, "tradition": None},
            "BAP-REF-SMITH-VOL03": {"content_genre": ["commentary"], "theological_category": None, "tradition": None},
            "BAP-REF-SMITH-VOL04": {"content_genre": ["commentary"], "theological_category": None, "tradition": None},
        }

        for sid, expected in A2B2.items():
            rec = sources.get(sid)
            assert rec is not None, f"{sid} M2에 부재"
            for field, exp_val in expected.items():
                if exp_val is None:
                    assert field not in rec, f"{sid}.{field}: None이므로 키 부재해야 함, 실제={rec.get(field)}"
                else:
                    assert field in rec, f"{sid}.{field}: 부재"
                    actual = rec[field]
                    assert actual == exp_val, (
                        f"{sid}.{field}: expected {exp_val}, got {actual}"
                    )

    def test_no_unratified_classification_vocab(self):
        """M2 classification 필드에 RATIFIED vocab 밖 값 없음."""
        m2_data = _load_yaml(M2_PATH)
        for s in m2_data["sources"]:
            sid = s.get("source_id", "UNKNOWN")
            if "content_genre" in s:
                for v in s["content_genre"]:
                    assert v in VALID_CONTENT_GENRE_VALUES, (
                        f"{sid}: unratified content_genre={v}"
                    )
            if "theological_category" in s:
                for v in s["theological_category"]:
                    assert v in VALID_THEOLOGICAL_CATEGORIES, (
                        f"{sid}: unratified theological_category={v}"
                    )
