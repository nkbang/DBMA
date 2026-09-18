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
  V9  authority_tier 값이 4-value enum 밖, 또는 tradition_relation 누락/오탈 (부재 = PASS)
      (ADR-030 Amendment D, PROPOSED — 구현 선행, Amendment 자체는 HQ 최종 승인 전)
  V10 authority_tier=T3 인데 counter_refs 없거나 비어있음
  V11 counter_refs 각 id가 (a) M2에 존재하는 source_id 가 아니거나(orphan),
      (b) 그 대상의 authority_tier ∉ {T1, T2}
  V12 authority_tier ∈ {T1, T2, T4} 인데 counter_refs 가 non-empty
      (V11(b)와 조합해 counter_ref 순환 참조를 구조적으로 차단)

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
VALID_CONTENT_GENRE_VALUES = frozenset([
    "confession", "theology", "history", "commentary",
    "sermon", "mission", "church_practice", "pastoral",
])
VALID_THEOLOGICAL_CATEGORIES = frozenset([
    "confession", "ecclesiology", "soteriology", "missions",
])
VALID_AUTHORITY_TIERS = frozenset(["T1", "T2", "T3", "T4"])
VALID_TRADITION_RELATIONS = frozenset([
    "own", "allied", "other_christian", "non_christian", "heterodox",
])
M2_BASE_KEYS = frozenset([
    "source_id", "title", "author", "author_id", "work_id",
    "edition_id", "year", "license", "archive_source", "raw_checksum",
])
ADR030_ADDITIVE_FIELDS = frozenset([
    "authority_class", "content_genre", "theological_category",
    "tradition", "raw_path", "checksum_target",
    # ADR-030 Amendment D (PROPOSED) — see docs/architecture/
    # ADR-030-AMENDMENT-D-Authority-Tier-Doctrinal-Orthodoxy-Axis.md
    "authority_tier", "tradition_relation", "counter_refs",
])
M2_PATH = PROJECT_ROOT / "NAE" / "pipeline" / "registration" / "state" / "source_manifest.yaml"
M1_PATH = PROJECT_ROOT / "NAE" / "authority" / "source_manifest.yaml"
M3_PATH = PROJECT_ROOT / "NAE" / "manifest" / "NAE_SOURCE_MANIFEST_v1.csv"
FORBIDDEN_REGISTRY_DIR = PROJECT_ROOT / "NAE" / "corpus" / "governance"
# registration_quality_passed: 10 (M-2 baseline) + 1 (BAP-COMM-SPURGEON-TDA-VOL01,
# ADR-030 Amendment B, 2026-09-13) + 1 (BAP-COMM-GILL-ENT-VOL01, same Amendment B
# authority, 2026-09-15) + 1 (BAP-COMM-BROADUS-MATT-VOL01, same Amendment B
# authority, 2026-09-15) + 1 (BAP-COMM-CARROLL-IEB-VOL02, same Amendment B
# authority, 2026-09-17) = 14. A drift guard, not an open range — any further
# increase needs its own explicit bump + authorization record.
BASELINE = {"nae_tsu_v1": 3319, "nae_ref_v1": 34948, "canonical_dirs": 17, "registration_quality_passed": 14}
# ADR-030 v2.1 §12 M-2 backfilled exactly these 14 source_ids (2026-08-28).
# ADR-030 Amendment B (2026-09-13) authorizes appending further M2 records —
# V7/V8 below protect this frozen set's identity/count without capping M2's
# total size going forward.
M2_FROZEN_BASELINE_SOURCE_IDS = frozenset([
    "BAP-CHURCH-DAGG-001", "BAP-CHURCH-HISCOX",
    "BAP-MISS-FULLER-VOL01", "BAP-MISS-FULLER-VOL02", "BAP-MISS-FULLER-VOL03",
    "BAP-MISS-FULLER-VOL04", "BAP-MISS-FULLER-VOL05", "BAP-MISS-FULLER-VOL06",
    "BAP-MISS-FULLER-VOL07", "BAP-MISS-FULLER-VOL08",
    "BAP-REF-SMITH-VOL01", "BAP-REF-SMITH-VOL02", "BAP-REF-SMITH-VOL03", "BAP-REF-SMITH-VOL04",
])


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
    """V5: 6필드 없는 합성 레코드에 per-record 검사 → FAIL 0 (optionality 계약)."""
    result = ValidationResult()
    synthetic = [{k: "x" for k in M2_BASE_KEYS}]
    fails = (check_authority_class_enum(synthetic).failed
             + check_new_field_definitions(synthetic).failed
             + check_authority_tier_fields(synthetic).failed)
    if fails:
        result.add("FAIL", f"V5: 합성 레코드에서 예상외 FAIL: {fails}")
    else:
        result.add("PASS", "V5: 합성 레코드(ADR-030 필드 0) → per-record FAIL 0")
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
                elif field_name == "content_genre":
                    invalid = [v for v in val if v not in VALID_CONTENT_GENRE_VALUES]
                    if invalid:
                        result.add("FAIL", f"V6: M2 record {sid} content_genre unknown values: {invalid}")
                elif field_name == "theological_category":
                    invalid = [v for v in val if v not in VALID_THEOLOGICAL_CATEGORIES]
                    if invalid:
                        result.add("FAIL", f"V6: M2 record {sid} theological_category unknown values: {invalid}")
        # tradition → str, 값은 canonical 표기 3개 중 하나
        if "tradition" in source:
            val = source["tradition"]
            if not isinstance(val, str):
                result.add("FAIL", f"V6: M2 record {sid} 'tradition' must be str")
            elif val not in ("Particular Baptist", "American Baptist", "Baptist Evangelical"):
                result.add("FAIL", f"V6: M2 record {sid} tradition unknown value: {val}")
    # V6 확장: raw_path / checksum_target 파일 존재 검사
    missing = []
    for source in sources:
        sid = source.get("source_id", "UNKNOWN")
        for field_name in ("raw_path", "checksum_target"):
            v = source.get(field_name)
            if isinstance(v, str) and not (PROJECT_ROOT / v).exists():
                missing.append(f"{sid}.{field_name}={v}")
    if missing:
        result.add("FAIL", f"V6: raw_path/checksum_target 파일 없음: {missing}")
    else:
        result.add("PASS", f"V6: raw_path/checksum_target 파일 전부 존재")
    result.add("PASS", "V6: all present ADR-030 fields have correct shape")
    return result


def check_authority_tier_fields(sources=None) -> ValidationResult:
    """V9-V12: authority_tier / tradition_relation / counter_refs (ADR-030 Amendment D, PROPOSED).

    V9  authority_tier ∉ 4-enum, 또는 authority_tier 있는데 tradition_relation
        없거나 값이 5-enum 밖 (부재 = skip)
    V10 authority_tier=T3 인데 counter_refs 없거나 비어있음
    V11 counter_refs 각 id가 (a) M2 내 존재하는 source_id 가 아니거나(orphan),
        (b) 그 대상 레코드의 authority_tier ∉ {T1, T2}
    V12 authority_tier ∈ {T1, T2, T4} 인데 counter_refs 가 non-empty
        (V11(b)와 조합해 counter_ref 그래프에 순환이 구조적으로 불가능해짐 —
        T3만 counter_refs를 가질 수 있고, T3는 T1/T2만 가리킬 수 있고,
        T1/T2는 counter_refs 자체를 가질 수 없으므로 그래프를 되짚어 올 간선이 없음)
    """
    result = ValidationResult()
    if sources is None:
        if not M2_PATH.exists():
            result.add("FAIL", "V9: M2 path missing")
            return result
        m2_data = yaml.safe_load(M2_PATH.read_text(encoding="utf-8"))
        sources = m2_data.get("sources", [])

    has_any = any(
        k in s for s in sources
        for k in ("authority_tier", "tradition_relation", "counter_refs")
    )
    if not has_any:
        result.add("PASS", "V9-V12: no authority_tier fields in M2 (not yet tagged, all skip)")
        return result

    by_id = {s.get("source_id"): s for s in sources if s.get("source_id")}

    for source in sources:
        sid = source.get("source_id", "UNKNOWN")
        tier = source.get("authority_tier")
        rel = source.get("tradition_relation")
        counter_refs = source.get("counter_refs")

        if tier is not None and tier not in VALID_AUTHORITY_TIERS:
            result.add("FAIL", f"V9: M2 record {sid} has invalid authority_tier '{tier}'")
        if tier is not None and rel is None:
            result.add("FAIL", f"V9: M2 record {sid} has authority_tier but no tradition_relation")
        if rel is not None and rel not in VALID_TRADITION_RELATIONS:
            result.add("FAIL", f"V9: M2 record {sid} has invalid tradition_relation '{rel}'")

        if tier == "T3" and not counter_refs:
            result.add("FAIL", f"V10: M2 record {sid} is authority_tier=T3 but has no counter_refs")

        if tier in ("T1", "T2", "T4") and counter_refs:
            result.add("FAIL", f"V12: M2 record {sid} authority_tier={tier} must not carry counter_refs")

        if counter_refs:
            if not isinstance(counter_refs, list) or not all(isinstance(x, str) for x in counter_refs):
                result.add("FAIL", f"V11: M2 record {sid} counter_refs must be list[str]")
            else:
                for ref in counter_refs:
                    target = by_id.get(ref)
                    if target is None:
                        result.add("FAIL", f"V11: M2 record {sid} counter_refs orphan reference '{ref}'")
                    elif target.get("authority_tier") not in ("T1", "T2"):
                        result.add(
                            "FAIL",
                            f"V11: M2 record {sid} counter_ref '{ref}' target "
                            f"authority_tier={target.get('authority_tier')!r} not in {{T1, T2}}",
                        )

    if not result.failed:
        result.add("PASS", "V9-V12: authority_tier fields valid where present")
    return result


def check_m2_identity() -> ValidationResult:
    result = ValidationResult()
    if not M2_PATH.exists():
        result.add("FAIL", "V7: M2 path missing")
        return result
    m2_data = yaml.safe_load(M2_PATH.read_text(encoding="utf-8"))
    sources = m2_data.get("sources", [])
    ids = {s.get("source_id") for s in sources}
    missing = M2_FROZEN_BASELINE_SOURCE_IDS - ids
    if missing:
        result.add("FAIL", f"V7: frozen baseline source_ids missing: {missing}")
        return result
    if len(sources) < len(M2_FROZEN_BASELINE_SOURCE_IDS):
        result.add("FAIL", f"V7: expected >= {len(M2_FROZEN_BASELINE_SOURCE_IDS)} M2 records, got {len(sources)}")
        return result
    result.add("PASS", f"V7: M2 has {len(sources)} records, frozen 14 baseline present (Amendment B)")
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
        ("V9-V12", check_authority_tier_fields),
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
