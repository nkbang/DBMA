"""Comprehensive tests for all control plane modules."""
from __future__ import annotations

import copy, json, os, sys, tempfile, time
from pathlib import Path
from unittest import TestCase, main as unittest_main

CP_PATH = Path(__file__).parent.parent.parent / ".automation" / "control-plane"
sys.path.insert(0, str(CP_PATH.resolve()))

from fixtures.synthetic_tasks import (
    SYNTHETIC_HAPPY_PATH, SYNTHETIC_MISSING_FIELDS,
    SYNTHETIC_INVALID_STATE, SYNTHETIC_PROD_MUTATION,
    SYNTHETIC_BAD_NAMESPACE, SYNTHETIC_BAD_TASK_TYPE,
    SYNTHETIC_TERMINAL_FAILED, SYNTHETIC_TERMINAL_COMPLETED,
    SYNTHETIC_VALIDATION_PASSED, SYNTHETIC_DEPENDENCY_CHAIN,
)
from task_contract import (
    TaskState, TaskQueue, enforce_transition,
    generate_transition_id, compute_payload_signature, make_evidence_entry,
    validate_task_schema,
)
from dependency_graph import DependencyGraph
from n8n_gateway import N8NGateway, GatewayError
from executor_dispatch import ExecutorDispatch, ExecutorPolicy
from policy_enforcement import PolicyEnforcement, PolicyViolation
from heartbeat import HeartbeatMonitor
from terminal_state import TerminalStateEnforcer, TerminalStateError
from evidence_collector import EvidenceCollector
from duplicate_protection import DuplicateProtection, DuplicateError, ConflictError
from failure_handling import FailureHandler
from morning_summary import MorningSummary
from control_plane import ControlPlane


class TestTaskState(TestCase):
    def test_all_states_exist(self):
        states = list(TaskState)
        expected_names = ["IDLE", "RECEIVED", "VALIDATION_PASSED",
                         "PENDING_APPROVAL", "QUEUED", "PROCESSING",
                         "COMPLETED", "FAILED", "IN_REVIEW"]
        self.assertEqual(len(states), 9)
        actual_names = [s.name for s in states]
        for name in expected_names:
            self.assertIn(name, actual_names)

    def test_legal_transitions(self):
        legal = [
            (TaskState.IDLE, TaskState.RECEIVED),
            (TaskState.RECEIVED, TaskState.VALIDATION_PASSED),
            (TaskState.RECEIVED, TaskState.FAILED),
            (TaskState.VALIDATION_PASSED, TaskState.PROCESSING),
            (TaskState.VALIDATION_PASSED, TaskState.QUEUED),
            (TaskState.QUEUED, TaskState.PROCESSING),
            (TaskState.PROCESSING, TaskState.COMPLETED),
            (TaskState.PROCESSING, TaskState.FAILED),
        ]
        for frm, to in legal:
            ok, msg = enforce_transition(frm, to)
            self.assertTrue(ok, f"{frm.name} -> {to.name}: {msg}")

    def test_illegal_transitions(self):
        illegal = [
            (TaskState.COMPLETED, TaskState.PROCESSING),
            (TaskState.FAILED, TaskState.PROCESSING),
            (TaskState.IDLE, TaskState.COMPLETED),
            (TaskState.IDLE, TaskState.FAILED),
            (TaskState.COMPLETED, TaskState.FAILED),
        ]
        for frm, to in illegal:
            ok, msg = enforce_transition(frm, to)
            self.assertFalse(ok, f"{frm.name} -> {to.name} should be illegal")

    def test_terminal_states(self):
        self.assertTrue(TaskState.is_terminal(TaskState.COMPLETED))
        self.assertTrue(TaskState.is_terminal(TaskState.FAILED))
        self.assertFalse(TaskState.is_terminal(TaskState.IDLE))
        self.assertFalse(TaskState.is_terminal(TaskState.PROCESSING))


class TestTaskQueue(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.queue = TaskQueue(Path(self.tmp))

    def _make_task(self, task_id):
        return {
            "task_id": task_id, "state": "IDLE",
            "schema_version": "1.0", "title": "Test", "owner": "test",
            "phase": "PILOT", "task_type": "pilot_echo",
            "scope": {"namespace": "control-plane-pilot"},
            "authorized_by": "test", "production_mutation": False,
            "constraints": {"max_runtime_s": 300},
            "automation": {"enabled": True},
        }

    def test_add_and_dequeue(self):
        task = self._make_task("Q-001")
        ok, msg = self.queue.add(task)
        self.assertTrue(ok)
        result = self.queue.dequeue()
        self.assertIsNotNone(result)
        self.assertEqual(result["task_id"], "Q-001")

    def test_fifo_order(self):
        for i in range(5):
            task = self._make_task(f"Q-{i}")
            ok, msg = self.queue.add(task)
            self.assertTrue(ok, f"add Q-{i}: {msg}")
        ids = []
        while True:
            t = self.queue.dequeue()
            if t is None:
                break
            ids.append(t["task_id"])
        self.assertEqual(ids, ["Q-0", "Q-1", "Q-2", "Q-3", "Q-4"])

    def test_empty_queue(self):
        result = self.queue.dequeue()
        self.assertIsNone(result)

    def test_persistence(self):
        task = self._make_task("PERSIST-001")
        self.queue.add(task)
        # Verify data is persisted to disk as JSON file
        ev_file = Path(self.tmp) / "PERSIST-001.json"
        self.assertTrue(ev_file.exists())
        content = json.loads(ev_file.read_text())
        self.assertEqual(content["task_id"], "PERSIST-001")


class TestTaskContractHelpers(TestCase):
    def test_validate_task_schema_valid(self):
        ok, errors = validate_task_schema(SYNTHETIC_HAPPY_PATH)
        self.assertTrue(ok, f"errors: {errors}")

    def test_validate_task_schema_missing_fields(self):
        ok, errors = validate_task_schema(SYNTHETIC_MISSING_FIELDS)
        self.assertFalse(ok)
        self.assertTrue(len(errors) > 0)

    def test_validate_task_schema_invalid_state(self):
        ok, errors = validate_task_schema(SYNTHETIC_INVALID_STATE)
        self.assertFalse(ok)

    def test_payload_signature_propagates_from_evidence(self):
        # compute_payload_signature does NOT recompute from the task dict --
        # it reads back whatever the gateway already wrote as the LAST
        # evidence entry for that task_id. Two reads of the same
        # already-written entry must be identical (propagation, not
        # independent computation).
        tmp = Path(tempfile.mkdtemp())
        ev_path = tmp / "SIG-TEST-001.jsonl"
        ev_path.write_text(json.dumps({
            "transition_id": "SIG-TEST-001#1", "task_id": "SIG-TEST-001",
            "from": "RECEIVED", "to": "VALIDATION_PASSED", "failure_code": None,
            "actor": "test_gateway_stub", "payload_signature": '{"task_id":"SIG-TEST-001"}',
            "execution_id": "1", "timestamp": "2026-08-17T00:00:00.000Z", "reason": "test fixture",
        }) + "\n", encoding="utf-8")
        sig1 = compute_payload_signature("SIG-TEST-001", tmp)
        sig2 = compute_payload_signature("SIG-TEST-001", tmp)
        self.assertEqual(sig1, sig2)
        self.assertEqual(sig1, '{"task_id":"SIG-TEST-001"}')

    def test_payload_signature_raises_without_evidence(self):
        # Fail-closed: no prior gateway evidence entry means there is
        # nothing canonical to propagate -- this must raise, not silently
        # fall back to an independently computed value.
        tmp = Path(tempfile.mkdtemp())
        with self.assertRaises(RuntimeError):
            compute_payload_signature("NO-SUCH-TASK", tmp)

    def test_generate_transition_id(self):
        tid = generate_transition_id("T-001", "42")
        self.assertIn("T-001", tid)
        self.assertIn("42", tid)

    def test_evidence_entry_creation(self):
        entry = make_evidence_entry(
            task_id="E-001", from_state="IDLE", to_state="COMPLETED",
            failure_code=None, payload_signature="sig123",
            execution_id="exec-1", reason="success",
        )
        self.assertEqual(entry["task_id"], "E-001")
        self.assertEqual(entry["to"], "COMPLETED")
        self.assertIsNone(entry["failure_code"])

    def test_evidence_entry_failure(self):
        entry = make_evidence_entry(
            task_id="E-002", from_state="PROCESSING", to_state="FAILED",
            failure_code="EXECUTION_ERROR", payload_signature="sig456",
            execution_id="exec-2", reason="crash",
        )
        self.assertEqual(entry["failure_code"], "EXECUTION_ERROR")


class TestDependencyGraph(TestCase):
    def test_add_and_update(self):
        g = DependencyGraph()
        g.add_task("A")
        g.update_state("A", "COMPLETED")
        ready = g.get_ready_tasks()
        self.assertIn("A", ready)

    def test_dependency_chain(self):
        g = DependencyGraph()
        g.add_task("A")
        g.add_task("B", dependencies=["A"])
        # B should NOT be ready yet (A is not COMPLETED)
        ready = g.get_ready_tasks()
        self.assertNotIn("B", ready)
        # After A completes, B becomes ready
        g.update_state("A", "COMPLETED")
        ready = g.get_ready_tasks()
        self.assertIn("B", ready)

    def test_cycle_detection(self):
        g = DependencyGraph()
        g.add_task("A")
        g.add_task("B")
        g.add_task("A", dependencies=["B"])  # A depends on B
        g.add_task("B", dependencies=["A"])  # B depends on A (overwrite)
        cycles = g.detect_cycles()
        self.assertTrue(len(cycles) > 0)

    def test_no_cycle(self):
        g = DependencyGraph()
        g.add_task("A")
        g.add_task("B", dependencies=["A"])
        result = g.topological_sort()
        self.assertIsNotNone(result)
        a_idx = result.index("A")
        b_idx = result.index("B")
        self.assertLess(a_idx, b_idx)


class TestN8NGateway(TestCase):
    def test_post_task_returns_http_code(self):
        gw = N8NGateway()
        task = {"task_id": "GW-001", "state": "IDLE"}
        code, resp = gw.post_task(task)
        self.assertIsInstance(code, int)
        self.assertIsInstance(resp, dict)

    def test_verify_response_valid(self):
        gw = N8NGateway()
        task = {"task_id": "GW-002", "state": "IDLE"}
        code, resp = gw.post_task(task)
        ok, errors = gw.verify_response(resp, "GW-002")
        self.assertTrue(ok)

    def test_verify_response_invalid(self):
        gw = N8NGateway()
        ok, errors = gw.verify_response({"invalid": True}, "GW-003")
        self.assertFalse(ok)
        self.assertTrue(len(errors) > 0)

    def test_http_error_raises(self):
        import unittest.mock as mock
        gw = N8NGateway()
        # Mock urllib.request.urlopen to raise URLError
        with mock.patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
            task = {"task_id": "GW-ERR", "state": "IDLE"}
            with self.assertRaises(Exception):
                gw.post_task(task)


class TestExecutorDispatch(TestCase):
    def test_dispatch_pilot_echo(self):
        ex = ExecutorDispatch(dry_run=True)
        task = dict(SYNTHETIC_HAPPY_PATH)
        task["task_type"] = "pilot_echo"
        ok, msg = ex.dispatch(task)
        self.assertTrue(ok)

    def test_dispatch_disallowed_type(self):
        ex = ExecutorDispatch(dry_run=True)
        task = dict(SYNTHETIC_HAPPY_PATH)
        task["task_type"] = "production_register"
        ok, msg = ex.dispatch(task)
        self.assertFalse(ok)


class TestPolicyEnforcement(TestCase):
    def test_isolation_policy(self):
        policy = PolicyEnforcement(strict=True)
        task = copy.deepcopy(SYNTHETIC_HAPPY_PATH)
        task["task_type"] = "production_register"
        ok, violations = policy.check_all(task)
        self.assertFalse(ok)

    def test_namespace_policy(self):
        policy = PolicyEnforcement(strict=True)
        task = copy.deepcopy(SYNTHETIC_HAPPY_PATH)
        task["scope"]["namespace"] = "production-corpus"
        ok, violations = policy.check_all(task)
        self.assertFalse(ok)

    def test_production_mutation_policy(self):
        policy = PolicyEnforcement(strict=True)
        task = copy.deepcopy(SYNTHETIC_PROD_MUTATION)
        ok, violations = policy.check_all(task)
        self.assertFalse(ok)

    def test_valid_task_passes_policy(self):
        policy = PolicyEnforcement(strict=True)
        ok, violations = policy.check_all(SYNTHETIC_HAPPY_PATH)
        self.assertTrue(ok)


class TestHeartbeatMonitor(TestCase):
    def test_register_and_detect_stale(self):
        hb = HeartbeatMonitor(default_interval_s=0.1)
        hb.register_worker("W-001")
        time.sleep(0.3)
        stale = hb.detect_stale_workers()
        self.assertIn("W-001", stale)

    def test_active_worker_not_stale(self):
        hb = HeartbeatMonitor(default_interval_s=1.0)
        hb.register_worker("W-ACTIVE")
        time.sleep(0.2)
        hb.record_heartbeat("W-ACTIVE")
        stale = hb.detect_stale_workers()
        self.assertNotIn("W-ACTIVE", stale)

    def test_default_interval(self):
        hb = HeartbeatMonitor(default_interval_s=60.0)
        hb.register_worker("W-DEFAULT")
        time.sleep(0.1)
        stale = hb.detect_stale_workers()
        self.assertNotIn("W-DEFAULT", stale)


class TestTerminalStateEnforcer(TestCase):
    def test_terminal_failed_blocked(self):
        enforcer = TerminalStateEnforcer()
        with self.assertRaises(TerminalStateError):
            enforcer.enforce("T-001", "FAILED", "PROCESSING")

    def test_terminal_completed_blocked(self):
        enforcer = TerminalStateEnforcer()
        with self.assertRaises(TerminalStateError):
            enforcer.enforce("T-002", "COMPLETED", "PROCESSING")

    def test_legal_transition_allowed(self):
        enforcer = TerminalStateEnforcer()
        ok, msg = enforcer.enforce("T-003", "IDLE", "VALIDATION_PASSED")
        self.assertTrue(ok)

    def test_terminal_log_records_violations(self):
        enforcer = TerminalStateEnforcer()
        with self.assertRaises(TerminalStateError):
            enforcer.enforce("T-004", "FAILED", "PROCESSING")
        self.assertTrue(len(enforcer.terminal_log) > 0)


class TestEvidenceCollector(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.collector = EvidenceCollector(Path(self.tmp))

    def test_collect_and_retrieve(self):
        entry = make_evidence_entry(
            task_id="EV-001", from_state="IDLE", to_state="COMPLETED",
            failure_code=None, payload_signature="sig1",
            execution_id="exec-1", reason="success",
        )
        ok, msg = self.collector.collect_entry(entry)
        self.assertTrue(ok)
        entries = self.collector.get_entries("EV-001")
        self.assertTrue(len(entries) > 0)

    def test_jsonl_persistence(self):
        entry = make_evidence_entry(
            task_id="EV-PERSIST", from_state="IDLE", to_state="COMPLETED",
            failure_code=None, payload_signature="sig2",
            execution_id="exec-2", reason="persist test",
        )
        self.collector.collect_entry(entry)
        # Verify file exists on disk
        ev_file = Path(self.tmp) / "EV-PERSIST.jsonl"
        self.assertTrue(ev_file.exists())
        content = ev_file.read_text()
        self.assertIn("EV-PERSIST", content)

    def test_completeness_check(self):
        entry = make_evidence_entry(
            task_id="EV-COMP", from_state="IDLE", to_state="COMPLETED",
            failure_code=None, payload_signature="sig3",
            execution_id="exec-3", reason="completeness test",
        )
        self.collector.collect_entry(entry)
        ok, missing = self.collector.verify_completeness("EV-COMP", [("IDLE", "COMPLETED")])
        self.assertTrue(ok)

    def test_missing_evidence_fields(self):
        entry = make_evidence_entry(
            task_id="EV-MISS", from_state="IDLE", to_state="COMPLETED",
            failure_code=None, payload_signature="sig4",
            execution_id="exec-4", reason="missing fields",
        )
        entry["reason"] = None
        ok, msg = self.collector.collect_entry(entry)
        self.assertTrue(ok)  # collect_entry only checks transition_id, task_id, from, to
        ok2, missing = self.collector.verify_completeness("EV-MISS", [("IDLE", "COMPLETED")])
        self.assertTrue(ok2)


class TestDuplicateProtection(TestCase):
    def test_duplicate_detection(self):
        dp = DuplicateProtection()
        ok1, _ = dp.register_submission("DUP-001", "t1", "sig1", "IDLE")
        self.assertTrue(ok1)
        ok2, msg = dp.register_submission("DUP-001", "t2", "sig2", "IDLE")
        self.assertFalse(ok2)

    def test_payload_mismatch(self):
        dp = DuplicateProtection()
        dp.register_submission("PM-001", "t1", "sig_original", "IDLE")
        ok, msg = dp.check_payload_integrity("PM-001", "sig_different")
        self.assertFalse(ok)

    def test_state_conflict(self):
        dp = DuplicateProtection()
        dp.register_submission("SC-001", "t1", "sig1", "IDLE")
        ok, msg = dp.check_state_conflict("SC-001", "IDLE")
        self.assertFalse(ok)

    def test_all_checks_pass(self):
        dp = DuplicateProtection()
        ok, issues = dp.check_all("NEW-001", "sig1", "IDLE")
        self.assertTrue(ok)
        self.assertEqual(len(issues), 0)


class TestFailureHandler(TestCase):
    def test_handle_failure_routes_to_review(self):
        fh = FailureHandler()
        task = {"task_id": "FAIL-001", "state": "IDLE"}
        ok, msg = fh.handle_failure(
            task_id="FAIL-001", failure_code="EXECUTION_ERROR",
            task_data=task, reason="test failure",
        )
        self.assertTrue(ok)
        self.assertIn("review queue", msg.lower())

    def test_failure_count(self):
        fh = FailureHandler()
        fh.handle_failure("F-001", "CODE_A", reason="r1")
        fh.handle_failure("F-002", "CODE_B", reason="r2")
        self.assertEqual(fh.failure_count, 2)

    def test_review_queue_files(self):
        fh = FailureHandler()
        fh.handle_failure("FQ-001", "CODE_X", task_data={"task_id": "FQ-001"})
        files = fh.get_review_queue_files()
        self.assertTrue(len(files) > 0)


class TestMorningSummary(TestCase):
    def test_generate_summary(self):
        ms = MorningSummary()
        summary = ms.generate(
            total_tasks=10, completed=7, failed=3,
            review_queue_count=2, stale_workers=["W-1"],
            policy_violations=[{"detail": "test"}],
            execution_times=[1.0, 2.0, 3.0],
        )
        self.assertEqual(summary["summary"]["total_tasks_processed"], 10)
        self.assertEqual(summary["summary"]["completed"], 7)
        self.assertEqual(summary["review_queue"]["count"], 2)

    def test_format_text(self):
        ms = MorningSummary()
        ms.generate(total_tasks=5, completed=3, failed=2)
        text = ms.format_text()
        self.assertIn("MORNING SUMMARY", text)
        self.assertIn("Total tasks processed: 5", text)


class TestControlPlaneOrchestrator(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cp = ControlPlane(
            dry_run=True,
            evidence_dir=Path(self.tmp) / "evidence",
            review_queue_dir=Path(self.tmp) / "review",
            queue_dir=Path(self.tmp) / "queue",
        )

    def test_submit_valid_task(self):
        ok, msg = self.cp.submit_task(SYNTHETIC_HAPPY_PATH)
        self.assertTrue(ok)

    def test_submit_invalid_state(self):
        ok, msg = self.cp.submit_task(SYNTHETIC_INVALID_STATE)
        self.assertFalse(ok)

    def test_submit_production_mutation(self):
        ok, msg = self.cp.submit_task(SYNTHETIC_PROD_MUTATION)
        self.assertFalse(ok)

    def test_submit_bad_namespace(self):
        task = copy.deepcopy(SYNTHETIC_BAD_NAMESPACE)
        ok, msg = self.cp.submit_task(task)
        self.assertFalse(ok)

    def test_submit_bad_task_type(self):
        task = copy.deepcopy(SYNTHETIC_BAD_TASK_TYPE)
        ok, msg = self.cp.submit_task(task)
        self.assertFalse(ok)

    def test_process_next_empty_queue(self):
        result = self.cp.process_next()
        self.assertEqual(result["status"], "EMPTY")

    def test_full_pipeline(self):
        ok, msg = self.cp.submit_task(SYNTHETIC_HAPPY_PATH)
        self.assertTrue(ok)
        result = self.cp.process_next()
        self.assertEqual(result["status"], "COMPLETED")
        self.assertIn("evidence_entry", result)

    def test_terminal_state_blocked(self):
        self.cp.submit_task(SYNTHETIC_TERMINAL_FAILED)
        result = self.cp.process_next()
        self.assertIn(result["status"], ["BLOCKED", "TERMINAL_ERROR"])

    def test_duplicate_prevention(self):
        ok1, _ = self.cp.submit_task(SYNTHETIC_HAPPY_PATH)
        self.assertTrue(ok1)
        ok2, msg = self.cp.submit_task(SYNTHETIC_HAPPY_PATH)
        self.assertFalse(ok2)

    def test_morning_summary(self):
        self.cp.submit_task(SYNTHETIC_HAPPY_PATH)
        self.cp.process_next()
        summary = self.cp.generate_morning_summary()
        self.assertEqual(summary["summary"]["total_tasks_processed"], 1)
        self.assertEqual(summary["summary"]["completed"], 1)

    def test_execution_log(self):
        self.cp.submit_task(SYNTHETIC_HAPPY_PATH)
        self.cp.process_next()
        log = self.cp.execution_log
        self.assertTrue(len(log) > 0)


if __name__ == "__main__":
    unittest_main(verbosity=2)
