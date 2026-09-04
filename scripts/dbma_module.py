"""DBMA Optional Module CLI (NAE-OPTIONAL-MODULE-PACKAGING-001).

기존 프로젝트에 통합 CLI 바이너리가 없어(`scripts/*.py` 각각 독립
argparse 실행) 그 관례를 따른다 — 새 CLI 프레임워크를 도입하지 않는다.

사용:
    python scripts/dbma_module.py list
    python scripts/dbma_module.py status nae_pd
    python scripts/dbma_module.py enable nae_pd
    python scripts/dbma_module.py disable nae_pd

`enable`은 config.yaml의 enabled=true만 켜고, 각 module의
`check_availability()`(READ-ONLY)를 실행해 활성화 안전성만 보고한다 —
embedding/indexing을 자동으로 시작하지 않는다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core import module_registry

# module 이름 -> activation self-check을 수행하는 함수. Core는 이 매핑을
# CLI 계층에서만 알고 있다 — core/module_registry.py 자체는 NAE를 모른다.
_ACTIVATION_CHECKS = {
    "nae_pd": lambda: __import__("NAE.module", fromlist=["check_availability"]).check_availability(),
}


def cmd_list(_args: argparse.Namespace) -> None:
    modules = module_registry.list_modules()
    if not modules:
        print(json.dumps({"modules": [], "note": "no optional modules registered"}, ensure_ascii=False, indent=2))
        return
    print(json.dumps(
        [{"name": name, "enabled": cfg.get("enabled", False), "display_name": cfg.get("display_name")}
         for name, cfg in modules.items()],
        ensure_ascii=False, indent=2,
    ))


def cmd_status(args: argparse.Namespace) -> None:
    print(json.dumps(module_registry.status(args.name), ensure_ascii=False, indent=2))


def cmd_enable(args: argparse.Namespace) -> None:
    module_registry.set_enabled(args.name, True)
    result = {"name": args.name, "config_enabled": True}
    check_fn = _ACTIVATION_CHECKS.get(args.name)
    if check_fn is not None:
        checks = check_fn()
        result["availability_check"] = checks
        result["activation_safe"] = checks.get("safe_to_activate", False)
        result["embedding_calls_made"] = 0
        result["indexing_calls_made"] = 0
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_disable(args: argparse.Namespace) -> None:
    module_registry.set_enabled(args.name, False)
    print(json.dumps({"name": args.name, "config_enabled": False}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="DBMA Optional Module CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list").set_defaults(func=cmd_list)

    p_status = sub.add_parser("status")
    p_status.add_argument("name")
    p_status.set_defaults(func=cmd_status)

    p_enable = sub.add_parser("enable")
    p_enable.add_argument("name")
    p_enable.set_defaults(func=cmd_enable)

    p_disable = sub.add_parser("disable")
    p_disable.add_argument("name")
    p_disable.set_defaults(func=cmd_disable)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
