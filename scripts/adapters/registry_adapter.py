"""scripts/adapters/registry_adapter.py — Authority Registry Adapter
(NAE-METADATA-MIGRATION-PILOT-IMPLEMENTATION-001, comment-preserving
YAML: NAE-ADAPTER-REFACTOR-001).

Migration Engine(`scripts/migration_engine.py`)은 Registry의 존재
자체를 모른다 — 이 Adapter가 유일하게 Registry YAML 구조(ADR-016
5-tier 모델, ADR-017 canonical_id/legacy_id)를 아는 계층이다. Engine은
`MigrationUnit(target_files, transform)`만 받으므로, 이 Adapter의
역할은 "Registry YAML을 읽고, canonical_id/legacy_id를 채우는
transform을 만들어 MigrationUnit으로 포장하는 것"뿐이다 — Engine
코드는 이 파일을 import하지 않는다(반대 방향으로만 의존).

**이 Adapter는 canonical_id 값을 스스로 추론하지 않는다** — ID
Governance v1(§6.2 매핑표)이 이미 정책으로 확정한 값을 호출자가
`canonical_id_map`으로 주입해야 한다. Adapter는 그 매핑을 "적용"할
뿐 "결정"하지 않는다(정책과 실행의 분리, ADR-017 Option B 원칙).

**Comment-Preserving YAML(NAE-ADAPTER-REFACTOR-001)**: `ruamel.yaml`
round-trip 모드를 사용해 파일을 로드·수정·저장한다 — PyYAML의
`safe_load()`/`safe_dump()` 왕복은 주석·따옴표 스타일·들여쓰기·키
순서·빈 줄을 전부 버리고 새로 직렬화하므로(NAE_PILOT_MIGRATION_
VALIDATION_REPORT_001.md §4에서 실측 발견), 여기서는 원본 노드를
그 자리에서 "수정"만 하고(재구성하지 않음) round-trip 표현으로
그대로 다시 쓴다.

실제 Production Registry(`resources/theological_sources/authority/`)나
Pilot Registry(`resources/theological_sources/manifest/pilot/`)를
대상으로 실행하는 것은 이번 구현 범위에서 금지된다 — 이 모듈 자체는
경로를 하드코딩하지 않으며, 호출자가 넘긴 임의의 root만 다룬다.
"""

from __future__ import annotations

import io
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.migration_engine import MigrationUnit

# ADR-016 5-tier 모델의 entity 파일명 -> (최상위 YAML 키, ID 필드명)
# authority_validator.py의 _ENTITY_FILES와 동일한 정본 구조(중복 정의—
# Adapter가 Engine뿐 아니라 Validator에도 의존하지 않도록 의도적으로 분리).
ENTITY_FILES: dict[str, tuple[str, str]] = {
    "authors": ("authors", "author_id"),
    "works": ("works", "work_id"),
    "editions": ("editions", "edition_id"),
    "volumes": ("volumes", "volume_id"),
    "sources": ("sources", "source_id"),
}

# ADR-017: canonical 표기 = lowercase snake_case(authority_validator.py의
# _CANONICAL_ID_RE와 동일 규칙 — 이번 Adapter가 생성하는 canonical_id 값도
# 반드시 이 형식을 만족해야 한다).
CANONICAL_ID_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")


def _represent_none(representer: Any, data: Any) -> Any:
    """None을 항상 명시적 `null` 토큰으로 덤프한다(ruamel 기본값은 빈 값을
    남기는데, 이는 원본이 `key: null`로 명시했던 표기를 바꿔버린다 —
    Whitespace/Formatting Preservation 위반)."""
    return representer.represent_scalar("tag:yaml.org,2002:null", "null")


def _yaml() -> YAML:
    """round-trip(comment/quote/order 보존) YAML 인스턴스. 매 호출마다
    새로 만든다 — YAML 객체는 내부 상태(마지막 dump 설정 등)를 갖고
    있어 여러 파일에서 공유하면 스타일이 섞일 수 있다."""
    y = YAML(typ="rt")
    y.preserve_quotes = True
    y.width = 100_000  # 긴 줄을 자동 줄바꿈하지 않음(원본 줄바꿈 그대로 유지)
    # Registry YAML 파일들의 실제 표기 스타일(2-space indent, dash가
    # block 안쪽으로 2칸 들여써짐 — "  - key:" 형태)과 일치시킨다.
    # 이 설정이 없으면 ruamel 기본값(offset=0)으로 덤프되어 원본과
    # 다른 들여쓰기가 나온다(Formatting Preservation 위반).
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
class RegistryEntityFile:
    """entity YAML 파일 1개(예: authors.yaml)의 파싱 결과."""

    path: Path
    top_key: str
    id_field: str
    entries: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def load_entity_file(root: Path, entity_key: str) -> RegistryEntityFile | None:
    """root/{entity_key}.yaml을 읽어 파싱한다. 파일이 없으면 None."""
    top_key, id_field = ENTITY_FILES[entity_key]
    path = root / f"{entity_key}.yaml"
    if not path.exists():
        return None
    raw = _load_yaml(path.read_text(encoding="utf-8"))
    entries = [e for e in (raw.get(top_key) or []) if isinstance(e, dict)]
    return RegistryEntityFile(path=path, top_key=top_key, id_field=id_field, entries=entries, raw=raw)


def load_registry(root: Path) -> dict[str, RegistryEntityFile]:
    """root 하위 5개 entity 파일을 전부 로드한다(존재하는 것만)."""
    result: dict[str, RegistryEntityFile] = {}
    for entity_key in ENTITY_FILES:
        loaded = load_entity_file(root, entity_key)
        if loaded is not None:
            result[entity_key] = loaded
    return result


def canonical_id_lookup(entity_file: RegistryEntityFile, entity_id: str) -> str | None:
    """entity_id에 해당하는 canonical_id를 조회한다(없으면 None)."""
    for entry in entity_file.entries:
        if entry.get(entity_file.id_field) == entity_id:
            return entry.get("canonical_id")
    return None


def legacy_id_lookup(entity_file: RegistryEntityFile, entity_id: str) -> list[str]:
    """entity_id에 해당하는 legacy_id 배열을 조회한다(없으면 빈 리스트)."""
    for entry in entity_file.entries:
        if entry.get(entity_file.id_field) == entity_id:
            legacy = entry.get("legacy_id")
            return list(legacy) if isinstance(legacy, list) else []
    return []


def build_canonical_id_backfill_unit(
    entity_file: RegistryEntityFile,
    migration_version: str,
    canonical_id_map: dict[str, str],
    legacy_id_map: dict[str, list[str]] | None = None,
) -> MigrationUnit:
    """canonical_id가 없는 entry에 canonical_id_map 값을 채우는 MigrationUnit
    을 만든다(ADR-017 Option B — 기존 ID 필드는 절대 건드리지 않음).

    canonical_id_map/legacy_id_map은 호출자가 미리 결정한 값(정책,
    ID Governance v1 §6.2)만 사용한다 — Adapter가 값을 새로 만들지 않는다.
    이미 canonical_id가 있는 entry는 건드리지 않는다(Idempotency —
    Engine의 no-op 체크와 별개로, Adapter 레벨에서도 불필요한 diff를
    만들지 않기 위함).

    round-trip 로드로 얻은 CommentedMap을 "그 자리에서" 수정만 하고
    재구성하지 않으므로, 손대지 않은 필드/주석/따옴표/들여쓰기/키 순서/
    빈 줄은 원본 그대로 보존된다(AC-1~AC-5).
    """
    legacy_id_map = legacy_id_map or {}
    path = entity_file.path
    id_field = entity_file.id_field
    top_key = entity_file.top_key

    def transform(old_contents: dict[str, str]) -> dict[str, str]:
        old_text = old_contents.get(str(path), "")
        raw = _load_yaml(old_text)
        entries = raw.get(top_key) or []

        changed = False
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            eid = entry.get(id_field)
            if eid is not None and "canonical_id" not in entry and eid in canonical_id_map:
                new_canonical = canonical_id_map[eid]
                if not CANONICAL_ID_RE.match(new_canonical):
                    raise ValueError(
                        f"canonical_id_map[{eid!r}]={new_canonical!r} — ADR-017 "
                        f"canonical 표기(lowercase snake_case) 위반"
                    )
                # id_field 바로 다음 위치에 canonical_id를 삽입(가독성 —
                # 기존에 수기로 편집했던 커밋(1042b1f)의 필드 배치와 동일).
                if isinstance(entry, CommentedMap):
                    pos = list(entry.keys()).index(id_field) + 1
                    entry.insert(pos, "canonical_id", new_canonical)
                else:
                    entry["canonical_id"] = new_canonical

                if eid in legacy_id_map:
                    legacy_seq = CommentedSeq(list(legacy_id_map[eid]))
                    legacy_seq.fa.set_flow_style()  # ["A", "B"] 형태(block 아님) — 기존 관례와 동일
                    if isinstance(entry, CommentedMap):
                        pos = list(entry.keys()).index("canonical_id") + 1
                        entry.insert(pos, "legacy_id", legacy_seq)
                    else:
                        entry["legacy_id"] = legacy_seq
                changed = True

        if not changed:
            # 아무것도 바뀌지 않았으면 원본 텍스트를 그대로 반환한다 —
            # Engine의 텍스트 비교 Idempotency 체크가 no-op을 정확히
            # 인식하도록 한다(재직렬화 자체를 아예 하지 않음).
            return {str(path): old_text}

        return {str(path): _dump_yaml(raw)}

    return MigrationUnit(
        target_key=f"registry:{entity_file.path.stem}",
        migration_version=migration_version,
        target_files=[path],
        transform=transform,
    )


def build_all_backfill_units(
    root: Path,
    migration_version: str,
    canonical_id_map: dict[str, str],
    legacy_id_map: dict[str, list[str]] | None = None,
) -> list[MigrationUnit]:
    """root 하위 모든 entity 파일에 대해 canonical_id backfill Migration
    Unit을 생성한다(entity 파일 1개 = Migration Unit 1개)."""
    registry = load_registry(root)
    return [
        build_canonical_id_backfill_unit(entity_file, migration_version, canonical_id_map, legacy_id_map)
        for entity_file in registry.values()
    ]
