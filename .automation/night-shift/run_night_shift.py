#!/usr/bin/env python3
"""NAE Night Shift Queue Runner — execution mode for the EXISTING n8n workflow.

This is NOT a new workflow. It is a driver that feeds a task queue into the
already-approved n8n workflow "Phase E State Machine" (id 9qIO3nFeWRia28Rb)
through its existing webhook, one task at a time, unattended.

    queue/*.json  ->  POST /webhook/dbma-automation-phase-e  ->  (n8n)
                      Read Task -> Validate -> Decide Transition
                      -> Execute Command (cli_driver -> register_source)
                      -> Exit Code Check -> Write Task/Evidence -> Respond
                  ->  independent evidence verification (here)
                  ->  done/  or  ../review-queue/

Governance boundaries enforced by this script
---------------------------------------------
* ADR-022 SS8: automation MUST NOT promote FAILED -> RETRY_PENDING.
  There is deliberately NO automatic retry / self-correction code here.
  Every failure terminates that task and routes it to the CUE review queue.
* ADR-023: the only production mutation path is the approved cli_driver
  invocation inside the existing workflow. This script never mutates
  production content itself.
* Protected paths (SS7 of the operating order) are checksummed before and
  after every task; any change aborts the whole run.
* Evidence-first: an n8n HTTP response saying "completed" is never enough.
  The task file state, the evidence jsonl transition and (for COMPLETED)
  the registration state store are re-read from disk before a task is
  recorded as PASS.

Usage
-----
    python3 .automation/night-shift/run_night_shift.py --once
    python3 .automation/night-shift/run_night_shift.py --watch 60
    python3 .automation/night-shift/run_night_shift.py --once --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
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
REVIEW_QUEUE = PROJECT_ROOT / ".automation" / "review-queue"
TASKS_DIR = PROJECT_ROOT / ".automation" / "tasks"
EVIDENCE_DIR = PROJECT_ROOT / ".automation" / "evidence"
REG_STATE = PROJECT_ROOT / "NAE" / "pipeline" / "registration" / "state" / "registration_state.json"

WEBHOOK = "http://localhost:5678/webhook/dbma-automation-phase-e"
REQUEST_TIMEOUT_S = 900  # register_source() on a full volume can be slow

# SS7 Production Boundary — these must not change while the night shift runs.
PROTECTED_PATHS = [
    "core/retrieval.py",
    "core/module_registry.py",
    "NAE/pipeline/registration/pipeline.py",
    ".automation/tasks/schema.json",
    "docs/architecture/ADR-022-DBMA-N8N-Automation-State-Machine.md",
    "docs/architecture/ADR-023-DBMA-N8N-Automation-Full-Processing.md",
]

TERMINAL_PASS = {"processing_completed"}
TERMINAL_HOLD = {"validation_passed"}  # queued task had no processing_input


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def log(msg: str) -> None:
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / "night-shift.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def sha256_of(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_snapshot() -> dict[str, str]:
    return {p: sha256_of(PROJECT_ROOT / p) for p in PROTECTED_PATHS}


class BoundaryViolation(RuntimeError):
    pass


def assert_boundary(before: dict[str, str]) -> None:
    after = protected_snapshot()
    changed = [p for p in before if before[p] != after[p]]
    if changed:
        raise BoundaryViolation(f"protected path(s) changed: {', '.join(changed)}")


def post_task(payload: dict) -> tuple[int, dict | str]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            raw = resp.read().decode("utf-8", "replace")
            code = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        code = exc.code
    except Exception as exc:  # connection refused, timeout, ...
        return 0, f"TRANSPORT_ERROR: {exc}"
    try:
        return code, json.loads(raw)
    except json.JSONDecodeError:
        return code, raw


def read_task_state(task_id: str) -> dict:
    path = TASKS_DIR / f"{task_id}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def read_evidence(task_id: str) -> list[dict]:
    path = EVIDENCE_DIR / f"{task_id}.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def registration_recorded(source_id: str) -> bool:
    """Independent third check: did the ADR-021 state store actually record it?"""
    if not source_id or not REG_STATE.exists():
        return False
    try:
        data = json.loads(REG_STATE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    entry = data.get(source_id) if isinstance(data, dict) else None
    if isinstance(entry, dict):
        return entry.get("state") == "QUALITY_PASSED"
    if isinstance(entry, str):
        return entry == "QUALITY_PASSED"
    return False


def verify(task_id: str, response: dict, source_id: str) -> tuple[bool, list[str]]:
    """Evidence-first verification. Returns (passed, reasons)."""
    reasons: list[str] = []
    status = response.get("status") if isinstance(response, dict) else None

    task = read_task_state(task_id)
    state = (task.get("automation") or {}).get("state")
    reasons.append(f"task_file.automation.state={state!r}")

    ev = read_evidence(task_id)
    last = ev[-1] if ev else {}
    reasons.append(f"evidence_lines={len(ev)} last_to={last.get('to') or last.get('to_state')!r}")

    if status not in TERMINAL_PASS:
        reasons.append(f"response.status={status!r} is not a PASS status")
        return False, reasons

    if state != "COMPLETED":
        reasons.append("task file does not say COMPLETED — response not trusted")
        return False, reasons

    if not ev:
        reasons.append("no evidence transitions written")
        return False, reasons

    if source_id:
        ok = registration_recorded(source_id)
        reasons.append(f"registration_state[{source_id}]==QUALITY_PASSED -> {ok}")
        if not ok:
            return False, reasons

    return True, reasons


def route_failure(item: Path, task_id: str, reasons: list[str], response) -> None:
    """ADR-022 SS8: no automatic retry. Hand off to the CUE review queue."""
    REVIEW_QUEUE.mkdir(parents=True, exist_ok=True)
    target = REVIEW_QUEUE / item.name
    shutil.move(str(item), str(target))
    note = REVIEW_QUEUE / f"{task_id}.review.md"
    note.write_text(
        "\n".join(
            [
                f"# CUE Review Required — {task_id}",
                "",
                f"- routed_at: {now()}",
                "- reason: night shift task did not pass evidence verification",
                "- ADR-022 SS8: automation must NOT auto-retry. A human/CUE decision",
                "  is required before this task returns to the queue.",
                "",
                "## n8n response",
                "```json",
                json.dumps(response, ensure_ascii=False, indent=2)
                if isinstance(response, dict)
                else str(response),
                "```",
                "",
                "## Independent verification",
                *[f"- {r}" for r in reasons],
                "",
            ]
        ),
        encoding="utf-8",
    )
    log(f"  -> ROUTED TO CUE REVIEW QUEUE: {target.relative_to(PROJECT_ROOT)}")


def run_item(item: Path, dry_run: bool) -> str:
    payload = json.loads(item.read_text(encoding="utf-8"))
    task_id = payload.get("task_id")
    if not task_id:
        log(f"  SKIP {item.name}: no task_id")
        return "SKIP"
    source_id = ((payload.get("automation") or {}).get("processing_input") or {}).get(
        "source_id", ""
    )

    log(f"TASK {task_id} (source_id={source_id or '-'})")
    if dry_run:
        log("  dry-run: not submitting")
        return "DRYRUN"

    before = protected_snapshot()

    # The workflow reads /automation/tasks/<task_id>.json from disk.
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    (TASKS_DIR / f"{task_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    # The workflow appends to an existing evidence file.
    ev_path = EVIDENCE_DIR / f"{task_id}.jsonl"
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    ev_path.touch(exist_ok=True)

    started = time.monotonic()
    code, response = post_task(payload)
    elapsed = time.monotonic() - started
    log(f"  http={code} elapsed={elapsed:.1f}s response={json.dumps(response, ensure_ascii=False)[:300] if isinstance(response, dict) else response}")

    assert_boundary(before)  # raises BoundaryViolation -> whole run aborts

    if code == 0:
        route_failure(item, task_id, [f"transport failure: {response}"], response)
        return "FAIL"

    passed, reasons = verify(task_id, response if isinstance(response, dict) else {}, source_id)
    for r in reasons:
        log(f"  verify: {r}")

    if passed:
        DONE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(item), str(DONE_DIR / item.name))
        log("  -> PASS (evidence verified)")
        return "PASS"

    status = response.get("status") if isinstance(response, dict) else None
    if status in TERMINAL_HOLD:
        DONE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(item), str(DONE_DIR / item.name))
        log("  -> VALIDATION_PASSED only (no processing_input) — no production mutation")
        return "VALIDATED"

    route_failure(item, task_id, reasons, response)
    return "FAIL"


def queue_items() -> list[Path]:
    return sorted(p for p in QUEUE_DIR.glob("*.json") if p.is_file())


def drain(dry_run: bool) -> dict[str, int]:
    tally: dict[str, int] = {}
    for item in queue_items():
        result = run_item(item, dry_run)
        tally[result] = tally.get(result, 0) + 1
    return tally


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="drain the queue once and exit")
    ap.add_argument("--watch", type=int, metavar="SECONDS", help="drain, then poll the queue")
    ap.add_argument("--dry-run", action="store_true", help="list what would run, submit nothing")
    ap.add_argument("--max-idle-cycles", type=int, default=480, help="stop after N empty polls")
    args = ap.parse_args()

    if not args.once and not args.watch:
        ap.error("one of --once / --watch is required")

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    log(f"night shift start (once={args.once} watch={args.watch} dry_run={args.dry_run})")
    log(f"queue depth: {len(queue_items())}")

    try:
        if args.once:
            tally = drain(args.dry_run)
            log(f"done: {tally}")
            return 0 if tally.get("FAIL", 0) == 0 else 1

        idle = 0
        while idle < args.max_idle_cycles:
            tally = drain(args.dry_run)
            if tally:
                idle = 0
                log(f"cycle: {tally}")
            else:
                idle += 1
            time.sleep(args.watch)
        log(f"idle limit reached ({args.max_idle_cycles} empty polls) — stopping")
        return 0
    except BoundaryViolation as exc:
        log(f"ABORT — PRODUCTION BOUNDARY VIOLATION: {exc}")
        return 2
    except KeyboardInterrupt:
        log("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
