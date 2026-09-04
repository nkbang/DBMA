=== CONTENT IDENTITY VALIDATION (original automated check, 2026-07-31) ===
Title marker found: True
  Sample: <rdf:li xml:lang="x-default">The Baptist confession of faith : first put forth in 1643 ; afterwards enlarged, corrected 
Philadelphia marker found: True
  Sample: <rdf:li xml:lang="x-default">The Baptist confession of faith : first put forth in 1643 ; afterwards enlarged, corrected 
1765 imprint marker found: False
Baptist confession body structure found: False
Error page detected: False

=== CUE-RECONCILIATION-010 MANUAL RE-VERIFICATION (2026-08-01) ===

The two "False" results above were checked against IA item metadata only
(title-field regex), not against the actual downloaded scan text. Direct grep
of the quarantined confeo00phil_djvu.txt (the real OCR transcript of the scan)
finds both markers genuinely present — the original automated check's "False"
results were false negatives caused by checking the wrong source, not evidence
of the markers' absence:

- 1765 imprint marker: TRUE
  confeo00phil_djvu.txt line 180-181 (OCR noise, long-s/ligature artifacts):
  ":c!phia>  printed   by  Ar.t.  Armhrttflcr  in  Rac*-" / "f;nct>  1765."
  Reading through OCR noise: "[Philadel]phia, printed by Ant. Armbruster in
  Race[-street, 1765]." — matches the IA metadata publisher field exactly
  (stage-a-preflight-decision.md: "Philadelphia : Printed by Ant. Armbruster").

- Baptist confession body structure: TRUE
  confeo00phil_djvu.txt lines 190, 406, 521, 648, 1157, 1237, 1416, 1429, 1494:
  "CHAP.     I.", "CHAP.     II.", "CHAP.     III." ... multiple sequential
  chapter headings present, consistent with the confession's expected
  chapter-based structure.

CORRECTION: content_identity status is VERIFIED on all 4 markers, not 2/4 as
the original automated check reported. Separately, the publisher name quoted
in manifest.json/provenance.json/hq-report.md as "A. Archbold" was in error —
no such string exists anywhere in the downloaded OCR text; the verified
correct reading is "Ant. Armbruster", matching the IA metadata.

See evidence/phase5_2/pbc1765_acquire_009/CUE-RECONCILIATION-010.md for the
full finding-by-finding record.
