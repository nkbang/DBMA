"""NAE Autonomous Night-Shift Control Plane.

Isolated control-plane layer for the existing n8n-based night-shift workflow.
Does NOT modify production code, corpus, or approved workflows.

Modules:
    task_contract   — Task Queue contract (schema validation, state machine)
    dependency_graph — Task dependency handling (DAG resolution)
    n8n_gateway      — n8n gateway/control-plane integration
    executor_dispatch — Host executor dispatch contract
    policy_enforcement — Executor policy enforcement
    heartbeat        — Heartbeat + stale-worker detection
    terminal_state   — Terminal-state enforcement
    evidence_collector — Evidence collection
    duplicate_protection — Duplicate/conflict protection
    failure_handling  — Safe failure handling
    morning_summary  — Morning summary generation
    control_plane    — Orchestrator (all modules integrated)
"""
