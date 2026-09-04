#!/usr/bin/env python3
"""10_packaging_audit.py — Packaging surface audit (read-only).

Checks:
  - pyproject.toml has no [project] section
  - dbma_ui.py exists
  - core/config.py exists
  - .gitattributes has 3 export-ignore patterns

Task Order: C1-TASK-ORDER-GATE2-ORCHESTRATOR-SCAFFOLDING.md §3 Phase A
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVIDENCE_DIR = Path(__file__).resolve().parent / ".." / ".." / "evidence" / "gate2"


def main() -> dict:
    results: dict = {}
    all_pass = True

    # 1. pyproject.toml — [project] 없음 확인
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    if not pyproject_path.exists():
        results["pyproject_no_project_section"] = {"status": "FAIL", "reason": "pyproject.toml not found"}
        all_pass = False
    else:
        content = pyproject_path.read_text(encoding="utf-8")
        has_project_section = any(
            line.strip().startswith("[project]") for line in content.splitlines()
        )
        if has_project_section:
            results["pyproject_no_project_section"] = {
                "status": "FAIL",
                "reason": "pyproject.toml contains [project] section",
            }
            all_pass = False
        else:
            results["pyproject_no_project_section"] = {"status": "PASS"}

    # 2. dbma_ui.py 존재 확인
    dbma_ui_path = PROJECT_ROOT / "dbma_ui.py"
    if dbma_ui_path.exists():
        results["dbma_ui_exists"] = {"status": "PASS", "path": str(dbma_ui_path)}
    else:
        results["dbma_ui_exists"] = {"status": "FAIL", "reason": "dbma_ui.py not found"}
        all_pass = False

    # 3. core/config.py 존재 확인
    config_path = PROJECT_ROOT / "core" / "config.py"
    if config_path.exists():
        results["core_config_exists"] = {"status": "PASS", "path": str(config_path)}
    else:
        results["core_config_exists"] = {"status": "FAIL", "reason": "core/config.py not found"}
        all_pass = False

    # 4. .gitattributes export-ignore 3개 패턴 확인
    gitattrs_path = PROJECT_ROOT / ".gitattributes"
    if not gitattrs_path.exists():
        results["gitattributes_patterns"] = {"status": "FAIL", "reason": ".gitattributes not found"}
        all_pass = False
    else:
        content = gitattrs_path.read_text(encoding="utf-8")
        patterns_found = []
        for pattern in ["NAE/", ".automation/", "test_seal_*"]:
            # Check each line of .gitattributes for the pattern + export-ignore
            for line in content.splitlines():
                if pattern in line and "export-ignore" in line:
                    patterns_found.append(pattern)
                    break
        results["gitattributes_patterns"] = {
            "status": "PASS" if len(patterns_found) == 3 else "FAIL",
            "expected": 3,
            "found": len(patterns_found),
            "patterns": patterns_found,
        }
        if len(patterns_found) != 3:
            all_pass = False

    summary = {
        "script": "10_packaging_audit.py",
        "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "all_pass": all_pass,
        "checks": results,
    }

    # Write evidence
    evidence_dir = EVIDENCE_DIR.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "10_packaging_audit.json"
    evidence_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Result: {'PASS' if all_pass else 'FAIL'}")
    print(f"Evidence written to: {evidence_file}")
    return summary


if __name__ == "__main__":
    sys.exit(0 if main()["all_pass"] else 1)
