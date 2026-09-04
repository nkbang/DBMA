#!/usr/bin/env python3
"""Pilot Executor — CUE Autonomous Governance Order, isolated control-plane pilot.

Mirrors host_executor.py's Option A pattern (n8n handles the validation
gateway only; a host-side process performs PROCESSING) but is a completely
separate script scoped to the pilot task_id prefixes in
TASK_ID_PREFIX_NAMESPACE only (never any real production task_id).

Governance boundaries
--------------------
- NEVER import NAE.pipeline.* / core.retrieval / any production module.
- NEVER invoke NAE/pipeline/registration/cli_driver.py or any other
  production script. Every task_type maps to exactly one fixed command
  (see run_pilot_command()); none of them touch production code.
- Only touches task_id values matching a known pilot prefix.
- Evidence-first: every state change is backed by an evidence entry,
  same schema as ADR-022 Section 11 / host_executor.py.

Executor isolation contract (G3/G8, extended by
CORPUS-FACTORY-INTEGRATION-PILOT-001):
- (task_type, scope.namespace) MUST be a member of ALLOWED_COMBINATIONS.
- task_id MUST start with the prefix that maps to that namespace.
- production_mutation MUST be False.
Any violation is checked independently by the executor (not just trusted
from the gateway) and refused with no subprocess invoked -- see
check_isolation_contract(). Adding a new combination is a separate,
explicitly authorized task, not something this file grows on its own.

Usage
-----
    python3 .automation/night-shift/pilot_executor.py --once
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = PROJECT_ROOT / ".automation" / "tasks"
EVIDENCE_DIR = PROJECT_ROOT / ".automation" / "evidence"
LOG_DIR = PROJECT_ROOT / ".automation" / "night-shift" / "logs"
PILOT_EVIDENCE_ROOT = EVIDENCE_DIR / "night-shift"
HEARTBEAT_ROOT = PROJECT_ROOT / ".automation" / "night-shift" / "heartbeats"
CORPUS_PILOT_DRIVER = PROJECT_ROOT / ".automation" / "control-plane" / "fixtures" / "corpus_pilot_driver.py"

# AUTONOMOUS-NIGHT-SHIFT-001 G9: a task stuck in PROCESSING with a
# heartbeat older than this is considered stale and force-terminated.
# Kept short deliberately -- every task_type here completes in well under a
# second, so any staleness at all in the pilot is either a genuinely
# crashed worker or a deliberate test fixture.
STALE_THRESHOLD_S = 10

# --- Executor isolation (G3/G8, extended by CORPUS-FACTORY-INTEGRATION-PILOT-001) ---
# (task_type, namespace) pairs are the isolation mechanism, not a convention
# the executor merely promises to respect -- a combination not in this set
# is refused outright, no subprocess invoked. Each task_id prefix maps to
# exactly one namespace, so a task can't claim namespace A while using
# task_id prefix B (checked in check_isolation_contract). Adding a new
# combination is itself a scope-expanding change and must go through a
# separate, explicitly authorized task.
ALLOWED_COMBINATIONS = {
    ("pilot_echo", "control-plane-pilot"),
    ("corpus_pilot_echo", "corpus-factory-pilot"),
}
TASK_ID_PREFIX_NAMESPACE = {
    "CONTROL-PLANE-PILOT-": "control-plane-pilot",
    "CORPUS-FACTORY-PILOT-": "corpus-factory-pilot",
}


def namespace_for_task_id(task_id: str) -> str:
    """Which pilot namespace a task_id belongs to, by its prefix.

    C1 cross-verification (CFI-Pilot-001) found that heartbeat/evidence
    files for different namespaces were being written to the same shared
    directory -- not a real cross-namespace access (files are still keyed
    by the full, prefix-distinct task_id, so nothing was ever overwritten
    or misread), but a legitimate structural gap the isolation claim didn't
    actually cover. Every heartbeat/evidence-adjacent path now goes through
    this function so each namespace gets its own subdirectory.
    """
    for prefix, ns in TASK_ID_PREFIX_NAMESPACE.items():
        if task_id.startswith(prefix):
            return ns
    return "unknown-namespace"


def all_pilot_task_files() -> list[Path]:
    """Every task file under any known pilot namespace's task_id prefix."""
    files: list[Path] = []
    for prefix in TASK_ID_PREFIX_NAMESPACE:
        files.extend(TASKS_DIR.glob(f"{prefix}*.json"))
    return sorted(files)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def log(msg: str) -> None:
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / "pilot-executor.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_canonical_payload_signature(task_id: str) -> str:
    """Return the payload_signature of the LAST evidence entry for task_id.

    Canonical definition (confirmed against the live n8n gateway's
    'Code — Decide Transition' node, not just ADR-022 prose): the gateway
    signs the raw webhook request body via JavaScript's native
    JSON.stringify(), and stores it under the field name
    'payload_signature' (ADR-022 Section 11's prose describes a SHA256
    'payload_hash', but that is not what the deployed Phase E code
    computes -- this is a known ADR-text/code discrepancy, out of scope
    for this pilot to correct).

    pilot_executor.py has no access to the original raw webhook body (it
    only ever sees the task file on disk), so instead of re-deriving a
    signature independently -- which is exactly how the two schemes
    drifted apart -- it reads the value the gateway already established
    and propagates it unchanged. This makes cross-runtime signature drift
    structurally impossible rather than something to keep in sync by hand.
    """
    ev_path = EVIDENCE_DIR / f"{task_id}.jsonl"
    lines = [l for l in ev_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        raise RuntimeError(f"no evidence entries found for {task_id}; cannot propagate signature")
    last_entry = json.loads(lines[-1])
    sig = last_entry.get("payload_signature")
    if not sig:
        raise RuntimeError(f"last evidence entry for {task_id} has no payload_signature")
    return sig


def write_evidence_entry(
    task_id: str,
    from_state: str,
    to_state: str,
    failure_code: str | None,
    payload_signature: str,
    execution_id: str,
    reason: str,
) -> Path:
    entry = {
        "transition_id": f"{task_id}#{execution_id}",
        "task_id": task_id,
        "from": from_state,
        "to": to_state,
        "failure_code": failure_code,
        "actor": "pilot_executor",
        "payload_signature": payload_signature,
        "execution_id": execution_id,
        "timestamp": now(),
        "reason": reason,
    }

    ev_path = EVIDENCE_DIR / f"{task_id}.jsonl"
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    with ev_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return ev_path


def update_task_file(task_id: str, to_state: str, failure_code: str | None) -> Path:
    task_path = TASKS_DIR / f"{task_id}.json"
    task_data = json.loads(task_path.read_text())
    task_data["automation"]["state"] = to_state
    task_data["automation"]["failure_code"] = failure_code
    task_data["automation"]["last_transition_id"] = f"{task_id}#{int(time.time() * 1000)}"
    task_path.write_text(
        json.dumps(task_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return task_path


def run_pilot_command(task_type: str, task_id: str) -> tuple[int, str, str]:
    """Run the ONE fixed, non-interpolated command for a given task_type.

    task_id is passed only as a CLI argument (argparse, not shell
    interpolation) -- this avoids command injection risk regardless of task
    file content. Each task_type maps to exactly one fixed command; there is
    no code path where task-controlled data selects what gets executed.
    """
    if task_type == "pilot_echo":
        cmd = ["/bin/echo", f"PILOT_OK {now()}"]
    elif task_type == "corpus_pilot_echo":
        cmd = ["python3", str(CORPUS_PILOT_DRIVER), "--task-id", task_id]
    else:
        raise RuntimeError(f"run_pilot_command: no dispatch defined for task_type={task_type!r}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


def write_heartbeat(task_id: str, exec_id: str) -> Path:
    """G8: record that this task is actively being processed.

    Written once at PROCESSING start. Real (non-instant) task_types would
    call this periodically during long-running work; pilot_echo completes
    fast enough that one write at start is sufficient to prove the
    mechanism -- the staleness test (G9) instead uses a hand-backdated
    heartbeat file to simulate a crashed worker, since this pilot has no
    task_type that actually runs long enough to go stale for real.
    """
    hb_dir = HEARTBEAT_ROOT / namespace_for_task_id(task_id)
    hb_dir.mkdir(parents=True, exist_ok=True)
    hb_path = hb_dir / f"{task_id}.json"
    hb_path.write_text(
        json.dumps({"task_id": task_id, "exec_id": exec_id, "last_beat": now()}, ensure_ascii=False),
        encoding="utf-8",
    )
    return hb_path


def heartbeat_age_s(task_id: str) -> float | None:
    """Seconds since task_id's last heartbeat, or None if no heartbeat file exists."""
    hb_path = HEARTBEAT_ROOT / namespace_for_task_id(task_id) / f"{task_id}.json"
    if not hb_path.exists():
        return None
    beat = json.loads(hb_path.read_text(encoding="utf-8"))
    last = datetime.strptime(beat["last_beat"], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last).total_seconds()


def dependencies_satisfied(data: dict) -> tuple[bool, list[str]]:
    """G7: a task may only run once every task_id in depends_on is COMPLETED.

    Returns (satisfied, blocking_task_ids). A dependency on a task_id that
    doesn't exist yet, or isn't COMPLETED, blocks -- fail-closed, not
    fail-open, matching this project's existing convention (unknown state
    is never treated as "go ahead").
    """
    blocking = []
    for dep_id in data.get("depends_on") or []:
        dep_path = TASKS_DIR / f"{dep_id}.json"
        if not dep_path.exists():
            blocking.append(dep_id)
            continue
        dep_data = json.loads(dep_path.read_text())
        if (dep_data.get("automation") or {}).get("state") != "COMPLETED":
            blocking.append(dep_id)
    return (len(blocking) == 0, blocking)


def detect_and_recover_stale_workers() -> list[str]:
    """G9: force any PROCESSING task with a stale heartbeat to FAILED.

    This is terminal-state enforcement, not retry -- a stale task becomes
    FAILED with failure_code=STALE_WORKER_TIMEOUT and stops there. Nothing
    in this function (or anywhere else in this file) promotes it onward to
    RETRY_PENDING; that stays human-only per ADR-022 Section 8.
    Returns the list of task_ids that were recovered.
    """
    recovered = []
    for task_path in all_pilot_task_files():
        data = json.loads(task_path.read_text())
        task_id = data["task_id"]
        automation = data.get("automation") or {}
        if automation.get("state") != "PROCESSING":
            continue
        age = heartbeat_age_s(task_id)
        if age is None or age <= STALE_THRESHOLD_S:
            continue
        log(f"  STALE WORKER: {task_id} heartbeat age={age:.1f}s > {STALE_THRESHOLD_S}s -- forcing FAILED")
        payload_signature = read_canonical_payload_signature(task_id)
        write_evidence_entry(
            task_id=task_id, from_state="PROCESSING", to_state="FAILED",
            failure_code="STALE_WORKER_TIMEOUT", payload_signature=payload_signature,
            execution_id=f"{int(time.time() * 1000)}-stale",
            reason=f"pilot_executor: heartbeat stale for {age:.1f}s (threshold {STALE_THRESHOLD_S}s), worker presumed crashed",
        )
        update_task_file(task_id, "FAILED", "STALE_WORKER_TIMEOUT")
        recovered.append(task_id)
    return recovered


def check_isolation_contract(data: dict) -> str | None:
    """Return a failure_code string if the task violates the executor's
    isolation contract, or None if it's cleared to run.

    This check is independent of (and does not trust) the gateway's own
    validation -- the gateway already rejects these at VALIDATION_PASSED
    time, but the executor re-checks so that an isolation violation can
    never depend solely on the gateway having done its job correctly
    (defense in depth, per G3/G8).
    """
    task_id = data.get("task_id", "")
    task_type = data.get("task_type")
    scope = data.get("scope") or {}
    namespace = scope.get("namespace")
    production_mutation = data.get("production_mutation")

    if (task_type, namespace) not in ALLOWED_COMBINATIONS:
        return "TASK_TYPE_NOT_AUTHORIZED"
    expected_prefix = next(
        (p for p, ns in TASK_ID_PREFIX_NAMESPACE.items() if ns == namespace), None
    )
    if not expected_prefix or not task_id.startswith(expected_prefix):
        return "NAMESPACE_VIOLATION"
    if production_mutation is not False:
        return "PRODUCTION_MUTATION_NOT_ALLOWED"
    # Defense in depth (C1 cross-verification, CFI-Pilot-001): the gateway
    # enforces authorized_by_task_order, but until now the executor didn't
    # independently re-check it -- meaning a gateway bypass (as already
    # demonstrated once this session, see 007-BYPASS) would not have been
    # caught here. Same principle as the checks above.
    authorized_by_task_order = data.get("authorized_by_task_order")
    if not authorized_by_task_order or not str(authorized_by_task_order).strip():
        return "MISSING_AUTHORIZATION"
    return None


def process_task(task_path: Path) -> str:
    data = json.loads(task_path.read_text())
    task_id = data["task_id"]
    automation = data.get("automation") or {}

    if automation.get("state") != "VALIDATION_PASSED":
        log(f"  skip {task_id}: state={automation.get('state')} (not VALIDATION_PASSED)")
        return "SKIP"

    satisfied, blocking = dependencies_satisfied(data)
    if not satisfied:
        log(f"  skip {task_id}: waiting on dependencies {blocking}")
        return "SKIP"

    log(f"=== Processing {task_id} ===")
    run_id = int(time.time() * 1000)
    seq = 0

    def next_exec_id() -> str:
        # G6 fix: PROCESSING and its terminal state must NOT share a
        # transition_id -- each transition gets its own unique id within
        # this run, even though both happen inside one process_task() call.
        nonlocal seq
        seq += 1
        return f"{run_id}-{seq}"

    payload_signature = read_canonical_payload_signature(task_id)
    log(f"  propagating canonical payload_signature={payload_signature!r}")

    isolation_failure = check_isolation_contract(data)
    if isolation_failure:
        log(f"  ISOLATION VIOLATION: {isolation_failure} -- refusing to execute")
        write_evidence_entry(
            task_id=task_id, from_state="VALIDATION_PASSED", to_state="FAILED",
            failure_code=isolation_failure, payload_signature=payload_signature,
            execution_id=next_exec_id(),
            reason=f"pilot_executor: isolation contract violation ({isolation_failure}), no subprocess invoked",
        )
        update_task_file(task_id, "FAILED", isolation_failure)
        log(f"  -> task file updated to FAILED ({isolation_failure})")
        return "FAIL"

    processing_exec_id = next_exec_id()
    write_evidence_entry(
        task_id=task_id, from_state="VALIDATION_PASSED", to_state="PROCESSING",
        failure_code=None, payload_signature=payload_signature, execution_id=processing_exec_id,
        reason="pilot_executor: starting isolated pilot processing",
    )
    write_heartbeat(task_id, processing_exec_id)

    exit_code, stdout_text, stderr_text = run_pilot_command(data.get("task_type"), task_id)
    log(f"  exit_code={exit_code} stdout={stdout_text.strip()!r}")
    if stderr_text.strip():
        log(f"  stderr={stderr_text.strip()!r}")

    pilot_evidence_dir = PILOT_EVIDENCE_ROOT / namespace_for_task_id(task_id)
    pilot_evidence_dir.mkdir(parents=True, exist_ok=True)
    (pilot_evidence_dir / f"{task_id}-{processing_exec_id}.stdout.log").write_text(stdout_text, encoding="utf-8")
    (pilot_evidence_dir / f"{task_id}-{processing_exec_id}.stderr.log").write_text(stderr_text, encoding="utf-8")
    (pilot_evidence_dir / f"{task_id}-{processing_exec_id}.exit_code.txt").write_text(str(exit_code), encoding="utf-8")

    if exit_code == 0:
        terminal_state, failure_code = "COMPLETED", None
        reason = "pilot echo command completed successfully"
    else:
        terminal_state, failure_code = "FAILED", "PILOT_EXEC_FAILED"
        reason = f"pilot echo command exit={exit_code}"

    write_evidence_entry(
        task_id=task_id, from_state="PROCESSING", to_state=terminal_state,
        failure_code=failure_code, payload_signature=payload_signature, execution_id=next_exec_id(),
        reason=reason,
    )
    update_task_file(task_id, terminal_state, failure_code)
    log(f"  -> task file updated to {terminal_state}")
    return "PASS" if terminal_state == "COMPLETED" else "FAIL"


def generate_morning_summary() -> Path:
    """G12: human-readable roll-up of every CONTROL-PLANE-PILOT-* task.

    Written fresh each call (not append-only -- this is a report, not
    evidence; the evidence it summarizes stays in .automation/evidence/).
    """
    rows = []
    counts: dict[str, int] = {}
    for task_path in all_pilot_task_files():
        data = json.loads(task_path.read_text())
        automation = data.get("automation") or {}
        state = automation.get("state") or "NO_STATE"
        failure_code = automation.get("failure_code")
        counts[state] = counts.get(state, 0) + 1
        rows.append((data["task_id"], state, failure_code or ""))

    ts = now()
    lines = [
        f"# Night-Shift Morning Summary — {ts}",
        "",
        f"Namespaces: `{', '.join(sorted(set(TASK_ID_PREFIX_NAMESPACE.values())))}` (isolated pilots, no production tasks)",
        "",
        "## Counts",
        "",
    ]
    for state, n in sorted(counts.items()):
        lines.append(f"- {state}: {n}")
    lines += ["", "## Tasks", "", "| task_id | state | failure_code |", "|---|---|---|"]
    for task_id, state, failure_code in rows:
        lines.append(f"| {task_id} | {state} | {failure_code} |")

    out_path = LOG_DIR / f"morning-summary-{ts.replace(':', '').replace('.', '')}.md"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"morning summary written: {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Scan once and exit.")
    parser.add_argument("--morning-summary", action="store_true", help="Generate the morning summary and exit.")
    args = parser.parse_args()

    if args.morning_summary:
        generate_morning_summary()
        return

    if not args.once:
        parser.error("only --once or --morning-summary is supported in this pilot")

    recovered = detect_and_recover_stale_workers()
    if recovered:
        log(f"stale-worker recovery: forced FAILED for {recovered}")

    candidates = all_pilot_task_files()
    log(f"scan: {len(candidates)} candidate task file(s) across prefixes {list(TASK_ID_PREFIX_NAMESPACE)}")
    for task_path in candidates:
        process_task(task_path)


if __name__ == "__main__":
    main()
