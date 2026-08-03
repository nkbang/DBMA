"""scripts/source_validator.py — NAE 검증 원문 소스 manifest 검사.

resources/theological_sources/ 하위의 모든 source_manifest.yaml 파일을
찾아 각 항목을 검사한다. 각 manifest의 최상위 `schema_version` 값으로
스키마를 판별해 v1.2(NAE-PD)와 v2.1.0(NAE-MODERN, ADR-016) 양쪽을 모두
지원한다 — 하나의 도구로 두 스키마를 동시에 검증한다(Dual Schema
Support, NAE-VALIDATOR-IMPLEMENTATION-001).

검사 항목(공통, 스키마 무관):
  - status 검사: status 값이 허용된 enum 중 하나인지
  - source id 중복 검사: 전체 트리(모든 manifest 합산)에서 source_id가
    유일한지

검사 항목(v1.2 전용, 기존 동작 그대로 유지 — 회귀 없음):
  - metadata 존재 확인: source_id/title/license/content_genre/status
  - license field 확인: license 필드 자체가 존재하는지(값의 타당성 판단은
    하지 않음 — source_manifest.schema.yaml 주석 참고)

검사 항목(v2.1.0 전용, 신규 — NAE_SOURCE_VALIDATOR_REQUIREMENTS_v1.md 기준):
  - metadata 존재 확인: source_id/author_id/work_id/edition_id/title/
    publication_year/category/source_type/copyright_status/
    usage_permission/access_control/citation_policy/status
  - enum 값 검증: source_type/copyright_status/usage_permission/
    access_control이 NAE_METADATA_GOVERNANCE_v1.md §4가 정의한 값 중
    하나인지
  - volume_number: 존재할 경우 1 이상의 정수인지
  - archive_source: 선택 필드 — 없으면 PASS, 있으면 문자열 타입인지만
    확인(형식 검증)

인식 불가능한 schema_version(1.x/2.x 어느 쪽도 아닌 값)은 FAIL 처리한다.

읽기 전용 — manifest 파일이나 원문을 수정하지 않는다.

사용례:
    python scripts/source_validator.py
    python scripts/source_validator.py --root resources/theological_sources
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

# status enum은 v1.2/v2.1.0 공통(NAE_SOURCE_VALIDATOR_REQUIREMENTS_v1.md §3.2/§3.3).
_VALID_STATUSES = (
    "PREPARED", "ACQUIRED", "VERIFIED", "INGESTED",
    "approved_for_acquisition", "permission_required", "verification_pending",
)

# ── v2.1.0 (NAE-MODERN, ADR-016) ─────────────────────────────────────────
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


def detect_schema_major(schema_version: Any) -> str | None:
    """schema_version 값으로 주 버전을 판별한다. "1" | "2" | None(인식 불가)."""
    if not isinstance(schema_version, str):
        return None
    if schema_version.startswith("1."):
        return "1"
    if schema_version.startswith("2."):
        return "2"
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


def _validate_entry_v2(entry: dict[str, Any], location: str, result: ValidationResult) -> None:
    """v2.1.0(NAE-MODERN, ADR-016) 검증 — 신규."""
    # 1) metadata 존재 확인 — Schema v2.1.0 Required Fields
    missing = [f for f in _V2_REQUIRED_FIELDS if not entry.get(f)]
    if missing:
        result.add("FAIL", f"{location}: 필수 필드 누락/공백(v2.1.0) — {', '.join(missing)}")
    else:
        result.add("PASS", f"{location}: 필수 필드 존재 확인(v2.1.0)")

    # 2) enum 값 검증 — 값 체계 정본: NAE_METADATA_GOVERNANCE_v1.md §4
    for field, allowed in _V2_ENUM_FIELDS.items():
        value = entry.get(field)
        if value is None:
            continue  # 누락은 위 필수 필드 검사에서 이미 FAIL 처리됨
        if value not in allowed:
            result.add(
                "FAIL",
                f"{location}: {field} 값 비정상 — {value!r} (허용값: {allowed})",
            )
        else:
            result.add("PASS", f"{location}: {field}={value}")

    # 3) volume_number — 선택 필드, 존재할 경우 1 이상의 정수인지 확인
    if "volume_number" in entry and entry.get("volume_number") is not None:
        vol_num = entry.get("volume_number")
        if not isinstance(vol_num, int) or isinstance(vol_num, bool) or vol_num < 1:
            result.add("FAIL", f"{location}: volume_number 값 비정상 — {vol_num!r} (1 이상의 정수여야 함)")
        else:
            result.add("PASS", f"{location}: volume_number={vol_num}")

    # 4) archive_source — 선택 필드. 없으면 PASS(검사 자체를 생략), 있으면
    #    형식(문자열 타입) 검증만 수행 — 값의 사실 여부는 판단하지 않음
    #    (Pilot-001 F-P4: RAW에 실제로 없는 정보인 경우가 많아 optional로
    #    확정, docs/NAE_CORPUS_INGESTION_STANDARD_v1.md Phase 7 참고).
    if entry.get("archive_source"):
        archive_source = entry.get("archive_source")
        if not isinstance(archive_source, str):
            result.add("FAIL", f"{location}: archive_source 형식 오류 — 문자열이어야 함(현재: {type(archive_source).__name__})")
        else:
            result.add("PASS", f"{location}: archive_source 형식 확인")


def validate_entry(
    entry: dict[str, Any],
    index: int,
    manifest_path: Path,
    schema_major: str | None,
    result: ValidationResult,
) -> str | None:
    """entry 하나를 검사한다. source_id가 있으면 반환(중복 검사용), 없으면 None."""
    label = _entry_label(entry, index)
    location = f"{manifest_path} / {label}"

    if schema_major == "1":
        _validate_entry_v1(entry, location, result)
    elif schema_major == "2":
        _validate_entry_v2(entry, location, result)
    else:
        result.add("FAIL", f"{location}: schema_version 인식 불가 — 1.x 또는 2.x 형식이어야 함")
        return entry.get("source_id")

    # status 검사 — 스키마 공통
    status = entry.get("status")
    if status not in _VALID_STATUSES:
        result.add("FAIL", f"{location}: status 값 비정상 — {status!r} (허용값: {_VALID_STATUSES})")
    else:
        result.add("PASS", f"{location}: status={status}")

    return entry.get("source_id")


def validate(root: Path) -> ValidationResult:
    result = ValidationResult()
    manifests = find_manifests(root)

    if not manifests:
        result.add("WARNING", f"{root} 하위에 {MANIFEST_FILENAME} 없음 — 검사할 대상 없음")
        return result

    seen_ids: dict[str, str] = {}  # source_id -> 최초 발견된 manifest 경로

    for manifest_path in manifests:
        entries, schema_version, error = load_manifest(manifest_path)
        if error is not None:
            result.add("FAIL", f"{manifest_path}: {error}")
            continue

        if not entries:
            result.add("WARNING", f"{manifest_path}: sources 배열이 비어 있음")
            continue

        schema_major = detect_schema_major(schema_version)

        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                result.add("FAIL", f"{manifest_path} / index={idx}: entry가 dict가 아님")
                continue

            source_id = validate_entry(entry, idx, manifest_path, schema_major, result)

            # source id 중복 검사 (전체 트리 기준, 스키마 무관 공통 —
            # v1.2/v2.1.0이 source_id 네임스페이스를 공유한다는 원칙,
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
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"[FAIL] 루트 디렉토리 없음: {root}")
        return 1

    result = validate(root)
    result.print_all()

    return 1 if result.fail_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
