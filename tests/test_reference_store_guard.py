"""ui/state/reference_store.py — Docker/컨테이너 자동 복구 순서."""
import ui.state.reference_store as rs


def _patch(monkeypatch, *, reachable, daemon_up_after_open, docker="/bin/docker"):
    state = {"reach": reachable, "daemon": not daemon_up_after_open, "calls": []}

    def fake_run(args, timeout):
        state["calls"].append(args[:2] if args[0] != "open" else ["open"])
        if args[1:2] == ["info"]:
            return state["daemon"]
        if args[0] == "open":
            state["daemon"] = True
            return True
        if args[1:2] == ["start"]:
            state["reach"] = True
            return True
        return False

    monkeypatch.setattr(rs, "_run", fake_run)
    monkeypatch.setattr(rs, "is_reachable", lambda timeout=0.7: state["reach"])
    monkeypatch.setattr(rs, "_docker_bin", lambda: docker)
    monkeypatch.setattr(rs, "_wait", lambda pred, seconds, step=3.0: pred())
    monkeypatch.setattr(rs.sys, "platform", "darwin")
    return state


def test_noop_when_reachable(monkeypatch):
    st = _patch(monkeypatch, reachable=True, daemon_up_after_open=False)
    rs._recover()
    assert st["calls"] == []


def test_starts_docker_then_container(monkeypatch):
    st = _patch(monkeypatch, reachable=False, daemon_up_after_open=True)
    rs._recover()
    kinds = [c[0] if c[0] == "open" else c[1] for c in st["calls"]]
    assert kinds == ["info", "open", "info", "start"] and st["reach"]


def test_only_container_start_when_daemon_up(monkeypatch):
    st = _patch(monkeypatch, reachable=False, daemon_up_after_open=False)
    rs._recover()
    assert [c[1] for c in st["calls"] if c[0] != "open"] == ["info", "start"]
    assert all(c[0] != "open" for c in st["calls"])


def test_no_docker_binary_is_silent(monkeypatch):
    st = _patch(monkeypatch, reachable=False, daemon_up_after_open=True, docker=None)
    rs._recover()
    assert st["calls"] == []
