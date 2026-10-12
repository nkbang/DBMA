#!/usr/bin/env python3
"""Validate rpv_real2_*.json results and compare with rpv_real_*.json."""
import json
from pathlib import Path

WORKTREE = Path("/Users/David/DBMA-rpv-c8f7e41a")
BENCH = WORKTREE / "output" / "bench"

QUERIES = {
    "01a": '로마서 8장 28절의 헬라어 원문에서 "모든 것이 합력하여 선을 이룬다"는 표현의 문법 구조는 어떻게 되어 있습니까?',
    "01b": '요한일서와 요한복음에서 "사랑"(agape)이 사용되는 용례 차이가 있습니까?',
    "02":  '야고보서 2장의 "행함이 없는 믿음은 죽은 것"이라는 구절을 로마서의 이신칭의 교리와 어떻게 조화시킬 수 있습니까?',
    "03a": '개혁주의 관점에서 예정론과 인간의 자유의지는 어떻게 양립합니까?',
    "03b": '침례교 신앙고백(1689 LBC 등)에서 성찬에 대한 입장은 무엇입니까?',
    "04":  '1세기 로마 제국의 노예 제도가 빌레몬서의 배경을 이해하는 데 어떤 영향을 줍니까?',
    "07":  '이번 주 설교 본문이 누가복음 15장(잃어버린 아들 비유)입니다. 설교 개요를 짜는 데 참고할 신학적/역사적 포인트를 정리해 주십시오.',
    "08a": '"김민수 목사"라는 신학자가 주장했다는 "제3의 은혜론"의 핵심 내용은 무엇입니까?',
    "08b": 'the grace of God',
}

def validate_file(qid, data):
    issues = []
    result = data[0]
    retrieval = result['stages']['retrieval']
    top_tsu = retrieval.get('top_candidate_tsu_id', 'N/A')
    cand_count = retrieval.get('candidate_count', 0)
    ep = result['stages']['evidence_pool']
    pool_size = ep.get('pool_size', 0)
    included_ids = ep.get('included_evidence_ids', [])
    claims = result['stages']['claim_extraction']['claims']
    claim_count = len(claims)
    ga_status = result['stages']['grounded_answer'].get('status', 'N/A')
    
    for c in claims:
        cid = c.get('claim_id', '?')
        valid = c.get('valid')
        eid = c.get('evidence_ids', [])
        if valid is None:
            issues.append(f"{cid}: valid 필드 없음")
        if isinstance(eid, list):
            for e in eid:
                es = str(e)
                if '...' in es:
                    issues.append(f"{cid}: evidence_ids에 '...' 포함: {es}")
                if '(' in es and ')' in es:
                    issues.append(f"{cid}: evidence_ids에 괄호 잔여물: {es}")
        elif isinstance(eid, str):
            es = eid
            if '...' in es:
                issues.append(f"{cid}: evidence_ids에 '...' 포함: {es}")
            if '(' in es and ')' in es:
                issues.append(f"{cid}: evidence_ids에 괄호 잔여물: {es}")
    
    for eid in included_ids:
        es = str(eid)
        if '...' in es:
            issues.append(f"included_evidence_ids에 '...' 포함: {es}")
        if '(' in es and ')' in es:
            issues.append(f"included_evidence_ids에 괄호 잔여물: {es}")
    
    summary = {
        'qid': qid, 'candidate_count': cand_count,
        'top_candidate_tsu_id': top_tsu, 'pool_size': pool_size,
        'included_evidence_ids_count': len(included_ids),
        'claim_count': claim_count, 'ga_status': ga_status,
        'claims': [],
    }
    for c in claims:
        cid = c.get('claim_id', '?')
        valid = c.get('valid', 'N/A')
        eid = c.get('evidence_ids', [])
        eid_str = ','.join(str(x) for x in eid) if isinstance(eid, list) else str(eid) if eid else ''
        text_preview = c.get('text', '')[:80]
        summary['claims'].append({'claim_id': cid, 'valid': valid, 'evidence_ids': eid_str, 'text_preview': text_preview})
    return summary, issues

def compare_with_previous(qid, new_summary):
    old_path = BENCH / f"rpv_real_{qid}.json"
    if not old_path.exists():
        return "이전 파일 없음"
    try:
        old_data = json.load(open(old_path))
        old_result = old_data[0]
        old_claims = old_result['stages']['claim_extraction']['claims']
        old_ga = old_result['stages']['grounded_answer']
        old_claim_count = len(old_claims)
        old_ga_status = old_ga.get('status', 'N/A')
        old_top_tsu = old_result['stages']['retrieval'].get('top_candidate_tsu_id', 'N/A')
        old_cand_count = old_result['stages']['retrieval'].get('candidate_count', 0)
        changes = []
        if old_claim_count != new_summary['claim_count']:
            changes.append(f"claim_count: {old_claim_count} -> {new_summary['claim_count']}")
        if old_ga_status != new_summary['ga_status']:
            changes.append(f"GA_status: {old_ga_status} -> {new_summary['ga_status']}")
        if old_top_tsu != new_summary['top_candidate_tsu_id']:
            changes.append(f"top_tsu: {old_top_tsu} -> {new_summary['top_candidate_tsu_id']}")
        if old_cand_count != new_summary['candidate_count']:
            changes.append(f"candidates: {old_cand_count} -> {new_summary['candidate_count']}")
        return "변경사항: " + "; ".join(changes) if changes else "이전 결과와 동일"
    except Exception as e:
        return f"비교 오류: {e}"

def main():
    print("=" * 80)
    print("RPV_REAL2 VALIDATION REPORT")
    print("=" * 80)
    all_issues = []
    for qid in sorted(QUERIES.keys()):
        new_path = BENCH / f"rpv_real2_{qid}.json"
        if not new_path.exists():
            print(f"\n[{qid}] 파일 없음: {new_path}")
            all_issues.append(f"{qid}: 결과 파일 없음")
            continue
        data = json.load(open(new_path, encoding='utf-8'))
        summary, issues = validate_file(qid, data)
        comparison = compare_with_previous(qid, summary)
        print(f"\n{'='*60}")
        print(f"[{qid}] Query: {QUERIES[qid][:70]}...")
        print(f"  Retrieval: {summary['candidate_count']} candidates, top={summary['top_candidate_tsu_id']}")
        print(f"  EvidencePool: size={summary['pool_size']}, included_ids={summary['included_evidence_ids_count']}")
        print(f"  Claims: {summary['claim_count']}, GA_status={summary['ga_status']}")
        for cl in summary['claims']:
            print(f"    [{cl['claim_id']}] valid={cl['valid']} ids=[{cl['evidence_ids']}]")
            print(f"      text={cl['text_preview']}...")
        if issues:
            print(f"  !!! ISSUES:")
            for iss in issues:
                print(f"    - {iss}")
            all_issues.extend([f"{qid}: {i}" for i in issues])
        else:
            print(f"  OK: no issues found")
        print(f"  vs previous: {comparison}")
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total files: 9/9")
    if all_issues:
        print(f"Issues found ({len(all_issues)}):")
        for iss in all_issues:
            print(f"  - {iss}")
    else:
        print("All 9 queries passed validation.")

if __name__ == '__main__':
    main()
