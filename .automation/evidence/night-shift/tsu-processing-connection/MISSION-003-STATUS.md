# C1 Night Shift Order 003 — Mission Status

## Issued
CUE, 2026-08-15, Rev. Bang approval

## Mission
Registration 10건 중 아직 처리 안 된 것에 대해 TSU→Embedding→Qdrant 실행

## Scope
- **Dagg, Hiscox**: 이미 2026-08-09에 완료 (Qdrant point 존재). **절대 건드리지 않음**
- **Fuller_Complete_Works_Vol01~08**: 8건 신규 처리 대상

## Current Status: PHASE 1 RUNNING (first checkpoint reached)

### Phase 1 — TSU Generation (Fuller Vol01)
- **Status**: RUNNING (launchd background job, PID 88689)
- **Command**: `python -m NAE.pipeline.tsu.runner --identifier Fuller_Complete_Works_Vol01`
- **Candidates**: 5,452 total
- **Progress**: 100/5,452 evaluated (first checkpoint reached)
- **Claims extracted**: 60
- **Elapsed**: 1,265.46s (~21 min for 100 candidates)
- **Actual speed**: 12.65s/candidate
- **Estimated remaining**: ~18.8 hours
- **Estimated total completion**: ~20.8 hours from start (14:29 KST → ~11:15 KST next day)
- **Checkpoint interval**: every 100 candidates (~21 min each)

#### First Checkpoint Data (evidence)
```json
{
  "identifier": "Fuller_Complete_Works_Vol01",
  "builder_version": "3.0.0",
  "generated_at": "2026-08-15T19:51:02.933891+00:00",
  "model": "my-theology-bot-v2:latest",
  "candidates_evaluated": 100,
  "candidates_total": 5452,
  "claims_extracted": 60,
  "llm_errors": 0,
  "doctrine_breakdown": {
    "Soteriology": 43,
    "Scripture / Authority": 2,
    "Sanctification": 3,
    "Justification": 4,
    "Providence": 3,
    "Election": 4
  },
  "elapsed_seconds": 1265.46,
  "partial": true
}
```

### Phase 2 — Embedding/Indexing Dry-run
- **Status**: BLOCKED (depends on Phase 1 completion)
- **Command**: `python scripts/nae_incremental_ingest.py --identifier Fuller_Complete_Works_Vol01`
- **Note**: Script only processes `review_status=="verified"` records

### Phase 3 — E2E Actual Execution
- **Status**: BLOCKED (depends on Phase 2 GREEN)
- **Command**: `python scripts/nae_incremental_ingest.py --identifier Fuller_Complete_Works_Vol01 --apply`
- **Qdrant baseline**: 3,319 points

### Phase 4 — Batch Expansion (Vol02-08)
- **Status**: BLOCKED (depends on Phase 3 GREEN)
- **Scope**: 7 volumes (Fuller_Complete_Works_Vol02 through Vol08)
- **Each volume**: ~20.8 hours TSU + embedding time

## Critical Constraints

1. **Tool timeout**: 30-second limit prevents direct interactive execution of TSU builder
2. **LLM speed**: my-theology-bot-v2:latest is the only available model (42GB)
3. **Actual speed**: 12.65s/candidate (not 4.8s as initially measured on single candidate)
4. **No code modification**: Per mission rules, cannot modify builder.py/embedding.py/indexing.py
5. **Review gate**: TSU records must be `review_status=="verified"` before embedding

## Monitoring Commands

```bash
# Check process status
ps aux | grep "tsu.runner" | grep -v grep

# Check progress (checkpoint every 100 candidates)
cat NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu_report.json

# Check Qdrant baseline
cd ~/DBMA && source ~/envs/dbma311/bin/activate && python -c "from qdrant_client import QdrantClient; c=QdrantClient(url='http://localhost:7333'); print(c.get_collection('nae_tsu_v1').points_count)"
```

## Launchd Job

```
Label: com.nae.tsu.vol01
PID: 88689 (Python), 88688 (bash wrapper)
Status: Running
Output: /tmp/tsu_vol01_full.log (buffered)
```

## Evidence Directory Structure

```
.automation/evidence/night-shift/tsu-processing-connection/
├── MISSION-003-STATUS.md (this file)
├── phase-1-tsu-generation/
│   └── README.md
├── phase-2-dry-run/
├── phase-3-e2e-execution/
└── phase-4-batch-expansion/
```

## Next Actions

1. Monitor Phase 1 progress (check every ~21 minutes for checkpoint updates)
2. Once Phase 1 completes, run Phase 2 dry-run
3. If Phase 2 GREEN, run Phase 3 apply
4. Verify Qdrant mutation (before/after point count)
5. Repeat Phase 1-3 for Vol02-08

## Total Estimated Time

- Phase 1 (Vol01): ~20.8 hours (实测 기반)
- Phase 2-3 (Vol01): ~minutes (depends on TSU record count)
- Phase 4 (Vol02-08): 7 × (~20.8 hours + embedding) ≈ ~150+ hours

**Total for all 8 volumes**: ~170+ hours

## Notes

- Dagg/Hiscox identity schema mismatch is OUT OF SCOPE for this mission
- Each volume is independent — failure in one does not affect others
- Builder checkpointing ensures partial progress is preserved
- First checkpoint shows healthy claim extraction (60 claims from 100 candidates = 60% claim rate)
- Doctrine breakdown is reasonable: Soteriology dominant (43/60), consistent with theological text analysis

