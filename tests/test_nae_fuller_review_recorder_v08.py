"""FU-004 b-1 — 기록 도구 v08 시리즈 확장 회귀 테스트. 사람 판정은 입력 스텁으로만 주입한다."""
from __future__ import annotations

import json

import pytest

from scripts import nae_fuller_review_recorder as rec


def test_batch_id_series():
    assert rec._batch_id("1") == "fuller_v01_batch_0001"
    assert rec._batch_id("1", "v08") == "fuller_v08_rereview_batch_001"
    assert rec._batch_id("fuller_v08_rereview_batch_007") == "fuller_v08_rereview_batch_007"
    assert rec._batch_id("fuller_v01_batch_0003", "v08") == "fuller_v01_batch_0003"


@pytest.fixture
def v08_env(tmp_path, monkeypatch):
    req_dir, dec_dir = tmp_path / "req", tmp_path / "dec"
    req_dir.mkdir()
    monkeypatch.setattr(rec, "REQUESTS_DIR", req_dir)
    monkeypatch.setattr(rec, "DECISIONS_DIR", dec_dir)
    bid = "fuller_v08_rereview_batch_001"
    reqs = [
        {"tsu_id": f"TSU-000000{i}", "claim": f"c{i}", "original_text": f"o{i}", "doctrine": "D",
         "tier": "P0", "triage_flags": ["cue_sample_R"]}
        for i in (1, 2)
    ]
    (req_dir / f"{bid}_requests.json").write_text(json.dumps({"requests": reqs}), encoding="utf-8")
    return bid, dec_dir


def _run(monkeypatch, bid, answers):
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda *_: next(it))
    rec._review_batch(bid, None)


def test_v08_default_questions_and_decisions(v08_env, monkeypatch, capsys):
    bid, dec_dir = v08_env
    # TSU-1: Q1 r, Q2 a, Q3 a, q4 없음, comment 없음, 제안 수락 → REJECTED
    # TSU-2: a a a → APPROVED
    _run(monkeypatch, bid, ["r", "a", "a", "", "왜곡", "", "a", "a", "a", "", "", ""])
    out = capsys.readouterr().out
    assert "tier     : P0" in out and "cue_sample_R" in out
    d = json.loads((dec_dir / f"{bid}_decisions.json").read_text(encoding="utf-8"))["decisions"]
    by = {e["tsu_id"]: e for e in d}
    assert by["TSU-0000001"]["final_decision"] == "REJECTED"
    assert by["TSU-0000001"]["answers"] == {"Q1": "R", "Q2": "A", "Q3": "A"}
    assert by["TSU-0000001"]["comment"] == "왜곡"
    assert by["TSU-0000002"]["final_decision"] == "APPROVED"


def test_v08_resume_skips_decided(v08_env, monkeypatch, capsys):
    bid, dec_dir = v08_env
    # 첫 건만 판정하고 두 번째 카드에서 q로 종료
    _run(monkeypatch, bid, ["a", "a", "a", "", "", "", "q"])
    capsys.readouterr()

    def _eof(*_):
        raise EOFError

    monkeypatch.setattr("builtins.input", _eof)  # 재실행: 입력 없이 대기 건수만 확인
    rec._review_batch(bid, None)
    assert f"{bid}: 2 requests, 1 already decided, 1 to go." in capsys.readouterr().out
    d = json.loads((dec_dir / f"{bid}_decisions.json").read_text(encoding="utf-8"))["decisions"]
    assert [e["tsu_id"] for e in d] == ["TSU-0000001"]
