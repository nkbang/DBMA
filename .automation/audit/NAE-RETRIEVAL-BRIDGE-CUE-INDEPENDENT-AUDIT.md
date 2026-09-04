# CUE Independent Audit — NAE Production Retrieval Bridge Feasibility

| | |
|---|---|
| Auditor | CUE |
| Date | 2026-08-15 |
| Subject | C1 Night Shift report: `output/nae_retrieval_bridge_feasibility_report.md` |
| Verdict | **GREEN — with 2 process deviations to correct before ADR-024** |

---

## 1. Verified independently (re-derived, not trusted from C1's narrative)

| Claim | Verification method | Result |
|---|---|---|
| `core/retrieval.py` unmodified | `git diff --stat core/retrieval.py` | empty — untouched ✅ |
| `nae_pd` module is opt-in (disabled by default) | Read `config.yaml:130-133` | `modules.nae_pd.enabled: false` ✅ opt-in confirmed |
| Probe script contains no Qdrant mutation calls | `grep upsert\|delete\|set_payload\|create_collection` on `scripts/nae_retrieval_bridge_probe.py` | 0 matches; file's own header states "read-only (no upsert/delete)" ✅ |
| Probe never touches Production Qdrant (`dbma_qdrant`, 6333) | `grep "6333\|dbma_qdrant\|dbma_sermon"` | 0 matches — only `nae_qdrant`/7333 referenced ✅ |
| Evidence JSON matches report's headline numbers | Opened `output/nae_bridge_probe_evidence.json` directly | Query 1 latency 946.46ms (report: 946.5ms), dimension 1024, `nae_actual_points: 3319`, real TSU payloads with `tsu_id/source_id/edition_id/work_id/metadata_provenance` present ✅ matches |
| Existing retrieval regression suite still green | Ran `pytest tests/test_book_alias_resolution.py tests/test_query_enhancements_full_regression.py` myself | 28 passed, 0 failed ✅ (C1 reported "14 retrieval tests" — different subset count, but no failures either way, no regression) |
| Broader NAE test surface still green | Ran `pytest tests/ -k "nae_benchmark or nae_qdrant or nae_verify"` myself | 176 passed, 0 failed ✅ |
| No production file mutation from this work | `git status --short core/ NAE/` filtered to tracked-file changes | 0 tracked-file modifications; only new untracked files (`scripts/nae_retrieval_bridge_probe.py`, `NAE/pipeline/registration/cli_driver.py` — pre-existing, unrelated) ✅ |

**Did not independently re-verify**: the exact "77/77 NAE benchmark" figure (would require running `NAE/benchmark/runner.py` against the gold dataset live, which is a longer job) and full `CitationBuilder` round-trip (see §3 below). Flagged as unverified, not disproven.

---

## 2. Confirms user's four audit questions

1. **Adapter boundary safe / opt-in?** — Confirmed. `nae_pd: enabled: false` by default in `config.yaml`; `NAE/retrieval_adapter.py::search()` raises `NaePdModuleDisabledError` unless explicitly enabled. `core/retrieval.py` does not import this module in either direction. This is a real opt-in boundary, not cosmetic.

2. **Prototype vs. production integration distinguished?** — Correctly distinguished in the report itself: "REQUIRED CHANGES" section explicitly defers actual wiring (`bridge_query()` extension, `config.yaml` flip, UI tab) to a future ADR-024 decision. The probe is read-only and additive-only (new script, no edits to existing production files). Agreed this is proof-of-technique, not integration-ready.

3. **Hybrid retrieval gap disclosed?** — Yes, explicitly listed under RISKS: NAE adapter is vector-only, no BM25/theological scoring (SSA/TRS/SUS) applied to NAE results. This is a real architecture asymmetry and correctly not hidden.

4. **Citation/provenance fields present end-to-end?** — **Partially verified.** I confirmed directly in `output/nae_bridge_probe_evidence.json` that returned hits carry `source_id`, `work_id`, `edition_id`, `tsu_id`, `source_text`, `metadata_provenance`. **However**, the report's Phase 7 claim is about field *presence* in the raw NAE payload — it does not show these fields actually being passed through `core/retrieval.py::CitationBuilder` to produce a `Citation` object. That transform was never executed. **This phase should be marked INCOMPLETE, not PASS.**

---

## 3. Findings requiring correction

**Process deviation 1 — evidence not stored at mandated path.**
Task Order §4/§13 required all evidence under `.automation/evidence/night-shift/nae-retrieval-bridge/`. That directory is empty. C1 instead wrote to `output/nae_bridge_probe_evidence.json` and `output/nae_retrieval_bridge_feasibility_report.md`. Not a safety issue, but a Task Order compliance gap — evidence discoverability and archive convention broken. **Correction: move/copy these two files (and the probe script, or a copy of it) into the mandated evidence directory before this Night Shift is considered closed.**

**Process deviation 2 — prototype script placed in a production-shared directory.**
Task Order Phase 5 required the prototype to live outside `core/`/`NAE/` production paths, in a scratch location. `scripts/` is a shared, committed, production-facing directory (per CLAUDE.md `scripts/`: "실행 및 평가 스크립트"). Placing an experimental probe there blurs prototype/production boundary — even though the script itself is inert (read-only, not imported by anything). **Correction: relocate to the evidence directory or clearly mark/quarantine, not leave as a standing entry in `scripts/`.**

**Gap — Phase 7 (Citation/Provenance) not fully executed.**
As above: field presence confirmed, actual `CitationBuilder` integration not run. **This must be closed (or explicitly deferred into ADR-024 scope) before "Citation/Provenance: ✅" is claimed in any roadmap doc.**

---

## 4. Verdict

**FEASIBLE (B Option)** — confirmed independently, not just accepted from C1's self-report. The core technical claim — NAE Qdrant can be queried and mapped into DBMA-compatible candidates without modifying `core/retrieval.py`, under an opt-in module gate, with zero production mutation — holds up under direct re-verification.

**Not yet GREEN for "close Night Shift"**: the two process deviations (§3) should be fixed and Phase 7 completed before this feasibility result is treated as final input to ADR-024 design. Recommend one short follow-up task to C1 (evidence relocation + CitationBuilder round-trip), not new investigation scope — then proceed to ADR-024.

**C1 should not receive new implementation work in the meantime**, consistent with the user's instruction — the follow-up below is cleanup/completion of already-issued Phase 7, not new scope.
