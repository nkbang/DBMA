"""Default Corpus Query Path Verification — Precision Strike Test

Purpose: Verify that the default corpus is fully queryable through the
existing retrieval pipeline without any manual indexing or additional steps.

Test commands:
    cd ~/DBMA && source ~/envs/dbma311/bin/activate && PYTHONPATH=. python scripts/test_default_corpus_query.py

Evidence: See output below for exact query results, latencies, and source distribution.
"""
import os
import time
from collections import Counter

os.environ['USE_INVERTED_INDEX'] = 'true'

from core.hybrid_candidate_pipeline import HybridQueryProcessor


def run_query(proc, query, label=''):
    t0 = time.perf_counter()
    result = proc.process(query, k=10)
    t1 = time.perf_counter()
    latency = (t1 - t0) * 1000

    sources = []
    for c in result.candidates:
        src = c.metadata.get('source_file', 'unknown')
        lang = c.metadata.get('language', '?')
        stype = c.metadata.get('source_type', '?')
        sources.append((src, lang, stype))

    source_counts = Counter(s[0] for s in sources)
    
    # Default corpus hit count (nae_canonical or txt type)
    default_hits = sum(1 for s in sources if s[2] in ('nae_canonical', 'nae_canonical_unprocessed', 'txt'))

    print(f'Query: "{query}" {label}')
    print(f'  Latency: {latency:.1f}ms')
    print(f'  Total results: {len(result.candidates)}')
    print(f'  Default corpus hits (Top-10): {default_hits}')
    print(f'  Top-10:')
    for i, (c, src) in enumerate(zip(result.candidates, sources), 1):
        print(f'    #{i} score={c.final_score:.4f}(bm25={c.bm25_score:.2f} theo={c.theological_score:.2f}) source={src[0]} lang={src[1]} type={src[2]}')
    print(f'  Source distribution:')
    for src, count in source_counts.most_common():
        print(f'    {src}: {count}')
    print()
    return result


if __name__ == '__main__':
    # Cold start - measure init separately
    print('=' * 60)
    print('COLD START TEST')
    print('=' * 60)
    
    t0 = time.perf_counter()
    proc = HybridQueryProcessor()
    t1 = time.perf_counter()
    init_latency = (t1 - t0) * 1000
    print(f'HybridQueryProcessor init: {init_latency:.1f}ms')
    
    # First query (cold - includes tsu_by_id lazy load)
    print('\n--- First query (cold) ---')
    run_query(proc, 'baptism', '(first)')

    # Second query (warm cache)
    print('--- Second query (warm cache) ---')
    run_query(proc, 'baptism', '(warm)')
    
    # Third query (different query, warm cache miss but warm tsu_by_id)
    print('--- Third query (different, warm tsu_by_id) ---')
    run_query(proc, '침례', '(KO warm)')

    # English queries
    print('\n--- English queries ---')
    for q in ['salvation', 'gospel', 'faith', 'church']:
        run_query(proc, q, '(EN)')

    # Korean queries
    print('\n--- Korean queries ---')
    for q in ['구원', '복음', '믿음', '교회']:
        run_query(proc, q, '(KO)')

    # Mixed
    print('\n--- Mixed queries ---')
    for q in ['baptism 침례', 'gospel 복음', 'salvation 구원', 'faith 믿음']:
        run_query(proc, q, '(MIXED)')


