"""텍스트 파일 입출력은 encoding을 명시해야 한다 (Windows 지원 대비 점검 — 인코딩 미지정 14곳 수정의 회귀 방지).

배경: `open(path, "w")`처럼 encoding을 생략하면 Python은 OS 로케일 인코딩을 쓴다. macOS는 UTF-8이라 드러나지 않지만
한국어 Windows는 cp949라서 헬라어·히브리어(신학 자료의 핵심)를 쓰는 순간 UnicodeEncodeError가 나거나 글자가 깨진다.

검사 대상: core/, ui/, dbma_ui.py 의 `open(...)`(텍스트 모드), `.read_text(...)`, `.write_text(...)`.
`fitz.open()`·`tantivy.Index.open()` 같은 다른 객체의 `.open`은 파일 텍스트 열기가 아니므로 대상이 아니다.
"""
from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOTS = ("core", "ui", "dbma_ui.py")


def _mode(call: ast.Call):
    mode = None
    if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant):
        mode = call.args[1].value
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            mode = kw.value.value
    return mode


def _violations() -> list[str]:
    files: list[Path] = []
    for r in ROOTS:
        p = REPO / r
        files += [p] if p.is_file() else sorted(p.rglob("*.py"))
    out = []
    for f in files:
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            has_enc = any(k.arg == "encoding" for k in n.keywords)
            if isinstance(n.func, ast.Name) and n.func.id == "open":
                m = _mode(n)
                if isinstance(m, str) and "b" in m:
                    continue
                if not has_enc:
                    out.append(f"{f.relative_to(REPO)}:{n.lineno} open(mode={m!r})")
            elif isinstance(n.func, ast.Attribute) and n.func.attr in ("read_text", "write_text"):
                if not has_enc:
                    out.append(f"{f.relative_to(REPO)}:{n.lineno} .{n.func.attr}()")
    return out


def test_no_text_io_without_explicit_encoding():
    v = _violations()
    assert not v, "encoding 미지정 텍스트 I/O (Windows cp949에서 헬라어·히브리어 손상 위험):\n  " + "\n  ".join(v)


def test_detector_catches_a_missing_encoding(tmp_path):
    """탐지기가 실제로 위반을 잡는지 확인 — 항상 통과하는 시험이 되지 않게 한다."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f(p):\n    with open(p, 'w') as fh:\n        fh.write('x')\n    return p.read_text()\n", encoding="utf-8")
    tree = ast.parse(bad.read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    flagged = 0
    for n in calls:
        has_enc = any(k.arg == "encoding" for k in n.keywords)
        if isinstance(n.func, ast.Name) and n.func.id == "open" and not has_enc:
            flagged += 1
        if isinstance(n.func, ast.Attribute) and n.func.attr == "read_text" and not has_enc:
            flagged += 1
    assert flagged == 2
