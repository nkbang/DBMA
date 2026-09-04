"""DBMA Optional Module Registry (NAE-OPTIONAL-MODULE-PACKAGING-001).

`core/`는 이 모듈만으로 module on/off를 다룬다 — 특정 module의 실제 코드
(예: `NAE/module.py`)를 import하지 않는다. 그래서 DBMA Core는 어떤 optional
module이 설치되어 있지 않아도(또는 disabled여도) 정상 동작한다.

`config.yaml`의 `modules:` 섹션이 유일한 정본(single source of truth)이다
— 이 파일 자체에는 module별 활성화 로직을 두지 않는다(그건 각 module의
`activate()`가 담당, 예: `NAE/module.py::activate()`).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def _load_config(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}




def list_modules(config_path: Path = CONFIG_PATH) -> dict[str, dict[str, Any]]:
    """modules: 섹션이 아예 없으면 빈 dict — DBMA Core는 이 경우에도
    정상 동작해야 한다(module 개념 자체가 optional)."""
    config = _load_config(config_path)
    return config.get("modules", {})


def is_enabled(name: str, config_path: Path = CONFIG_PATH) -> bool:
    modules = list_modules(config_path)
    return bool(modules.get(name, {}).get("enabled", False))


def get_module_config(name: str, config_path: Path = CONFIG_PATH) -> dict[str, Any] | None:
    modules = list_modules(config_path)
    return modules.get(name)


def status(name: str, config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    module_config = get_module_config(name, config_path)
    if module_config is None:
        return {"name": name, "registered": False, "enabled": False}
    return {
        "name": name,
        "registered": True,
        "enabled": bool(module_config.get("enabled", False)),
        "display_name": module_config.get("display_name"),
    }


def set_enabled(name: str, enabled: bool, config_path: Path = CONFIG_PATH) -> None:
    """config.yaml의 `modules.<name>.enabled` 줄만 텍스트 레벨로 치환한다
    — `yaml.safe_dump()`로 파일 전체를 재작성하지 않는다. config.yaml은
    주석이 섹션 구조의 일부인 "단일 설정 소스" 문서이므로(파일 상단
    docstring 참고), 파싱 후 재직렬화하면 그 주석이 전부 사라진다(실측
    확인, NAE-OPTIONAL-MODULE-PACKAGING-001 구현 중 발견 및 즉시 수정).
    """
    config = _load_config(config_path)
    modules = config.get("modules", {})
    if name not in modules:
        raise KeyError(f"module '{name}' is not registered in config.yaml modules: section")

    import re
    text = config_path.read_text(encoding="utf-8")
    # "  <name>:\n    enabled: <bool>" 블록만 정확히 매치 — 다른 module의
    # enabled 줄이나 다른 섹션의 동일 이름 키를 건드리지 않는다.
    pattern = re.compile(rf"(^  {re.escape(name)}:\n(?:.*\n)*?    enabled: )(true|false)", re.MULTILINE)
    new_value = "true" if enabled else "false"
    new_text, count = pattern.subn(rf"\g<1>{new_value}", text, count=1)
    if count != 1:
        raise RuntimeError(f"could not locate 'modules.{name}.enabled' line in {config_path} for in-place patch")
    config_path.write_text(new_text, encoding="utf-8")
