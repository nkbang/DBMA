"""
scripts/adr011_noise_classifier_repetition_delta.py — ADR-011 제안4 §2:
before/after HEADER_FOOTER classification counts once
core.noise_classifier.classify() is given a document-scoped
core.repetition_detector.RepetitionTracker signal, on Profile B (the
running-header-affected genre).

Diagnostic/analysis artifact only — NOT part of the production pipeline.
core/ must never import this module. Reuses the same candidate extraction
as scripts/shadow_d5_metrics.py.

Usage:
    python scripts/adr011_noise_classifier_repetition_delta.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from shadow_boundary_analysis import MD_DIR, _extract_body_text, _resolve_pdf
from shadow_boundary_delta import candidates_with_offsets
from core.config import DEFAULT_CHUNK_SIZE
from core.hierarchical_chunk_builder import SAFETY_CAP_RATIO
from core.noise_classifier import classify
from core.repetition_detector import RepetitionTracker
from core.text_normalizer import normalize_pipeline_text

SAFETY_CAP = int(DEFAULT_CHUNK_SIZE * SAFETY_CAP_RATIO)


def classify_profile(candidates: List[Tuple[str, int]]) -> str:
    return "B" if any(len(text) > SAFETY_CAP for text, _ in candidates) else "A"


def main() -> None:
    md_files = sorted(MD_DIR.glob("*_pdf.md"))
    rows = []
    for md_path in md_files:
        chunks_path = md_path.with_name(md_path.stem + "_chunks.txt")
        if not chunks_path.exists():
            continue
        body_text = _extract_body_text(md_path.read_text(encoding="utf-8"))
        normalized = normalize_pipeline_text(body_text)
        candidates = candidates_with_offsets(normalized)
        profile = classify_profile(candidates)
        if profile != "B":
            continue

        before_count = sum(1 for text, _ in candidates if classify(text).noise_type == "HEADER_FOOTER")

        tracker = RepetitionTracker()
        after_count = 0
        for text, _ in candidates:
            signal = tracker.observe(text)
            if classify(text, repetition_signal=signal).noise_type == "HEADER_FOOTER":
                after_count += 1

        rows.append((md_path.stem.replace("_pdf", ""), len(candidates), before_count, after_count))

    print(f"{'document':<50} {'candidates':>10} {'HEADER_FOOTER before':>21} {'after':>7} {'delta':>7}")
    tot_candidates = tot_before = tot_after = 0
    for name, n, before, after in rows:
        print(f"{name:<50} {n:>10} {before:>21} {after:>7} {after - before:>+7}")
        tot_candidates += n
        tot_before += before
        tot_after += after
    print()
    print(f"Profile B total: candidates={tot_candidates} HEADER_FOOTER before={tot_before} after={tot_after} delta={tot_after - tot_before:+d}")


if __name__ == "__main__":
    main()
