# Phase 1 — TSU Generation (Fuller_Complete_Works_Vol01)

## Status: RUNNING (background via launchd)

## Pre-flight Evidence

### Qdrant Baseline
```
Baseline points: 3319
Collection: nae_tsu_v1
Host: localhost:7333
```

### Canonical.json Verification
```
identifier: Fuller_Complete_Works_Vol01
source_id: None (registration will compute)
doc_type: None
page_count: 1
File: NAE/corpus/canonical/Fuller_Complete_Works_Vol01/canonical.json
Size: 2,765,539 bytes
Modified: 2026-08-07 00:10
```

### TSU Directory Check (before Phase 1)
```
NAE/corpus/tsu/Fuller_Complete_Works_Vol01/ — EXISTS but EMPTY (0 claims)
  tsu.json: [] (from earlier partial run, 2 candidates evaluated)
  tsu_report.json: generated_at=2026-08-15T19:11:10, partial=false
```

### Dagg/Hiscox Verification (excluded per mission)
```
Dagg_Church_Order: 3,377 records, indexed=5, generated_at=2026-08-09
Hiscox_Standard_Manual: 740 records, indexed=5, generated_at=2026-08-09
Qdrant source_id=BAP-CHURCH-DAGG-001: 10 points, work_id=WORK-DAGG-CHURCH-ORDER-001
```

## Execution

### Command Used
```bash
launchctl load /tmp/com.nae.tsu.vol01.plist
# Equivalent to:
cd ~/DBMA && source ~/envs/dbma311/bin/activate && python -m NAE.pipeline.tsu.runner --identifier Fuller_Complete_Works_Vol01 > /tmp/tsu_vol01_full.log 2>&1
```

### Launchd Job Status
```
PID: 88689 (Python), 88688 (bash wrapper)
Label: com.nae.tsu.vol01
Exit code: 0 (still running)
```

### Candidate Analysis
```
Total candidates: 5,452
LLM call time per candidate: ~4.8s (实测)
Estimated total time: 5,452 × 4.8s = 26,170s ≈ 7.3 hours
Checkpoint interval: every 100 candidates (~8 minutes)
```

### Progress Monitoring
```
Process running: YES (2 processes confirmed)
tsu_report.json updated: NO (still from 14:11, checkpoint not reached yet)
Output file (/tmp/tsu_vol01_full.log): 0 bytes (Python buffering)
```

## Constraints

1. **Tool timeout**: 30-second limit prevents direct interactive execution
2. **LLM speed**: my-theology-bot-v2:latest is the only available model (42GB)
3. **No faster model**: Cannot use a different model per mission requirements
4. **Checkpointing**: Builder writes partial results every 100 candidates

## Next Steps

- Monitor launchd job progress via `ps aux | grep tsu.runner`
- Check tsu_report.json periodically for checkpoint updates
- Once complete, proceed to Phase 2 (dry-run)
- **Estimated completion**: ~7.3 hours from start (14:29 KST)

## Evidence Files

- `/tmp/tsu_vol01_full.log` — stdout/stderr log
- `NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu_report.json` — builder report
- `NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu.json` — TSU records
