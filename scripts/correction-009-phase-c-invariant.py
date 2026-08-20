#!/usr/bin/env python3
"""Correction Order 009 - Phase C: Invariant 검증

Invariant: READY -> PROCESSING -> (EXTRACTED | FAILED+error record)

Phase C 요구:
6. 정상적인 worker invocation이 끝났는데 PROCESSING에 그대로 남는 상태가
   invariant 위반임을 증명. FAILED 경로도 검증.
"""
import json, sys, tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "NAE"))

from pipeline.tsu.worker.state import TSUExtractionStateStore, TSUExtractionState
from pipeline.tsu.worker.worker import process_candidate
import pipeline.tsu.claim as claim_mod

def capture_state(store, cid):
    entry = store.get_entry(cid)
    if entry is None:
        return {"error": "not found"}
    return {
        "state": entry.state.value,
        "metadata_keys": sorted(entry.metadata.keys()) if entry.metadata else [],
        "metadata": dict(entry.metadata) if entry.metadata else {},
    }

def main():
    evidence_dir = Path(".automation/evidence/night-shift/corpus-factory-transition/phase3-completion/correction-009/phase-c")
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # --- Test C-1: FAILED path (LLM exception) ---
    print("=== Phase C-1: FAILED Path Invariant ===")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_state_path = Path(tf.name)

    initial_data = {
        "cand-c1-fail-test-001": {
            "state": "READY",
            "updated_at": "2026-08-17T05:00:00+00:00",
            "metadata": {
                "source_identifier": "Fuller_Complete_Works_Vol01",
                "page": 997, "paragraph_index": 97, "sentence_index": 0,
                "text": "This text will trigger an LLM error.",
                "collector_version": "", "canonical_version": "2.0.0",
            },
        }
    }
    temp_state_path.write_text(json.dumps(initial_data, indent=2))
    store = TSUExtractionStateStore(path=temp_state_path)

    s0 = capture_state(store, "cand-c1-fail-test-001")
    print(f"Step 0 (READY): state={s0['state']}, keys={s0['metadata_keys']}")

    # Patch LLM to raise an exception
    with patch.object(claim_mod, "extract_claim", side_effect=RuntimeError("Simulated LLM connection timeout")):
        result = process_candidate(
            candidate_id="cand-c1-fail-test-001",
            candidate_text="This text will trigger an LLM error.",
            model="test-model-fail",
            state_store=store,
        )

    s1 = capture_state(store, "cand-c1-fail-test-001")
    print(f"Step 1 (after fail): state={s1['state']}, keys={s1['metadata_keys']}")
    print(f"Result: state={result.state.value}, error_type={result.error_type}, error_message={result.error_message}")

    # Verify invariant
    invariant_holds = (
        result.state == TSUExtractionState.FAILED
        and s1['state'] == 'FAILED'
        and 'error_type' in s1['metadata']
        and 'error_message' in s1['metadata']
    )
    print(f"Invariant holds (READY->PROCESSING->FAILED+error): {invariant_holds}")

    # --- Test C-2: Verify no stuck PROCESSING ---
    print("\n=== Phase C-2: No Stuck PROCESSING ===")
    all_states = store.summary()
    has_stuck = all_states.get('PROCESSING', 0) > 0
    print(f"Queue after FAILED test: {all_states}")
    print(f"Has stuck PROCESSING: {has_stuck}")

    # --- Test C-3: retry-failed path ---
    print("\n=== Phase C-3: retry-failed Path ===")
    from pipeline.tsu.worker.worker import retry_failed, get_queue_depth
    ok, msg = retry_failed("cand-c1-fail-test-001", state_store=store)
    s2 = capture_state(store, "cand-c1-fail-test-001")
    print(f"retry-failed: success={ok}, msg={msg}")
    print(f"After retry: state={s2['state']}, keys={s2['metadata_keys']}")
    
    # Check if error fields are still in metadata after retry
    has_error_after_retry = any(k.startswith('error_') for k in s2['metadata_keys'])
    print(f"Error fields remain after retry: {has_error_after_retry}")
    
    queue_after = get_queue_depth(store)
    print(f"Queue after retry: {queue_after}")

    # Save evidence
    evidence = {
        "phase": "C",
        "c1_failed_path": {
            "test_candidate": "cand-c1-fail-test-001",
            "initial_state": s0['state'],
            "final_state": s1['state'],
            "result_state": result.state.value,
            "error_type": result.error_type,
            "error_message": result.error_message,
            "has_error_in_metadata": 'error_type' in s1['metadata'] and 'error_message' in s1['metadata'],
            "invariant_holds": invariant_holds,
        },
        "c2_no_stuck": {
            "queue_after_test": all_states,
            "has_stuck_processing": has_stuck,
        },
        "c3_retry_failed": {
            "retry_success": ok,
            "retry_msg": msg,
            "state_after_retry": s2['state'],
            "error_fields_remain": has_error_after_retry,
            "queue_after_retry": queue_after,
        },
    }
    evidence_file = evidence_dir / "phase-c-invariant.json"
    evidence_file.write_text(json.dumps(evidence, indent=2, ensure_ascii=False))
    print(f"\nEvidence saved to: {evidence_file}")
    temp_state_path.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
