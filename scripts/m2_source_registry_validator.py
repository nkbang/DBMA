"""scripts/m2_source_registry_validator.py - NAE M2 Source Registry Governance Validator.

ADR-030 v2.1 invariant 기반 검증. self-validation 제거.

검사 항목:
  V1  잘못된 M1/M2/M3 경로 / parallel registry 파일 존재
  V2  schema 내 corpus_tier 필드 존재 (금지)
  V3  ELIGIBLE / ACTIVE lifecycle state 정의 존재 (금지)
  V4  authority_class 값이 4-value enum 밖
  V5  metadata 필드에 required: true
  V6  content_genre[] / theological_category[] / tradition 정의 누락
  V7  실제 M2 record identity 변형
  V8  baseline 이탈

read-only. exit!=0 은 위반 존재 시에만.

사용례:
    python scripts/m2_source_registry_validator.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml

# Constants
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
BASELINE = {"nae_tsu_v1": 3319, "nae_ref_v1": 34948, "canonical_dirs": 17, "registration_quality_passed": 10}


class ValidationResult:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.warnings: list[str] = []

    def add(self, status: str, message: str) -> None:
        if status == "PASS":
            self.passed.append(message)
        elif status == "FAIL":
            self.failed.append(message)
        else:
            self.warnings.append(message)

    @property
    def fail_count(self) -> int:
        return len(self.failed)

    def print_all(self) -> None:
        print("=" * 70)
        print("M2 Source Registry Governance Validation Report")
        print("=" * 70)
        print(f"  PASS:   {len(self.passed)}")
        print(f"  FAIL:   {len(self.failed)}")
        print(f"  WARN:   {len(self.warnings)}")
        print("-" * 70)
        if self.passed:
            print("\n[PASS]")
            for msg in self.passed:
                print(f"  + {msg}")
        if self.failed:
            print("\n[FAIL]")
            for msg in self.failed:
                print(f"  - {msg}")
        if self.warnings:
            print("\n[WARN]")
            for msg in self.warnings:
                print(f"  ~ {msg}")
        print("=" * 70)


def check_paths() -> ValidationResult:
    result = ValidationResult()
    for name, path in [("M2", M2_PATH), ("M1", M1_PATH), ("M3", M3_PATH)]:
        if path.exists():
            result.add("PASS", f"V1: {name} path exists")
        else:
            result.add("FAIL", f"V1: {name} path missing: {path}")
    if FORBIDDEN_REGISTRY_DIR.exists():
        files = list(FORBIDDEN_REGISTRY_DIR.rglob("*"))
        result.add("FAIL", f"V1: forbidden parallel registry dir exists: {FORBIDDEN_REGISTRY_DIR} ({len(files)} files)")
    else:
        result.add("PASS", "V1: no forbidden parallel registry (NAE/corpus/governance/ removed)")
    return result


def check_no_corpus_tier() -> ValidationResult:
    result = ValidationResult()
    if not SCHEMA_PATH.exists():
        result.add("FAIL", "V2: schema file missing")
        return result
    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    fields = schema.get("fields", {})
    if "corpus_tier" in fields:
        result.add("FAIL", "V2: corpus_tier field must NOT exist in schema")
    else:
        result.add("PASS", "V2: corpus_tier field absent from schema")
    return result


def check_no_lifecycle_states() -> ValidationResult:
    result = ValidationResult()
    if SCHEMA_PATH.exists():
        schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
        for state in ("ELIGIBLE", "ACTIVE"):
            if f'"{state}"' in schema_text or f'"{state}"' in schema_text:
                result.add("FAIL", f"V3: lifecycle state '{state}' found in schema")
            else:
                result.add("PASS", f"V3: lifecycle state '{state}' absent from schema")
    if M2_PATH.exists():
        m2_data = yaml.safe_load(M2_PATH.read_text(encoding="utf-8"))
        for source in m2_data.get("sources", []):
            status = source.get("status", "")
            if status in ("ELIGIBLE", "ACTIVE"):
                result.add("FAIL", f"V3: M2 record {source.get('source_id')} has forbidden state '{status}'")
    reg_state = PROJECT_ROOT / "NAE" / "pipeline" / "registration" / "state" / "registration_state.json"
    if reg_state.exists():
        with open(reg_state) as f:
            reg_data = json.load(f)
        if isinstance(reg_data, dict):
            for sid, entry in reg_data.items():
                if isinstance(entry, dict):
                    state = entry.get("state", "")
                    if state in ("ELIGIBLE", "ACTIVE"):
                        result.add("FAIL", f"V3: registration_state {sid} has forbidden state '{state}'")
    return result


def check_authority_class_enum() -> ValidationResult:
    result = ValidationResult()
    if SCHEMA_PATH.exists():
        schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
        fields = schema.get("fields", {})
        ac_field = fields.get("authority_class", {})
        values = ac_field.get("values", [])
        for v in values:
            if v in FORBIDDEN_AUTHORITY_VALUES:
                result.add("FAIL", f"V4: forbidden authority_class value in schema: '{v}'")
            elif v not in VALID_AUTHORITY_CLASSES:
                result.add("FAIL", f"V4: unknown authority_class value in schema: '{v}'")
        if len(values) == 4 and set(values) == VALID_AUTHORITY_CLASSES:
            result.add("PASS", "V4: authority_class has exactly 4 allowed values")
        else:
            result.add("WARN", f"V4: authority_class values = {values}")
    if M2_PATH.exists():
        m2_data = yaml.safe_load(M2_PATH.read_text(encoding="utf-8"))
        for source in m2_data.get("sources", []):
            ac = source.get("authority_class")
            if ac is not None and ac in FORBIDDEN_AUTHORITY_VALUES:
                result.add("FAIL", f"V4: M2 record {source['source_id']} has forbidden authority_class '{ac}'")
    return result


def check_no_required_metadata() -> ValidationResult:
    """V5: ADR-030 신규 필드에 required: true가 없어야 함."""
    result = ValidationResult()
    if SCHEMA_PATH.exists():
        schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
        fields = schema.get("fields", {})
        # Only check ADR-030 new fields, not existing v1.2 fields
        adr_fields = ("content_genre", "theological_category", "tradition",
                      "raw_path", "checksum_target", "authority_class")
        for field_name in adr_fields:
            field_def = fields.get(field_name, {})
            if isinstance(field_def, dict) and field_def.get("required") is True:
                result.add("FAIL", f"V5: ADR-030 field '{field_name}' has required: true")
        # Also check for any field with required: true that should be optional
        for field_name, field_def in fields.items():
            if isinstance(field_def, dict) and field_def.get("required") is True:
                if field_name not in ("source_id", "author_id", "author_name",
                                      "work_id", "edition_id", "title",
                                      "publication_year", "category", "source_type",
                                      "copyright_status", "usage_permission",
                                      "access_control", "citation_policy", "status"):
                    result.add("FAIL", f"V5: field '{field_name}' has required: true")
    return result


def check_new_field_definitions() -> ValidationResult:
    result = ValidationResult()
    if not SCHEMA_PATH.exists():
        result.add("FAIL", "V6: schema file missing")
        return result
    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    fields = schema.get("fields", {})
    for field_name, expected_type in [
        ("content_genre", "array"),
        ("theological_category", "array"),
        ("tradition", "string"),
        ("raw_path", "string"),
        ("checksum_target", "string"),
    ]:
        if field_name not in fields:
            result.add("FAIL", f"V6: field '{field_name}' missing from schema")
        else:
            actual_type = fields[field_name].get("type", "")
            if expected_type in actual_type:
                result.add("PASS", f"V6: field '{field_name}' defined (type={actual_type})")
            else:
                result.add("FAIL", f"V6: field '{field_name}' type mismatch: expected {expected_type}, got {actual_type}")
    return result


def check_m2_identity() -> ValidationResult:
    result = ValidationResult()
    if not M2_PATH.exists():
        result.add("FAIL", "V7: M2 path missing")
        return result
    m2_data = yaml.safe_load(M2_PATH.read_text(encoding="utf-8"))
    sources = m2_data.get("sources", [])
    required_identity_fields = ("source_id", "work_id", "edition_id", "raw_checksum")
    for source in sources:
        sid = source.get("source_id", "UNKNOWN")
        for field in required_identity_fields:
            if field not in source:
                result.add("FAIL", f"V7: M2 record {sid} missing identity field '{field}'")
            elif not source[field]:
                result.add("FAIL", f"V7: M2 record {sid} has empty identity field '{field}'")
    sids = [s.get("source_id") for s in sources if s.get("source_id")]
    if len(sids) != len(set(sids)):
        result.add("FAIL", "V7: duplicate source_ids found in M2")
    else:
        result.add("PASS", f"V7: M2 has {len(sids)} unique source_ids, no duplicates")
    return result


def check_baseline() -> ValidationResult:
    result = ValidationResult()
    tsu_state = PROJECT_ROOT / "NAE" / "corpus" / "tsu" / "tsu_id_state.json"
    if tsu_state.exists():
        with open(tsu_state) as f:
            tsu_data = json.load(f)
        next_id = tsu_data.get("next_id", 0)
        result.add("PASS", f"V8: TSU state exists (next_id={next_id})")
    canonical_dir = PROJECT_ROOT / "NAE" / "corpus" / "canonical"
    if canonical_dir.exists():
        dirs = [d for d in canonical_dir.iterdir() if d.is_dir()]
        if len(dirs) == BASELINE["canonical_dirs"]:
            result.add("PASS", f"V8: canonical dirs = {len(dirs)} (baseline OK)")
        else:
            result.add("FAIL", f"V8: canonical dirs = {len(dirs)} (baseline={BASELINE['canonical_dirs']})")
    reg_state = PROJECT_ROOT / "NAE" / "pipeline" / "registration" / "state" / "registration_state.json"
    if reg_state.exists():
        with open(reg_state) as f:
            reg_data = json.load(f)
        passed_count = sum(
            1 for v in reg_data.values()
            if isinstance(v, dict) and v.get("state") == "QUALITY_PASSED"
        )
        if passed_count == BASELINE["registration_quality_passed"]:
            result.add("PASS", f"V8: registration QUALITY_PASSED = {passed_count} (baseline OK)")
        else:
            result.add("FAIL", f"V8: registration QUALITY_PASSED = {passed_count} (baseline={BASELINE['registration_quality_passed']})")
    return result


def validate() -> ValidationResult:
    result = ValidationResult()
    for name, fn in [
        ("V1", check_paths),
        ("V2", check_no_corpus_tier),
        ("V3", check_no_lifecycle_states),
        ("V4", check_authority_class_enum),
        ("V5", check_no_required_metadata),
        ("V6", check_new_field_definitions),
        ("V7", check_m2_identity),
        ("V8", check_baseline),
    ]:
        r = fn()
        result.passed.extend(r.passed)
        result.failed.extend(r.failed)
        result.warnings.extend(r.warnings)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    args = parser.parse_args()
    result = validate()
    result.print_all()
    return 1 if result.fail_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
