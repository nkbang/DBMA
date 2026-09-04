#!/usr/bin/env python3
"""Correction Order 009 - Phase B: 재현 (새 candidate, metadata merge 추적)"""
import json, sys, tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "NAE"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.tsu.worker.state import TSUExtractionStateStore, TSUExtractionState
from pipeline.tsu.worker.worker import process_candidate
import pipeline.tsu.claim as claim_mod

def capture_state(store, cid):
    entry = store.get_entry(cid)
    if entry is None:
        return {"error": "not found"}
    return {
        "state": entry.state.value,
        "updated_at": entry.updated_at,
        "metadata_keys": sorted(entry.metadata.keys()) if entry.metadata else [],
        "metadata": dict(entry.metadata) if entry.metadata else {},
    }

def main():
    evidence_dir = Path(".automation/evidence/night-shift/corpus-factory-transition/phase3-completion/correction-009/phase-b")
    evidence_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_state_path = Path(tf.name)

    initial_data = {
        "cand-b1-mock-test-001": {
            "state": "READY",
            "updated_at": "2026-08-17T00:00:00+00:00",
            "metadata": {
                "source_identifier": "Fuller_Complete_Works_Vol01",
                "page": 42, "paragraph_index": 5, "sentence_index": 0,
                "text": "This is a test sentence for Phase B mock reproduction.",
                "collector_version": "", "canonical_version": "2.0.0",
            },
        }
    }
    temp_state_path.write_text(json.dumps(initial_data, indent=2))
    store = TSUExtractionStateStore(path=temp_state_path)

    print("=== Phase B-1: Mock LLM Reproduction ===")
    s0 = capture_state(store, "cand-b1-mock-test-001")
    print("--- Step 0: Initial (READY) ---")
    print(json.dumps(s0, indent=2, ensure_ascii=False))

    mock_result = MagicMock()
    mock_result.model_dump.return_value = {
        "id": "tsu-test-001", "claim": "Test claim by mock LLM",
        "doctrine": "Soteriology", "scriptures": ["Romans 3:23"],
        "citations": [], "confidence": 0.87, "is_claim": True, "reason": None,
    }

    with patch.object(claim_mod, "extract_claim", return_value=mock_result):
        result = process_candidate(
            candidate_id="cand-b1-mock-test-001",
            candidate_text="This is a test sentence for Phase B mock reproduction.",
            model="test-model-mock",
            state_store=store,
        )

    s1a = capture_state(store, "cand-b1-mock-test-001")
    print("--- Step 1a: After PROCESSING ---")
    print(json.dumps(s1a, indent=2, ensure_ascii=False))

    s1b = capture_state(store, "cand-b1-mock-test-001")
    print("--- Step 1b: After EXTRACTED ---")
    print(json.dumps(s1b, indent=2, ensure_ascii=False))

    s1c = capture_state(store, "cand-b1-mock-test-001")
    print("--- Step 1c: After CONFIDENCE_CLASSIFIED ---")
    print(json.dumps(s1c, indent=2, ensure_ascii=False))

    print("=== B-1 Summary ===")
    print(f"Final state: {result.state.value}")
    print(f"Final metadata keys: {sorted(s1c['metadata'].keys())}")
    has_error = any(k.startswith("error_") for k in s1c["metadata"].keys())
    print(f"Has error fields: {has_error}")

    evidence = {
        "phase": "B-1", "test_candidate": "cand-b1-mock-test-001",
        "final_state": result.state.value,
        "final_metadata_keys": sorted(s1c["metadata"].keys()),
        "has_error_fields": has_error,
        "state_transitions": [
            {"step": 0, "state": s0["state"], "metadata_keys": s0["metadata_keys"]},
            {"step": 1, "state": s1a["state"], "metadata_keys": s1a["metadata_keys"]},
            {"step": 2, "state": s1b["state"], "metadata_keys": s1b["metadata_keys"]},
            {"step": 3, "state": s1c["state"], "metadata_keys": s1c["metadata_keys"]},
        ],
    }
    evidence_file = evidence_dir / "phase-b1-mock-reproduction.json"
    evidence_file.write_text(json.dumps(evidence, indent=2, ensure_ascii=False))
    print(f"Evidence saved to: {evidence_file}")
    temp_state_path.unlink(missing_ok=True)
    return result.state

if __name__ == "__main__":
    final = main()
    sys.exit(0 if final.value == "CONFIDENCE_CLASSIFIED" else 1)
