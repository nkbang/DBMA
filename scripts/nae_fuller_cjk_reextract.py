"""NAE Fuller F2 — targeted repair of CJK-contaminated TSU `claim` text.

WHY: `my-theology-bot-v2` (Qwen-family) code-switched into Chinese/Japanese
under GPU load, leaving Han characters in ~10% of Vol.01 and ~8% of Vol.02
`claim` strings. Pure string substitution cannot fix this cleanly (the
contamination is morpheme-level — particles/conjugation break). This script
does a targeted LLM *repair* pass on only the affected records.

SCOPE / SAFETY:
- Does NOT modify `NAE/pipeline/tsu/builder.py` / `claim.py` / `builder_version`.
- Does NOT create/renumber TSU ids, and does NOT change `doctrine`,
  `scriptures`, `citations`, `is_claim`, `page/paragraph/sentence`.
- Only rewrites the `claim` STRING so it says the same thing in clean Korean.
- Original kept in `claim_raw`; `cjk_status` set to `repaired` /
  `reextracted` / `residual`; `needs_review` cleared on success.
- Refuses a volume whose `tsu_report.json` has `partial: true`
  (run only AFTER F2 finishes that volume) unless `--allow-partial`.
- Run when the GPU is otherwise idle (F2 done) — one `ollama.generate`
  call per affected record, temperature 0.

MODES:
  repair    (default) — direct LLM rewrite: source_text + contaminated claim
                        -> clean Korean restatement, meaning unchanged.
  reextract           — rebuild candidate context from parser and call the
                        real `claim.extract_claim` again; only accepted if the
                        new result is is_claim=True AND Han-free. Falls back to
                        `repair` otherwise.

Usage:
  python -m scripts.nae_fuller_cjk_reextract --identifier Fuller_Complete_Works_Vol01            # dry-run
  python -m scripts.nae_fuller_cjk_reextract --identifier Fuller_Complete_Works_Vol01 --apply
  python -m scripts.nae_fuller_cjk_reextract --all --apply
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from ollama import Client

REPO_ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(REPO_ROOT))

from NAE.pipeline.tsu import config as tsu_config  # noqa: E402

# Bounded HTTP read timeout — same wedge protection as claim.py (a hung Ollama
# daemon must fail the call, not block this script forever). This runs
# unattended right after F2.
_CLIENT = Client(timeout=tsu_config.CLAIM_HTTP_TIMEOUT_S)

TSU_ROOT = REPO_ROOT / "NAE" / "corpus" / "tsu"
REEXTRACT_VERSION = "1.0.0"
HAN = re.compile(r"[㐀-䶿一-鿿豈-﫿\U00020000-\U0002a6df]")

_REPAIR_PROMPT = """다음 한국어 문장에는 한자 또는 중국어·일본어 단어가 잘못 섞여 있다.
그 한자·외국어 부분만 같은 뜻의 한국어(한글)로 바꿔라.

문장: {claim}

엄격한 규칙:
- 문장의 구조·어순·길이·의미를 그대로 둔다. 섞인 한자/외국어 토큰만 한글로 치환한다.
- 내용을 추가·삭제·부연하지 않는다. 원래 문장보다 길어지면 안 된다.
- 한자, 병음, 중국어 간체/번체, 일본어 가나를 결과에 남기지 않는다.
- 조사·어미가 어색해지면 그 부분만 자연스럽게 맞춘다.
- 고친 문장 한 줄만 출력한다. 설명·따옴표·화살표·"원문"/"결과" 같은 라벨 금지."""


def _repair_claim(source_text: str, claim: str, model: str) -> str | None:
    prompt = _REPAIR_PROMPT.format(claim=claim)
    try:
        r = _CLIENT.generate(model=model, prompt=prompt, options={"temperature": 0.0})
        out = (r.get("response") or "").strip()
    except Exception as e:  # noqa: BLE001
        print(f"    [repair] LLM error: {e}")
        return None
    # last non-empty line; drop any "label:" or "... -> " prefix the model adds
    cand = None
    for line in out.splitlines():
        line = line.strip().strip("\"'`").strip()
        if line:
            cand = line
    if not cand:
        return None
    for sep in ("->", "→", "결과:", "고친 문장:", "출력:"):
        if sep in cand:
            cand = cand.split(sep)[-1].strip().strip("\"'`").strip()
    # reject a runaway rewrite (drift guard): >1.6x the original length
    if len(cand) > max(40, int(len(claim) * 1.6)):
        return None
    return cand


def _context_index(identifier: str):
    """(page, paragraph_index, sentence_index) -> SentenceCandidate, for reextract mode."""
    from NAE.pipeline.tsu import parser as tsu_parser
    idx = {}
    for c in tsu_parser.build_candidates(identifier):
        idx[(c.page, c.paragraph_index, c.sentence_index)] = c
    return idx


def process_volume(identifier: str, *, apply: bool, allow_partial: bool, mode: str, model: str,
                   max_records: int | None) -> dict:
    vol_dir = TSU_ROOT / identifier
    tsu_path = vol_dir / "tsu.json"
    rpt_path = vol_dir / "tsu_report.json"
    if not tsu_path.exists():
        return {"identifier": identifier, "error": "tsu.json not found"}

    rpt = json.loads(rpt_path.read_text(encoding="utf-8")) if rpt_path.exists() else None
    if rpt and rpt.get("partial") is True and not allow_partial:
        return {"identifier": identifier, "error": "tsu_report.partial=true — run after F2 finishes this volume (or --allow-partial)"}

    records = json.loads(tsu_path.read_text(encoding="utf-8"))
    targets = [r for r in records
               if r.get("cjk_status") not in ("repaired", "reextracted")
               and isinstance(r.get("claim"), str) and HAN.search(r["claim"])]
    if max_records:
        targets = targets[:max_records]

    ctx_idx = _context_index(identifier) if (mode == "reextract" and apply and targets) else {}

    repaired = reextracted = residual = failed = 0
    t0 = time.monotonic()
    for i, r in enumerate(targets, 1):
        original = r["claim"]
        new_claim = None
        method = None

        if apply:
            if mode == "reextract":
                key = (r.get("page"), r.get("paragraph"), r.get("sentence"))
                cand = ctx_idx.get(key)
                if cand is not None:
                    from NAE.pipeline.tsu import claim as claim_mod
                    res = claim_mod.extract_claim(
                        cand.text, context_before=cand.context_before,
                        context_after=cand.context_after,
                        candidate_scriptures=cand.candidate_scriptures,
                        candidate_citations=cand.candidate_citations, model=model)
                    if res.is_claim and res.claim and not HAN.search(res.claim):
                        new_claim, method = res.claim.strip(), "reextracted"
            if new_claim is None:  # repair mode, or reextract fell through
                rc = _repair_claim(r.get("source_text", ""), original, model)
                if rc:
                    new_claim, method = rc, "repaired"

        if not apply:
            residual += 1  # dry-run just counts candidates
            continue

        if new_claim is None:
            failed += 1
            continue
        if "claim_raw" not in r:
            r["claim_raw"] = original
        r["claim"] = new_claim
        if HAN.search(new_claim):
            r["cjk_status"] = "residual"
            r["needs_review"] = "cjk_residual"
            residual += 1
        else:
            r["cjk_status"] = method
            r.pop("needs_review", None)
            if method == "reextracted":
                reextracted += 1
            else:
                repaired += 1
        if i % 25 == 0:
            print(f"    {identifier}: {i}/{len(targets)} | repaired={repaired} reextracted={reextracted} "
                  f"residual={residual} failed={failed} | {time.monotonic()-t0:.0f}s")

    summary = {
        "identifier": identifier,
        "cjk_reextract_version": REEXTRACT_VERSION,
        "mode": mode,
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidates": len(targets),
        "repaired": repaired,
        "reextracted": reextracted,
        "residual": residual,
        "failed": failed,
        "elapsed_seconds": round(time.monotonic() - t0, 1),
        "applied": apply,
    }
    if apply:
        tsu_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        (vol_dir / "cjk_reextract_report.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        if rpt is not None:
            rpt["cjk_reextract_version"] = REEXTRACT_VERSION
            rpt_path.write_text(json.dumps(rpt, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fuller TSU claim CJK repair / re-extraction (post-F2)")
    ap.add_argument("--identifier")
    ap.add_argument("--all", action="store_true", help="every Fuller_Complete_Works_Vol* with a non-partial tsu.json")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-partial", action="store_true")
    ap.add_argument("--mode", choices=["repair", "reextract"], default="repair")
    ap.add_argument("--model", default=tsu_config.DEFAULT_CLAIM_MODEL)
    ap.add_argument("--max-records", type=int, default=None, help="cap per volume (testing)")
    args = ap.parse_args(argv)

    if args.all:
        targets = sorted(d.name for d in TSU_ROOT.iterdir()
                         if d.is_dir() and d.name.startswith("Fuller_Complete_Works_Vol")
                         and (d / "tsu.json").exists())
    elif args.identifier:
        targets = [args.identifier]
    else:
        ap.error("pass --identifier or --all")
        return 2

    for ident in targets:
        s = process_volume(ident, apply=args.apply, allow_partial=args.allow_partial,
                           mode=args.mode, model=args.model, max_records=args.max_records)
        if s.get("error"):
            print(f"[{ident}] SKIP — {s['error']}")
            continue
        tag = "APPLIED" if args.apply else "DRY-RUN"
        print(f"[{ident}] {tag} mode={s['mode']} — candidates={s['candidates']} "
              f"repaired={s['repaired']} reextracted={s['reextracted']} "
              f"residual={s['residual']} failed={s['failed']} ({s['elapsed_seconds']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
