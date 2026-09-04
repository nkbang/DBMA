#!/usr/bin/env python3
"""Build TSU for a single identifier."""
import sys, time, json
sys.path.insert(0, '/Users/David/DBMA')
from NAE.pipeline.tsu import builder

identifier = sys.argv[1] if len(sys.argv) > 1 else 'Fuller_Complete_Works_Vol01'
print(f'Starting build_tsu_for_identifier for {identifier}...', flush=True)
start = time.time()
result = builder.build_tsu_for_identifier(identifier)
elapsed = time.time() - start
print(f'Done in {elapsed:.1f}s', flush=True)
report = result['report']
print(json.dumps(report, ensure_ascii=False, indent=2)[:3000], flush=True)
# Save report
with open(f'/tmp/tsu_report_{identifier}.json', 'w') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f'Report saved to /tmp/tsu_report_{identifier}.json', flush=True)
