#!/usr/bin/env python3
"""30_package_integrity.py — Package integrity verification (read-only).

Uses `git archive HEAD` locally to verify:
  - NAE/, .automation/, test_seal_* are NOT in the archive (export-ignore)
  - README.md, INSTALL.md, dbma_ui.py, core/retrieval.py, requirements.txt ARE in the archive

Task Order: C1-TASK-ORDER-GATE2-ORCHESTRATOR-SCAFFOLDING.md §3 Phase A
"""

import json
import os
import subprocess
import sys
import tempfile
import tarfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVIDENCE_DIR = Path(__file__).resolve().parent / ".." / ".." / "evidence" / "gate2"


def main() -> dict:
    results: dict = {}
    all_pass = True

    # Create temp dir for archive extraction
    with tempfile.TemporaryDirectory(prefix="gate2_pkg_") as tmpdir:
        archive_path = Path(tmpdir) / "package.tar.gz"

        # Run git archive HEAD
        try:
            subprocess.run(
                ["git", "archive", "--prefix=package/", "-o", str(archive_path), "HEAD"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                check=True,
            )
            results["git_archive_created"] = {"status": "PASS"}
        except subprocess.CalledProcessError as exc:
            results["git_archive_created"] = {
                "status": "FAIL",
                "reason": f"git archive failed: {exc.stderr}",
            }
            all_pass = False
            summary = {
                "script": "30_package_integrity.py",
                "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "all_pass": False,
                "checks": results,
            }
            evidence_dir = EVIDENCE_DIR.resolve()
            evidence_dir.mkdir(parents=True, exist_ok=True)
            (evidence_dir / "30_package_integrity.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"Result: FAIL")
            print(f"Evidence written to: {evidence_dir / '30_package_integrity.json'}")
            return summary

        # Extract and inspect
        with tarfile.open(archive_path, "r:gz") as tf:
            member_names = tf.getnames()

        # Check exclusion patterns (should NOT be present)
        # git archive --prefix=package/ adds "package/" to every entry, so patterns must match the full path.
        excluded_patterns = ["package/NAE/", "package/.automation/", "package/test_seal_"]
        for pattern in excluded_patterns:
            found = [m for m in member_names if m.startswith(pattern)]
            key = f"excluded_{pattern.replace('package/', '')}"
            results[key] = {
                "status": "FAIL" if found else "PASS",
                "match_count": len(found),
                "examples": found[:3],
            }
            if found:
                all_pass = False

        # Check inclusion patterns (should be present)
        required_files = [
            "package/README.md",
            "package/INSTALL.md",
            "package/dbma_ui.py",
            "package/core/retrieval.py",
            "package/requirements.txt",
        ]
        for req_file in required_files:
            if req_file in member_names:
                results[f"required_{req_file.replace('/', '_')}"] = {"status": "PASS"}
            else:
                results[f"required_{req_file.replace('/', '_')}"] = {
                    "status": "FAIL",
                    "reason": f"Required file '{req_file}' not in archive",
                }
                all_pass = False

        results["total_members"] = len(member_names)

    summary = {
        "script": "30_package_integrity.py",
        "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "all_pass": all_pass,
        "checks": results,
    }

    evidence_dir = EVIDENCE_DIR.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "30_package_integrity.json"
    evidence_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Result: {'PASS' if all_pass else 'FAIL'}")
    print(f"Archive members: {results.get('total_members', '?')}")
    print(f"Evidence written to: {evidence_file}")
    return summary


if __name__ == "__main__":
    sys.exit(0 if main()["all_pass"] else 1)
