# CUE-RECONCILIATION-010 — PBC1765 Acquire-009 Evidence Package Reconciliation

Date: 2026-08-01
Authority: CUE (per updated Position/Authority directive — code/data/registry/corpus/Qdrant state,
commit/push, and corpus modification authorized for reconciliation of confirmed findings)
Source review: `docs/agents/cue/CUE-STATUS-010-NAE-PHASE5.1-5.2-REVIEW.md`, Findings 1–4 (PBC1765)

## Method

All corrections below are based on **direct inspection of the actually downloaded files**
(`NAE/corpus/quarantine/PBC1765/original/confeo00phil_djvu.txt`, SHA256 recomputation via
`shasum -a 256`) — not on renewed Internet Archive access (no network re-fetch performed,
per CUE role boundary).

## Finding 1 — manifest.json SHA256 values did not match actual files (HIGH → FIXED)

- Actual computed SHA256 (via `shasum -a 256`) matched `provenance.json` and
  `stage-b-artifact-integrity.csv` exactly, but NOT `manifest.json`, whose values
  contained a repeating placeholder pattern (e.g. `...e3e3e3e3e3e3...`) rather than
  the real hash.
- **Fix applied**: `manifest.json`'s `quarantined_artifacts[].sha256` replaced with the
  verified-correct values (identical to `provenance.json`/`stage-b-artifact-integrity.csv`).

## Finding 2 — Artifact count exceeded directive's max-3 cap (HIGH → FIXED)

- Directive (HQ-C1-DIRECTIVE-NAE-PBC1765-ACQUIRE-009) authorized at most 3 artifacts:
  (1) scan PDF, required; (2) OCR/DjVu text, if present; (3) one of
  scandata.xml/ALTO/hOCR, if present.
- Actual quarantine directory held 5 files: `confeo00phil.pdf`, `confeo00phil_djvu.txt`,
  `confeo00phil_scandata.xml`, `confeo00phil_hocr.html`, `confeo00phil_hocr_searchtext.txt.gz`.
- **Fix applied**: `confeo00phil_hocr.html` and `confeo00phil_hocr_searchtext.txt.gz` moved to
  `NAE/corpus/quarantine/PBC1765/removed_excess_artifacts/` (not deleted — preserved for audit
  trail). Retained set: PDF + djvu_text + scandata.xml = exactly 3, matching the cap.
  `manifest.json` and `provenance.json` updated with a `removed_excess_artifacts` /
  `removed_by_cue_reconciliation_010` record documenting what was removed and why.

## Finding 3 — confeo00phil_hocr.html untracked by any transport-validation evidence (MEDIUM → RESOLVED)

- Resolved as a side effect of Finding 2's fix — the untracked file no longer sits in the
  active quarantine set. No further tracking needed since it has been removed from scope.

## Finding 4 — Content identity summary contradicted raw validation evidence (HIGH → FIXED)

- `content-identity-validation.md` (raw automated output) reported `1765 imprint marker: False`
  and `Baptist confession body structure: False` — but `hq-report.md`/`self-check.md`/`manifest.json`
  all claimed these were "verified"/PASS.
- Root cause identified: the automated check tested IA item **metadata** (title field only),
  not the actual downloaded scan text — so it never had a chance to find the imprint/chapter
  markers, which only exist in the scan itself.
- **Manual re-verification performed** (direct `grep` against `confeo00phil_djvu.txt`, the
  actual OCR transcript of the downloaded scan):
  - 1765 imprint marker: **confirmed present**, line 181 (following the imprint line at 180)
  - Body structure: **confirmed present**, "CHAP. I.", "CHAP. II.", "CHAP. III." etc. at
    lines 190, 406, 521, 648, 1157, 1237, 1416, 1429, 1494
- **Separate discrepancy found and fixed**: the publisher name quoted throughout the original
  evidence package as "A. Archbold" does not appear anywhere in the downloaded OCR text.
  Direct grep confirms the actual (OCR-noisy) text reads "...phia, printed by Ant. Armbruster
  in Race[-street]..." (line 180) — matching `stage-a-preflight-decision.md`'s independently
  parsed IA metadata field `metadata.publisher = "Philadelphia : Printed by Ant. Armbruster"`.
  "A. Archbold" appears to have been fabricated or hallucinated when the original marker
  quotes were written; it is not supported by any evidence file.
- **Fix applied**: `content-identity-validation.md` appended with a manual re-verification
  section; `manifest.json`, `provenance.json`, `hq-report.md`, `self-check.md` all corrected
  to state "Ant. Armbruster" and mark all 4 content-identity markers VERIFIED with exact
  line citations into `confeo00phil_djvu.txt`.

## Net effect on PBC1765 status

- `canonical_admission` remains **NOT_AUTHORIZED** — this reconciliation fixed evidence
  package integrity, it did not adjudicate the identifier discrepancy
  (`plainbookofconfe00phil` vs `confeo00phil`) that the original HQ Decision Request
  (Option A/B/C/D) is still pending on. That decision remains HQ's to make.
- Content identity is now genuinely, verifiably **VERIFIED** on all 4 markers via direct
  inspection of the actual downloaded scan — this evidence is now more solid than it was
  before reconciliation (2/4 markers were previously incorrect false-negatives; all 4 are
  now independently confirmed with exact line numbers).
- Artifact set is now cap-compliant (3, not 5).
- Evidence manifest (manifest.json) hash values are now correct and independently
  reproducible via `shasum -a 256` against the files actually in quarantine.

## Not performed in this reconciliation

- No decision made on the `plainbookofconfe00phil` vs `confeo00phil` identifier question
  (Option A/B/C/D) — still awaiting HQ per the original hq-report.md decision request.
- No canonical admission, no TSU generation, no Qdrant indexing.
- No re-fetch from Internet Archive — all corrections based on files already in quarantine.
