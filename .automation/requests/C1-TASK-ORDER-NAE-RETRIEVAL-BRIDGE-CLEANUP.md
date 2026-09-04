# C1 Task Order — NAE Retrieval Bridge: Evidence Cleanup + Phase 7 Completion

| | |
|---|---|
| Issued by | CUE |
| Issued | 2026-08-15 |
| Executor | C1 |
| Verifier | CUE |
| Basis | `.automation/audit/NAE-RETRIEVAL-BRIDGE-CUE-INDEPENDENT-AUDIT.md` §3 |
| Scope | Cleanup + completion only — **no new investigation, no ADR-024, no production changes** |

---

## Background

CUE's independent audit confirmed the FEASIBLE finding but found 2 process
deviations and 1 incomplete phase. Fix these three before ADR-024 design begins.

## Items

**1. Relocate evidence to the mandated path**
Move (not copy-and-leave-duplicate) into `.automation/evidence/night-shift/nae-retrieval-bridge/`:
- `output/nae_bridge_probe_evidence.json`
- `output/nae_retrieval_bridge_feasibility_report.md`
Update any relative paths referenced inside the report if needed. Confirm `output/`
no longer holds these two files afterward.

**2. Quarantine the prototype script out of `scripts/`**
`scripts/nae_retrieval_bridge_probe.py` is a shared production-facing directory
per CLAUDE.md. Move it to
`.automation/evidence/night-shift/nae-retrieval-bridge/prototype/nae_retrieval_bridge_probe.py`.
It must not remain as a standing entry in `scripts/`. If anything referenced its
old path, update it.

**3. Complete Phase 7 (Citation/Provenance) — currently only field-presence checked**
Take one real hit already captured in the evidence JSON (has `tsu_id`, `source_id`,
`work_id`, `edition_id`, `source_text`, `metadata_provenance`) and actually run it
through `core/retrieval.py::CitationBuilder` (read the class first — do not guess
its constructor shape) to produce a real `Citation` object, in an isolated script
or REPL snippet — not by editing `CitationBuilder` itself. Record:
- exact call made
- resulting `Citation` object fields (repr or `__dict__`)
- whether any required `CitationBuilder` input was missing from the NAE payload
  (if so, name the exact missing field — this becomes required scope for ADR-024)
Save this as `.automation/evidence/night-shift/nae-retrieval-bridge/phase7-citation-roundtrip.md`
(command, code, input payload, output object, exit code).

## Constraints (unchanged from original Task Order)

- No modification to `core/retrieval.py`, `NAE/retrieval_adapter.py`'s existing
  `search()`, or any production file.
- No Qdrant mutation (read-only only).
- No ADR-024 authoring.
- If Phase 7 reveals a missing field that `CitationBuilder` requires and NAE
  payload cannot supply without an architecture change — stop, report to CUE as
  a "new architecture decision needed" finding. Do not patch around it.

## Report format

```
ITEM 1 — DONE/BLOCKED — evidence: <path>
ITEM 2 — DONE/BLOCKED — evidence: <path>
ITEM 3 — DONE/BLOCKED — evidence: <path>
```

CUE will re-verify each independently before this Night Shift is marked closed
and ADR-024 design begins.
