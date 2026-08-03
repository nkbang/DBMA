"""scripts/manifest_validator.py — NAE Manifest Layer 검증 (ADR-019).

resources/theological_sources/ 하위의 모든 manifest.yaml(최상위 키
`manifests:`) 파일을 찾아 각 Manifest Entry를 검사한다.
`source_validator.py`(corpus manifest, `source_manifest.yaml`/`sources:`
전담)와는 별도 도구다 — 두 파일 형식이 다르고 책임도 다르다
(NAE_MANIFEST_VALIDATOR_DESIGN_001.md §1 책임 경계표 참고).

검사 항목:
  1. Identity: manifest_id/source_id/schema_version 존재
  2. Authority Reference FK: author_id/work_id/edition_id/volume_id/
     issue_id/source_id가 Authority Registry(--registry-path, 필수)에
     실재하는지 — Registry Design v1의 work_type 조건부 규칙
     (source_validator.py의 _WORK_TYPE_FIELD_RULES와 동일 표)을
     Registry의 work_type 조회 결과에 적용
  3. Processing Lifecycle: acquisition_status/ocr_status/
     metadata_status/tsu_status/embedding_status 5개 필드 enum 검증
  4. Audit: created_at/updated_at 존재(필수), verified_by 없으면 WARNING
  5. TSU_ELIGIBLE 계산(읽기 전용, 판정만 — TSU 생성 없음):
     ocr_status=="complete" AND metadata_status=="verified" AND
     authority_verified(FK 전부 PASS) AND ocr_quality가 FAIL이 아님
     AND copyright_status=="public_domain"(--corpus-manifest-root로
     source_id 교차 조회, Manifest에는 저작권 정보를 저장하지 않음 —
     Single Source of Truth 원칙, NAE_MANIFEST_VALIDATOR_DESIGN_001.md §4)

읽기 전용 — manifest/Registry/corpus manifest 어느 것도 수정하지 않는다.

사용례:
    python scripts/manifest_validator.py \
        --root resources/theological_sources/manifest \
        --registry-path resources/theological_sources/authority \
        --corpus-manifest-root resources/theological_sources
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml

DEFAULT_ROOT = os.path.join("resources", "theological_sources", "manifest")
MANIFEST_FILENAME = "manifest.yaml"
CORPUS_MANIFEST_FILENAME = "source_manifest.yaml"

_IDENTITY_REQUIRED_FIELDS = ("manifest_id", "source_id")  # schema_version은 파일 최상위 필드

_LIFECYCLE_ENUMS: dict[str, tuple[str, ...]] = {
    # 정본: docs/NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md §Phase2 Processing Lifecycle
    "acquisition_status": ("pending", "acquired", "failed"),
    "ocr_status": ("not_started", "in_progress", "complete", "failed"),
    "metadata_status": ("not_started", "in_progress", "verified", "failed"),
    "tsu_status": ("not_ready", "ready", "complete", "failed"),
    "embedding_status": ("not_started", "in_progress", "complete", "failed"),
}

_AUDIT_REQUIRED_FIELDS = ("created_at", "updated_at")

# Manifest→Registry FK: entry 필드명 -> Registry 파일명(authority/{key}.yaml)의 최상위 키 및 ID 필드명
_FK_MAP: dict[str, tuple[str, str]] = {
    "author_id": ("authors", "author_id"),
    "work_id": ("works", "work_id"),
    "edition_id": ("editions", "edition_id"),
    "volume_id": ("volumes", "volume_id"),
    "issue_id": ("issues", "issue_id"),
    "source_id": ("sources", "source_id"),
}

# work_type별 edition_id/volume_id/issue_id 조건부 규칙 — source_validator.py의
# _WORK_TYPE_FIELD_RULES와 동일 표(중복 정의 금지 원칙, 값만 재확인용으로 복제
# — 두 스크립트가 서로 import하지 않는 현재 구조를 유지하기 위해 값을 그대로
# 옮겨 적었다. 규칙이 바뀌면 두 파일을 함께 갱신해야 한다).
_WORK_TYPE_FIELD_RULES: dict[str, dict[str, str]] = {
    "monograph":    {"edition_id": "required", "volume_id": "forbidden", "issue_id": "forbidden"},
    "multi_volume": {"edition_id": "required", "volume_id": "required", "issue_id": "forbidden"},
    "collection":   {"edition_id": "required", "volume_id": "required", "issue_id": "forbidden"},
    "periodical":   {"edition_id": "optional", "volume_id": "optional", "issue_id": "optional"},
}
_DEFAULT_WORK_TYPE = "monograph"

_OCR_QUALITY_ACCEPTABLE = ("PASS", "WARNING", None)


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


def find_manifest_files(root: Path) -> list[Path]:
    return sorted(root.rglob(MANIFEST_FILENAME))


def load_manifest_file(path: Path) -> tuple[list[dict[str, Any]], str | None, str | None]:
    """반환값: (entries, schema_version_or_None, error_or_None)."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [], None, f"YAML 파싱 실패: {e}"

    if not isinstance(data, dict):
        return [], None, "manifest 최상위는 dict(schema_version/manifests)여야 함"

    entries = data.get("manifests")
    if entries is None:
        return [], None, "'manifests' 키 없음"
    if not isinstance(entries, list):
        return [], None, "'manifests'는 배열이어야 함"

    return entries, data.get("schema_version"), None


def load_registry_index(registry_path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    """authority/{authors,works,editions,volumes,issues,sources}.yaml을 읽어
    entity별 {id: entry_dict} 인덱스를 만든다. 없는 파일은 빈 인덱스."""
    index: dict[str, dict[str, dict[str, Any]]] = {}
    for entry_field, (registry_key, id_field) in _FK_MAP.items():
        path = registry_path / f"{registry_key}.yaml"
        by_id: dict[str, dict[str, Any]] = {}
        if path.exists():
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                for e in data.get(registry_key, []) or []:
                    if isinstance(e, dict) and e.get(id_field):
                        by_id[e[id_field]] = e
            except Exception:
                pass  # 읽기 실패 시 빈 인덱스 — FK 조회는 실패로 이어짐(안전한 실패)
        index[registry_key] = by_id
    return index


def load_corpus_manifest_index(corpus_root: Path) -> dict[str, dict[str, Any]]:
    """resources/theological_sources/ 하위 source_manifest.yaml 전체를 읽어
    source_id -> entry 인덱스를 만든다(copyright_status 교차 조회 전용)."""
    index: dict[str, dict[str, Any]] = {}
    for path in corpus_root.rglob(CORPUS_MANIFEST_FILENAME):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        for e in data.get("sources", []) or []:
            if isinstance(e, dict) and e.get("source_id"):
                index[e["source_id"]] = e
    return index


def _entry_label(entry: dict[str, Any], index: int) -> str:
    mid = entry.get("manifest_id")
    return mid if mid else f"(manifest_id 없음, index={index})"


def _validate_identity(entry: dict[str, Any], top_schema_version: Any, location: str, result: ValidationResult) -> None:
    missing = []
    if not top_schema_version:
        missing.append("schema_version")
    for field in _IDENTITY_REQUIRED_FIELDS:
        if not entry.get(field):
            missing.append(field)
    if missing:
        result.add("FAIL", f"{location}: Identity 필수 필드 누락 — {', '.join(missing)}")
    else:
        result.add("PASS", f"{location}: Identity 필드 존재 확인(manifest_id/source_id/schema_version)")


def _resolve_work_type(work_id: Any, registry_index: dict[str, dict[str, dict[str, Any]]]) -> str:
    work_entry = registry_index.get("works", {}).get(work_id)
    if work_entry is None:
        return _DEFAULT_WORK_TYPE
    return work_entry.get("work_type") or _DEFAULT_WORK_TYPE


def _validate_authority_fk(
    entry: dict[str, Any],
    location: str,
    registry_index: dict[str, dict[str, dict[str, Any]]],
    result: ValidationResult,
) -> bool:
    """Authority Reference FK 검증. 반환값: 전부 PASS면 True(authority_verified)."""
    all_ok = True
    for entry_field, (registry_key, _id_field) in _FK_MAP.items():
        value = entry.get(entry_field)
        if not value:
            continue  # 값이 없는 FK는 여기서 검사하지 않음(work_type 조건부 규칙이 별도로 처리)
        known = registry_index.get(registry_key, {})
        if value not in known:
            result.add("FAIL", f"{location}: {entry_field}={value!r} — Registry({registry_key})에 존재하지 않음")
            all_ok = False
        else:
            result.add("PASS", f"{location}: {entry_field}={value!r} Registry 참조 확인")

    # work_type 조건부 규칙(source_validator.py와 동일 표) 재확인
    work_type = _resolve_work_type(entry.get("work_id"), registry_index)
    rules = _WORK_TYPE_FIELD_RULES.get(work_type, _WORK_TYPE_FIELD_RULES[_DEFAULT_WORK_TYPE])
    for field, rule in rules.items():
        value = entry.get(field)
        present = value is not None and value != ""
        if rule == "required" and not present:
            result.add("FAIL", f"{location}: {field} 누락 — work_type={work_type}(Registry 조회)에서 필수")
            all_ok = False
        elif rule == "forbidden" and present:
            result.add("FAIL", f"{location}: {field} 존재 — work_type={work_type}(Registry 조회)에서는 금지")
            all_ok = False

    return all_ok


def _validate_lifecycle(entry: dict[str, Any], location: str, result: ValidationResult) -> None:
    missing = [f for f in _LIFECYCLE_ENUMS if not entry.get(f)]
    if missing:
        result.add("FAIL", f"{location}: Lifecycle 필드 누락 — {', '.join(missing)}")
    for field, allowed in _LIFECYCLE_ENUMS.items():
        value = entry.get(field)
        if value is None:
            continue
        if value not in allowed:
            result.add("FAIL", f"{location}: {field} 값 비정상 — {value!r} (허용값: {allowed})")
        else:
            result.add("PASS", f"{location}: {field}={value}")


def _validate_audit(entry: dict[str, Any], location: str, result: ValidationResult) -> None:
    missing = [f for f in _AUDIT_REQUIRED_FIELDS if not entry.get(f)]
    if missing:
        result.add("FAIL", f"{location}: Audit 필수 필드 누락 — {', '.join(missing)}")
    else:
        result.add("PASS", f"{location}: Audit 필수 필드 존재 확인(created_at/updated_at)")

    if not entry.get("verified_by"):
        result.add("WARNING", f"{location}: verified_by 없음 — 사람 검증 이력 미기록")
    else:
        result.add("PASS", f"{location}: verified_by={entry.get('verified_by')}")


def compute_tsu_eligible(
    entry: dict[str, Any],
    authority_verified: bool,
    corpus_entry: dict[str, Any] | None,
) -> tuple[str, list[str]]:
    """TSU_ELIGIBLE 판정. 반환값: ("READY"|"BLOCKED", [사유 목록])."""
    reasons: list[str] = []

    if entry.get("ocr_status") != "complete":
        reasons.append(f"ocr_status={entry.get('ocr_status')!r} (요구: complete)")
    if entry.get("metadata_status") != "verified":
        reasons.append(f"metadata_status={entry.get('metadata_status')!r} (요구: verified)")
    if not authority_verified:
        reasons.append("authority_verified=false (Authority Registry FK 검증 실패)")

    ocr_quality = entry.get("ocr_quality")
    if ocr_quality not in _OCR_QUALITY_ACCEPTABLE:
        reasons.append(f"ocr_quality={ocr_quality!r} (요구: PASS/WARNING/미측정)")

    if corpus_entry is None:
        reasons.append("copyright_status 조회 불가 — --corpus-manifest-root 미지정 또는 source_id 없음")
    elif corpus_entry.get("copyright_status") != "public_domain":
        reasons.append(f"copyright_status={corpus_entry.get('copyright_status')!r} (요구: public_domain)")

    return ("BLOCKED" if reasons else "READY"), reasons


def validate_entry(
    entry: dict[str, Any],
    index: int,
    manifest_path: Path,
    top_schema_version: Any,
    registry_index: dict[str, dict[str, dict[str, Any]]],
    corpus_manifest_index: dict[str, dict[str, Any]] | None,
    result: ValidationResult,
) -> str | None:
    label = _entry_label(entry, index)
    location = f"{manifest_path} / {label}"

    _validate_identity(entry, top_schema_version, location, result)
    authority_verified = _validate_authority_fk(entry, location, registry_index, result)
    _validate_lifecycle(entry, location, result)
    _validate_audit(entry, location, result)

    corpus_entry = None
    if corpus_manifest_index is not None:
        corpus_entry = corpus_manifest_index.get(entry.get("source_id"))

    verdict, reasons = compute_tsu_eligible(entry, authority_verified, corpus_entry)
    if verdict == "READY":
        result.add("PASS", f"{location}: TSU_ELIGIBLE=READY")
    else:
        result.add("WARNING", f"{location}: TSU_ELIGIBLE=BLOCKED — {'; '.join(reasons)}")

    return entry.get("manifest_id")


def validate(root: Path, registry_path: Path, corpus_manifest_root: Path | None) -> ValidationResult:
    result = ValidationResult()
    manifest_files = find_manifest_files(root)

    if not manifest_files:
        result.add("WARNING", f"{root} 하위에 {MANIFEST_FILENAME} 없음 — 검사할 대상 없음")
        return result

    registry_index = load_registry_index(registry_path)
    corpus_manifest_index = load_corpus_manifest_index(corpus_manifest_root) if corpus_manifest_root else None

    seen_manifest_ids: dict[str, str] = {}
    seen_source_ids: dict[str, str] = {}  # Source:Manifest 1:1 무결성 확인용

    for manifest_path in manifest_files:
        entries, schema_version, error = load_manifest_file(manifest_path)
        if error is not None:
            result.add("FAIL", f"{manifest_path}: {error}")
            continue

        if not entries:
            result.add("WARNING", f"{manifest_path}: manifests 배열이 비어 있음")
            continue

        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                result.add("FAIL", f"{manifest_path} / index={idx}: entry가 dict가 아님")
                continue

            manifest_id = validate_entry(
                entry, idx, manifest_path, schema_version, registry_index, corpus_manifest_index, result
            )

            if manifest_id:
                if manifest_id in seen_manifest_ids:
                    result.add(
                        "FAIL",
                        f"manifest_id 중복: {manifest_id!r} — {seen_manifest_ids[manifest_id]} 와 {manifest_path} 에 동시 존재",
                    )
                else:
                    seen_manifest_ids[manifest_id] = str(manifest_path)

            source_id = entry.get("source_id")
            if source_id:
                if source_id in seen_source_ids:
                    result.add(
                        "FAIL",
                        f"Source:Manifest 1:1 위반 — source_id={source_id!r}가 {seen_source_ids[source_id]} 와 {manifest_path} 양쪽에 존재",
                    )
                else:
                    seen_source_ids[source_id] = str(manifest_path)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=DEFAULT_ROOT, help=f"검사 루트 디렉토리 (기본: {DEFAULT_ROOT})")
    parser.add_argument(
        "--registry-path",
        required=True,
        help="Authority Registry 디렉토리(필수) — Manifest Validator의 핵심 책임(Manifest↔Registry FK)이므로 선택 아님",
    )
    parser.add_argument(
        "--corpus-manifest-root",
        default=None,
        help="corpus manifest(source_manifest.yaml) 트리 루트(선택) — TSU_ELIGIBLE 계산용 copyright_status 교차 조회",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"[FAIL] 루트 디렉토리 없음: {root}")
        return 1

    registry_path = Path(args.registry_path)
    if not registry_path.exists():
        print(f"[FAIL] Registry 디렉토리 없음: {registry_path}")
        return 1

    corpus_manifest_root = Path(args.corpus_manifest_root) if args.corpus_manifest_root else None
    if corpus_manifest_root is not None and not corpus_manifest_root.exists():
        print(f"[FAIL] corpus manifest 루트 없음: {corpus_manifest_root}")
        return 1

    result = validate(root, registry_path, corpus_manifest_root)
    result.print_all()

    return 1 if result.fail_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
