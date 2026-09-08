#!/usr/bin/env python3
"""scripts/nae_fuller_review_recorder.py — interactive human-review recorder for
Fuller Vol.01 TSU batches.

This tool ONLY records the reviewer's own keystrokes into
NAE/review/human/decisions/<batch>_decisions.json in the schema
NAE/review/human/decision_gate.py expects. It never proposes or fabricates a
judgment; the reviewer answers every question.

Usage:
    python scripts/nae_fuller_review_recorder.py --batch 1
    python scripts/nae_fuller_review_recorder.py --batch fuller_v01_batch_0003
    python scripts/nae_fuller_review_recorder.py --list
    python scripts/nae_fuller_review_recorder.py --batch 1 --stats
    python scripts/nae_fuller_review_recorder.py --batch 1 --redo TSU-0004133

Per question: a / r / c   (A=accurate/ok, R=reject, C=context insufficient)
Any prompt also accepts:  s = skip this TSU   b = back (redo previous)   q = save & quit
Resumable: TSUs already in the decisions file are skipped.
Writes after every entry (crash-safe). Touches nothing else.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUESTS_DIR = REPO_ROOT / "NAE/review/human/requests"
DECISIONS_DIR = REPO_ROOT / "NAE/review/human/decisions"
REVIEWER_ID = "David"

VALID_ANS = {"A", "R", "C"}
VALID_Q4 = {
    "SCRIPTURE_MISMATCH", "DOCTRINE_MISMATCH", "CONTEXT_LOSS",
    "AMBIGUOUS", "EVIDENCE_INSUFFICIENT", "NONE",
}
FINAL = {"APPROVED", "CONDITIONAL", "REJECTED"}


def _batch_id(arg: str) -> str:
    if arg.startswith("fuller_v01_batch_"):
        return arg
    return f"fuller_v01_batch_{int(arg):04d}"


def _req_path(bid: str) -> Path:
    return REQUESTS_DIR / f"{bid}_requests.json"


def _dec_path(bid: str) -> Path:
    return DECISIONS_DIR / f"{bid}_decisions.json"


def _load_decisions(bid: str) -> dict:
    p = _dec_path(bid)
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        return {e["tsu_id"]: e for e in d.get("decisions", [])}
    return {}


def _save_decisions(bid: str, by_id: dict) -> None:
    DECISIONS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0.0",
        "batch_id": bid,
        "decisions": [by_id[k] for k in sorted(by_id)],
    }
    tmp = _dec_path(bid).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_dec_path(bid))


def _final_from_answers(ans: dict) -> str:
    j = {k: v for k, v in ans.items() if k != "Q4"}
    if any(v == "R" for v in j.values()):
        return "REJECTED"
    if j and all(v == "A" for v in j.values()):
        return "APPROVED"
    return "CONDITIONAL"


class _Quit(Exception):
    pass


class _Skip(Exception):
    pass


class _Back(Exception):
    pass


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        raise _Quit()


def _ask_answer(code: str, label: str, text: str) -> str:
    while True:
        raw = _ask(f"  {code} {label} — {text}\n  [a/r/c | s=skip b=back q=quit] > ").lower()
        if raw in ("a", "r", "c"):
            return raw.upper()
        if raw == "s":
            raise _Skip()
        if raw == "b":
            raise _Back()
        if raw == "q":
            raise _Quit()
        print("  ? enter one of: a r c s b q")


def _ask_q4() -> str | None:
    opts = " ".join(sorted(VALID_Q4))
    raw = _ask(f"  Q4 flag (enter=none | {opts}) > ").strip().upper()
    if not raw:
        return None
    if raw in VALID_Q4:
        return raw
    print(f"  ignored (not a valid flag): {raw}")
    return None


def _print_card(bid: str, i: int, n: int, tally: dict, req: dict) -> None:
    print("\n" + "=" * 78)
    print(f"[{bid}]  {i}/{n}   A:{tally['APPROVED']}  C:{tally['CONDITIONAL']}  R:{tally['REJECTED']}")
    print("-" * 78)
    print(f"tsu_id   : {req['tsu_id']}   doctrine: {req.get('doctrine') or '(none)'}")
    print(f"claim    : {req.get('claim','')}")
    print("-" * 78)
    print("original_text:")
    print(textwrap.fill(req.get("original_text", ""), width=76,
                        initial_indent="  ", subsequent_indent="  "))
    ev = req.get("evidence") or ""
    if ev:
        print("\ncontext (canonical +/-600 chars):")
        print(textwrap.fill(ev, width=76, initial_indent="  ", subsequent_indent="  "))
    print("=" * 78)


def _review_batch(bid: str, redo: str | None) -> None:
    rp = _req_path(bid)
    if not rp.exists():
        sys.exit(f"no such batch requests file: {rp}")
    reqs = json.loads(rp.read_text(encoding="utf-8"))["requests"]
    by_id = _load_decisions(bid)
    if redo:
        by_id.pop(redo, None)

    todo = [r for r in reqs if r["tsu_id"] not in by_id]
    done = len(reqs) - len(todo)
    tally = {"APPROVED": 0, "CONDITIONAL": 0, "REJECTED": 0}
    for e in by_id.values():
        tally[e.get("final_decision", "CONDITIONAL")] = tally.get(e.get("final_decision", "CONDITIONAL"), 0) + 1

    print(f"{bid}: {len(reqs)} requests, {done} already decided, {len(todo)} to go.")
    if not todo:
        print("nothing to review. (use --redo <tsu_id> to revisit one)")
        return

    order = list(todo)
    idx = 0
    history: list[str] = []
    while idx < len(order):
        req = order[idx]
        _print_card(bid, done + idx + 1, len(reqs), tally, req)
        try:
            ans = {}
            for q in req.get("review_questions", []):
                ans[q["code"]] = _ask_answer(q["code"], q["label"], q["prompt"])
            q4 = _ask_q4()
            if q4:
                ans["Q4"] = q4
            comment = _ask("  comment (enter=none) > ") or None
            suggested = _final_from_answers(ans)
            ov = _ask(f"  final_decision = {suggested}  [enter=accept | A/C/R=override] > ").strip().upper()
            final = suggested
            if ov in ("A", "APPROVED"):
                final = "APPROVED"
            elif ov in ("C", "CONDITIONAL"):
                final = "CONDITIONAL"
            elif ov in ("R", "REJECTED"):
                final = "REJECTED"
        except _Skip:
            print("  -> skipped (left PENDING).")
            idx += 1
            continue
        except _Back:
            if history:
                prev = history.pop()
                by_id.pop(prev, None)
                tally_key = None
                # recompute tally
                tally = {"APPROVED": 0, "CONDITIONAL": 0, "REJECTED": 0}
                for e in by_id.values():
                    k = e.get("final_decision", "CONDITIONAL")
                    tally[k] = tally.get(k, 0) + 1
                _save_decisions(bid, by_id)
                # move order pointer back to the prev item
                order.insert(idx, next(r for r in reqs if r["tsu_id"] == prev))
                print(f"  -> back: {prev} cleared, re-review.")
            else:
                print("  -> nothing to go back to.")
            continue
        except _Quit:
            _save_decisions(bid, by_id)
            print(f"\nsaved. {len(by_id)} decisions in {_dec_path(bid)}")
            return

        entry = {
            "gate_id": req.get("gate_id") or f"GATE-{req['tsu_id']}",
            "tsu_id": req["tsu_id"],
            "reviewer_id": REVIEWER_ID,
            "answers": ans,
            "final_decision": final,
            "review_timestamp": _dt.date.today().isoformat(),
            "comment": comment,
        }
        by_id[req["tsu_id"]] = entry
        tally[final] = tally.get(final, 0) + 1
        history.append(req["tsu_id"])
        _save_decisions(bid, by_id)
        idx += 1

    print(f"\nbatch complete. {len(by_id)}/{len(reqs)} decided -> {_dec_path(bid)}")
    print(f"  APPROVED {tally['APPROVED']}  CONDITIONAL {tally['CONDITIONAL']}  REJECTED {tally['REJECTED']}")


def _stats(bid: str) -> None:
    rp = _req_path(bid)
    if not rp.exists():
        sys.exit(f"no such batch: {rp}")
    n = len(json.loads(rp.read_text(encoding="utf-8"))["requests"])
    by_id = _load_decisions(bid)
    t = {"APPROVED": 0, "CONDITIONAL": 0, "REJECTED": 0}
    for e in by_id.values():
        t[e.get("final_decision", "CONDITIONAL")] = t.get(e.get("final_decision", "CONDITIONAL"), 0) + 1
    print(f"{bid}: {len(by_id)}/{n} decided  "
          f"(A {t['APPROVED']}  C {t['CONDITIONAL']}  R {t['REJECTED']})")


def _list_all() -> None:
    files = sorted(glob.glob(str(REQUESTS_DIR / "fuller_v01_batch_*_requests.json")))
    grand = {"n": 0, "done": 0}
    for f in files:
        bid = Path(f).name.replace("_requests.json", "")
        n = len(json.loads(Path(f).read_text(encoding="utf-8"))["requests"])
        done = len(_load_decisions(bid))
        grand["n"] += n
        grand["done"] += done
        bar = "#" * (done * 20 // n) + "-" * (20 - done * 20 // n)
        print(f"  {bid}  [{bar}] {done:3d}/{n}")
    print(f"  TOTAL {grand['done']}/{grand['n']}  ({grand['done']*100//max(grand['n'],1)}%)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Fuller Vol.01 human-review recorder")
    ap.add_argument("--batch", help="batch number (1) or id (fuller_v01_batch_0001)")
    ap.add_argument("--list", action="store_true", help="show all batches + progress")
    ap.add_argument("--stats", action="store_true", help="show one batch's progress and exit")
    ap.add_argument("--redo", metavar="TSU_ID", help="clear one decision and re-review it")
    args = ap.parse_args()

    if args.list:
        _list_all()
        return
    if not args.batch:
        ap.error("--batch is required (or use --list)")
    bid = _batch_id(args.batch)
    if args.stats:
        _stats(bid)
        return
    _review_batch(bid, args.redo)


if __name__ == "__main__":
    main()
