"""NAE Fuller F3 — pattern-based triage scan (read-only, no data mutation).

WHY: the F3 pilot review (320-item stratified sample, docs/
NAE_GOLD... no — see NAE/review/human/{requests,decisions}/
fuller_f3_pilot_sample_001_*, 2026-09-26) found a rejection rate of
27-45% dominated by a handful of *structural* defect classes that recur
because of how Fuller's 19th-century argumentative prose is written, not
random noise:
  - conditional/hypothetical clauses ("if...", "were...", "admitting
    that...") flattened into absolute claims
  - quoted / attributed statements (named opponents, "Mr. X says...",
    "according to...") presented as the author's own claim
  - rhetorical questions converted into flat assertions
  - truncated sentence fragments (OCR page/paragraph boundary cuts)
    built into claims

This script flags candidate records matching these *shapes* in
`source_text` so a human reviewer (or a future review-queue UI) can sort
"needs extra scrutiny" from "likely straightforward" before spending
review time. It does NOT judge whether a `claim` is actually wrong --
only that its `source_text` has a shape historically correlated with
higher defect rates. It writes nothing back into tsu.json; each volume's
report goes to its own tsu/<identifier>/f3_triage_flags.json.

Usage:
  python -m scripts.nae_fuller_f3_triage_scan --identifier Fuller_Complete_Works_Vol01
  python -m scripts.nae_fuller_f3_triage_scan --all
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TSU_ROOT = REPO_ROOT / "NAE" / "corpus" / "tsu"
TRIAGE_VERSION = "1.0.0"

_CONJ_OK_START = {
    "and", "but", "or", "if", "that", "which", "who", "whom", "he", "she",
    "it", "they", "so", "for", "as", "yet", "then", "not", "nor", "when",
    "where", "while", "since", "because", "though", "although", "after",
    "before", "until", "unless", "whether",
}

_QUOTE_ATTRIB_RE = re.compile(
    r"\b(says?|said|maintains?|argues?|objects?|replies?|answers?|"
    r"observes?|admits?|acknowledges?|professes?|contends?|according to|"
    r"asserts?)\b",
    re.IGNORECASE,
)
_NAMED_PERSON_RE = re.compile(r"\b(Mr|Mrs|Dr|Rev)\.\s+[A-Z][a-zA-Z']+")
_CONDITIONAL_START_RE = re.compile(
    r"^\s*(if|were|should|had|admitting|suppose|supposing|granting)\b",
    re.IGNORECASE,
)


def _flags_for(source_text: str) -> list[str]:
    s = source_text.strip()
    flags: list[str] = []

    if s.endswith("?"):
        flags.append("rhetorical_question")

    if _CONDITIONAL_START_RE.match(s):
        flags.append("conditional_hypothetical")

    if _QUOTE_ATTRIB_RE.search(s) or _NAMED_PERSON_RE.search(s) or ('"' in s):
        flags.append("quote_attribution")

    words = s.split()
    first_word = words[0] if words else ""
    starts_lower_odd = bool(first_word) and first_word[0].islower() and (
        first_word.lower().strip(",;:") not in _CONJ_OK_START
    )
    ends_broken = bool(re.search(r"[a-zA-Z]-\s*$", s))
    very_short = len(words) < 8
    if starts_lower_odd or ends_broken:
        flags.append("truncated_fragment")
    elif very_short:
        flags.append("very_short_fragment")

    return flags


def scan_volume(identifier: str) -> dict:
    vol_dir = TSU_ROOT / identifier
    tsu_path = vol_dir / "tsu.json"
    if not tsu_path.exists():
        return {"identifier": identifier, "error": "tsu.json not found"}

    records = json.loads(tsu_path.read_text(encoding="utf-8"))
    flagged = []
    counts: dict[str, int] = {}
    for r in records:
        flags = _flags_for(r.get("source_text", ""))
        if not flags:
            continue
        for f in flags:
            counts[f] = counts.get(f, 0) + 1
        flagged.append({
            "tsu_id": r.get("id"),
            "doctrine": r.get("doctrine"),
            "flags": flags,
        })

    report = {
        "identifier": identifier,
        "triage_version": TRIAGE_VERSION,
        "total_records": len(records),
        "flagged_records": len(flagged),
        "flag_counts": counts,
        "items": flagged,
    }
    (vol_dir / "f3_triage_flags.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fuller F3 pattern-based triage scan (read-only)")
    ap.add_argument("--identifier")
    ap.add_argument("--all", action="store_true")
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

    grand_total = grand_flagged = 0
    for ident in targets:
        r = scan_volume(ident)
        if r.get("error"):
            print(f"[{ident}] SKIP — {r['error']}")
            continue
        grand_total += r["total_records"]
        grand_flagged += r["flagged_records"]
        print(f"[{ident}] total={r['total_records']} flagged={r['flagged_records']} "
              f"({100*r['flagged_records']/r['total_records']:.1f}%) — {r['flag_counts']}")

    if grand_total:
        print(f"\nTOTAL: {grand_flagged}/{grand_total} flagged ({100*grand_flagged/grand_total:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
