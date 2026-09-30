"""Regression test — ADR-035 §3.1 항목2: 검색 결과 자동 수집(옵트인).

ui/pages/research.py::_maybe_auto_collect_for_sermon_research()이
sermon_research_auto_collect 세션 상태 플래그를 정확히 존중하는지
검증한다. 무거운 Streamlit 런타임/Retrieval Engine 없이, st.* 호출을
경량 레코더로 monkeypatch해 순수 로직만 검사한다
(tests/test_research_saved_sessions_ui.py의 _Recorder 패턴과 동일).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ui.pages.research as mod


class _Recorder:
    def __init__(self):
        self.session_state = {}
        self.toast_calls = []

    def toast(self, msg):
        self.toast_calls.append(msg)


def _fake_results(n: int) -> list[dict]:
    return [
        {
            "tsu_id": f"TSU-{i}",
            "document_id": f"doc{i}",
            "snippet": f"발췌문 {i}",
            "source": f"source{i}.md",
        }
        for i in range(n)
    ]


def test_auto_collect_off_by_default_does_nothing(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(mod, "st", rec)

    mod._maybe_auto_collect_for_sermon_research(_fake_results(5))

    assert "sermon_research_selection" not in rec.session_state
    assert rec.toast_calls == []


def test_auto_collect_on_appends_top_n_only(monkeypatch):
    rec = _Recorder()
    rec.session_state["sermon_research_auto_collect"] = True
    monkeypatch.setattr(mod, "st", rec)

    mod._maybe_auto_collect_for_sermon_research(_fake_results(5))

    selection = rec.session_state["sermon_research_selection"]
    assert len(selection) == mod._AUTO_COLLECT_TOP_N == 3
    assert [item["tsu_id"] for item in selection] == ["TSU-0", "TSU-1", "TSU-2"]
    assert selection[0]["document_id"] == "doc0"
    assert selection[0]["excerpt"] == "발췌문 0"
    assert selection[0]["source_label"] == "source0.md"
    assert rec.toast_calls == ["설교 연구에 상위 3건 자동 반영됨"]


def test_auto_collect_on_with_no_results_is_noop(monkeypatch):
    rec = _Recorder()
    rec.session_state["sermon_research_auto_collect"] = True
    monkeypatch.setattr(mod, "st", rec)

    mod._maybe_auto_collect_for_sermon_research([])

    assert "sermon_research_selection" not in rec.session_state
    assert rec.toast_calls == []


def test_manual_send_button_helper_still_matches_auto_collect_shape(monkeypatch):
    """수동 버튼(_render_send_to_sermon_research_button)과 자동 수집이
    같은 append 헬퍼(_append_search_result_to_sermon_research)를 공유해
    버퍼에 쌓이는 dict 모양이 동일한지 확인 — 허브(sermon_research.py)의
    소비 로직이 두 경로를 구분 없이 처리하기 때문에 모양이 갈리면
    회귀가 된다."""
    rec = _Recorder()
    monkeypatch.setattr(mod, "st", rec)

    result = _fake_results(1)[0]
    mod._append_search_result_to_sermon_research(result)

    selection = rec.session_state["sermon_research_selection"]
    assert len(selection) == 1
    assert set(selection[0].keys()) == {
        "tsu_id", "document_id", "excerpt", "source_label", "added_at",
    }
