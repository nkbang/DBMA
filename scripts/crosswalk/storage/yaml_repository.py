"""scripts/crosswalk/storage/yaml_repository.py — Crosswalk YAML
Storage Repository (NAE-CROSSWALK-STORAGE-ADAPTER-IMPLEMENTATION-001 §2).

`ruamel.yaml` round-trip으로 `crosswalk.yaml`을 읽고 쓴다 — 기존
`scripts/adapters/registry_adapter.py`/`manifest_adapter.py`가
NAE-ADAPTER-REFACTOR-001에서 확립한 것과 동일한 comment/quote/order/
whitespace 보존 원칙(§3)을 따른다. `yaml.safe_dump()`는 절대 쓰지
않는다 — PyYAML 왕복이 주석/따옴표/순서를 파괴한다는 것이 실측으로
이미 확인됐다(`NAE_PILOT_MIGRATION_VALIDATION_REPORT_001.md` §4).

**삭제 기능 없음** — `delete()`를 의도적으로 구현하지 않는다
(`CrosswalkRecord`가 이미 `frozen=True`인 것과 동일한 append-only
정신, 작업 명령서 §2 "delete() 금지").
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from scripts.crosswalk.repository import CrosswalkRepository, DuplicateCrosswalkIdError
from scripts.crosswalk.schema import CrosswalkRecord
from scripts.crosswalk.storage.index_manager import IndexManager

_RECORDS_KEY = "records"

# Check 2(Schema validation) 대상 — 명령서 §Phase2 명시 5개 필드.
# (confidence는 unmapped 레코드의 경우 값이 None일 수 있지만, "키 자체"는
# CrosswalkRecord.to_dict()가 항상 포함시키므로 정상 레코드라면 항상 존재
# — 키가 아예 없으면 손상으로 간주.)
_REQUIRED_SCHEMA_FIELDS = ("crosswalk_id", "source_identifier", "target_identifier", "mapping_status", "confidence")


def _yaml() -> YAML:
    y = YAML(typ="rt")
    y.preserve_quotes = True
    y.width = 100_000
    y.indent(mapping=2, sequence=4, offset=2)
    return y


class YamlCrosswalkRepository(CrosswalkRepository):
    """`docs/NAE_CROSSWALK_STORAGE_DECISION_001.md`(Option B)의
    `crosswalk.yaml`을 정본으로 삼는 `CrosswalkRepository` 구현체.

    `index_path`를 주면 `add()` 이후 자동으로 `index.json`을
    재생성한다(YAML authority — index는 항상 파생값, 절대 그 반대
    방향으로 신뢰하지 않음).
    """

    def __init__(self, yaml_path: Path, index_path: Path | None = None) -> None:
        self.yaml_path = Path(yaml_path)
        self.index_manager = IndexManager(index_path) if index_path is not None else None
        if not self.yaml_path.exists():
            self._write_raw(self._empty_raw())
        # index.json도 crosswalk.yaml과 함께 초기화한다 — 그렇지 않으면
        # "레코드 0건인 신선한 저장소"가 add() 이전까지 잠깐
        # validate_storage()에서 "index.json 없음"으로 오탐(false ERROR)
        # 될 수 있다(발견된 실제 결함, 수동 테스트로 확인 후 수정).
        if self.index_manager is not None and not self.index_manager.index_path.exists():
            self._refresh_index(self.list_all())

    def _empty_raw(self) -> CommentedMap:
        raw = CommentedMap()
        raw[_RECORDS_KEY] = []
        return raw

    def _read_raw(self) -> CommentedMap:
        if not self.yaml_path.exists():
            return self._empty_raw()
        text = self.yaml_path.read_text(encoding="utf-8")
        raw = _yaml().load(text)
        if raw is None:
            raw = self._empty_raw()
        if _RECORDS_KEY not in raw:
            raw[_RECORDS_KEY] = []
        return raw

    def _write_raw(self, raw: CommentedMap) -> None:
        self.yaml_path.parent.mkdir(parents=True, exist_ok=True)
        buf = io.StringIO()
        _yaml().dump(raw, buf)
        self.yaml_path.write_text(buf.getvalue(), encoding="utf-8")

    def _refresh_index(self, records: list[CrosswalkRecord]) -> None:
        if self.index_manager is not None:
            self.index_manager.rebuild(records)

    # ---- CrosswalkRepository interface ----

    def list_all(self) -> list[CrosswalkRecord]:
        raw = self._read_raw()
        entries = raw.get(_RECORDS_KEY) or []
        return [CrosswalkRecord.from_dict(dict(entry)) for entry in entries]

    def get(self, crosswalk_id: str) -> CrosswalkRecord | None:
        for record in self.list_all():
            if record.crosswalk_id == crosswalk_id:
                return record
        return None

    def get_by_source(self, source_identifier: str) -> list[CrosswalkRecord]:
        return [r for r in self.list_all() if r.source_identifier == source_identifier]

    def add(self, record: CrosswalkRecord) -> None:
        raw = self._read_raw()
        entries = raw.get(_RECORDS_KEY) or []

        for entry in entries:
            if entry.get("crosswalk_id") == record.crosswalk_id:
                raise DuplicateCrosswalkIdError(
                    f"crosswalk_id 중복: {record.crosswalk_id!r}(crosswalk.yaml에 이미 존재)"
                )

        entries.append(record.to_dict())
        raw[_RECORDS_KEY] = entries
        self._write_raw(raw)

        self._refresh_index(self.list_all())

    # ---- Corruption Detection(NAE-TSU-GATE-RELIABILITY-IMPLEMENTATION-001 Phase 2) ----
    #
    # 이 3개 검사는 예외를 던지지 않는다 — (ok: bool, error_message: str | None)
    # 튜플을 반환해, 호출자(GateOrchestrator)가 그 결과를 TSU_GATE_ERROR로
    # 매핑할 수 있게 한다. YAML authority 원칙 재확인: 불일치를 발견해도
    # 이 메서드들은 절대 자동으로 고치지 않는다(§Check 3 "복구 시도하지
    # 말고 rebuild 가능 상태만 기록").

    def check_parse(self) -> tuple[bool, str | None]:
        """Check 1 — YAML parse 가능 여부."""
        if not self.yaml_path.exists():
            return True, None  # 아직 생성 전 — 손상이 아니라 초기 상태
        try:
            text = self.yaml_path.read_text(encoding="utf-8")
            _yaml().load(text)
        except Exception as exc:  # noqa: BLE001 — ruamel의 다양한 파싱 예외를 전부 포착
            return False, f"YAML parse 실패: {exc}"
        return True, None

    def check_schema(self) -> tuple[bool, str | None]:
        """Check 2 — 레코드별 필수 필드 존재 여부(schema.py CrosswalkRecord
        구성 자체가 아니라, 원본 YAML의 raw dict 키 존재만 확인 — 값 자체의
        enum 유효성은 `CrosswalkRecord.from_dict()`가 조회 시점에 별도로
        검증한다)."""
        parse_ok, parse_err = self.check_parse()
        if not parse_ok:
            return False, parse_err

        raw = self._read_raw()
        entries = raw.get(_RECORDS_KEY) or []
        for index, entry in enumerate(entries):
            missing = [field for field in _REQUIRED_SCHEMA_FIELDS if field not in entry]
            if missing:
                return False, f"레코드[{index}](crosswalk_id={entry.get('crosswalk_id')!r}) 필수 필드 누락: {missing}"
        return True, None

    def check_index_consistency(self) -> tuple[bool, str | None]:
        """Check 3 — index.json이 crosswalk.yaml(정본)과 일치하는지.

        불일치를 발견해도 이 메서드는 index.json을 다시 쓰지 않는다 —
        "rebuild 가능한 상태"라는 사실만 보고한다. 실제 재생성은 호출자가
        `IndexManager.rebuild()`를 명시적으로 호출해야 한다.
        """
        if self.index_manager is None:
            return True, None  # index 미사용 — 검사 대상 아님

        if not self.index_manager.index_path.exists():
            return False, "index.json 없음(rebuild 가능 상태 — IndexManager.rebuild() 필요)"

        try:
            current_index = self.index_manager.load()
        except Exception as exc:  # noqa: BLE001
            return False, f"index.json 파싱 실패: {exc}(rebuild 가능 상태)"

        schema_ok, schema_err = self.check_schema()
        if not schema_ok:
            return False, schema_err

        expected_index = {
            record.crosswalk_id: {
                "source_identifier": record.source_identifier,
                "target_identifier": record.target_identifier,
            }
            for record in self.list_all()
        }
        if current_index != expected_index:
            return False, "index.json이 crosswalk.yaml과 불일치(rebuild 가능 상태 — 자동 복구하지 않음)"
        return True, None

    def validate_storage(self) -> tuple[bool, str | None]:
        """Check 1~3을 순서대로 실행, 첫 실패 지점의 (False, 사유)를 반환.
        전부 통과하면 (True, None) — `GateOrchestrator`가 호출하는
        단일 진입점."""
        for check in (self.check_parse, self.check_schema, self.check_index_consistency):
            ok, error = check()
            if not ok:
                return False, error
        return True, None
