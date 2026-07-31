"""Round-trip tests for ui/pages/chat.py's disk persistence helpers
(fix for chat_messages resetting on browser refresh, 2026-07-30).

Only exercises the pure serialize/deserialize functions - no Streamlit
session_state involved, so no Streamlit test harness needed.
"""

from core.claim_guard import ClaimGuardResult, RiskLevel
from core.retrieval import RankedCandidate
from ui.pages.chat import _serialize_messages, _deserialize_messages


def test_round_trip_plain_user_message():
    messages = [{"role": "user", "content": "질문입니다"}]
    restored = _deserialize_messages(_serialize_messages(messages))
    assert restored == messages


def test_round_trip_assistant_message_with_sources():
    candidate = RankedCandidate(
        tsu_id="tsu-1",
        content="본문 내용",
        metadata={"source_file": "gen.md"},
        vector_score=0.5,
        bm25_score=0.4,
        theological_score=0.3,
        passage_score=0.2,
        final_score=0.9,
        explanation="설명",
    )
    messages = [{
        "role": "assistant",
        "content": "답변",
        "sources": [candidate],
        "error": None,
        "low_confidence": False,
        "claim_guard_result": None,
    }]
    restored = _deserialize_messages(_serialize_messages(messages))
    assert restored[0]["content"] == "답변"
    assert len(restored[0]["sources"]) == 1
    assert isinstance(restored[0]["sources"][0], RankedCandidate)
    assert restored[0]["sources"][0].tsu_id == "tsu-1"


def test_round_trip_claim_guard_result():
    result = ClaimGuardResult(
        risk_level=RiskLevel.HIGH,
        matched_terms=["최초"],
        absolute_claim_blocked=True,
    )
    messages = [{
        "role": "assistant",
        "content": "답변",
        "claim_guard_result": result,
    }]
    restored = _deserialize_messages(_serialize_messages(messages))
    cg = restored[0]["claim_guard_result"]
    assert isinstance(cg, ClaimGuardResult)
    assert cg.risk_level == RiskLevel.HIGH
    assert cg.absolute_claim_blocked is True


def test_deserialize_corrupted_source_is_skipped_not_raised():
    raw = [{
        "role": "assistant",
        "content": "답변",
        "sources": [{"unexpected_field": "broken"}],
    }]
    restored = _deserialize_messages(raw)
    assert restored[0]["sources"] == []


def test_deserialize_corrupted_claim_guard_is_none_not_raised():
    raw = [{
        "role": "assistant",
        "content": "답변",
        "claim_guard_result": {"risk_level": "not-a-real-level"},
    }]
    restored = _deserialize_messages(raw)
    assert restored[0]["claim_guard_result"] is None
