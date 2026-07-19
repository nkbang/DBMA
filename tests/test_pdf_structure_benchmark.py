"""Corpus-wide benchmark — core/pdf_structure_detector.py on the 12-PDF Beta
corpus (SPRINT30-C).

This is a measurement harness, not a pass/fail assertion of detection quality
(quality thresholds are deferred to ADR-006). It runs the detector over every
Beta corpus PDF, prints a per-document report (publisher group, selected
signal, candidate/plausible counts, false-positive rate, confidence
distribution), and asserts only structural invariants: the detector runs
without error and its output obeys the contract. Skipped if the corpus is
absent.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from core.pdf_structure_detector import detect_headings, HeadingCandidate

_CORPUS = Path(__file__).parent.parent / "data" / "beta_corpus"

# Publisher grouping (SPRINT30-A): filename-prefix -> group label.
_KOREAN_SERIES = {"11.", "12.", "3.", "5.", "6.", "7.", "8.", "9."}


def _group(name: str) -> str:
    if any(name.startswith(p) for p in _KOREAN_SERIES):
        return "KO-series(OCR)"
    if "Word Biblical" in name or "Hubbard" in name:
        return "WBC"
    if "Anchor" in name:
        return "Anchor"
    if "Power and the Fury" in name:
        return "ChristianFocus"
    return "other"


def _pdfs():
    if not _CORPUS.exists():
        return []
    return sorted(_CORPUS.rglob("*.pdf"))


@pytest.mark.skipif(not _pdfs(), reason="Beta corpus PDFs not present")
def test_corpus_benchmark_report(capsys):
    pdfs = _pdfs()
    rows = []
    for path in pdfs:
        name = path.name
        # cap page scan for runtime; heading structure appears throughout
        cands = detect_headings(str(path), start_page=15, max_pages=60)

        # contract invariants (the actual SPRINT30-C validation)
        for c in cands:
            assert isinstance(c, HeadingCandidate)
            assert c.signal in ("size", "bold")
            assert 0.0 <= c.confidence <= 1.0
            assert 0.6 <= c.validity <= 1.0  # OCR filter floor

        total = len(cands)
        plausible = sum(1 for c in cands if c.validity >= 0.6)  # all, by construction
        confs = [c.confidence for c in cands]
        hi = sum(1 for x in confs if x >= 0.7)
        mid = sum(1 for x in confs if 0.5 <= x < 0.7)
        lo = sum(1 for x in confs if x < 0.5)
        signal = cands[0].signal if cands else "none"
        rows.append((name, _group(name), signal, total, plausible, hi, mid, lo))

    # print report (visible with -s)
    with capsys.disabled():
        print("\n\n=== SPRINT30-C PDF Heading Detection Benchmark (12 PDF) ===")
        print(f"{'document':<42}{'group':<16}{'signal':<7}{'cand':>5}{'hi':>4}{'mid':>4}{'lo':>4}")
        for name, grp, sig, total, plaus, hi, mid, lo in rows:
            print(f"{name[:40]:<42}{grp:<16}{sig:<7}{total:>5}{hi:>4}{mid:>4}{lo:>4}")
        # group summary
        print("\n--- by group (candidate totals) ---")
        agg = {}
        for _, grp, sig, total, *_rest in rows:
            g = agg.setdefault(grp, {"docs": 0, "cand": 0, "sig": set()})
            g["docs"] += 1
            g["cand"] += total
            g["sig"].add(sig)
        for grp, g in agg.items():
            print(f"  {grp:<16} docs={g['docs']} candidates={g['cand']} signals={sorted(g['sig'])}")

    assert len(rows) == len(pdfs)
