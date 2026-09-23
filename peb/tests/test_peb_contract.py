from pathlib import Path
import ast
import json
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from peb.runner import action_signature, resolve_step_action  # noqa: E402

def test_scenario_is_valid():
    path = ROOT / "peb" / "scenarios" / "PEB-SERMON-001.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["id"] == "PEB-SERMON-001"
    assert data["limits"]["max_steps"] == 12
    assert len(data["workflow"]) == 4

def test_peb_runner_has_no_dbma_imports():
    for rel_path in ["peb/runner.py", "peb/llm.py", "peb/peb.py"]:
        path = ROOT / rel_path
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for name in imports:
            assert name != "core" and not name.startswith("core."), name
            assert "qdrant" not in name.lower(), name
            assert "embedding" not in name.lower(), name
            assert "dbma_ui" not in name.lower(), name

def test_peb_does_not_define_pass_fail_judgment():
    text = (ROOT / "peb" / "runner.py").read_text(encoding="utf-8").lower()
    assert "pass/fail" not in text
    assert "pass_fail" not in text

def test_runtime_logs_are_ignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "peb/runs/*.jsonl" in gitignore

def test_run_artifacts_are_per_run_not_accumulated():
    text = (ROOT / "peb" / "peb.py").read_text(encoding="utf-8")
    assert "run_stamp" in text
    assert '{scenario[\'id\']}-{run_stamp}.jsonl' in text

# --- Planner previous-action / repeated-action handling -------------------

_SCENARIO = {"goal": {"statement": "test"}, "workflow": [], "limits": {"max_steps": 5}}

class _StubPlanner:
    """Records the kwargs/args it was called with and returns queued actions."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def next_action(self, scenario, observation, history, blocked_action=None):
        self.calls.append({
            "observation": observation,
            "history": history,
            "blocked_action": blocked_action,
        })
        return self._responses[len(self.calls) - 1]

class _RecordingOllamaCall:
    """Captures the JSON body PEB would send to Ollama, without a live server."""

    def __init__(self):
        self.last_payload: dict | None = None

    def __call__(self, request, timeout=180):
        self.last_payload = json.loads(request.data.decode("utf-8"))

        class _Resp:
            def __enter__(_self):
                return _self
            def __exit__(_self, *exc):
                return False
            def read(_self):
                return json.dumps({
                    "message": {"content": json.dumps({
                        "action": "finish", "reason": "stub",
                    })}
                }).encode("utf-8")
        return _Resp()

def test_previous_action_is_passed_to_planner(monkeypatch):
    """Test A: the planner receives the previous action/history it made."""
    import urllib.request
    from peb.llm import OllamaPlanner

    recorder = _RecordingOllamaCall()
    monkeypatch.setattr(urllib.request, "urlopen", recorder)

    planner = OllamaPlanner("test-model")
    history = [{
        "step": 1,
        "action": {"action": "click", "target": "연구 시작하기"},
        "observation": "landing page",
    }]
    planner.next_action(_SCENARIO, "연구·채팅 화면", history)

    assert recorder.last_payload is not None
    user_message = json.loads(recorder.last_payload["messages"][1]["content"])
    assert user_message["previous_action"] == {"action": "click", "target": "연구 시작하기"}
    assert user_message["interaction_history"] == history

def test_repeated_action_is_not_executed():
    """Test B: identical action+target repeated back-to-back is not run."""
    duplicate = {"action": "click", "target": "연구 시작하기"}
    planner = _StubPlanner([duplicate, duplicate])

    action, should_execute, was_blocked = resolve_step_action(
        planner, _SCENARIO, "same screen", [],
        last_signature=action_signature(duplicate),
    )

    assert was_blocked is True
    assert should_execute is False
    assert action == duplicate

def test_blocked_action_lets_planner_pick_a_different_visible_action():
    """Test C: after a block, the planner can choose a different control."""
    duplicate = {"action": "click", "target": "연구 시작하기"}
    alternative = {"action": "click", "target": "연구·채팅"}
    planner = _StubPlanner([duplicate, alternative])

    action, should_execute, was_blocked = resolve_step_action(
        planner, _SCENARIO, "same screen", [],
        last_signature=action_signature(duplicate),
    )

    assert was_blocked is True
    assert should_execute is True
    assert action == alternative
    # the retry call must carry the rejected action so the planner knows why
    assert planner.calls[1]["blocked_action"] == duplicate
