#!/usr/bin/env python3
"""Run Phase 1 of ns003_nae_ingestion for BAP-CHURCH-DAGG-001 and save results."""
import json, time, sys, os
sys.path.insert(0, '/Users/David/DBMA')

from pathlib import Path
from scripts.ns003_nae_ingestion import process_single_source

source_id = "BAP-CHURCH-DAGG-001"
print(f"Starting Phase 1 for {source_id}...", flush=True)
start = time.time()

result = process_single_source(source_id)

elapsed = time.time() - start
print(f"\nPhase 1 completed in {elapsed:.1f}s", flush=True)
print(f"Success: {result.get('success')}", flush=True)
print(f"Error: {result.get('error')}", flush=True)
print(f"Document ID: {result.get('document_id')}", flush=True)
print(f"Chunk count: {result.get('chunk_count')}", flush=True)
print(f"TSU records: {result.get('tsu_records')}", flush=True)

# Save logs
for log in result.get('logs', []):
    print(log, flush=True)

# Save result to file
output = {
    'source_id': source_id,
    'success': result.get('success'),
    'elapsed': elapsed,
    'document_id': result.get('document_id'),
    'chunk_count': result.get('chunk_count'),
    'tsu_records': result.get('tsu_records'),
    'error': result.get('error'),
    'logs': result.get('logs', []),
}
Path('/tmp/ns003_phase1_result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2))
print(f"\nResult saved to /tmp/ns003_phase1_result.json", flush=True)
