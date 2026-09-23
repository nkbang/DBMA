from pathlib import Path
import ast
import yaml

ROOT = Path(__file__).resolve().parents[2]

def test_scenario_is_valid():
    path = ROOT / "peb" / "scenarios" / "PEB-SERMON-001.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["id"] == "PEB-SERMON-001"
    assert data["limits"]["max_steps"] == 12
    assert len(data["workflow"]) == 4

def test_peb_runner_has_no_dbma_imports():
    for path in [ROOT / "peb" / "runner.py", ROOT / "peb" / "llm.py"]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any(name == "core" or name.startswith("core.") for name in imports)

def test_peb_does_not_define_pass_fail_judgment():
    text = (ROOT / "peb" / "runner.py").read_text(encoding="utf-8").lower()
    assert "pass/fail" not in text
    assert "pass_fail" not in text

def test_runtime_logs_are_ignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "peb/runs/*.jsonl" in gitignore
