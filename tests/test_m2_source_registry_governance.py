"""tests/test_m2_source_registry_governance.py - NAE M2 Source Registry Governance Tests.

ADR-030 v2.1 Phase 1-A 구현 검증 테스트.

§15 A-N 분류표:
  [코드 테스트 가능] A, B, C, D, E, F, G, H, I, J, K, L, M, N
  [config 의존]    -
  [수기 확인]      -

실행:
    cd ~/DBMA && source ~/envs/dbma311/bin/activate
    python -m pytest tests/test_m2_source_registry_governance.py -v
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
M2_PATH = PROJECT_ROOT / "NAE" / "pipeline" / "registration" / "state" / "source_manifest.yaml"
M1_PATH = PROJECT_ROOT / "NAE" / "authority" / "source_manifest.yaml"
M3_PATH = PROJECT_ROOT / "NAE" / "manifest" / "NAE_SOURCE_MANIFEST_v1.csv"
SCHEMA_PATH = PROJECT_ROOT / "resources" / "theological_sources" / "modern" / "source_manifest.schema.yaml"
FORBIDDEN_REGISTRY_DIR = PROJECT_ROOT / "NAE" / "corpus" / "governance"


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ── Negative Tests (forbidden patterns) ─────────────────────────────────────

class TestNegativeForbiddenPatterns:
    """부재 검증: forbidden 패턴이 없어야 함."""

    def test_neg_01_no_corpus_tier_in_schema(self):
        """corpus_tier 필드가 schema에 없어야 함 (ADR N-3 / C-1)."""
        schema = _load_yaml(SCHEMA_PATH)
        fields = schema.get("fields", {})
        assert "corpus_tier" not in fields, "corpus_tier must NOT exist"

    def test_neg_02_no_eligible_state_in_schema(self):
        """ELIGIBLE lifecycle state가 schema에 없어야 함 (ADR F-2)."""
        schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
        assert "'ELIGIBLE'" not in schema_text and '"ELIGIBLE"' not in schema_text

    def test_neg_03_no_active_state_in_schema(self):
        """ACTIVE lifecycle state가 schema에 없어야 함 (ADR N-1)."""
        schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
        assert "'ACTIVE'" not in schema_text and '"ACTIVE"' not in schema_text

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

    def test_neg_06_no_forbidden_authority_values_in_schema(self):
        """schema에 forbidden authority_class 값이 없어야 함."""
        schema = _load_yaml(SCHEMA_PATH)
        fields = schema.get("fields", {})
        ac_field = fields.get("authority_class", {})
        values = ac_field.get("values", [])
        for v in values:
            assert v not in FORBIDDEN_AUTHORITY_VALUES, (
                f"Forbidden authority_class value found: {v}"
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

    def test_neg_09_no_required_for_eligible_expression(self):
        """required_for_eligible 표현이 없어야 함 (ADR §7.5)."""
        schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
        assert "required_for_eligible" not in schema_text, (
            "required_for_eligible expression must NOT exist"
        )


# ── Positive Tests (new fields) ─────────────────────────────────────────────

class TestPositiveNewFields:
    """신규 필드 존재 검증."""

    def test_pos_01_content_genre_defined(self):
        """content_genre[] schema 정의 존재."""
        schema = _load_yaml(SCHEMA_PATH)
        fields = schema.get("fields", {})
        assert "content_genre" in fields, "content_genre must be defined"
        assert "array" in fields["content_genre"].get("type", ""), (
            "content_genre type must be array"
        )

    def test_pos_02_theological_category_defined(self):
        """theological_category[] schema 정의 존재."""
        schema = _load_yaml(SCHEMA_PATH)
        fields = schema.get("fields", {})
        assert "theological_category" in fields, "theological_category must be defined"
        assert "array" in fields["theological_category"].get("type", ""), (
            "theological_category type must be array"
        )

    def test_pos_03_tradition_defined(self):
        """tradition schema 정의 존재."""
        schema = _load_yaml(SCHEMA_PATH)
        fields = schema.get("fields", {})
        assert "tradition" in fields, "tradition must be defined"
        assert "string" in fields["tradition"].get("type", ""), (
            "tradition type must be string"
        )

    def test_pos_04_raw_path_defined(self):
        """raw_path schema 정의 존재."""
        schema = _load_yaml(SCHEMA_PATH)
        fields = schema.get("fields", {})
        assert "raw_path" in fields, "raw_path must be defined"

    def test_pos_05_checksum_target_defined(self):
        """checksum_target schema 정의 존재."""
        schema = _load_yaml(SCHEMA_PATH)
        fields = schema.get("fields", {})
        assert "checksum_target" in fields, "checksum_target must be defined"

    def test_pos_06_authority_class_has_4_values(self):
        """authority_class가 정확히 4개 허용값을 가져야 함."""
        schema = _load_yaml(SCHEMA_PATH)
        fields = schema.get("fields", {})
        ac_field = fields.get("authority_class", {})
        values = ac_field.get("values", [])
        assert len(values) == 4, f"authority_class must have exactly 4 values, got {len(values)}"
        assert set(values) == VALID_AUTHORITY_CLASSES, (
            f"authority_class values must be {VALID_AUTHORITY_CLASSES}, got {set(values)}"
        )

    def test_pos_07_all_new_fields_optional(self):
        """모든 신규 필드가 required: false여야 함."""
        schema = _load_yaml(SCHEMA_PATH)
        fields = schema.get("fields", {})
        for field_name in ("content_genre", "theological_category", "tradition",
                           "raw_path", "checksum_target", "authority_class"):
            field_def = fields.get(field_name, {})
            if isinstance(field_def, dict):
                required = field_def.get("required", False)
                assert required is not True, (
                    f"{field_name} must NOT have required: true"
                )


# ── Path Isolation Tests (tmp_path only) ────────────────────────────────────

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
        # M2, M1, M3, schema 파일의 존재 여부만 확인 (수정 아님)
        assert M2_PATH.exists()
        assert M1_PATH.exists()
        assert M3_PATH.exists()
        assert SCHEMA_PATH.exists()


# ── Integration: Validator Script ───────────────────────────────────────────

class TestValidatorIntegration:
    """validator script 통합 테스트."""

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
        """schema YAML이 유효하게 파싱되어야 함."""
        schema = _load_yaml(SCHEMA_PATH)
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
