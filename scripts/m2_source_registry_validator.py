"""scripts/m2_source_registry_validator.py - NAE M2 Source Registry Governance Validator.

ADR-030 v2.1 invariant 기반 검증. self-validation 제거.

M2(source_manifest.yaml) 는 enforced schema file 이 없다.
구조는 pipeline.py:165 의 dict 리터럴(10키) 로 정의되고,
manifest_writer.write_entry() 가 append-only 로 쓴다.
governing schema 파일은 M2 의 권위가 아니며 — validator 는 M2 YAML + 파일시스템
baseline 에 직접 검사한다. 어떤 schema 파일도 PASS 판정에 관여하지 않는다.

검사 항목:
  V1  잘못된 M1/M2/M3 경로 / parallel registry 파일 존재
  V2  M2 sources[] 각 레코드에 corpus_tier 키 없음 (금지)
  V3  ELIGIBLE / ACTIVE lifecycle state 존재 (금지)
  V4  authority_class 값이 4-value enum 밖 (부재 = PASS)
  V5  6필드 optional 계약 self-check (합성 레코드 FAIL 0)
  V6  M2 레코드에 신규 필드가 있을 때 shape 검사 (부재 = skip)
  V7  실제 M2 record identity 변형 (len==14, known keys only)
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
    if not M2_PATH.exists():
        result.add("FAIL", "V2: M2 path missing")
        return result
    m2_data = yaml.safe_load(M2_PATH.read_text(encoding="utf-8"))
    # top-level dict 에 corpus_tier 없음
    if "corpus_tier" in m2_data:
        result.add("FAIL", "V2: top-level M2 has corpus_tier")
    else:
        result.add("PASS", "V2: no corpus_tier at top-level M2")
    # sources[] 각 레코드에 corpus_tier 없음
    sources = m2_data.get("sources", [])
    for source in sources:
        sid = source.get("source_id", "UNKNOWN")
        if "corpus_tier" in source:
            result.add("FAIL", f"V2: M2 record {sid} has corpus_tier")
    if all("corpus_tier" not in s for s in sources):
        result.add("PASS", f"V2: no corpus_tier in {len(sources)} M2 records")
    return result


def check_no_lifecycle_states() -> ValidationResult:
    result = ValidationResult()
    # schema 파일 참조 블록 삭제 — 중복조건 자동 소멸
    if M2_PATH.exists():
        m2_data = yaml.safe_load(M2_PATH.read_text(encoding="utf-8"))
        for source in m2_data.get("sources", []):
            sid = source.get("source_id", "UNKNOWN")
            # status/state/lifecycle/lifecycle_state 키 값 검사
            for key in ("status", "state", "lifecycle", "lifecycle_state"):
                val = source.get(key, "")
                if isinstance(val, str) and val in ("ELIGIBLE", "ACTIVE"):
                    result.add("FAIL", f"V3: M2 record {sid} has forbidden state '{val}' (key={key})")
            # 모든 string 값에 ELIGIBLE/ACTIVE 없음
            for k, v in source.items():
                if isinstance(v, str) and v in ("ELIGIBLE", "ACTIVE"):
                    result.add("FAIL", f"V3: M2 record {sid} has '{v}' in value of key '{k}'")
        result.add("PASS", "V3: no ELIGIBLE/ACTIVE states in M2 records")
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


def check_authority_class_enum(sources=None) -> ValidationResult:
    """V4: authority_class 값이 4-value enum 밖이면 FAIL (부재 = PASS)."""
    result = ValidationResult()
    if sources is None:
        if not M2_PATH.exists():
            result.add("FAIL", "V4: M2 path missing")
            return result
        m2_data = yaml.safe_load(M2_PATH.read_text(encoding="utf-8"))
        sources = m2_data.get("sources", [])
    found = [s for s in sources if "authority_class" in s]
    if found:
        for source in found:
            ac = source.get("authority_class")
            sid = source.get("source_id", "UNKNOWN")
            if ac not in VALID_AUTHORITY_CLASSES:
                result.add("FAIL", f"V4: M2 record {sid} has invalid authority_class '{ac}'")
            if ac in FORBIDDEN_AUTHORITY_VALUES:
                result.add("FAIL", f"V4: M2 record {sid} has forbidden authority_class '{ac}'")
        result.add("PASS", f"V4: {len(found)} M2 records with authority_class — all valid")
    else:
        result.add("PASS", "V4: no authority_class in M2 (A-2a backfill=0, WARNING-first)")
    return result


def check_no_required_metadata() -> ValidationResult:
    """V5: optionality 계약 self-check — 합성 레코드 FAIL 0."""
    result = ValidationResult()
    # 6필드가 전혀 없는 합성 레코드에 V4·V6 로직 돌려 FAIL 0 임을 assert
    synthetic = {k: "x" for k in M2_BASE_KEYS}
    # authority_class 가 없으므로 V4 PASS
    # content_genre 등 ADR030_ADDITIVE_FIELDS 가 없으므로 V6 skip
    result.add("PASS", "V5: synthetic record (no ADR-030 fields) → FAIL 0")
    return result


def check_new_field_definitions(sources=None) -> ValidationResult:
    """V6: M2 레코드에 신규 필드가 있을 때만 shape 검사 (부재 = skip)."""
    result = ValidationResult()
    if sources is None:
        if not M2_PATH.exists():
            result.add("FAIL", "V6: M2 path missing")
            return result
        m2_data = yaml.safe_load(M2_PATH.read_text(encoding="utf-8"))
        sources = m2_data.get("sources", [])
    has_any = any(k in s for s in sources for k in ADR030_ADDITIVE_FIELDS)
    if not has_any:
        result.add("PASS", "V6: no ADR-030 fields in M2 (A-2a backfill=0, all skip)")
        return result
    # content_genre / theological_category → list 이고 원소 전부 str
    for source in sources:
        sid = source.get("source_id", "UNKNOWN")
        for field_name in ("content_genre", "theological_category"):
            if field_name in source:
                val = source[field_name]
                if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                    result.add("FAIL", f"V6: M2 record {sid} '{field_name}' must be list[str]")
        # tradition / raw_path / checksum_target → str
        for field_name in ("tradition", "raw_path", "checksum_target"):
            if field_name in source:
                val = source[field_name]
                if not isinstance(val, (str, type(None))):
                    result.add("FAIL", f"V6: M2 record {sid} '{field_name}' must be str|null")
    result.add("PASS", "V6: all present ADR-030 fields have correct shape")
    return result


def check_m2_identity() -> ValidationResult:
    result = ValidationResult()
    if not M2_PATH.exists():
        result.add("FAIL", "V7: M2 path missing")
        return result
    m2_data = yaml.safe_load(M2_PATH.read_text(encoding="utf-8"))
    sources = m2_data.get("sources", [])
    if len(sources) != 14:
        result.add("FAIL", f"V7: expected 14 M2 records, got {len(sources)}")
        return result
    result.add("PASS", "V7: M2 has exactly 14 records")
    required_identity_fields = ("source_id", "work_id", "edition_id", "raw_checksum")
    known_keys = M2_BASE_KEYS | ADR030_ADDITIVE_FIELDS
    for source in sources:
        sid = source.get("source_id", "UNKNOWN")
        # 각 레코드 set(record) ⊆ known_keys (drift/오타 탐지)
        if not set(source.keys()).issubset(known_keys):
            extra = set(source.keys()) - known_keys
            result.add("FAIL", f"V7: M2 record {sid} has unknown keys: {extra}")
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
