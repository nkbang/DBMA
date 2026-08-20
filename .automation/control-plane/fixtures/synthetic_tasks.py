"""Synthetic task fixtures for control plane testing.

All tasks are isolated synthetic data - NOT production data.
Used only for unit/integration testing of the control plane.
"""
from __future__ import annotations


def make_synthetic_task(
    task_id: str = "CONTROL-PLANE-SYNTH-001",
    state: str = "IDLE",
    task_type: str = "pilot_echo",
    namespace: str = "control-plane-pilot",
    production_mutation: bool = False,
    **overrides: object,
) -> dict:
    """Create a synthetic test task. All fields are synthetic."""
    base = {
        "schema_version": "1.2.0",
        "task_id": task_id,
        "parent_task_id": "CONTROL-PLANE-SPEC-001",
        "title": f"Synthetic test task: {task_id}",
        "owner": "C1",
        "state": state,
        "phase": "PILOT",
        "requires_human_approval": False,
        "production_mutation": production_mutation,
        "task_type": task_type,
        "scope": {
            "namespace": namespace,
            "allowed_paths": [],
        },
        "authorized_by": "C1",
        "required_evidence": ["gateway_transition", "executor_transition", "stdout", "stderr", "exit_code"],
        "constraints": {
            "max_runtime_s": 30,
            "allow_production_paths": False,
        },
        "evidence": [],
        "audit": {"status": None, "verdict": None, "reviewer": None, "report": None},
        "notes": ["synthetic test fixture"],
        "automation": {
            "state": state,
            "failure_code": None,
            "last_transition_id": None,
            "processing_input": {},
        },
        "failure_codes": [
            "VALIDATION_FAILED", "FILE_ERROR", "PARSE_ERROR",
            "TASK_ID_PAYLOAD_CONFLICT", "TASK_TYPE_NOT_AUTHORIZED",
            "NAMESPACE_VIOLATION", "PRODUCTION_MUTATION_NOT_ALLOWED",
            "PILOT_EXEC_FAILED", "INTERNAL_STATE_MAPPING_ERROR",
        ],
    }
    base.update(overrides)
    return base


# Pre-built synthetic tasks for testing
SYNTHETIC_HAPPY_PATH = make_synthetic_task(
    task_id="CONTROL-PLANE-SYNTH-001",
    state="IDLE",
    title="Happy path: valid task, completes successfully",
)

SYNTHETIC_MISSING_FIELDS = make_synthetic_task(
    task_id="CONTROL-PLANE-SYNTH-002",
    state="IDLE",
    title="Missing required fields test",
)
del SYNTHETIC_MISSING_FIELDS["scope"]
del SYNTHETIC_MISSING_FIELDS["constraints"]

SYNTHETIC_INVALID_STATE = make_synthetic_task(
    task_id="CONTROL-PLANE-SYNTH-003",
    state="INVALID_STATE_XYZ",
    title="Invalid state test",
)

SYNTHETIC_PROD_MUTATION = make_synthetic_task(
    task_id="CONTROL-PLANE-SYNTH-004",
    state="IDLE",
    production_mutation=True,
    title="Production mutation prohibited test",
)

SYNTHETIC_BAD_NAMESPACE = make_synthetic_task(
    task_id="CONTROL-PLANE-SYNTH-005",
    state="IDLE",
    namespace="production-corpus",
    title="Bad namespace test",
)

SYNTHETIC_BAD_TASK_TYPE = make_synthetic_task(
    task_id="CONTROL-PLANE-SYNTH-006",
    state="IDLE",
    task_type="production_register",
    title="Disallowed task type test",
)

SYNTHETIC_TERMINAL_FAILED = make_synthetic_task(
    task_id="CONTROL-PLANE-SYNTH-007",
    state="FAILED",
    title="Terminal state: FAILED - should not be processable",
)

SYNTHETIC_TERMINAL_COMPLETED = make_synthetic_task(
    task_id="CONTROL-PLANE-SYNTH-008",
    state="COMPLETED",
    title="Terminal state: COMPLETED - should not be processable",
)

SYNTHETIC_VALIDATION_PASSED = make_synthetic_task(
    task_id="CONTROL-PLANE-SYNTH-009",
    state="VALIDATION_PASSED",
    title="Validation passed - ready for processing",
)

SYNTHETIC_DEPENDENCY_CHAIN = [
    make_synthetic_task(task_id=f"CONTROL-PLANE-SYNTH-DEP-{i}", state="IDLE")
    for i in range(1, 4)
]
SYNTHETIC_DEPENDENCY_CHAIN[0]["automation"]["state"] = "COMPLETED"
SYNTHETIC_DEPENDENCY_CHAIN[1]["parent_task_id"] = "CONTROL-PLANE-SYNTH-DEP-1"
SYNTHETIC_DEPENDENCY_CHAIN[2]["parent_task_id"] = "CONTROL-PLANE-SYNTH-DEP-2"
