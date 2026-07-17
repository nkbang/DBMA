#!/usr/bin/env python3
"""scripts/check_environment.py — DBMA Execution Environment Check (SPRINT20-F1).

Verifies the four conditions whose silent failure caused the SPRINT20-E2
near-incident (config.yaml being ignored because PyYAML was missing,
DEFAULT_OUTPUT_DIR falling back to a stale "output" path, and TSU rebuild
nearly overwriting the production dataset with 6,307 empty-content
records instead of the correct 8,079).

Read-only: performs no writes, does not import core.retrieval/generation,
does not touch the TSU dataset or registry.

Usage:
    python scripts/check_environment.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _print_result(label: str, ok: bool, detail: str) -> None:
    status = "PASS" if ok else "FAIL"
    print(f"{label}:\n{detail:<30} {status}\n")


def check_python_version() -> bool:
    major, minor = sys.version_info[:2]
    ok = (major, minor) in {(3, 11), (3, 12)}
    detail = f"{major}.{minor}.{sys.version_info[2]}"
    if not ok:
        detail += "  (expected 3.11.x or 3.12.x — see environment.yml)"
    _print_result("Python", ok, detail)
    return ok


def check_pyyaml() -> bool:
    try:
        import yaml  # noqa: F401
        _print_result("PyYAML", True, "installed")
        return True
    except ImportError:
        _print_result("PyYAML", False, "NOT installed")
        return False


def check_config_yaml_exists() -> bool:
    config_path = ROOT / "config.yaml"
    ok = config_path.exists()
    _print_result("Config", ok, "loaded" if ok else "config.yaml not found")
    return ok


def check_output_dir() -> bool:
    try:
        sys.path.insert(0, str(ROOT))
        from core.config import DEFAULT_OUTPUT_DIR
    except RuntimeError as exc:
        _print_result("Output", False, f"config load failed: {exc}")
        return False

    ok = DEFAULT_OUTPUT_DIR != "output"
    _print_result("Output", ok, DEFAULT_OUTPUT_DIR)
    return ok


def main() -> int:
    print("DBMA Environment Check\n")
    results = [
        check_python_version(),
        check_pyyaml(),
        check_config_yaml_exists(),
        check_output_dir(),
    ]
    if all(results):
        print("All checks passed.")
        return 0
    print("One or more checks failed — do not trust results produced in this environment.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
