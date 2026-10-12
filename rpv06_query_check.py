import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('USE_INVERTED_INDEX', 'true')
from core.hybrid_candidate_pipeline import HybridQueryProcessor
from core.query_planner import classify
from core.retrieval import QueryParser

FIXTURE_A_MARKERS = ('TSU-JHN-6f323b08',)
FIXTURE_B_MARKERS = ('5ce2824e947da15da8893fbb45c07239',)

candidates_to_test = {
    'RPV-06a-candidate-1': '포도나무와 가지의 비유에서 열매를 맺기 위해 주님 안에 거한다는 의미를 설명해 주세요',
    'RPV-06b-candidate-1': '성령께서 교회에 다양한 은사를 주신다는 관점에서 은사의 종류와 목적을 정리해 주세요',
}

parser = QueryParser()
processor = HybridQueryProcessor()

for label, q in candidates_to_test.items():
    pq = parser.parse(q)
    plan = classify(q, pq)
    resp = processor.process(q, k=10)
    cands = list(resp.top_k_results)
    print(f'=== {label} ===')
    print('query:', q)
    print('route:', plan.route, '| scripture_refs:', pq.scripture_refs)
    print('candidate_count:', len(cands))
    is_a = 'a' in label.lower()
    markers = FIXTURE_A_MARKERS if is_a else FIXTURE_B_MARKERS
    for i, c in enumerate(cands):
        hit = any(m in (c.tsu_id or '') for m in markers)
        if hit:
            print(f'  [rank {i}] FIXTURE HIT tsu_id={c.tsu_id} bm25={c.bm25_score} theological={c.theological_score} final={c.final_score}')
    fixture_ranks = [i for i, c in enumerate(cands) if any(m in (c.tsu_id or '') for m in markers)]
    print('fixture_candidate_count_in_top10:', len(fixture_ranks))
    print('fixture_ranks:', fixture_ranks)
    print()
