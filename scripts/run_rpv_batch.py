#!/usr/bin/env python3
"""Batch runner for RPV real2 queries."""
import json
import subprocess
import sys
import time
from pathlib import Path

WORKTREE = Path("/Users/David/DBMA-rpv-c8f7e41a")
OUTPUT_DIR = WORKTREE / "output" / "bench"
SCRIPT = WORKTREE / "scripts" / "grounded_synthesis_integration_demo.py"
PYTHON = "/Users/David/envs/dbma311/bin/python"

QUERIES = {
    "01a": '로마서 8장 28절의 헬라어 원문에서 "모든 것이 합력하여 선을 이룬다"는 표현의 문법 구조는 어떻게 되어 있습니까?',
    "01b": '요한일서와 요한복음에서 "사랑"(ἀγάπη)이 사용되는 용례 차이가 있습니까?',
    "02":  '야고보서 2장의 "행함이 없는 믿음은 죽은 것"이라는 구절을 로마서의 이신칭의 교리와 어떻게 조화시킬 수 있습니까?',
    "03a": '개혁주의 관점에서 예정론과 인간의 자유의지는 어떻게 양립합니까?',
    "03b": '침례교 신앙고백(1689 LBC 등)에서 성찬에 대한 입장은 무엇입니까?',
    "04":  '1세기 로마 제국의 노예 제도가 빌레몬서의 배경을 이해하는 데 어떤 영향을 줍니까?',
    "07":  '이번 주 설교 본문이 누가복음 15장(잃어버린 아들 비유)입니다. 설교 개요를 짜는 데 참고할 신학적/역사적 포인트를 정리해 주십시오.',
    "08a": '"김민수 목사"라는 신학자가 주장했다는 "제3의 은혜론"의 핵심 내용은 무엇입니까?',
    "08b": 'the grace of God',
}

def run_query(query_text):
    """Run the demo script and return raw output string."""
    result = subprocess.run(
        [PYTHON, str(SCRIPT), query_text],
        cwd=str(WORKTREE),
        capture_output=True,
        text=True,
        timeout=300,  # 5 min per query
    )
    return result.stdout + result.stderr

def extract_json(raw_output):
    """Extract JSON from the raw output."""
    idx = raw_output.find('=== JSON RESULTS ===')
    if idx < 0:
        return None
    return json.loads(raw_output[idx+len('=== JSON RESULTS ==='):].strip())

def validate_result(data, qid):
    """Validate the result and return issues list."""
    issues = []
    claims = data[0]['stages']['claim_extraction']['claims']
    ga = data[0]['stages']['grounded_answer']
    
    # Check for ... in evidence_ids
    for c in claims:
        eid = c.get('evidence_ids', [])
        if isinstance(eid, list):
            for e in eid:
                if '...' in str(e) or ('(' in str(e) and ')' in str(e)):
                    issues.append(f"claim {c['claim_id']}: evidence_ids에 ... 또는 괄호 잔여물: {e}")
        elif isinstance(eid, str):
            if '...' in eid or ('(' in eid and ')' in eid):
                issues.append(f"claim {c['claim_id']}: evidence_ids에 ... 또는 괄호 잔여물: {eid}")
    
    # Check claim validity
    for c in claims:
        if c.get('valid') is None:
            issues.append(f"claim {c['claim_id']}: valid 필드 없음")
    
    # Check GA status
    if ga.get('status') is None:
        issues.append("grounded_answer status 필드 없음")
    
    return issues

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    for qid, query in QUERIES.items():
        print(f"\n{'='*60}")
        print(f"Running {qid}: {query[:60]}...")
        print(f"{'='*60}")
        
        raw = run_query(query)
        
        data = extract_json(raw)
        if data is None:
            print(f"ERROR {qid}: JSON extraction failed")
            # Save raw for debugging
            with open(OUTPUT_DIR / f"rpv_real2_{qid}_raw.txt", 'w') as f:
                f.write(raw)
            continue
        
        # Save result
        out_path = OUTPUT_DIR / f"rpv_real2_{qid}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Quick summary
        claims = data[0]['stages']['claim_extraction']['claims']
        ga = data[0]['stages']['grounded_answer']
        retrieval = data[0]['stages']['retrieval']
        
        print(f"  Retrieval: {retrieval['candidate_count']} candidates, "
              f"top={retrieval.get('top_candidate_tsu_id', 'N/A')}")
        print(f"  Claims: {len(claims)}, GA_status={ga['status']}")
        for c in claims:
            eid = c.get('evidence_ids', [])
            if isinstance(eid, list):
                eid_str = ','.join(str(x) for x in eid)
            else:
                eid_str = str(eid)
            print(f"    [{c['claim_id']}] valid={c['valid']} ids=[{eid_str}]")
        
        # Validate
        issues = validate_result(data, qid)
        if issues:
            print(f"  ISSUES:")
            for iss in issues:
                print(f"    - {iss}")
        
        print(f"  Saved to: rpv_real2_{qid}.json")

if __name__ == '__main__':
    main()
