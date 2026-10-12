"""PR-4: scripts/ 의 레지스트리 저장 호출이 strict 인지(실패를 성공으로 출력하지 않는지) 고정한다."""
import ast
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXEMPT = {"windows/verify_windows_readiness.py"}  # 반환값(bool)을 직접 검증하는 점검 스크립트


def _calls(name):
    for p in sorted((ROOT / "scripts").rglob("*.py")):
        rel = p.relative_to(ROOT / "scripts").as_posix()
        if rel in EXEMPT:
            continue
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", None)) == name:
                yield rel, n.lineno, any(k.arg == "strict" and getattr(k.value, "value", None) is True for k in n.keywords)


def test_every_script_save_is_strict():
    calls = list(_calls("save_identity_registry"))
    assert len(calls) >= 7
    bad = [(f, l) for f, l, strict in calls if not strict]
    assert not bad, f"strict=True 누락: {bad}"


def test_backfill_doc_type_aborts_on_corrupt_registry(tmp_path):
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import backfill_doc_type as m
    from core.identity_registry import RegistryCorruptError
    p = tmp_path / "documents.json"
    p.write_text("{broken", encoding="utf-8")
    with pytest.raises(RegistryCorruptError):
        m.backfill(str(p), str(tmp_path), apply=True)
    assert p.read_text(encoding="utf-8") == "{broken"
