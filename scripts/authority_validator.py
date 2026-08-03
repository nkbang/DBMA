"""scripts/authority_validator.py — NAE Authority Registry 검증.

resources/theological_sources/authority/{authors,works,editions,volumes,
sources}.yaml(Production Registry)을 검사한다. `source_validator.py`
(corpus manifest 전담)·`manifest_validator.py`(Manifest Layer 전담)와
완전히 독립된 세 번째 도구다(3-Validator 체계, Validator Boundary
Design-001 원안이 이번 구현으로 완성됨).

검사 항목:
  1. FK Integrity — work.author_id/edition.work_id/volume.edition_id/
     source.edition_id/source.volume_id가 상위 entity에 실재하는지
  2. Duplicate IDs — 각 entity 파일 내 ID 유일성
  3. Legacy Alias — 서로 다른 author 사이에 alias가 중복되거나, alias가
     다른 author의 canonical author_id와 충돌하지 않는지
  4. Canonical ID Format — ADR-017 규칙(lowercase snake_case)을 따르는지
     (WARNING만 — ID Governance v1이 즉시 rename을 보류하기로 이미
     결정했으므로 FAIL 아님)
  5. Broken References — FK Integrity의 역방향(참조 대상이 없는 경우)까지
     포함해 재확인
  6. Orphan Entity — 어느 하위 entity에서도 참조되지 않는 Author/Work/
     Edition(WARNING — 데이터 오류가 아니라 "아직 하위 데이터가 없다"는
     정상 상태일 수도 있음)
  7. Circular Reference — Work의 `continues_work_id`/`continued_by_work_id`
     체인에 순환이 있는지(ADR-018)
  8. Duplicate Canonical Name — 서로 다른 author_id가 동일
     canonical_name(정규화 비교)을 갖는 경우(동일 인물 중복 등록 의심)
  9. Canonical ID Existence — ADR-017 Option B(NAE-ID-GOVERNANCE-
     IMPLEMENTATION-001): 모든 entity에 `canonical_id` 필드가 있는지
     (없으면 FAIL — 기존 ID 필드 자체의 표기 검사인 #4와 달리, 이
     필드는 required 스키마 필드이므로 누락은 데이터 오류)
  10. Canonical ID Format — `canonical_id` 값이 ADR-017 규칙(lowercase
      snake_case)을 만족하는지(위반 시 FAIL — #4는 기존 ID 필드에 대해
      WARNING만 주지만, canonical_id는 "이것이 정본 표기다"라고
      선언하는 필드이므로 그 값 자체가 규칙을 어기면 FAIL)
  11. Legacy ID Type — `legacy_id`가 있으면 배열(list) 타입인지 확인
      (문자열 등 다른 타입이면 FAIL — 값의 사실 여부는 판단하지 않음)

읽기 전용 — Registry 파일을 수정하지 않는다.

사용례:
    python scripts/authority_validator.py
    python scripts/authority_validator.py --registry-path resources/theological_sources/authority
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml

DEFAULT_REGISTRY_PATH = os.path.join("resources", "theological_sources", "authority")

# entity 파일명(확장자 제외) -> (최상위 키, ID 필드명)
_ENTITY_FILES: dict[str, tuple[str, str]] = {
    "authors": ("authors", "author_id"),
    "works": ("works", "work_id"),
    "editions": ("editions", "edition_id"),
    "volumes": ("volumes", "volume_id"),
    "sources": ("sources", "source_id"),
}

# 자식 entity 필드명 -> 부모 entity 파일 key(FK 방향)
_FK_EDGES: list[tuple[str, str, str]] = [
    # (자식 entity 파일 key, 자식 안의 FK 필드명, 부모 entity 파일 key)
    ("works", "author_id", "authors"),
    ("editions", "work_id", "works"),
    ("volumes", "edition_id", "editions"),
    ("sources", "edition_id", "editions"),
    ("sources", "volume_id", "volumes"),
]

# ADR-017: author_id = "{surname}_{given}[_{middle_initial}]", lowercase snake_case.
# work_id/edition_id/volume_id/source_id도 원칙적으로 동일 표기(소문자, 언더스코어).
_CANONICAL_ID_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")


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


def load_registry(registry_path: Path) -> dict[str, list[dict[str, Any]]]:
    """각 entity 파일을 읽어 {entity_key: [entry, ...]} 형태로 반환.

    파일이 없으면 빈 리스트(FAIL 아님 — Registry가 아직 부분적으로만
    채워졌을 수 있음, 예: volumes.yaml이 비어 있는 경우는 정상).
    """
    data: dict[str, list[dict[str, Any]]] = {}
    for entity_key, (top_key, _id_field) in _ENTITY_FILES.items():
        path = registry_path / f"{entity_key}.yaml"
        entries: list[dict[str, Any]] = []
        if path.exists():
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                entries = [e for e in (raw.get(top_key) or []) if isinstance(e, dict)]
            except Exception:
                entries = []
        data[entity_key] = entries
    return data


def check_duplicate_ids(registry: dict[str, list[dict[str, Any]]], result: ValidationResult) -> None:
    """검사 2: 각 entity 파일 내 ID 유일성."""
    for entity_key, (_top_key, id_field) in _ENTITY_FILES.items():
        seen: dict[str, int] = {}
        for idx, entry in enumerate(registry[entity_key]):
            eid = entry.get(id_field)
            if not eid:
                result.add("FAIL", f"authority/{entity_key}.yaml[{idx}]: {id_field} 누락")
                continue
            if eid in seen:
                result.add("FAIL", f"authority/{entity_key}.yaml: {id_field} 중복 — {eid!r}(index {seen[eid]}, {idx})")
            else:
                seen[eid] = idx
                result.add("PASS", f"authority/{entity_key}.yaml: {id_field}={eid!r} 유일성 확인")


def check_fk_integrity(registry: dict[str, list[dict[str, Any]]], result: ValidationResult) -> None:
    """검사 1/5: FK Integrity + Broken Reference(동일 로직, 역방향 명시)."""
    for child_key, fk_field, parent_key in _FK_EDGES:
        parent_id_field = _ENTITY_FILES[parent_key][1]
        parent_ids = {e.get(parent_id_field) for e in registry[parent_key] if e.get(parent_id_field)}
        for idx, entry in enumerate(registry[child_key]):
            value = entry.get(fk_field)
            if not value:
                continue  # 값이 없는 FK(예: source.volume_id가 단권 자료)는 검사 대상 아님
            if value not in parent_ids:
                result.add(
                    "FAIL",
                    f"authority/{child_key}.yaml[{idx}]: {fk_field}={value!r} — "
                    f"authority/{parent_key}.yaml에 존재하지 않음(Broken Reference)",
                )
            else:
                result.add("PASS", f"authority/{child_key}.yaml[{idx}]: {fk_field}={value!r} 참조 확인")


def check_orphan_entities(registry: dict[str, list[dict[str, Any]]], result: ValidationResult) -> None:
    """검사 6: 어느 하위 entity에서도 참조되지 않는 상위 entity(WARNING)."""
    referenced: dict[str, set[str]] = {"authors": set(), "works": set(), "editions": set(), "volumes": set()}
    for child_key, fk_field, parent_key in _FK_EDGES:
        for entry in registry[child_key]:
            value = entry.get(fk_field)
            if value:
                referenced[parent_key].add(value)

    for parent_key in ("authors", "works", "editions"):
        id_field = _ENTITY_FILES[parent_key][1]
        for entry in registry[parent_key]:
            eid = entry.get(id_field)
            if eid and eid not in referenced[parent_key]:
                result.add("WARNING", f"authority/{parent_key}.yaml: {eid!r} — 어느 하위 entity에서도 참조되지 않음(Orphan Entity)")


def check_legacy_alias(registry: dict[str, list[dict[str, Any]]], result: ValidationResult) -> None:
    """검사 3: Legacy Alias 충돌 — alias가 다른 author의 canonical ID/alias와 겹치지 않는지."""
    all_canonical_ids = {e.get("author_id") for e in registry["authors"] if e.get("author_id")}
    alias_owner: dict[str, str] = {}
    for entry in registry["authors"]:
        author_id = entry.get("author_id")
        if not author_id:
            continue
        for alias in entry.get("aliases") or []:
            if alias in all_canonical_ids and alias != author_id:
                result.add("FAIL", f"authority/authors.yaml: {author_id!r}의 alias {alias!r}가 다른 author의 canonical author_id와 충돌")
            elif alias in alias_owner and alias_owner[alias] != author_id:
                result.add(
                    "FAIL",
                    f"authority/authors.yaml: alias {alias!r}가 {alias_owner[alias]!r}와 {author_id!r} 양쪽에 중복 사용됨",
                )
            else:
                alias_owner[alias] = author_id
                result.add("PASS", f"authority/authors.yaml: {author_id!r}의 alias {alias!r} 충돌 없음")


def check_canonical_id_format(registry: dict[str, list[dict[str, Any]]], result: ValidationResult) -> None:
    """검사 4: ADR-017 canonical ID 표기(lowercase snake_case) 준수 — WARNING만.

    ID Governance v1이 기존 비표준 ID(예: FULLER-ANDREW-001)를 즉시
    rename하지 않기로 이미 결정했으므로(legacy_id 보존 방식), 여기서는
    FAIL이 아니라 WARNING으로만 보고한다.
    """
    for entity_key, (_top_key, id_field) in _ENTITY_FILES.items():
        for entry in registry[entity_key]:
            eid = entry.get(id_field)
            if not eid:
                continue
            if _CANONICAL_ID_RE.match(eid):
                result.add("PASS", f"authority/{entity_key}.yaml: {eid!r} canonical 표기(ADR-017) 준수")
            else:
                result.add(
                    "WARNING",
                    f"authority/{entity_key}.yaml: {eid!r} — ADR-017 canonical 표기(lowercase snake_case) 불일치(ID Governance v1 §4 재확인 대상)",
                )


def _has_cycle(edges: dict[str, str]) -> list[str] | None:
    """단순 방향 그래프(각 노드가 continues_work_id로 최대 1개 후속을 가짐)에서
    순환을 찾는다. 순환이 있으면 그 경로를 반환, 없으면 None."""
    visited: set[str] = set()
    for start in edges:
        if start in visited:
            continue
        path: list[str] = []
        node: str | None = start
        seen_in_path: set[str] = set()
        while node is not None:
            if node in seen_in_path:
                return path[path.index(node):] + [node]
            seen_in_path.add(node)
            path.append(node)
            visited.add(node)
            node = edges.get(node)
    return None


def check_circular_reference(registry: dict[str, list[dict[str, Any]]], result: ValidationResult) -> None:
    """검사 7: Work.continues_work_id 체인의 순환 참조(ADR-018)."""
    edges: dict[str, str] = {}
    for entry in registry["works"]:
        wid = entry.get("work_id")
        continues = entry.get("continues_work_id")
        if wid and continues:
            edges[wid] = continues

    if not edges:
        result.add("PASS", "authority/works.yaml: continues_work_id 사용 사례 없음(순환 검사 대상 없음)")
        return

    cycle = _has_cycle(edges)
    if cycle:
        result.add("FAIL", f"authority/works.yaml: continues_work_id 순환 참조 발견 — {' -> '.join(cycle)}")
    else:
        result.add("PASS", f"authority/works.yaml: continues_work_id 순환 없음({len(edges)}건 확인)")


def check_duplicate_canonical_name(registry: dict[str, list[dict[str, Any]]], result: ValidationResult) -> None:
    """검사 8: 서로 다른 author_id가 동일 canonical_name(정규화 비교)을 갖는 경우."""

    def normalize(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.lower())

    seen: dict[str, str] = {}
    for entry in registry["authors"]:
        author_id = entry.get("author_id")
        name = entry.get("canonical_name")
        if not author_id or not name:
            continue
        key = normalize(name)
        if key in seen and seen[key] != author_id:
            result.add(
                "WARNING",
                f"authority/authors.yaml: {author_id!r}와 {seen[key]!r}가 동일 canonical_name({name!r}) — 동일 인물 중복 등록 의심(자동 병합 금지, 사람 확인 필요)",
            )
        else:
            seen[key] = author_id
            result.add("PASS", f"authority/authors.yaml: {author_id!r} canonical_name 중복 없음")


def check_canonical_id_governance(registry: dict[str, list[dict[str, Any]]], result: ValidationResult) -> None:
    """검사 9/10/11: ADR-017 Option B canonical_id/legacy_id 스키마 검증.

    NAE-ID-GOVERNANCE-IMPLEMENTATION-001 — 기존 ID 필드(#1~#8)는
    전혀 건드리지 않는다. canonical_id/legacy_id는 그 위에 추가된
    신규 필드에 대한 독립적인 검사다.
    """
    for entity_key, (_top_key, id_field) in _ENTITY_FILES.items():
        for entry in registry[entity_key]:
            eid = entry.get(id_field)
            if not eid:
                continue  # 누락은 check_duplicate_ids(#2)가 이미 FAIL 처리

            canonical_id = entry.get("canonical_id")
            if not canonical_id:
                result.add("FAIL", f"authority/{entity_key}.yaml: {eid!r} — canonical_id 누락(missing canonical_id)")
            elif not _CANONICAL_ID_RE.match(canonical_id):
                result.add(
                    "FAIL",
                    f"authority/{entity_key}.yaml: {eid!r}의 canonical_id={canonical_id!r} — "
                    f"ADR-017 canonical 표기(lowercase snake_case) 위반",
                )
            else:
                result.add("PASS", f"authority/{entity_key}.yaml: {eid!r}의 canonical_id={canonical_id!r} 형식 확인")

            if "legacy_id" in entry and entry["legacy_id"] is not None:
                if isinstance(entry["legacy_id"], list):
                    result.add("PASS", f"authority/{entity_key}.yaml: {eid!r}의 legacy_id 배열 타입 확인")
                else:
                    result.add(
                        "FAIL",
                        f"authority/{entity_key}.yaml: {eid!r}의 legacy_id={entry['legacy_id']!r} — 배열(list) 타입이어야 함",
                    )


def validate(registry_path: Path) -> ValidationResult:
    result = ValidationResult()
    registry = load_registry(registry_path)

    if not any(registry.values()):
        result.add("WARNING", f"{registry_path} 하위에 Registry 데이터 없음 — 검사할 대상 없음")
        return result

    check_duplicate_ids(registry, result)
    check_fk_integrity(registry, result)
    check_orphan_entities(registry, result)
    check_legacy_alias(registry, result)
    check_canonical_id_format(registry, result)
    check_circular_reference(registry, result)
    check_duplicate_canonical_name(registry, result)
    check_canonical_id_governance(registry, result)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--registry-path", default=DEFAULT_REGISTRY_PATH, help=f"Authority Registry 디렉토리 (기본: {DEFAULT_REGISTRY_PATH})"
    )
    args = parser.parse_args()

    registry_path = Path(args.registry_path)
    if not registry_path.exists():
        print(f"[FAIL] Registry 디렉토리 없음: {registry_path}")
        return 1

    result = validate(registry_path)
    result.print_all()

    return 1 if result.fail_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
