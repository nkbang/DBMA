#!/usr/bin/env python3
"""50_runtime_smoke.py — Streamlit runtime smoke test (read-only).

Starts streamlit on a separate port, checks HTTP 200, then tears down.
Uses ~/envs/dbma311 environment (no new venv).

Task Order: C1-TASK-ORDER-GATE2-ORCHESTRATOR-SCAFFOLDING.md §3 Phase A
"""

import http.client
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVIDENCE_DIR = Path(__file__).resolve().parent / ".." / ".." / "evidence" / "gate2"
SMOKE_PORT = 8502  # non-default port to avoid conflicts


def main() -> dict:
    results: dict = {}
    all_pass = True

    # 1. Verify env exists
    env_path = Path.home() / "envs" / "dbma311"
    if not env_path.exists():
        results["env_exists"] = {"status": "FAIL", "reason": f"{env_path} not found"}
        all_pass = False
        summary = {
            "script": "50_runtime_smoke.py",
            "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "all_pass": False,
            "checks": results,
        }
        evidence_dir = EVIDENCE_DIR.resolve()
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "50_runtime_smoke.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Result: FAIL")
        return summary

    results["env_exists"] = {"status": "PASS", "path": str(env_path)}

    # 2. Start streamlit
    ui_app = PROJECT_ROOT / "dbma_ui.py"
    if not ui_app.exists():
        results["ui_file"] = {"status": "FAIL", "reason": "dbma_ui.py not found"}
        all_pass = False
        summary = {
            "script": "50_runtime_smoke.py",
            "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "all_pass": False,
            "checks": results,
        }
        evidence_dir = EVIDENCE_DIR.resolve()
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "50_runtime_smoke.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Result: FAIL")
        return summary

    results["ui_file"] = {"status": "PASS", "path": str(ui_app)}

    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(env_path)
    env["PATH"] = str(env_path / "bin") + ":" + os.environ.get("PATH", "")

    proc = subprocess.Popen(
        [
            str(env_path / "bin" / "python"), "-m", "streamlit", "run",
            str(ui_app),
            "--server.headless", "true",
            "--server.port", str(SMOKE_PORT),
            "--server.address", "127.0.0.1",
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for startup (up to 30s)
    started = False
    for _ in range(60):  # 30 seconds (500ms * 60)
        time.sleep(0.5)
        try:
            conn = http.client.HTTPConnection("127.0.0.1", SMOKE_PORT, timeout=3)
            conn.request("GET", "/")
            resp = conn.getresponse()
            if resp.status == 200:
                started = True
                results["http_response"] = {"status": "PASS", "code": resp.status}
                conn.close()
                break
            conn.close()
        except Exception:
            pass

    # Teardown
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    if not started:
        results["http_response"] = {"status": "FAIL", "reason": "Streamlit did not respond with 200 within 30s"}
        all_pass = False

    summary = {
        "script": "50_runtime_smoke.py",
        "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "all_pass": all_pass,
        "checks": results,
    }

    evidence_dir = EVIDENCE_DIR.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "50_runtime_smoke.json"
    evidence_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Result: {'PASS' if all_pass else 'FAIL'}")
    print(f"Evidence written to: {evidence_file}")
    return summary


if __name__ == "__main__":
    sys.exit(0 if main()["all_pass"] else 1)
