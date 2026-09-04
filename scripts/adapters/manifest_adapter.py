"""scripts/adapters/manifest_adapter.py — Manifest Layer Adapter
(NAE-METADATA-MIGRATION-PILOT-IMPLEMENTATION-001, comment-preserving
YAML: NAE-ADAPTER-REFACTOR-001).

Migration Engine은 Manifest(`manifest.yaml`, ADR-019)의 존재를 모른다.
이 Adapter가 Manifest 구조(Identity/Authority Reference FK/Processing
Lifecycle/Audit 필드, `manifest_validator.py` §책임 경계표와 동일 원칙)
를 아는 유일한 계층이다.

**ADR-017 Option B 원칙 재확인**: Registry의 canonical_id/legacy_id
backfill은 기존 FK 문자열(author_id/work_id/edition_id/volume_id/
source_id)을 전혀 바꾸지 않으므로, Manifest가 그 FK를 그대로 참조하고
있다면 **Manifest의 FK 값 자체는 변경할 필요가 없다** — 이 Adapter의
"Manifest 수정" 역할은 FK 값을 고쳐 쓰는 것이 아니라, Registry
Migration이 반영된 뒤에도 FK 참조가 여전히 유효한지 재확인(verify)하고,
그 결과를 Audit 성격의 필드(`updated_at` 등)에 반영하는 것으로 제한한다.

**Comment-Preserving YAML(NAE-ADAPTER-REFACTOR-001)**: `ruamel.yaml`
round-trip 모드로 원본 노드를 그 자리에서만 수정한다 — PyYAML
safe_load/safe_dump 왕복이 주석·따옴표·들여쓰기·키 순서·빈 줄을 전부
버리는 문제(NAE_PILOT_MIGRATION_VALIDATION_REPORT_001.md §4에서 실측
발견)를 제거한다.

실제 Production/Pilot Manifest(`resources/theological_sources/manifest/
pilot/*.yaml`)를 대상으로 실행하는 것은 이번 구현 범위에서 금지된다 —
이 모듈은 경로를 하드코딩하지 않으며 호출자가 넘긴 임의의 파일만 다룬다.
"""

from __future__ import annotations

import io
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.migration_engine import MigrationUnit

MANIFEST_TOP_KEY = "manifests"

# manifest_validator.py §2와 동일한 FK 필드 목록(자식 필드명 -> Registry
# entity_key). Adapter는 authority_validator.py의 실제 값을 몰라도 되며,
# 호출자가 넘겨주는 registry_index(entity_id 집합)로만 대조한다.
FK_FIELDS: tuple[str, ...] = ("author_id", "work_id", "edition_id", "volume_id", "source_id")


def _represent_none(representer: Any, data: Any) -> Any:
    """None을 항상 명시적 `null` 토큰으로 덤프한다(registry_adapter.py와
    동일 이유 — ruamel 기본값은 원본의 `key: null` 표기를 빈 값으로
    바꿔버린다)."""
    return representer.represent_scalar("tag:yaml.org,2002:null", "null")


def _yaml() -> YAML:
    y = YAML(typ="rt")
    y.preserve_quotes = True
    y.width = 100_000
    # Manifest YAML 파일의 실제 표기 스타일(2-space indent, dash가 block
    # 안쪽으로 2칸 들여써짐)과 일치시킨다 — registry_adapter.py와 동일 이유.
    y.indent(mapping=2, sequence=4, offset=2)
    y.representer.add_representer(type(None), _represent_none)
    return y


def _load_yaml(text: str) -> CommentedMap:
    if not text:
        return CommentedMap()
    return _yaml().load(text) or CommentedMap()


def _dump_yaml(data: CommentedMap) -> str:
    buf = io.StringIO()
    _yaml().dump(data, buf)
    return buf.getvalue()


@dataclass
class ManifestFile:
    path: Path
    entries: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def load_manifest(path: Path) -> ManifestFile:
    raw = _load_yaml(path.read_text(encoding="utf-8"))
    entries = [e for e in (raw.get(MANIFEST_TOP_KEY) or []) if isinstance(e, dict)]
    return ManifestFile(path=path, entries=entries, raw=raw)


def source_id_lookup(manifest: ManifestFile, source_id: str) -> dict[str, Any] | None:
    for entry in manifest.entries:
        if entry.get("source_id") == source_id:
            return entry
    return None


def edition_id_lookup(manifest: ManifestFile, edition_id: str) -> list[dict[str, Any]]:
    return [e for e in manifest.entries if e.get("edition_id") == edition_id]


def volume_id_lookup(manifest: ManifestFile, volume_id: str) -> list[dict[str, Any]]:
    return [e for e in manifest.entries if e.get("volume_id") == volume_id]


def verify_fk(manifest: ManifestFile, registry_index: dict[str, set[str]]) -> list[tuple[bool, str]]:
    """Manifest entry의 FK 필드가 registry_index(entity_key -> 유효 ID
    집합)에 존재하는지 확인한다. Registry Migration(canonical_id backfill)
    이후에도 기존 FK 문자열은 안 바뀌므로(Option B), registry_index는
    canonical_id 적용 전/후 동일해야 한다 — 이 함수는 그 불변성을
    검증하는 용도다.
    """
    results: list[tuple[bool, str]] = []
    entity_key_by_fk = {
        "author_id": "authors",
        "work_id": "works",
        "edition_id": "editions",
        "volume_id": "volumes",
        "source_id": "sources",
    }
    for entry in manifest.entries:
        manifest_id = entry.get("manifest_id", "?")
        for fk_field in FK_FIELDS:
            value = entry.get(fk_field)
            if not value:
                continue
            entity_key = entity_key_by_fk[fk_field]
            valid_ids = registry_index.get(entity_key, set())
            if value in valid_ids:
                results.append((True, f"{manifest_id}: {fk_field}={value!r} 참조 확인"))
            else:
                results.append((False, f"{manifest_id}: {fk_field}={value!r} — Registry에 존재하지 않음(Broken Reference)"))
    return results


def build_touch_unit(
    manifest_path: Path,
    migration_version: str,
    updated_at: str,
) -> MigrationUnit:
    """Registry Migration 반영 이후 Manifest의 `updated_at` Audit 필드만
    갱신하는 MigrationUnit을 만든다. FK 필드는 절대 건드리지 않는다
    (Option B 재확인 — 이 함수 자체가 FK 관련 키를 일절 다루지 않음).

    round-trip 로드로 얻은 CommentedMap을 그 자리에서만 수정하므로,
    `updated_at`를 제외한 어떤 줄도(주석/빈 줄/다른 필드) 바뀌지 않는다
    (AC-6 — git diff 결과 `updated_at` 한 줄만 변경).
    """

    def transform(old_contents: dict[str, str]) -> dict[str, str]:
        old_text = old_contents.get(str(manifest_path), "")
        raw = _load_yaml(old_text)
        entries = raw.get(MANIFEST_TOP_KEY) or []

        changed = False
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            current = entry.get("updated_at")
            if current == updated_at:
                continue
            # 원본이 따옴표로 감싸져 있었다면(ruamel이 DoubleQuotedScalarString
            # 으로 로드) 새 값도 동일 스타일을 유지한다 — 값만 바뀌고
            # 형식은 그대로(AC-2 Quote Preservation과 동일 원칙을
            # 이번에 "새로 쓰는 값"에도 적용).
            if isinstance(current, DoubleQuotedScalarString) or current is None:
                entry["updated_at"] = DoubleQuotedScalarString(updated_at)
            else:
                entry["updated_at"] = type(current)(updated_at) if isinstance(current, str) else updated_at
            changed = True

        if not changed:
            return {str(manifest_path): old_text}

        return {str(manifest_path): _dump_yaml(raw)}

    return MigrationUnit(
        target_key=f"manifest:{manifest_path.stem}:{manifest_path.parent.name}",
        migration_version=migration_version,
        target_files=[manifest_path],
        transform=transform,
    )
