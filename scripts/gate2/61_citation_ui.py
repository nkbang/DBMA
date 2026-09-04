#!/usr/bin/env python3
"""61_citation_ui.py — Wrapper for test_citation_ui_surface.py tests.

Runs the existing pytest suite and wraps results in evidence JSON.
Does NOT rewrite test logic — just calls existing pytest.

Task Order: C1-TASK-ORDER-GATE2-ORCHESTRATOR-SCAFFOLDING.md §3 Phase A
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVIDENCE_DIR = Path(__file__).resolve().parent / ".." / ".." / "evidence" / "gate2"
TEST_FILE = PROJECT_ROOT / "tests" / "test_citation_ui_surface.py"


def main() -> dict:
    results: dict = {}
    all_pass = True

    # 1. Verify test file exists
    if not TEST_FILE.exists():
        results["test_file"] = {"status": "FAIL", "reason": f"{TEST_FILE} not found"}
        summary = {
            "script": "61_citation_ui.py",
            "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "all_pass": False,
            "checks": results,
        }
        evidence_dir = EVIDENCE_DIR.resolve()
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "61_citation_ui.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Result: FAIL — test file not found")
        return summary

    results["test_file"] = {"status": "PASS", "path": str(TEST_FILE)}

    # 2. Run pytest
    env = os.environ.copy()
    venv_bin = Path.home() / "envs" / "dbma311" / "bin"
    env["PATH"] = str(venv_bin) + ":" + env.get("PATH", "")

    try:
        proc = subprocess.run(
            [
                str(venv_bin / "python"), "-m", "pytest",
                str(TEST_FILE),
                "-v", "--tb=short",
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )

        results["pytest_exit_code"] = {"status": "PASS" if proc.returncode == 0 else "FAIL", "code": proc.returncode}

        # Parse pytest output for summary
        stdout_lines = proc.stdout.strip().splitlines() if proc.stdout else []
        stderr_lines = proc.stderr.strip().splitlines() if proc.stderr else []

        # Count passed/failed from pytest output
        # Only count individual test result lines (e.g., "... PASSED [ 71%]"), not the summary line ("7 passed").
        passed = sum(1 for l in stdout_lines if re.search(r"\sPASSED\s*\[", l))
        failed = sum(1 for l in stdout_lines if re.search(r"\sFAILED\s*\[", l))
        errors = sum(1 for l in stderr_lines if "ERROR" in l)

        results["pytest_summary"] = {
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "total_tests": passed + failed,
        }

        if proc.returncode != 0:
            all_pass = False

        # Capture stdout/stderr for evidence
        results["stdout_sample"] = stdout_lines[-20:] if stdout_lines else []
        results["stderr_sample"] = stderr_lines[-10:] if stderr_lines else []

    except subprocess.TimeoutExpired:
        results["pytest_exit_code"] = {"status": "FAIL", "reason": "timeout (120s)"}
        all_pass = False
    except Exception as exc:
        results["pytest_run"] = {"status": "FAIL", "reason": str(exc)}
        all_pass = False

    summary = {
        "script": "61_citation_ui.py",
        "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "all_pass": all_pass,
        "checks": results,
    }

    evidence_dir = EVIDENCE_DIR.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "61_citation_ui.json"
    evidence_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Result: {'PASS' if all_pass else 'FAIL'}")
    print(f"Evidence written to: {evidence_file}")
    return summary


if __name__ == "__main__":
    sys.exit(0 if main()["all_pass"] else 1)
