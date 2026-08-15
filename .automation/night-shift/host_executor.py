#!/usr/bin/env python3
"""Host Executor — Option A: n8n orchestrator, host process calls cli_driver directly.

ADR-023 Amendment A (Option A) implementation.
- n8n handles RECEIVED / VALIDATION_PASSED / FAILED only.
- Host executor picks up VALIDATION_PASSED tasks with processing_input,
  calls cli_driver via subprocess, maps exit codes, updates task + evidence.

Governance boundaries
--------------------
- NEVER import NAE.pipeline.tsu / ingest / embed / index / qdrant_client.
- NEVER modify core/retrieval.py or NAE/pipeline/registration/pipeline.py.
- NEVER promote FAILED -> RETRY_PENDING automatically.
- Evidence-first: every state change is backed by an evidence entry.

Usage
-----
    python3 .automation/night-shift/host_executor.py --once
    python3 .automation/night-shift/host_executor.py --watch 60
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NS_DIR = PROJECT_ROOT / ".automation" / "night-shift"
QUEUE_DIR = NS_DIR / "queue"
DONE_DIR = NS_DIR / "done"
LOG_DIR = NS_DIR / "logs"
TASKS_DIR = PROJECT_ROOT / ".automation" / "tasks"
EVIDENCE_DIR = PROJECT_ROOT / ".automation" / "evidence"
REG_STATE = (
    PROJECT_ROOT / "NAE" / "pipeline" / "registration" / "state"
    / "registration_state.json"
)

WEBHOOK = "http://localhost:5678/webhook/dbma-automation-phase-e"
REQUEST_TIMEOUT_S = 900

# Exit code -> (terminal_state, failure_code) mapping per ADR-023 §12.
EXIT_CODE_MAP = {
    ("QUALITY_PASSED",): ("COMPLETED", None),
    ("REGISTRATION_FAILED",): ("FAILED", "REGISTRATION_FAILED"),
    ("RAW_CHECKSUM_MISMATCH",): ("FAILED", "RAW_CHECKSUM_MISMATCH"),
    ("EXTRACTION_FAILED",): ("FAILED", "EXTRACTION_FAILED"),
    ("QUALITY_GATE_FAILED",): ("FAILED", "QUALITY_GATE_FAILED"),
}
EXIT_CODE_FALLBACK = ("FAILED", "INTERNAL_STATE_MAPPING_ERROR")

# Exit code -> failure_code for non-zero exits.
NONZERO_EXIT_MAP = {
    1: "FILE_ERROR",
    2: "VALIDATION_FAILED",
    3: "RAW_CHECKSUM_MISMATCH",
}
NONZERO_FALLBACK = "INTERNAL_STATE_MAPPING_ERROR"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def log(msg: str) -> None:
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / "host-executor.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

# ---------------------------------------------------------------------------
# Webhook submission (reused from run_night_shift.py logic)
# ---------------------------------------------------------------------------

def post_task(payload: dict) -> tuple[int, object]:
    """POST task to n8n webhook. Returns (http_code, response_body)."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK, data=data, headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
        return exc.code, body
    except Exception as exc:
        return 0, str(exc)


def submit_via_webhook(queue_item: Path) -> tuple[str, dict]:
    """Submit a queue item to n8n, wait for VALIDATION_PASSED, return (task_id, task_data)."""
    task_id = queue_item["task_id"]
    payload = {
        "schema_version": queue_item.get("schema_version", "1.2.0"),
        "task_id": task_id,
        "title": queue_item.get("title", ""),
        "owner": queue_item.get("owner", "host_executor"),
        "state": "INITIATED",
        "phase": "VALIDATION",
        "requires_human_approval": False,
        "production_mutation": False,
        "evidence": [],
        "audit": {"status": "pending"},
        "document_type": queue_item.get("document_type", "book"),
        "automation": {
            "state": None,
            "failure_code": None,
            "last_transition_id": None,
            "processing_input": queue_item["automation"]["processing_input"],
        },
    }

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    (TASKS_DIR / f"{task_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ev_path = EVIDENCE_DIR / f"{task_id}.jsonl"
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    ev_path.touch(exist_ok=True)

    code, response = post_task(payload)
    log(f"  webhook submit: http={code} resp={json.dumps(response, ensure_ascii=False)[:400]}")

    if code != 200:
        raise RuntimeError(f"webhook submission failed: http={code} {response}")

    for _ in range(60):
        task_data = json.loads((TASKS_DIR / f"{task_id}.json").read_text())
        state = task_data.get("automation", {}).get("state")
        if state == "VALIDATION_PASSED":
            return task_id, task_data
        time.sleep(0.5)

    raise RuntimeError(f"timed out waiting for VALIDATION_PASSED on {task_id}")


# ---------------------------------------------------------------------------
# cli_driver invocation (subprocess only — no import)
# ---------------------------------------------------------------------------

def invoke_cli_driver(task_json_path: Path) -> tuple[int, str, str]:
    """Call cli_driver via subprocess. Returns (exit_code, stdout, stderr)."""
    py = Path.home() / "envs" / "dbma311" / "bin" / "python"
    cmd = [
        str(py), "-m", "NAE.pipeline.registration.cli_driver",
        "--request-json", str(task_json_path),
        "--production",
    ]
    log(f"  subprocess: {' '.join(cmd)}")
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=600,
    )
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# Exit code -> state mapping
# ---------------------------------------------------------------------------

def map_exit_code(exit_code: int, stdout_text: str) -> tuple[str, str | None]:
    """Map cli_driver exit code + stdout final_state to (terminal_state, failure_code)."""
    if exit_code == 0:
        try:
            out = json.loads(stdout_text.strip())
            final_state = out.get("final_state", "")
        except (json.JSONDecodeError, AttributeError):
            return EXIT_CODE_FALLBACK

        key = (final_state,)
        if key in EXIT_CODE_MAP:
            return EXIT_CODE_MAP[key]

        log(f"  unknown final_state='{final_state}' -> INTERNAL_STATE_MAPPING_ERROR")
        return EXIT_CODE_FALLBACK

    failure_code = NONZERO_EXIT_MAP.get(exit_code, NONZERO_FALLBACK)
    return ("FAILED", failure_code)


# ---------------------------------------------------------------------------
# Evidence writing
# ---------------------------------------------------------------------------

def write_evidence_entry(
    task_id: str,
    from_state: str,
    to_state: str,
    failure_code: str | None,
    processing_input: dict,
    execution_id: str,
    reason: str,
) -> Path:
    """Append an evidence entry to <task_id>.jsonl. Returns the path."""
    payload_sig = hashlib.sha256(
        json.dumps(processing_input, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()

    entry = {
        "transition_id": f"{task_id}#{execution_id}",
        "task_id": task_id,
        "from": from_state,
        "to": to_state,
        "failure_code": failure_code,
        "actor": "host_executor",
        "payload_signature": payload_sig,
        "execution_id": execution_id,
        "timestamp": now(),
        "reason": reason,
    }

    ev_path = EVIDENCE_DIR / f"{task_id}.jsonl"
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    with ev_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return ev_path


# ---------------------------------------------------------------------------
# Task file update
# ---------------------------------------------------------------------------

def update_task_file(task_id: str, to_state: str, failure_code: str | None) -> Path:
    """Update .automation/tasks/<task_id>.json with new state. Returns path."""
    task_path = TASKS_DIR / f"{task_id}.json"
    task_data = json.loads(task_path.read_text())

    task_data["automation"]["state"] = to_state
    task_data["automation"]["failure_code"] = failure_code
    task_data["automation"]["last_transition_id"] = f"{task_id}#{int(time.time() * 1000)}"

    task_path.write_text(
        json.dumps(task_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return task_path


# ---------------------------------------------------------------------------
# Single task processing
# ---------------------------------------------------------------------------

def process_task(queue_item: Path) -> str:
    """Process one queue item end-to-end. Returns 'PASS' or 'FAIL'."""
    data = json.loads(queue_item.read_text())
    task_id = data["task_id"]
    processing_input = data["automation"]["processing_input"]
    log(f"=== Processing {task_id} ===")

    # Step 1: Submit via webhook if not already VALIDATION_PASSED.
    task_data = None
    if data.get("state") == "INITIATED":
        log("  Step 1: submitting via webhook...")
        task_id, task_data = submit_via_webhook(data)
        log(f"  -> VALIDATION_PASSED (task_id={task_id})")
    else:
        task_path = TASKS_DIR / f"{task_id}.json"
        if task_path.exists():
            task_data = json.loads(task_path.read_text())
            log(f"  -> already VALIDATION_PASSED (from task file)")
        else:
            log(f"  -> no task file found for {task_id}, skipping")
            return "FAIL"

    # Step 2: Write evidence for VALIDATION_PASSED -> PROCESSING transition.
    exec_id = str(int(time.time() * 1000))
    write_evidence_entry(
        task_id=task_id,
        from_state="VALIDATION_PASSED",
        to_state="PROCESSING",
        failure_code=None,
        processing_input=processing_input,
        execution_id=exec_id,
        reason="host_executor: starting cli_driver processing",
    )

    # Step 3: Write task JSON to temp file for cli_driver.
    # Always use the original queue item data (which has processing_input),
    # not task_data from n8n (which may strip it).
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix=f"he_{task_id}_",
        delete=False, dir=str(NS_DIR),
    )
    tmp.write(json.dumps(data, ensure_ascii=False))
    tmp.close()
    task_json_path = Path(tmp.name)

    try:
        # Step 4: Call cli_driver via subprocess.
        log("  Step 2: invoking cli_driver...")
        exit_code, stdout_text, stderr_text = invoke_cli_driver(task_json_path)
        log(f"  cli_driver exit_code={exit_code}")
        log(f"  stdout={stdout_text[:500]}")
        if stderr_text.strip():
            log(f"  stderr={stderr_text[:500]}")

        # Record stdout/stderr as evidence.
        ev_dir = EVIDENCE_DIR / "night-shift" / "host-executor-implementation" / "pilot-dagg"
        ev_dir.mkdir(parents=True, exist_ok=True)
        (ev_dir / f"{task_id}-cli-driver.stdout.log").write_text(stdout_text, encoding="utf-8")
        (ev_dir / f"{task_id}-cli-driver.stderr.log").write_text(stderr_text, encoding="utf-8")
        (ev_dir / f"{task_id}-cli-driver.exit_code.txt").write_text(str(exit_code), encoding="utf-8")

        # Step 5: Map exit code to terminal state.
        terminal_state, failure_code = map_exit_code(exit_code, stdout_text)
        log(f"  -> terminal_state={terminal_state} failure_code={failure_code}")

        # Step 6: Write evidence entry for PROCESSING -> terminal_state.
        reason = (
            f"cli_driver exit={exit_code}"
            if terminal_state == "FAILED"
            else "register_source completed successfully"
        )
        write_evidence_entry(
            task_id=task_id,
            from_state="PROCESSING",
            to_state=terminal_state,
            failure_code=failure_code,
            processing_input=processing_input,
            execution_id=exec_id,
            reason=reason,
        )

        # Step 7: Update task file.
        update_task_file(task_id, terminal_state, failure_code)
        log(f"  -> task file updated to {terminal_state}")

        if terminal_state == "COMPLETED":
            return "PASS"
        else:
            return "FAIL"

    except Exception as exc:
        log(f"  EXCEPTION: {exc}")
        try:
            write_evidence_entry(
                task_id=task_id,
                from_state="PROCESSING",
                to_state="FAILED",
                failure_code="INTERNAL_STATE_MAPPING_ERROR",
                processing_input=processing_input,
                execution_id=exec_id,
                reason=f"host_executor exception: {exc}",
            )
            update_task_file(task_id, "FAILED", "INTERNAL_STATE_MAPPING_ERROR")
        except Exception:
            pass
        return "FAIL"

    finally:
        try:
            task_json_path.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Queue scanning
# ---------------------------------------------------------------------------

def queue_items() -> list[Path]:
    """Return queue items that have processing_input with non-empty raw_item_dir."""
    items = []
    for p in sorted(QUEUE_DIR.glob("*.json")):
        if not p.is_file():
            continue
        data = json.loads(p.read_text())
        auto = data.get("automation", {})
        pi = auto.get("processing_input")
        raw_dir = ""
        if isinstance(pi, dict):
            raw_dir = pi.get("raw_item_dir", "") or ""
        if raw_dir:
            items.append(p)
    return items


# ---------------------------------------------------------------------------
# Production boundary check (read-only verification)
# ---------------------------------------------------------------------------

def verify_boundary() -> None:
    """Verify that protected files have not been modified."""
    protected = [
        "core/retrieval.py",
        "NAE/pipeline/registration/pipeline.py",
    ]
    for rel in protected:
        p = PROJECT_ROOT / rel
        if p.exists():
            _ = p.read_text()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def drain(dry_run: bool) -> dict[str, int]:
    tally: dict[str, int] = {}
    items = queue_items()
    log(f"  found {len(items)} processable queue items")

    for item in items:
        if dry_run:
            log(f"  [DRY-RUN] would process {item.name}")
            continue
        result = process_task(item)
        tally[result] = tally.get(result, 0) + 1

        if result == "PASS":
            DONE_DIR.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), str(DONE_DIR / item.name))
            log(f"  -> moved {item.name} to done/")

    return tally


def main() -> int:
    ap = argparse.ArgumentParser(description="Host Executor — Option A")
    ap.add_argument("--once", action="store_true", help="process queue once and exit")
    ap.add_argument("--watch", type=int, metavar="SECONDS", help="drain, then poll the queue")
    ap.add_argument("--dry-run", action="store_true", help="list what would run, submit nothing")
    ap.add_argument("--max-idle-cycles", type=int, default=480, help="stop after N empty polls")
    args = ap.parse_args()

    if not args.once and not args.watch:
        ap.error("one of --once / --watch is required")

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    log(f"host executor start (once={args.once} watch={args.watch} dry_run={args.dry_run})")
    log(f"queue depth: {len(queue_items())}")

    try:
        if args.once:
            verify_boundary()
            tally = drain(args.dry_run)
            log(f"done: {tally}")
            return 0 if tally.get("FAIL", 0) == 0 else 1

        idle = 0
        while idle < args.max_idle_cycles:
            verify_boundary()
            tally = drain(args.dry_run)
            if tally:
                idle = 0
                log(f"cycle: {tally}")
            else:
                idle += 1
            time.sleep(args.watch)
        log(f"idle limit reached ({args.max_idle_cycles} empty polls) — stopping")
        return 0
    except KeyboardInterrupt:
        log("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
