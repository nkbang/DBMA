"""scripts/source_validator.py — NAE 검증 원문 소스 manifest 검사.

resources/theological_sources/ 하위의 모든 source_manifest.yaml 파일을
찾아 각 항목을 검사한다. 각 manifest의 최상위 `schema_version` 값으로
스키마를 판별해 v1.2(NAE-PD), v2.1.0(NAE-MODERN, ADR-016),
v2.2.x(NAE-MODERN, ADR-018/019 — Periodical/Manifest 필드) 세 트랙을
모두 지원한다(Dual/Triple Schema Support,
NAE-VALIDATOR-IMPLEMENTATION-001 → NAE-VALIDATOR-V2.2-IMPLEMENTATION-001).

검사 항목(공통, 스키마 무관):
  - status 검사: status 값이 허용된 enum 중 하나인지
  - source id 중복 검사: 전체 트리(모든 manifest 합산)에서 source_id가
    유일한지
  - manifest_id/processing_status(Manifest Layer, ADR-019) — entry에
    manifest_id 필드가 존재할 때만 추가로 검사(선택적, 존재하지 않는
    entry는 영향 없음)

검사 항목(v1.2 전용, 기존 동작 그대로 유지 — 회귀 없음):
  - metadata 존재 확인: source_id/title/license/content_genre/status
  - license field 확인

검사 항목(v2.1.x 전용, 기존 동작 그대로 유지 — 회귀 없음):
  - metadata 존재 확인(edition_id 포함 항상 필수)
  - enum 값 검증: source_type/copyright_status/usage_permission/
    access_control
  - volume_number/archive_source 선택 필드 형식 검증

검사 항목(v2.2.x 전용, 신규 — NAE_SCHEMA_V2_2_APPLICATION_REPORT_001.md 기준):
  - metadata 존재 확인(edition_id는 조건부 필수로 완화)
  - work_type(monograph/multi_volume/periodical/collection) enum 검증,
    누락 시 monograph로 간주(Application Report §Field Specification)
  - work_type별 edition_id/volume_id/issue_id 조건부 규칙(§Phase3/4/5)
  - Authority Reference(author_id/work_id/edition_id/volume_id/
    issue_id) FK 존재 검증 — `--registry-path` 지정 시에만 수행(선택)

인식 불가능한 schema_version(1.x/2.x 어느 쪽도 아닌 값)은 FAIL 처리한다.

읽기 전용 — manifest 파일이나 원문을 수정하지 않는다.

사용례:
    python scripts/source_validator.py
    python scripts/source_validator.py --root resources/theological_sources
    python scripts/source_validator.py --registry-path resources/theological_sources/authority
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml

DEFAULT_ROOT = os.path.join("resources", "theological_sources")
MANIFEST_FILENAME = "source_manifest.yaml"

# ── v1.2 (NAE-PD) ────────────────────────────────────────────────────────
# [NAE-SOURCE-003] resources/theological_sources/source_manifest.schema.yaml
# v1.1 — RAW 후보 심사 단계에서 쓰이는 3개 값(approved_for_acquisition/
# permission_required/verification_pending)을 기존 4단계
# (PREPARED/ACQUIRED/VERIFIED/INGESTED, STEP5_REGISTRY_TRANSITION.md)에
# 추가. 스키마 파일이 이 상수의 정본이므로, 둘이 어긋나면 스키마를
# 기준으로 여기를 갱신할 것.
_V1_REQUIRED_FIELDS = ("source_id", "title", "license", "content_genre", "status")

# status enum은 v1.2/v2.x 공통(NAE_SOURCE_VALIDATOR_REQUIREMENTS_v1.md §3.2/§3.3).
_VALID_STATUSES = (
    "PREPARED", "ACQUIRED", "VERIFIED", "INGESTED",
    "approved_for_acquisition", "permission_required", "verification_pending",
)

# ── v2.1.x (NAE-MODERN, ADR-016) ─────────────────────────────────────────
# 정본: resources/theological_sources/modern/source_manifest.schema.yaml,
# 값 체계 정본: docs/NAE_METADATA_GOVERNANCE_v1.md §4.
_V2_REQUIRED_FIELDS = (
    "source_id", "author_id", "work_id", "edition_id", "title",
    "publication_year", "category", "source_type", "copyright_status",
    "usage_permission", "access_control", "citation_policy", "status",
)

_V2_ENUM_FIELDS: dict[str, tuple[str, ...]] = {
    "source_type": ("licensed", "purchased", "personal", "reference", "public_archive"),
    "copyright_status": ("public_domain", "copyrighted", "licensed", "unknown"),
    "usage_permission": ("research", "citation_only", "internal_use", "no_redistribution"),
    "access_control": ("public", "restricted", "private"),
}

# ── v2.2.x (NAE-MODERN, ADR-018/019) ─────────────────────────────────────
# 정본: docs/NAE_SCHEMA_V2_2_APPLICATION_REPORT_001.md
# edition_id는 v2.1.x와 달리 여기서 "항상 필수"에서 제외 — work_type별
# 조건부 규칙(_validate_work_type_conditional_fields)으로 별도 검사한다.
_V22_BASE_REQUIRED_FIELDS = tuple(f for f in _V2_REQUIRED_FIELDS if f != "edition_id")

_V22_WORK_TYPES = ("monograph", "multi_volume", "periodical", "collection")
_DEFAULT_WORK_TYPE = "monograph"  # work_type 필드 누락 시 간주값(Application Report §Field Specification)

# work_type별 edition_id/volume_id/issue_id 조건부 규칙(Application Report §Phase3/4/5).
# "collection"은 명령서에 별도 규칙이 명시되지 않아 multi_volume과 동일하게
# 취급한다(문서화된 가정 — Remaining Risk로 기록, 최종 보고서 참고).
_WORK_TYPE_FIELD_RULES: dict[str, dict[str, str]] = {
    # 값: "required" | "forbidden" | "optional"
    "monograph":    {"edition_id": "required", "volume_id": "forbidden", "issue_id": "forbidden"},
    "multi_volume": {"edition_id": "required", "volume_id": "required", "issue_id": "forbidden"},
    "collection":   {"edition_id": "required", "volume_id": "required", "issue_id": "forbidden"},
    "periodical":   {"edition_id": "optional", "volume_id": "optional", "issue_id": "optional"},
}

# 정기간행물 최소 요구: volume_id 또는 issue_id 중 최소 1개(Application Report §Phase3).
_PERIODICAL_MIN_ONE_OF = ("volume_id", "issue_id")

# ── Manifest Layer(ADR-019) — 선택적 검사, entry에 manifest_id가 있을 때만 ──
_MANIFEST_REQUIRED_FIELDS = ("schema_version", "manifest_id", "source_id")
_MANIFEST_STATUS_VALUES = ("acquired", "ocr_complete", "metadata_complete", "tsu_ready", "embedded")


class ValidationResult:
    def __init__(self) -> None:
        self.pass_count = 0
        self.warn_count = 0
        self.fail_count = 0
        self.lines: list[str] = []

    def add(self, level: str, message: str) -> None:
        if level == "PASS":
            self.pass_count += 1
        elif level == "WARNING":
            self.warn_count += 1
        elif level == "FAIL":
            self.fail_count += 1
        self.lines.append(f"[{level}] {message}")

    def print_all(self) -> None:
        for line in self.lines:
            print(line)
        print()
        print(f"=== 결과 요약: PASS={self.pass_count} WARNING={self.warn_count} FAIL={self.fail_count} ===")


def find_manifests(root: Path) -> list[Path]:
    return sorted(root.rglob(MANIFEST_FILENAME))


def load_manifest(path: Path) -> tuple[list[dict[str, Any]], str | None, str | None]:
    """manifest 파일을 로드한다. 반환값: (entries, schema_version_or_None, error_or_None)."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [], None, f"YAML 파싱 실패: {e}"

    if not isinstance(data, dict):
        return [], None, "manifest 최상위는 dict(schema_version/sources)여야 함"

    sources = data.get("sources")
    if sources is None:
        return [], None, "'sources' 키 없음"
    if not isinstance(sources, list):
        return [], None, "'sources'는 배열이어야 함"

    schema_version = data.get("schema_version")
    return sources, schema_version, None


def detect_schema_track(schema_version: Any) -> str | None:
    """schema_version 값으로 검증 트랙을 판별한다.

    "v1" | "v2.1" | "v2.2" | None(인식 불가). 2.2.0 이상 2.x는 "v2.2"
    (conditional rules 적용), 그 외 2.x(2.0.x/2.1.x)는 "v2.1"(기존 동작
    유지 — 회귀 없음).
    """
    if not isinstance(schema_version, str):
        return None
    if schema_version.startswith("1."):
        return "v1"
    if schema_version.startswith("2."):
        parts = schema_version.split(".")
        try:
            major, minor = int(parts[0]), int(parts[1])
        except (IndexError, ValueError):
            return "v2.1"  # 파싱 실패해도 2.x는 기존 v2.1 동작으로 폴백(과거 회귀 없음 우선)
        if (major, minor) >= (2, 2):
            return "v2.2"
        return "v2.1"
    return None


def _entry_label(entry: dict[str, Any], index: int) -> str:
    sid = entry.get("source_id")
    return sid if sid else f"(source_id 없음, index={index})"


def _validate_entry_v1(entry: dict[str, Any], location: str, result: ValidationResult) -> None:
    """v1.2(NAE-PD) 검증 — 기존 동작 그대로(회귀 없음)."""
    # 1) metadata 존재 확인 — 필수 필드가 비어 있지 않은지
    missing = [f for f in _V1_REQUIRED_FIELDS if not entry.get(f)]
    if missing:
        result.add("FAIL", f"{location}: 필수 필드 누락/공백 — {', '.join(missing)}")
    else:
        result.add("PASS", f"{location}: 필수 필드 존재 확인")

    # 2) license field 확인 (존재 여부만 — missing에 이미 포함되지만
    #    라이선스는 데이터 재사용 가능 여부를 가르는 필드라 별도로도 명시)
    if not entry.get("license"):
        result.add("FAIL", f"{location}: license 필드 없음")
    else:
        result.add("PASS", f"{location}: license={entry.get('license')}")


def _validate_v2_enum_and_optional_fields(entry: dict[str, Any], location: str, result: ValidationResult) -> None:
    """v2.1.x/v2.2.x 공통 — enum 값, volume_number, archive_source 검증."""
    for field, allowed in _V2_ENUM_FIELDS.items():
        value = entry.get(field)
        if value is None:
            continue  # 누락은 필수 필드 검사에서 이미 처리됨(v2.1) 또는 optional(v2.2 일부)
        if value not in allowed:
            result.add(
                "FAIL",
                f"{location}: {field} 값 비정상 — {value!r} (허용값: {allowed})",
            )
        else:
            result.add("PASS", f"{location}: {field}={value}")

    if "volume_number" in entry and entry.get("volume_number") is not None:
        vol_num = entry.get("volume_number")
        if not isinstance(vol_num, int) or isinstance(vol_num, bool) or vol_num < 1:
            result.add("FAIL", f"{location}: volume_number 값 비정상 — {vol_num!r} (1 이상의 정수여야 함)")
        else:
            result.add("PASS", f"{location}: volume_number={vol_num}")

    if entry.get("archive_source"):
        archive_source = entry.get("archive_source")
        if not isinstance(archive_source, str):
            result.add("FAIL", f"{location}: archive_source 형식 오류 — 문자열이어야 함(현재: {type(archive_source).__name__})")
        else:
            result.add("PASS", f"{location}: archive_source 형식 확인")


def _validate_entry_v2(entry: dict[str, Any], location: str, result: ValidationResult) -> None:
    """v2.1.x(NAE-MODERN, ADR-016) 검증 — 기존 동작 그대로(회귀 없음)."""
    missing = [f for f in _V2_REQUIRED_FIELDS if not entry.get(f)]
    if missing:
        result.add("FAIL", f"{location}: 필수 필드 누락/공백(v2.1.x) — {', '.join(missing)}")
    else:
        result.add("PASS", f"{location}: 필수 필드 존재 확인(v2.1.x)")

    _validate_v2_enum_and_optional_fields(entry, location, result)


def _validate_work_type_conditional_fields(entry: dict[str, Any], location: str, result: ValidationResult) -> None:
    """work_type별 edition_id/volume_id/issue_id 조건부 규칙(v2.2.x 전용).

    정본: docs/NAE_SCHEMA_V2_2_APPLICATION_REPORT_001.md §Phase3/4/5.
    """
    work_type = entry.get("work_type")
    if work_type is None:
        effective_work_type = _DEFAULT_WORK_TYPE
        result.add("PASS", f"{location}: work_type 누락 — {_DEFAULT_WORK_TYPE}로 간주")
    elif work_type not in _V22_WORK_TYPES:
        result.add("FAIL", f"{location}: work_type 값 비정상 — {work_type!r} (허용값: {_V22_WORK_TYPES})")
        return  # 유효하지 않은 work_type이면 조건부 규칙 자체를 적용할 수 없음
    else:
        effective_work_type = work_type
        result.add("PASS", f"{location}: work_type={work_type}")

    rules = _WORK_TYPE_FIELD_RULES[effective_work_type]
    for field, rule in rules.items():
        value = entry.get(field)
        present = value is not None and value != ""
        if rule == "required" and not present:
            result.add("FAIL", f"{location}: {field} 누락 — work_type={effective_work_type}에서 필수")
        elif rule == "forbidden" and present:
            result.add("FAIL", f"{location}: {field} 존재 — work_type={effective_work_type}에서는 금지(값: {value!r})")
        else:
            result.add("PASS", f"{location}: {field} 규칙 준수(work_type={effective_work_type}, rule={rule})")

    if effective_work_type == "periodical":
        if not any(entry.get(f) for f in _PERIODICAL_MIN_ONE_OF):
            result.add(
                "FAIL",
                f"{location}: periodical 최소 요구 미충족 — {_PERIODICAL_MIN_ONE_OF} 중 최소 1개 필요",
            )
        else:
            result.add("PASS", f"{location}: periodical 최소 요구 충족(volume_id 또는 issue_id 존재)")


def _validate_entry_v22(entry: dict[str, Any], location: str, result: ValidationResult) -> None:
    """v2.2.x(NAE-MODERN, ADR-018/019) 검증 — 신규.

    edition_id는 base required에서 제외하고 work_type 조건부 규칙으로
    별도 검사한다(NAE_SCHEMA_V2_2_APPLICATION_REPORT_001.md §2 변경 6).
    """
    missing = [f for f in _V22_BASE_REQUIRED_FIELDS if not entry.get(f)]
    if missing:
        result.add("FAIL", f"{location}: 필수 필드 누락/공백(v2.2.x) — {', '.join(missing)}")
    else:
        result.add("PASS", f"{location}: 필수 필드 존재 확인(v2.2.x, edition_id 제외 — 조건부 별도 검사)")

    _validate_v2_enum_and_optional_fields(entry, location, result)
    _validate_work_type_conditional_fields(entry, location, result)


def _validate_manifest_fields(entry: dict[str, Any], location: str, top_schema_version: Any, result: ValidationResult) -> None:
    """Manifest Layer(ADR-019) 필드 검증 — entry에 manifest_id가 있을 때만 수행.

    이번 단계(NAE-VALIDATOR-V2.2-IMPLEMENTATION-001 Phase 7)에서는
    processing_status의 상태 전이(역행 금지 등) 로직은 구현하지 않는다
    — enum 값 검증과 audit 필드(verified_by) 존재 확인만 수행한다.
    """
    if "manifest_id" not in entry:
        return  # Manifest Layer를 사용하지 않는 entry는 검사 대상 아님(선택적)

    missing = []
    for field in _MANIFEST_REQUIRED_FIELDS:
        value = top_schema_version if field == "schema_version" else entry.get(field)
        if not value:
            missing.append(field)
    if missing:
        result.add("FAIL", f"{location}: Manifest 필수 필드 누락 — {', '.join(missing)}")
    else:
        result.add("PASS", f"{location}: Manifest 필수 필드 존재 확인(schema_version/manifest_id/source_id)")

    status = entry.get("processing_status")
    if status is not None:
        if status not in _MANIFEST_STATUS_VALUES:
            result.add("FAIL", f"{location}: processing_status 값 비정상 — {status!r} (허용값: {_MANIFEST_STATUS_VALUES})")
        else:
            result.add("PASS", f"{location}: processing_status={status}")

    # audit 필드 존재 확인만(역행 검사/lifecycle enforcement는 이번 단계 범위 밖)
    if not entry.get("verified_by"):
        result.add("WARNING", f"{location}: Manifest audit 필드(verified_by) 없음 — 사람 검증 이력 미기록")
    else:
        result.add("PASS", f"{location}: verified_by={entry.get('verified_by')}")


def _validate_authority_references(
    entry: dict[str, Any],
    location: str,
    registry_index: dict[str, set[str]] | None,
    result: ValidationResult,
) -> None:
    """Authority Reference(FK) 존재 검증 — registry_index가 주어질 때만 수행(선택).

    --registry-path 미지정 시 이 함수는 아무 것도 하지 않는다(schema
    validation only, NAE-VALIDATOR-V2.2-IMPLEMENTATION-001 Phase 6).
    """
    if registry_index is None:
        return

    fk_map = {
        "author_id": "authors",
        "work_id": "works",
        "edition_id": "editions",
        "volume_id": "volumes",
        "issue_id": "issues",
    }
    for field, registry_key in fk_map.items():
        value = entry.get(field)
        if not value:
            continue
        known_ids = registry_index.get(registry_key, set())
        if value not in known_ids:
            result.add("FAIL", f"{location}: {field}={value!r} — Registry({registry_key})에 존재하지 않음")
        else:
            result.add("PASS", f"{location}: {field}={value!r} Registry 참조 확인")


def load_registry_index(registry_path: Path) -> dict[str, set[str]]:
    """Authority Registry 디렉토리에서 각 entity의 ID 집합을 읽어온다(읽기 전용).

    파일명 규칙: authors.yaml/works.yaml/editions.yaml/volumes.yaml/
    issues.yaml — 없는 파일은 빈 집합으로 취급(FAIL 아님, 선택적 계층).
    """
    id_field = {
        "authors": "author_id",
        "works": "work_id",
        "editions": "edition_id",
        "volumes": "volume_id",
        "issues": "issue_id",
    }
    index: dict[str, set[str]] = {}
    for key, field in id_field.items():
        path = registry_path / f"{key}.yaml"
        ids: set[str] = set()
        if path.exists():
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                for entry in (data or {}).get(key, []) or []:
                    if isinstance(entry, dict) and entry.get(field):
                        ids.add(entry[field])
            except Exception:
                pass  # 읽기 실패 시 빈 집합(FK 검사는 실패로 이어짐 — 의도된 안전한 실패)
        index[key] = ids
    return index


def validate_entry(
    entry: dict[str, Any],
    index: int,
    manifest_path: Path,
    schema_track: str | None,
    schema_version: Any,
    registry_index: dict[str, set[str]] | None,
    result: ValidationResult,
) -> str | None:
    """entry 하나를 검사한다. source_id가 있으면 반환(중복 검사용), 없으면 None."""
    label = _entry_label(entry, index)
    location = f"{manifest_path} / {label}"

    if schema_track == "v1":
        _validate_entry_v1(entry, location, result)
    elif schema_track == "v2.1":
        _validate_entry_v2(entry, location, result)
    elif schema_track == "v2.2":
        _validate_entry_v22(entry, location, result)
    else:
        result.add("FAIL", f"{location}: schema_version 인식 불가 — 1.x 또는 2.x 형식이어야 함")
        return entry.get("source_id")

    # status 검사 — 스키마 공통
    status = entry.get("status")
    if status not in _VALID_STATUSES:
        result.add("FAIL", f"{location}: status 값 비정상 — {status!r} (허용값: {_VALID_STATUSES})")
    else:
        result.add("PASS", f"{location}: status={status}")

    # Manifest Layer 필드(선택적) + Authority Reference FK(선택적, --registry-path)
    _validate_manifest_fields(entry, location, schema_version, result)
    if schema_track in ("v2.1", "v2.2"):
        _validate_authority_references(entry, location, registry_index, result)

    return entry.get("source_id")


def validate(root: Path, registry_path: Path | None = None) -> ValidationResult:
    result = ValidationResult()
    manifests = find_manifests(root)

    if not manifests:
        result.add("WARNING", f"{root} 하위에 {MANIFEST_FILENAME} 없음 — 검사할 대상 없음")
        return result

    registry_index = load_registry_index(registry_path) if registry_path is not None else None

    seen_ids: dict[str, str] = {}  # source_id -> 최초 발견된 manifest 경로

    for manifest_path in manifests:
        entries, schema_version, error = load_manifest(manifest_path)
        if error is not None:
            result.add("FAIL", f"{manifest_path}: {error}")
            continue

        if not entries:
            result.add("WARNING", f"{manifest_path}: sources 배열이 비어 있음")
            continue

        schema_track = detect_schema_track(schema_version)

        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                result.add("FAIL", f"{manifest_path} / index={idx}: entry가 dict가 아님")
                continue

            source_id = validate_entry(entry, idx, manifest_path, schema_track, schema_version, registry_index, result)

            # source id 중복 검사 (전체 트리 기준, 스키마 무관 공통 —
            # v1.2/v2.x가 source_id 네임스페이스를 공유한다는 원칙,
            # NAE_METADATA_GOVERNANCE_v1.md §5.3)
            if source_id:
                if source_id in seen_ids:
                    result.add(
                        "FAIL",
                        f"source_id 중복: {source_id!r} — {seen_ids[source_id]} 와 {manifest_path} 에 동시 존재",
                    )
                else:
                    seen_ids[source_id] = str(manifest_path)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=DEFAULT_ROOT, help=f"검사 루트 디렉토리 (기본: {DEFAULT_ROOT})")
    parser.add_argument(
        "--registry-path",
        default=None,
        help="Authority Registry 디렉토리(선택) — 지정 시 FK 존재 검증 수행, 미지정 시 schema validation만",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"[FAIL] 루트 디렉토리 없음: {root}")
        return 1

    registry_path = Path(args.registry_path) if args.registry_path else None
    if registry_path is not None and not registry_path.exists():
        print(f"[FAIL] Registry 디렉토리 없음: {registry_path}")
        return 1

    result = validate(root, registry_path)
    result.print_all()

    return 1 if result.fail_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
