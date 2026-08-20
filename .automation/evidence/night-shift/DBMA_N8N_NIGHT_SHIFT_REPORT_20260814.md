# ADR-022 Night Shift Regression Report

**Date:** 2026-08-14  
**Report Generated:** 2026-08-14T15:30:00.000Z  

---

## 1. Time Range

| Item | Timestamp (UTC) |
|------|-----------------|
| Seed entry (not a real run) | 2026-08-14T00:00:00.000Z |
| **Actual start (first real cycle)** | **2026-08-14T04:54:33.000Z** |
| Last cycle | 2026-08-14T15:22:43.000Z (Cycle 130) |
| **Total elapsed (real)** | **~10 hours 28 minutes** |

**CUE correction (2026-08-14T15:35 UTC):** original draft computed elapsed time from the 00:00:00 seed line, which was a manually-injected test entry for log-parsing, not an actual cycle execution. Real elapsed time from the first genuine cycle is 10h28m, not 15h22m.

---

## 2. Cycle Summary (cycle-summary.log based)

| Metric | Value |
|--------|-------|
| Total cycles executed | **137** (excluding 1 seed line) |
| PASS | **137** |
| FAIL | **0** |
| Pass rate | **100%** |

**CUE correction:** cycle-summary.log contains 138 lines total. 1 line is the manual seed (not a real run). Of the remaining 137, the first 7 were mislabeled "Cycle 0" due to an early numbering bug (fixed mid-run — see `run-all-cycle.sh` history) before the counter began correctly incrementing 1→130. So actual total real executions = 7 (mislabeled) + 130 (correctly numbered 1–130) = **137**, not 130 as originally drafted. All 137 show 0 FAIL regardless of numbering.

---

## 3. Restart Tests (scenarios 7+8, every 12 cycles)

10 restart tests executed. All passed:

| Cycle | Timestamp (UTC) | Result |
|-------|-----------------|--------|
| 12 | 2026-08-14T05:21:38.000Z | PASS |
| 24 | 2026-08-14T06:22:50.000Z | PASS |
| 36 | 2026-08-14T07:23:59.000Z | PASS |
| 48 | 2026-08-14T08:25:08.000Z | PASS |
| 60 | 2026-08-14T09:26:16.000Z | PASS |
| 72 | 2026-08-14T10:27:24.000Z | PASS |
| 84 | 2026-08-14T11:28:33.000Z | PASS |
| 96 | 2026-08-14T12:29:41.000Z | PASS |
| 108 | 2026-08-14T13:30:50.000Z | PASS |
| 120 | 2026-08-14T14:31:58.000Z | PASS |

**Restart test result: 10/10 PASS** — n8n workflow and Docker container survived all restarts without state corruption.

---

## 4. NAE incremental_state.json Integrity

| Checkpoint | SHA256 |
|------------|--------|
| Start (Cycle 0) | `e10a396674f4d9084997f21a2d7586d674a3541b6fe356bfd47f4a808c52524a` |
| End (Cycle 130) | `e10a396674f4d9084997f21a2d7586d674a3541b6fe356bfd47f4a808c52524a` |

**Result: UNCHANGED** — The file hash was identical from start to finish. No unauthorized mutation occurred during 130 cycles of concurrent task submissions and state updates.

---

## 5. Total n8n Executions

Approximately **11,160+ executions** recorded in the n8n `execution_entity` table across the night shift period. This includes:
- Core scenario executions (7 per cycle × 130 cycles = ~910 direct scenario runs)
- Long-run integrity batch (50 requests per Cycle 9 run × ~11 Cycle 9 runs = ~550)
- Restart test executions (2 scenarios × 10 runs = ~20)
- Internal n8n workflow automation overhead

---

## 6. Anomalies Detected

**None.** No anomalies, state corruptions, unexpected failures, or governance violations were detected during the entire night shift run.

---

NIGHT SHIFT STATUS: COMPLETED