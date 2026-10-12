#!/usr/bin/env python3
"""Windows(및 모든 OS) 준비 상태 자동 점검 — docs/WINDOWS_VERIFICATION_PROCEDURE.md 의 실행 도구.

사용 (저장소 루트에서, 앱 의존성이 설치된 파이썬으로):
    python scripts/windows/verify_windows_readiness.py --out C:\\gate2-win\\run1
    python scripts/windows/verify_windows_readiness.py --out ... --with-full-tests   # 전체 시험(오래 걸림)

원칙
  * 출력 디렉터리는 새로 만든다 — 이미 내용이 있으면 중단한다(이전 결과를 덮어쓰지 않기 위해).
  * 각 점검의 상세 출력은 logs/<이름>.txt 에 따로 저장한다. results.json / REPORT.md 가 요약이다.
  * 상태: PASS(통과) / FAIL(결함) / WARN(알려진 위험이 관찰됨, 사람이 판단) / INFO(기록) / SKIP.
  * 종료 코드: FAIL 이 하나라도 있으면 1, 아니면 0.  WARN 은 종료 코드에 영향을 주지 않는다.
  * 저장소를 수정하지 않는다(임시 파일은 시스템 임시 폴더). 단 앱을 실제로 import/실행하므로 __pycache__ 가 생길 수 있다.

주의: 이 스크립트 자체는 macOS 에서만 시험되었다. Windows 에서 처음 도는 것이므로, 스크립트가 이상하게
동작하면 앱 결함으로 단정하기 전에 먼저 이 스크립트의 오류를 의심할 것.
"""
from __future__ import annotations

import argparse
import datetime
import json
import locale
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable, Optional

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable
RESULTS: list[dict] = []
OUT: Optional[Path] = None


# ───────────────────────────── 공통 도구 ─────────────────────────────
def log_file(name: str, text: str) -> None:
    assert OUT is not None
    (OUT / "logs").mkdir(exist_ok=True)
    (OUT / "logs" / f"{name}.txt").write_text(text, encoding="utf-8", errors="replace")


def child_env(extra: Optional[dict] = None) -> dict:
    """자식 파이썬의 표준 입출력만 UTF-8 로 고정한다(콘솔 인코딩 때문에 점검 출력 해석이 깨지지 않도록).
    PYTHONUTF8 은 일부러 설정하지 않는다: open() 의 기본 인코딩(로케일)을 그대로 두어야 인코딩 결함이 드러난다."""
    e = dict(os.environ)
    e["PYTHONIOENCODING"] = "utf-8"
    if extra:
        e.update(extra)
    return e


def run_py(code: str, timeout: int = 180, cwd: Path = REPO, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    return subprocess.run([PY, "-W", "ignore", "-c", code], cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout, env=env or child_env())


def tail(text: str, n: int = 12) -> str:
    return "\n".join(text.strip().splitlines()[-n:])


def check(name: str):
    """점검 함수 데코레이터 — 결과를 RESULTS 에 기록하고, 예외도 FAIL 로 잡는다."""
    def deco(fn: Callable[[], tuple[str, str, str]]):
        def wrapper():
            t0 = time.time()
            try:
                status, detail, logtext = fn()
            except subprocess.TimeoutExpired as e:
                status, detail, logtext = "FAIL", f"시간 초과 ({e.timeout}s)", ""
            except Exception as e:  # noqa: BLE001 — 점검 자체의 오류도 기록해야 한다
                import traceback
                status, detail, logtext = "FAIL", f"점검 중 예외: {type(e).__name__}: {e}", traceback.format_exc()
            dt = round(time.time() - t0, 1)
            RESULTS.append({"name": name, "status": status, "detail": detail, "seconds": dt})
            if logtext:
                log_file(name, logtext)
            print(f"[{status:<4}] {name:<28} {dt:>6}s  {detail.splitlines()[0] if detail else ''}", flush=True)
        wrapper.__name__ = fn.__name__
        return wrapper
    return deco


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ───────────────────────────── 점검들 ─────────────────────────────
@check("01_environment")
def c_environment():
    info = {
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "python": sys.version.replace("\n", " "),
        "executable": PY,
        "locale_preferred_encoding": locale.getpreferredencoding(False),
        "filesystem_encoding": sys.getfilesystemencoding(),
        "utf8_mode": bool(sys.flags.utf8_mode),
        "PYTHONUTF8_env": os.environ.get("PYTHONUTF8"),
        "cwd": os.getcwd(),
        "repo": str(REPO),
        "path_len_repo": len(str(REPO)),
    }
    try:
        info["git_head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        info["git_head"] = None
    notes = []
    if platform.system() == "Windows":
        if info["locale_preferred_encoding"].lower() in ("utf-8", "utf8"):
            notes.append("로케일 인코딩이 UTF-8 — cp949 환경의 결함은 이 기기에서는 재현되지 않는다(인코딩 시험 의미 약화)")
        if info["machine"].lower() not in ("amd64", "x86_64"):
            notes.append(f"CPU 아키텍처 {info['machine']} — Windows on ARM 은 평가 범위 밖")
    ver = sys.version_info
    if (ver.major, ver.minor) != (3, 11):
        notes.append(f"Python {ver.major}.{ver.minor} — 프로젝트는 3.11 기준")
    detail = f"{info['platform']} / Python {ver.major}.{ver.minor} / 로케일 {info['locale_preferred_encoding']}" + (" | " + "; ".join(notes) if notes else "")
    return "INFO", detail, json.dumps(info, ensure_ascii=False, indent=2)


REQUIRED = [("streamlit", "streamlit"), ("chromadb", "chromadb"), ("qdrant_client", "qdrant-client"), ("ollama", "ollama"),
            ("torch", "torch"), ("sentence_transformers", "sentence-transformers"), ("docling", "docling"),
            ("easyocr", "easyocr"), ("tantivy", "tantivy"), ("fitz", "PyMuPDF"), ("filelock", "filelock"),
            ("kiwipiepy", "kiwipiepy"), ("yaml", "PyYAML"), ("numpy", "numpy"), ("pandas", "pandas")]
OPTIONAL = [("hunspell", "hunspell"), ("pytesseract", "pytesseract"), ("pdf2image", "pdf2image")]


def _probe(mod: str, dist: str) -> tuple[bool, str]:
    code = (f"import importlib,importlib.metadata as m;importlib.import_module({mod!r});"
            f"print(m.version({dist!r}))")
    r = run_py(code, timeout=300)
    return (r.returncode == 0), (r.stdout.strip() if r.returncode == 0 else tail(r.stderr, 3))


@check("02_dependencies")
def c_dependencies():
    lines, missing, opt_missing = [], [], []
    for mod, dist in REQUIRED:
        ok, info = _probe(mod, dist)
        lines.append(f"{'OK  ' if ok else 'FAIL'} {dist:<24} {info}")
        if not ok:
            missing.append(dist)
    for mod, dist in OPTIONAL:
        ok, info = _probe(mod, dist)
        lines.append(f"{'OK  ' if ok else 'n/a '} {dist:<24} {info if ok else '(선택) ' + info[:60]}  [선택]")
        if not ok:
            opt_missing.append(dist)
    text = "\n".join(lines)
    if missing:
        return "FAIL", f"필수 패키지 import 실패 {len(missing)}개: {', '.join(missing)}", text
    extra = f" | 선택 패키지 없음: {', '.join(opt_missing)}" if opt_missing else ""
    return "PASS", f"필수 {len(REQUIRED)}개 import 성공{extra}", text


@check("03_external_binaries")
def c_binaries():
    out = []
    ollama = shutil.which("ollama")
    ver = ""
    if ollama:
        r = subprocess.run([ollama, "--version"], capture_output=True, text=True, timeout=30, errors="replace")
        import re as _re
        m = _re.search(r"\d+\.\d+\.\d+", r.stdout + r.stderr)
        ver = m.group(0) if m else ""
    out.append(f"ollama: {ollama or '없음'} {ver}")
    tess = shutil.which("tesseract"); pdf = shutil.which("pdftoppm")
    out.append(f"tesseract: {tess or '없음'}")
    out.append(f"pdftoppm(poppler): {pdf or '없음'}")
    text = "\n".join(out)
    notes = []
    if not ollama:
        return "WARN", "ollama 실행 파일이 PATH 에 없음 — 생성·임베딩 기능 시험 불가", text
    if not tess or not pdf:
        notes.append("OCR/스캔 PDF 기능은 제한됨(선택 구성 요소)")
    return "PASS", f"ollama {ver or '확인됨'}" + (" | " + "; ".join(notes) if notes else ""), text


@check("04_ollama_server")
def c_ollama_server():
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return "WARN", f"Ollama 서버 응답 없음({type(e).__name__}) — 생성·임베딩 시험 불가", str(e)
    names = [m.get("name", "") for m in data.get("models", [])]
    text = "\n".join(names)
    has_embed = any(n.startswith("bge-m3") for n in names)
    has_gen = any(n.startswith(("llama3", "qwen", "llama")) for n in names)
    if not has_embed:
        return "WARN", f"모델 {len(names)}개, 그러나 임베딩 모델 bge-m3 없음", text
    if not has_gen:
        return "WARN", f"bge-m3 있음, 생성 모델(llama3.x 등)이 없음 — 모델 {len(names)}개", text
    return "PASS", f"서버 응답, bge-m3와 생성 모델 있음 (모델 {len(names)}개)", text


@check("05_app_import")
def c_app_import():
    r = run_py("import ui.app", timeout=300)
    text = f"rc={r.returncode}\n--- stdout\n{r.stdout}\n--- stderr\n{r.stderr}"
    if r.returncode == 0:
        return "PASS", "import ui.app 성공 (fcntl 의존 제거 확인)", text
    return "FAIL", "import ui.app 실패: " + tail(r.stderr, 2).replace("\n", " | "), text


@check("06_file_lock")
def c_file_lock():
    code = r'''
import sys, threading, time, subprocess, tempfile, os
from pathlib import Path
from core.file_lock import file_lock
d = Path(tempfile.mkdtemp()); lock = d / "x.json.lock"
# 1) 스레드 간 상호 배제
inside = []; overlap = []
def w(n):
    with file_lock(lock):
        inside.append(n)
        if len(inside) > 1: overlap.append(tuple(inside))
        time.sleep(0.12); inside.remove(n)
ts = [threading.Thread(target=w, args=(n,)) for n in "ABC"]
[t.start() for t in ts]; [t.join() for t in ts]
print("threads_overlap", len(overlap))
# 2) 프로세스 간 상호 배제
child = subprocess.Popen([sys.executable, "-c",
    "import sys,time;sys.path.insert(0,%r);from core.file_lock import file_lock\n"
    "with file_lock(%r):\n print('holding',flush=True);time.sleep(1.0)" % (os.getcwd(), str(lock))],
    stdout=subprocess.PIPE, text=True)
assert child.stdout.readline().strip() == "holding"
t0 = time.monotonic()
with file_lock(lock): waited = time.monotonic() - t0
child.wait(timeout=10)
print("process_wait_seconds", round(waited, 2))
# 3) 예외 시 해제
try:
    with file_lock(lock): raise RuntimeError("x")
except RuntimeError: pass
with file_lock(lock, timeout=3): print("released_after_exception", True)
# 4) 한글·공백이 든 경로
d2 = d / "한글 폴더 with space"; p2 = d2 / "레지스트리.json.lock"
with file_lock(p2): print("unicode_path_ok", p2.parent.is_dir())
'''
    r = run_py(code, timeout=120)
    text = f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
    if r.returncode != 0:
        return "FAIL", "잠금 시험 실행 실패: " + tail(r.stderr, 2).replace("\n", " | "), text
    kv = dict(l.split(" ", 1) for l in r.stdout.strip().splitlines() if " " in l)
    problems = []
    if kv.get("threads_overlap") != "0": problems.append(f"스레드 겹침 {kv.get('threads_overlap')}")
    if float(kv.get("process_wait_seconds", "0")) < 0.5: problems.append(f"프로세스 간 배제 실패(대기 {kv.get('process_wait_seconds')}s)")
    if kv.get("released_after_exception") != "True": problems.append("예외 후 해제 실패")
    if kv.get("unicode_path_ok") != "True": problems.append("한글 경로 실패")
    if problems:
        return "FAIL", "; ".join(problems), text
    return "PASS", f"스레드·프로세스 상호 배제, 예외 해제, 한글 경로 모두 통과 (프로세스 대기 {kv['process_wait_seconds']}s)", text


@check("07_encoding_roundtrip")
def c_encoding():
    code = r'''
import sys, tempfile, os, json
from core.identity_registry import load_identity_registry, save_identity_registry
d = tempfile.mkdtemp(); p = os.path.join(d, "한글", "documents.json")
reg = load_identity_registry(p)
txt = {"hebrew": "בְּרֵאשִׁית בָּרָא", "polytonic_greek": "ἐν ἀρχῇ ἦν ὁ λόγος", "korean": "태초에 하나님이", "dash": "A — B"}
reg["documents"]["doc-enc"] = {"title": txt}
ok = save_identity_registry(reg, p)
back = load_identity_registry(p)
raw = open(p, "rb").read()
print("save_ok", ok)
print("roundtrip_equal", back["documents"].get("doc-enc", {}).get("title") == txt)
print("file_is_utf8", raw.decode("utf-8") is not None)
'''
    r = run_py(code, timeout=60)
    text = f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
    if r.returncode != 0:
        return "FAIL", "인코딩 왕복 실행 실패: " + tail(r.stderr, 2).replace("\n", " | "), text
    kv = dict(l.split(" ", 1) for l in r.stdout.strip().splitlines() if " " in l)
    if kv.get("save_ok") == "True" and kv.get("roundtrip_equal") == "True":
        return "PASS", "히브리어·폴리토닉 헬라어·한글·em dash 가 레지스트리 저장/로드에서 보존됨", text
    return "FAIL", f"저장 {kv.get('save_ok')}, 왕복 {kv.get('roundtrip_equal')}", text


@check("08_registry_replace_stress")
def c_registry_stress():
    """Windows 에서 가장 의심되는 위험: 잠금 없는 읽기와 os.replace 교체의 충돌.
    save 는 OSError 를 삼키고 False 를 반환하고, load 는 OSError 시 '빈 레지스트리'를 반환한다.
    → 저장이 소리 없이 사라지거나(save False), 읽기가 빈 레지스트리를 받는 횟수를 센다."""
    seconds = int(os.environ.get("STRESS_SECONDS", "12"))
    code = r'''
import sys, tempfile, os, threading, time, json
from core.identity_registry import load_identity_registry, save_identity_registry
SEC = %d
d = tempfile.mkdtemp(); p = os.path.join(d, "documents.json")
base = load_identity_registry(p)
for i in range(300):
    base["documents"][f"doc-{i}"] = {"title": f"문서 {i} בראשית ἀρχή", "pad": "x" * 200}
assert save_identity_registry(base, p)
EXPECT = len(base["documents"])
stop = threading.Event()
stats = {"saves": 0, "save_false": 0, "save_exc": 0, "loads": 0, "load_empty": 0, "load_short": 0, "load_exc": 0}
lock = threading.Lock()
def writer():
    reg = load_identity_registry(p)
    n = 0
    while not stop.is_set():
        reg["documents"]["doc-0"]["n"] = n; n += 1
        try:
            ok = save_identity_registry(reg, p)
        except Exception:
            with lock: stats["save_exc"] += 1
            continue
        with lock:
            stats["saves"] += 1
            if not ok: stats["save_false"] += 1
def reader():
    while not stop.is_set():
        try:
            r = load_identity_registry(p)
        except Exception:
            with lock: stats["load_exc"] += 1
            continue
        c = len(r.get("documents", {}))
        with lock:
            stats["loads"] += 1
            if c == 0: stats["load_empty"] += 1
            elif c < EXPECT: stats["load_short"] += 1
if os.environ.get("STRESS_INJECT_FAILURE") == "1":
    # 대조 실험(탐지기 검증용): Windows 에서 일어날 법한 실패를 인위적으로 주입한다. 실제 점검에는 쓰지 않는다.
    import random
    _real_replace = os.replace
    def _flaky_replace(a, b):
        if random.random() < 0.05: raise PermissionError(13, "injected: file in use")
        return _real_replace(a, b)
    os.replace = _flaky_replace
    import core.identity_registry as _ir
    _real_load = _ir.json.load
    def _flaky_load(f, *a, **k):
        if random.random() < 0.03: raise OSError(5, "injected: transient read error")
        return _real_load(f, *a, **k)
    _ir.json.load = _flaky_load
ts = [threading.Thread(target=writer)] + [threading.Thread(target=reader) for _ in range(4)]
[t.start() for t in ts]; time.sleep(SEC); stop.set(); [t.join() for t in ts]
print(json.dumps(stats))
''' % seconds
    r = run_py(code, timeout=seconds + 120)
    text = f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
    if r.returncode != 0:
        return "FAIL", "교체 경합 시험 실행 실패: " + tail(r.stderr, 2).replace("\n", " | "), text
    s = json.loads(r.stdout.strip().splitlines()[-1])
    summary = (f"{seconds}초: 저장 {s['saves']}회(실패 False {s['save_false']}), 읽기 {s['loads']}회"
               f"(빈 레지스트리 {s['load_empty']}, 일부만 {s['load_short']}), 예외 저장 {s['save_exc']}/읽기 {s['load_exc']}")
    if s["saves"] < 20 or s["loads"] < 20:
        return "WARN", "시험 횟수가 너무 적어 판단 불가 — " + summary, text
    bad = s["save_false"] + s["load_empty"] + s["load_short"] + s["save_exc"] + s["load_exc"]
    if bad == 0:
        return "PASS", "교체 경합에서 저장 실패·빈 읽기 0건 — " + summary, text
    return "WARN", ("★ Windows 알려진 위험 관찰: 저장이 조용히 사라지거나 읽기가 빈 레지스트리를 받음 — " + summary +
                   " (조치 필요: os.replace 재시도, load 의 OSError→빈 레지스트리 처리 재설계)"), text


@check("09_streamlit_smoke")
def c_streamlit():
    port = free_port()
    assert OUT is not None
    logp = OUT / "logs" / "09_streamlit_server_output.txt"
    (OUT / "logs").mkdir(exist_ok=True)
    with open(logp, "w", encoding="utf-8", errors="replace") as lf:
        proc = subprocess.Popen([PY, "-m", "streamlit", "run", "dbma_ui.py", "--server.headless", "true",
                                 "--server.port", str(port), "--browser.gatherUsageStats", "false"],
                                cwd=str(REPO), stdout=lf, stderr=subprocess.STDOUT, env=child_env())
        ok, last = False, ""
        try:
            for _ in range(120):
                if proc.poll() is not None:
                    last = f"서버 프로세스가 종료됨 rc={proc.returncode}"
                    break
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=3) as r:
                        if r.read().decode().strip() == "ok":
                            ok = True
                            break
                except Exception as e:  # noqa: BLE001
                    last = f"{type(e).__name__}"
                time.sleep(1)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()
    text = f"port={port} ok={ok} last={last}"
    if ok:
        return "PASS", f"streamlit 서버 기동 후 /_stcore/health = ok (포트 {port}), 정상 종료 시도함", text
    return "FAIL", f"streamlit 서버가 120초 안에 응답하지 않음 ({last})", text


@check("10_apptest_pages")
def c_apptest():
    code = r'''
import json
from streamlit.testing.v1 import AppTest
KEYS = ["Dashboard", "Library", "Processing", "Research", "설교 준비", "도움말"]
out = []
for k in KEYS:
    at = AppTest.from_file("dbma_ui.py", default_timeout=120)
    at.session_state["show_onboarding"] = False
    at.session_state["nav_page"] = k
    at.run()
    try: sel = at.sidebar.radio(key="nav_page").value
    except Exception: sel = None
    out.append({"page": k, "selected": sel, "selected_ok": sel == k, "exceptions": [str(e.value)[:200] for e in at.exception]})
print(json.dumps(out, ensure_ascii=False))
'''
    r = run_py(code, timeout=900)
    text = f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
    if r.returncode != 0:
        return "FAIL", "AppTest 실행 실패: " + tail(r.stderr, 2).replace("\n", " | "), text
    rows = json.loads(r.stdout.strip().splitlines()[-1])
    exc = [x for x in rows if x["exceptions"]]
    notsel = [x["page"] for x in rows if not x["selected_ok"]]
    if exc:
        return "FAIL", f"{len(exc)}개 페이지에서 예외: " + "; ".join(f"{x['page']}={x['exceptions'][0][:60]}" for x in exc), text
    if notsel:
        return "WARN", f"예외는 없으나 페이지 선택이 적용되지 않음(이 버전의 메뉴 키가 다를 수 있음): {notsel}", text
    return "PASS", f"{len(rows)}개 페이지 예외 없이 렌더링 (페이지 선택값 일치 확인)", text


@check("11_pytest_windows_set")
def c_pytest_set():
    tests = ["tests/test_file_lock.py", "tests/test_registry_lock.py", "tests/test_tsu_dataset_lock.py",
             "tests/test_explicit_text_encoding.py", "tests/test_ui_imports_without_nae.py"]
    tests = [t for t in tests if (REPO / t).exists()]
    if not tests:
        return "SKIP", "대상 시험 파일 없음", ""
    r = subprocess.run([PY, "-m", "pytest", *tests, "-q", "-p", "no:cacheprovider", "-W", "ignore"], cwd=str(REPO),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900, env=child_env())
    text = r.stdout + "\n" + r.stderr
    if "No module named pytest" in text:
        return "FAIL", "pytest 가 설치되어 있지 않음 — `pip install pytest` 후 재실행", text
    summ = [l for l in r.stdout.splitlines() if " passed" in l or " failed" in l or " error" in l]
    s = summ[-1].strip() if summ else tail(r.stdout, 1)
    return ("PASS" if r.returncode == 0 else "FAIL"), s, text


def c_full_tests():
    @check("12_pytest_full")
    def inner():
        r = subprocess.run([PY, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider", "-W", "ignore", "-x" if False else "--maxfail=1000"],
                           cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=7200, env=child_env())
        text = r.stdout + "\n" + r.stderr
        failed = [l for l in r.stdout.splitlines() if l.startswith(("FAILED", "ERROR"))]
        summ = [l for l in r.stdout.splitlines() if " passed" in l or " failed" in l]
        s = summ[-1].strip() if summ else tail(r.stdout, 1)
        (OUT / "logs" / "12_pytest_full_failures.txt").write_text("\n".join(failed), encoding="utf-8")
        return ("PASS" if r.returncode == 0 else "WARN"), f"{s} (실패 목록: logs/12_pytest_full_failures.txt — 분류 필요)", text
    inner()


# ───────────────────────────── 보고서 ─────────────────────────────
def write_report() -> int:
    assert OUT is not None
    (OUT / "results.json").write_text(json.dumps({"generated_at": datetime.datetime.now().astimezone().isoformat(),
                                                   "repo": str(REPO), "results": RESULTS}, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {k: sum(1 for r in RESULTS if r["status"] == k) for k in ("PASS", "FAIL", "WARN", "INFO", "SKIP")}
    L = ["# Windows 준비 상태 점검 결과", "", f"- 실행: {datetime.datetime.now().astimezone().isoformat(timespec='seconds')}",
         f"- 저장소: `{REPO}`", f"- 집계: " + ", ".join(f"{k} {v}" for k, v in counts.items()), "",
         "| 점검 | 상태 | 시간(s) | 요약 |", "|---|---|---:|---|"]
    for r in RESULTS:
        L.append(f"| {r['name']} | **{r['status']}** | {r['seconds']} | {r['detail'].splitlines()[0].replace('|', '/')} |")
    L += ["", "상세 출력은 `logs/` 폴더의 같은 이름 파일을 보세요. FAIL 은 결함 후보, WARN 은 알려진 위험이 관찰되어 사람이 판단해야 하는 항목입니다."]
    (OUT / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return 1 if counts["FAIL"] else 0


def main() -> int:
    global OUT
    # 한국어 Windows 콘솔(cp949)에서 em dash(—) 같은 문자를 출력하다 죽지 않도록 한다. (실제로 재현된 결함)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="결과를 쓸 새 디렉터리 (이미 내용이 있으면 중단)")
    ap.add_argument("--with-full-tests", action="store_true", help="tests/ 전체를 실행(오래 걸림, 실패 목록은 사람이 분류)")
    ap.add_argument("--skip", default="", help="건너뛸 점검 이름의 일부를 쉼표로 (예: 09,10)")
    a = ap.parse_args()
    OUT = Path(a.out).resolve()
    if OUT.exists() and any(OUT.iterdir()):
        print(f"중단: {OUT} 에 이미 내용이 있습니다. 새 디렉터리를 지정하세요(이전 결과를 덮어쓰지 않기 위해).")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    skips = [s for s in a.skip.split(",") if s]
    steps = [c_environment, c_dependencies, c_binaries, c_ollama_server, c_app_import, c_file_lock, c_encoding,
             c_registry_stress, c_streamlit, c_apptest, c_pytest_set]
    print(f"== Windows 준비 상태 점검 시작 → {OUT}\n")
    NAMES = {"c_environment": "01_environment", "c_dependencies": "02_dependencies", "c_binaries": "03_external_binaries",
             "c_ollama_server": "04_ollama_server", "c_app_import": "05_app_import", "c_file_lock": "06_file_lock",
             "c_encoding": "07_encoding_roundtrip", "c_registry_stress": "08_registry_replace_stress",
             "c_streamlit": "09_streamlit_smoke", "c_apptest": "10_apptest_pages", "c_pytest_set": "11_pytest_windows_set"}
    for fn in steps:
        full = NAMES[fn.__name__]
        if any(s and full.startswith(s) for s in skips):
            RESULTS.append({"name": full, "status": "SKIP", "detail": "--skip 지정", "seconds": 0})
            continue
        fn()
    if a.with_full_tests:
        c_full_tests()
    rc = write_report()
    print(f"\n== 완료. 보고서: {OUT / 'REPORT.md'}  (종료 코드 {rc})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
