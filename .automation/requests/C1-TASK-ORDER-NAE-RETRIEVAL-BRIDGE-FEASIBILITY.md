# C1 Task Order — NAE Production Retrieval Bridge Feasibility Investigation

| | |
|---|---|
| Issued by | CUE |
| Issued | 2026-08-15 |
| Executor | C1 |
| Verifier | CUE |
| Approver (final) | Rev. Bang |
| Status | ISSUED (pending CUE pre-review gate before C1 executes) |

---

## 0. Purpose (scope-limited)

**"NAE Qdrant를 현재 DBMA Retrieval Architecture(`core/retrieval.py::RetrievalEngine`)를
보존하면서 Production Retrieval 경로에 연결할 수 있는가?"**

This Task Order produces investigation evidence only. It does **not**:
- write or approve ADR-024
- make any Architecture decision
- modify `core/retrieval.py` production behavior
- mutate Production Qdrant (`dbma_qdrant`, port 6333) or NAE Qdrant (`nae_qdrant`, port 7333) production data

---

## 1. Prior Facts (established by CUE before issuing this order — do not re-derive)

- **ADR-001** (Accepted): `core/retrieval.py::RetrievalEngine` is the sole Retrieval Engine
  Authority. No parallel retrieval path may be created.
- **ADR-003** (Accepted, corrected SPRINT20-H-3): `RetrievalEngine` currently queries
  **no persistent vector store at all** — it uses the TSU dataset
  (`output/bench/tsu_dataset.jsonl`) + `core/embedder.py` (BGE-M3 via Ollama) +
  in-memory cosine/TF-IDF similarity. Legacy Chroma/Qdrant (`dbma_qdrant`, port 6333)
  are frozen artifacts, not queried by RetrievalEngine.
- **ADR-013** (Accepted): NAE has its own fully isolated Qdrant instance
  (`nae_qdrant`, port 7333, collection `nae_tsu_v{TSU_SCHEMA_VERSION}`, currently
  `nae_tsu_v1`). ADR-013 explicitly states: *"향후 NAE corpus를 RetrievalEngine의
  production 경로에 통합하려면 이 ADR을 개정하는 신규 ADR이 필요하다."*
- **`NAE/retrieval_adapter.py`** already exists (34 lines, module `NAE-OPTIONAL-MODULE-PACKAGING-001`).
  It is an explicit, one-directional adapter stub: `RetrievalEngine` does not import it,
  it does not import `RetrievalEngine`. It gates on `core/module_registry.py`
  (`is_enabled("nae_pd")`) and calls `NAE.pipeline.index.qdrant_store.get_client()`
  to search `nae_tsu_v1`. **C1 must treat this file as the existing injection point
  candidate and start Phase 4 from it — do not assume no adapter exists.**
- Related design doc: `docs/NAE_OPTIONAL_MODULE_PACKAGING_v1.md`.

Because `RetrievalEngine` has no vector-store query path today, "connecting NAE to
production retrieval" is not a one-line swap — it implies either (a) NAE search results
being merged into `RetrievalEngine`'s in-memory candidate set via an explicit adapter
call (module-boundary pattern, matching `retrieval_adapter.py`'s existing design), or
(b) a deeper architecture change. **Which of these is actually required is exactly
what this investigation must determine — do not assume (a).**

---

## 2. Role Separation

**C1 (executor)**:
- Phase 1–9 investigation, prototyping, testing (below)
- All work in isolated/read-only contexts unless a phase explicitly permits a
  temp/prototype write (must go to a scratch path, never Production)
- Writes raw evidence (commands, inputs, outputs, exit codes, logs) to
  `.automation/evidence/night-shift/nae-retrieval-bridge/`
- Does **not** interpret results as final feasibility judgment — reports facts only

**CUE (verifier)**:
- Confirms this Task Order does not conflict with ADR-001/003/013 before issuing (§10 below)
- After each phase, reviews C1's evidence against Architecture boundary
- Classifies any failure (bug / fixture / env / architecture constraint / new
  architecture decision needed) per §5 of the Night Shift directive
- Issues PASS → next phase / INCOMPLETE → rework / STOP → escalate
- Writes final feasibility verdict (FEASIBLE / PARTIALLY_FEASIBLE / NOT_FEASIBLE / UNKNOWN)

**Rev. Bang (approver)**: Architecture changes, ADR-024 approval, Production boundary
changes — none of which occur in this Task Order.

---

## 3. Phases (execute in order; do not skip ahead on failure — investigate first)

**Phase 1 — RetrievalEngine architecture inspection**
Read `core/retrieval.py` (`RetrievalEngine`, `QueryProcessor`, `EmbeddingCache`,
candidate scoring functions). Document: where candidates enter the ranking pipeline,
what shape a "candidate" dict/object must have, where an external result set could
be merged without modifying `RetrievalEngine`'s public contract.

**Phase 2 — NAE Qdrant schema inspection**
Read `NAE/pipeline/index/qdrant_store.py`, `NAE/pipeline/index/config.py` (or
equivalents). Document collection name, vector size/model, payload schema for
`nae_tsu_v1` points. Read-only (`client.get_collection`, `client.scroll`) against
`nae_qdrant` (port 7333) — never `dbma_qdrant`.

**Phase 3 — Compatibility matrix**
Compare RetrievalEngine's expected candidate shape (Phase 1) against NAE Qdrant
payload shape (Phase 2). Table: field-by-field match / mismatch / missing.

**Phase 4 — Adapter injection feasibility**
Evaluate `NAE/retrieval_adapter.py` as the injection point. Can its `search()` output
be transformed into RetrievalEngine candidates without touching `core/retrieval.py`?
Identify exact transform code needed (as a proposal, not yet written into production).

**Phase 5 — Isolated prototype**
Write a prototype (scratch script/notebook under
`.automation/evidence/night-shift/nae-retrieval-bridge/prototype/`, NOT under `core/`
or `NAE/` production paths) that calls `retrieval_adapter.search()` and transforms
output into RetrievalEngine-shaped candidates in-memory only. No production file edits.

**Phase 6 — Real NAE retrieval proof**
Run the Phase 5 prototype against live `nae_qdrant` (read-only search calls) with a
real query. Capture actual hits, scores, payload.

**Phase 7 — Citation/provenance verification**
Confirm NAE TSU payload carries enough provenance (source doc, canonical_id per
ADR-017, page/location) to build a `Citation` via `core/retrieval.py::CitationBuilder`
without modification.

**Phase 8 — Regression**
Run existing RetrievalEngine test suite (e.g. `tests/test_book_alias_resolution.py`,
`tests/test_query_enhancements_full_regression.py`) unmodified, confirm zero change
in pass/fail state — proves nothing in production path was touched.

**Phase 9 — Final evidence package**
Assemble all phase outputs into `.automation/evidence/night-shift/nae-retrieval-bridge/EVIDENCE-INDEX.md`.

If any phase fails: stop, classify (bug/fixture/env/architecture-constraint/
new-decision-needed) per Night Shift directive §5, report to CUE before proceeding.

---

## 4. Evidence Requirements (every phase)

Command · source file · relevant line · input · output · exit code · test result ·
mutation yes/no. Conclusions without command+output are not accepted. Store under:

```
.automation/evidence/night-shift/nae-retrieval-bridge/
```

---

## 5. Hard Stop Conditions (same as Night Shift directive §6)

Immediately stop and escalate to CUE (not Rev. Bang directly) if any of:
1. Production `RetrievalEngine` behavior modification appears required
2. Production Qdrant (`dbma_qdrant`) or `nae_qdrant` production data mutation appears required
3. An existing ADR (001/003/013/017) would need to be violated to proceed
4. DBMA Core architecture change appears required
5. NAE schema change appears required
6. Existing regression tests would break
7. A new Architecture decision is clearly required to go further

Do not implement a workaround for any of the above. Collect evidence, stop, report to CUE.

**Never touch**: RAW data, `core/retrieval.py` production behavior, embedding model
config, TSU pipeline production contract, ADR-001/003/013/017, Production Qdrant,
NAE/DBMA corpus isolation.

---

## 6. Output format expected from C1 per phase

Short status: `PHASE N — <PASS|INCOMPLETE|BLOCKED> — <1-line summary> — evidence: <path>`

---

## 7. CUE Pre-Review Gate (must PASS before this order is sent to C1)

- [ ] Conflicts with ADR-001 (sole Retrieval Engine Authority)? → No: adapter pattern
      keeps RetrievalEngine untouched, matches existing `retrieval_adapter.py` design.
- [ ] Conflicts with ADR-003 (no new production dependency on Chroma/Qdrant without
      new ADR)? → No: NAE Qdrant is not being added to the *production* RetrievalEngine
      path in this order — only read-only investigation/prototype in isolated scope.
      Actually wiring it into production would itself require the ADR-024 this order
      explicitly defers.
- [ ] Conflicts with ADR-013 (NAE Qdrant isolated, integration requires new ADR)? →
      No: this order investigates feasibility only, does not integrate.
- [ ] Requires Architecture decision to execute Phases 1–9 as scoped? → No.
- [ ] Requires Production mutation to execute Phases 1–9 as scoped? → No (Phase 5/6
      write only to scratch path and read-only query `nae_qdrant`).

**CUE Pre-Review verdict: PASS — Task Order may be issued to C1.**
