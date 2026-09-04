# C1 Task Order — NAE Retrieval Bridge Night Shift Closeout

| | |
|---|---|
| Issued by | CUE |
| Issued | 2026-08-15 |
| Executor | C1 |
| Verifier | CUE |
| Basis | `.automation/audit/NAE-RETRIEVAL-BRIDGE-CUE-INDEPENDENT-AUDIT.md` §3 |
| Scope | Closeout only — no new investigation, no ADR-024, no production wiring |

---

## Context

CUE's independent audit confirmed the FEASIBLE finding but is not GREEN yet. Three
items must close before ADR-024 design begins. This order has no other scope — do
not extend it.

---

## Item 1 — Relocate evidence to the mandated path

Move (not duplicate-and-leave-both) into
`.automation/evidence/night-shift/nae-retrieval-bridge/`:
- `output/nae_bridge_probe_evidence.json`
- `output/nae_retrieval_bridge_feasibility_report.md`

Report the `git mv`/`mv` commands used and confirm both files exist only at the new
path afterward (`ls` output as evidence).

## Item 2 — Quarantine the prototype script out of `scripts/`

`scripts/nae_retrieval_bridge_probe.py` is a shared production-facing directory per
CLAUDE.md. Move it to
`.automation/evidence/night-shift/nae-retrieval-bridge/prototype/nae_retrieval_bridge_probe.py`.
Confirm nothing else imports it (`grep -rn "nae_retrieval_bridge_probe" --include=*.py .`
should show no importers besides itself) before/after the move, so the move is safe.

## Item 3 — Run the actual CitationBuilder round-trip (Phase 7, was INCOMPLETE)

Using one real NAE hit already captured in the evidence JSON (e.g. `TSU-0002742`),
construct whatever input `core/retrieval.py::CitationBuilder` actually requires
(read the class first — do not guess its constructor) and call it with the NAE
payload's `source_id` / `work_id` / `edition_id` / `tsu_id` / `source_text` /
`metadata_provenance` mapped in. Capture:
- the exact mapping used (NAE field → CitationBuilder input field)
- the resulting `Citation` object's repr/fields
- whether any field was unavailable/had to be synthesized (do not silently drop or fake data — report gaps as gaps)

This is read-only against `core/retrieval.py` (call it, do not edit it). Save output
to `.automation/evidence/night-shift/nae-retrieval-bridge/phase7-citation-roundtrip.md`.

---

## Constraints (unchanged from original Task Order)

- No `core/retrieval.py` edits.
- No production Qdrant mutation (`dbma_qdrant` or `nae_qdrant` — this is still read-only work).
- No ADR-024 drafting.
- No new adapter functions beyond what's needed to call `CitationBuilder` for the test above.

## Report format

Per item: `ITEM N — PASS/INCOMPLETE/BLOCKED — 1-line summary — evidence path`.
