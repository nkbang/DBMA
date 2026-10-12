"""PE(Perplexity) 개발업무처리능력 테스트 하니스.

실제 저장소 모듈(core/date_extractor.py, core/citation_format.py)만 사용한다.
RAW/코퍼스/.env 는 전송하지 않는다. 모델 출력은 임시 디렉터리에서만 검증한다.

사용: python scripts/pe_devtest/run.py --provider pplx --model sonar-pro
      python scripts/pe_devtest/run.py --provider ollama --model qwen3.6:35b-DBMAcode-Cline
"""
from __future__ import annotations

import argparse, json, os, re, shutil, subprocess, sys, tempfile, time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from tasks import TASKS  # noqa: E402


def load_key() -> str:
    k = os.environ.get("PERPLEXITY_API_KEY")
    if k:
        return k
    for line in Path("/Users/David/DBMA/.env").read_text().splitlines():
        if line.startswith("PERPLEXITY_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("PERPLEXITY_API_KEY 없음")


def call(provider: str, model: str, prompt: str) -> tuple[str, float]:
    sysmsg = ("당신은 Python 개발자다. 요청한 파일의 전체 내용을 단 하나의 ```python 코드블록으로만 "
              "출력하라. 설명은 코드블록 밖에 한 줄 이내로 쓴다.")
    msgs = [{"role": "system", "content": sysmsg}, {"role": "user", "content": prompt}]
    if provider == "pplx":
        url, hdr = "https://api.perplexity.ai/chat/completions", {"Authorization": f"Bearer {load_key()}"}
        body = {"model": model, "messages": msgs, "temperature": 0, "disable_search": True}
    else:
        url, hdr = "http://localhost:11434/v1/chat/completions", {}
        body = {"model": model, "messages": msgs, "temperature": 0}
    req = urllib.request.Request(url, json.dumps(body).encode(),
                                 {"Content-Type": "application/json", **hdr})
    t = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"], time.time() - t


def extract_code(text: str) -> str | None:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    blocks = re.findall(r"```(?:python)?\n(.*?)```", text, flags=re.S)
    return max(blocks, key=len) if blocks else None


def pytest(tmp: Path, *files: str) -> tuple[bool, str]:
    p = subprocess.run([str(Path.home() / "envs/dbma311/bin/python"), "-m", "pytest", "-q", "-x",
                        "-p", "no:cacheprovider", *files], cwd=tmp, capture_output=True, text=True, timeout=120)
    return p.returncode == 0, (p.stdout + p.stderr)[-1500:]


def sandbox(extra: dict[str, str]) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="pe_"))
    (tmp / "core").mkdir(); (tmp / "tests").mkdir()
    (tmp / "core/__init__.py").write_text("")
    for rel in ("core/date_extractor.py", "core/citation_format.py",
                "tests/test_date_extractor.py", "tests/test_citation_format.py"):
        shutil.copy(ROOT / rel, tmp / rel)
    for rel, txt in extra.items():
        (tmp / rel).write_text(txt)
    return tmp


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["pplx", "ollama"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default=str(ROOT / "docs/audit/pe_devtest_results.jsonl"))
    a = ap.parse_args()
    results = []
    for t in TASKS:
        tmp0 = sandbox(t.get("setup", {}))
        prompt = t["prompt"](tmp0)
        shutil.rmtree(tmp0)
        rec = {"task": t["id"], "provider": a.provider, "model": a.model}
        try:
            raw, sec = call(a.provider, a.model, prompt)
            rec["seconds"] = round(sec, 1)
            code = extract_code(raw)
            rec["format_ok"] = code is not None
            if code:
                tmp = sandbox(t.get("setup", {}))
                (tmp / t["target"]).write_text(code)
                rec.update(t["grade"](tmp, pytest))
                shutil.rmtree(tmp)
            else:
                rec["pass"] = False
        except Exception as e:  # 호출 실패도 기록
            rec.update(error=repr(e)[:200], **{"pass": False})
        print(json.dumps(rec, ensure_ascii=False)); results.append(rec)
    with open(a.out, "a") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"PASS {sum(r['pass'] for r in results)}/{len(results)}")


if __name__ == "__main__":
    main()
