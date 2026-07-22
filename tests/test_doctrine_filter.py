"""Unit tests — core/sermon/doctrine_filter.py (ADR-009 §Decision-4).

Guards the three principles ADR-009 fixes as non-negotiable: never
blocks/raises, never scores (no numeric fidelity %), and low-confidence
findings are surfaced rather than hidden or silently suppressed.
"""

import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if "ollama" not in sys.modules:
    _ollama_stub = types.ModuleType("ollama")
    _ollama_stub.generate = lambda *args, **kwargs: {"response": ""}
    sys.modules["ollama"] = _ollama_stub

import json
from unittest.mock import patch

from core.generation import SermonOutline
from core.sermon.doctrine_filter import DoctrineReport, _parse_response, check
from core.sermon.doctrine_vocabulary import BAPTIST_THEME, DOCTRINE_CATEGORY


def _outline() -> SermonOutline:
    return SermonOutline(
        title="로마서 5:1-5 - 고난 중의 소망",
        introduction="서론",
        points=["대지1", "대지2"],
        conclusion="결론",
    )


def _fake_ollama_response(payload: dict) -> dict:
    return {"response": json.dumps(payload, ensure_ascii=False)}


class TestParseResponse:
    def test_clean_json_no_concern(self):
        raw = json.dumps({"has_concern": False, "warnings": [], "flagged_categories": [], "confidence": "high"})
        has_concern, warnings, flagged, confidence = _parse_response(raw)
        assert has_concern is False
        assert warnings == []
        assert confidence == "high"

    def test_json_wrapped_in_extra_text_is_extracted(self):
        raw = 'Sure, here is the result:\n{"has_concern": true, "warnings": ["문제"], "flagged_categories": ["Soteriology"], "confidence": "medium"}\nDone.'
        has_concern, warnings, flagged, confidence = _parse_response(raw)
        assert has_concern is True
        assert warnings == ["문제"]
        assert flagged == ["Soteriology"]

    def test_malformed_json_returns_safe_defaults_not_false_positive(self):
        has_concern, warnings, flagged, confidence = _parse_response("not json at all")
        assert has_concern is False
        assert warnings == []
        assert confidence == "low"  # 파싱 실패 = 확인 불가, "문제 없음" 확정 아님

    def test_flagged_categories_outside_vocabulary_are_dropped(self):
        # 모델이 승인된 어휘 밖의 범주를 지어내면 걸러낸다.
        raw = json.dumps({
            "has_concern": True,
            "warnings": ["경고"],
            "flagged_categories": ["Soteriology", "InventedCategory"],
            "confidence": "high",
        })
        _, _, flagged, _ = _parse_response(raw)
        assert flagged == ["Soteriology"]

    def test_invalid_confidence_value_falls_back_to_low(self):
        raw = json.dumps({"has_concern": False, "warnings": [], "flagged_categories": [], "confidence": "very_sure"})
        _, _, _, confidence = _parse_response(raw)
        assert confidence == "low"


class TestCheckNeverBlocksOrScores:
    def test_ollama_failure_returns_passed_true_not_raise(self):
        with patch("ollama.generate", side_effect=RuntimeError("network down")):
            report = check(_outline())
        assert isinstance(report, DoctrineReport)
        assert report.passed is True  # 실패해도 개요 검토를 막지 않는다
        assert report.error == "network down"

    def test_no_concern_path(self):
        payload = {"has_concern": False, "warnings": [], "flagged_categories": [], "confidence": "high"}
        with patch("ollama.generate", return_value=_fake_ollama_response(payload)):
            report = check(_outline())
        assert report.passed is True
        assert report.warnings == []

    def test_low_confidence_concern_is_prefixed_not_hidden(self):
        payload = {
            "has_concern": True,
            "warnings": ["이 부분이 모호합니다"],
            "flagged_categories": ["Christology"],
            "confidence": "low",
        }
        with patch("ollama.generate", return_value=_fake_ollama_response(payload)):
            report = check(_outline())
        assert report.passed is False
        assert report.confidence == "low"
        assert all("확실하지 않음" in w for w in report.warnings)

    def test_report_never_carries_a_numeric_score_field(self):
        # ADR-009: 점수화 금지 — DoctrineReport에 숫자 신뢰도 필드가 없어야 한다.
        payload = {"has_concern": True, "warnings": ["경고"], "flagged_categories": [], "confidence": "high"}
        with patch("ollama.generate", return_value=_fake_ollama_response(payload)):
            report = check(_outline())
        for f in report.__dataclass_fields__:
            assert f in ("passed", "warnings", "flagged_categories", "confidence", "error")
        assert isinstance(report.confidence, str)  # 백분율 아님


def test_vocabulary_is_closed_and_matches_adr_009():
    assert DOCTRINE_CATEGORY == [
        "Scripture", "Trinity", "Christology", "Anthropology",
        "Soteriology", "Ecclesiology", "Eschatology",
    ]
    assert BAPTIST_THEME == [
        "SolaScriptura", "SolaFide", "SolaGratia", "SolusChristus", "SoliDeoGloria",
        "DivineSovereigntyInSalvation", "ParticularRedemption",
        "BelieversBaptism", "RegenerateChurchMembership", "CovenantTheology1689",
    ]
