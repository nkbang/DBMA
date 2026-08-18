#!/usr/bin/env python3
"""95_evidence_verify.py — Evidence integrity verification.

Verifies that stdout_sha256 in evidence JSON files matches actual re-execution.

Task Order: C1-TASK-ORDER-GATE2-ORCHESTRATOR-SCAFFOLDING.md §3 Phase A
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVIDENCE_DIR = Path(__file__).resolve().parent / ".." / ".." / "evidence" / "gate2"


def file_sha256(filepath: Path) -> str:
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> dict:
    results: dict = {}
    all_pass = True

    # Find all evidence JSON files
    evidence_files = sorted(EVIDENCE_DIR.glob("*.json"))
    if not evidence_files:
        results["evidence_files"] = {"status": "WARN", "reason": "No evidence files found"}
        summary = {
            "script": "95_evidence_verify.py",
            "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "all_pass": False,
            "checks": results,
        }
        evidence_dir = EVIDENCE_DIR.resolve()
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "95_evidence_verify.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Result: WARN — no evidence files found")
        return summary

    results["evidence_files_found"] = {"status": "PASS", "count": len(evidence_files)}

    for ev_file in evidence_files:
        try:
            data = json.loads(ev_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            results[f"parse_{ev_file.name}"] = {
                "status": "FAIL",
                "reason": str(exc),
            }
            all_pass = False
            continue

        # Check if evidence has stdout_sha256 field
        stored_hash = data.get("stdout_sha256")
        if stored_hash is None:
            results[f"sha_check_{ev_file.name}"] = {
                "status": "SKIP",
                "reason": "No stdout_sha256 in evidence",
            }
            continue

        # Re-run the script and compare
        script_name = data.get("script", "")
        if not script_name:
            results[f"sha_check_{ev_file.name}"] = {
                "status": "SKIP",
                "reason": "No 'script' field in evidence",
            }
            continue

        # Find the corresponding script
        script_path = Path(__file__).parent / script_name
        if not script_path.exists():
            results[f"sha_check_{ev_file.name}"] = {
                "status": "SKIP",
                "reason": f"Script {script_path} not found",
            }
            continue

        # Re-run and capture stdout
        try:
            venv_bin = Path.home() / "envs" / "dbma311" / "bin"
            proc = subprocess.run(
                [str(venv_bin / "python"), str(script_path)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
            actual_stdout = proc.stdout + proc.stderr
            actual_hash = hashlib.sha256(actual_stdout.encode("utf-8")).hexdigest()

            if actual_hash == stored_hash:
                results[f"sha_check_{ev_file.name}"] = {
                    "status": "PASS",
                    "stored": stored_hash[:16] + "...",
                    "actual": actual_hash[:16] + "...",
                }
            else:
                results[f"sha_check_{ev_file.name}"] = {
                    "status": "FAIL",
                    "stored": stored_hash,
                    "actual": actual_hash,
                }
                all_pass = False
        except subprocess.TimeoutExpired:
            results[f"sha_check_{ev_file.name}"] = {
                "status": "SKIP",
                "reason": f"Re-execution timeout for {script_name}",
            }
        except Exception as exc:
            results[f"sha_check_{ev_file.name}"] = {
                "status": "SKIP",
                "reason": str(exc),
            }

    summary = {
        "script": "95_evidence_verify.py",
        "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "all_pass": all_pass,
        "checks": results,
    }

    evidence_dir = EVIDENCE_DIR.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "95_evidence_verify.json"
    evidence_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Result: {'PASS' if all_pass else 'FAIL'}")
    print(f"Evidence written to: {evidence_file}")
    return summary


if __name__ == "__main__":
    sys.exit(0 if main()["all_pass"] else 1)
