"""중복 source_file 정리 + TSU rebuild + 정합성 검증."""
import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, '.')
from core.index_orchestrator import rebuild_tsu_index
from core.identity_registry import load_identity_registry, save_identity_registry, registry_lock
from core.config import registry_path_for

REG_PATH = Path('data/제련완성본/registry/documents.json')
OUTPUT_DIR = 'data/제련완성본'


def find_duplicates(docs: dict) -> dict[str, list]:
    """source_file별 document_id 그룹화."""
    by_source = defaultdict(list)
    for doc_id, doc in docs.items():
        src = doc.get('source_file', '')
        if src:
            by_source[src].append(doc_id)
    return {s: ids for s, ids in by_source.items() if len(ids) > 1}


def pick_winner(docs: dict, doc_ids: list[str]) -> str:
    """마지막 처리 시각이 가장 빠른 문서ID 선택."""
    best_id = None
    best_time = ''
    for did in doc_ids:
        t = docs[did].get('last_processed_at', '') or ''
        if t > best_time:
            best_time = t
            best_id = did
    return best_id


def main():
    # 1. Registry 로드
    registry = load_identity_registry(str(REG_PATH))
    docs = registry.get('documents', {})
    
    print(f'=== Registry 전체 문서: {len(docs)}개 ===')
    
    # 2. 중복 source_file 찾기
    dups = find_duplicates(docs)
    print(f'\\\\n=== 중복 source_file: {len(dups)}개 ===')
    
    if not dups:
        print('중복 없음 — rebuild만 실행')
    else:
        # 3. 각 그룹에서 winner 선택 + loser 제거
        to_remove = []
        for src, ids in sorted(dups.items()):
            winner = pick_winner(docs, ids)
            losers = [did for did in ids if did != winner]
            print(f'\\\\n{src}:')
            print(f'  winner: {winner[:8]} (last_processed={docs[winner].get("last_processed_at", "?")})')
            for loser in losers:
                print(f'  loser:  {loser[:8]} (last_processed={docs[loser].get("last_processed_at", "?")}) → 제거')
                to_remove.append(loser)
        
        # 4. loser 문서 제거
        if to_remove:
            with registry_lock(str(REG_PATH)):
                reg = load_identity_registry(str(REG_PATH))
                for did in to_remove:
                    del reg['documents'][did]
                save_identity_registry(reg, str(REG_PATH))
            print(f'\\\\n{len(to_remove)}개 문서 제거 완료')
        
        # 5. rebuild_tsu_index 실행
        print('\\\\n=== rebuild_tsu_index() 시작 ===')
        result = rebuild_tsu_index()
        for k, v in result.items():
            print(f'{k}: {v}')
        print('=== rebuild 완료 ===')
    
    # 6. 정합성 검증
    print('\\\\n=== 정합성 검증 ===')
    
    # Registry
    reg = json.load(open(REG_PATH, encoding='utf-8'))
    reg_docs = reg.get('documents', {})
    reg_doc_ids = set(reg_docs.keys())
    reg_sources = {d.get('source_file') for d in reg_docs.values() if d.get('source_file')}
    
    # TSU dataset
    tsus_by_doc = {}
    with open('output/bench/tsu_dataset.jsonl', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                doc_id = rec.get('document_id')
                if doc_id:
                    tsus_by_doc.setdefault(doc_id, []).append(rec.get('source_file'))
    tsu_doc_ids = set(tsus_by_doc.keys())
    
    # 일치 확인
    missing_in_tsu = reg_doc_ids - tsu_doc_ids
    extra_in_tsu = tsu_doc_ids - reg_doc_ids
    
    print(f'Registry document_id: {len(reg_doc_ids)}개')
    print(f'TSU dataset document_id: {len(tsu_doc_ids)}개')
    
    if missing_in_tsu:
        print(f'\\\\n❌ Registry에 있지만 TSU에 없는 문서 ({len(missing_in_tsu)}개):')
        for did in sorted(missing_in_tsu):
            src = reg_docs[did].get('source_file', '')
            print(f'  - {did[:8]} ({src})')
    else:
        print('\\\\n✅ Registry와 TSU dataset document_id 일치')
    
    if extra_in_tsu:
        print(f'\\\\n❌ TSU에 있지만 Registry에 없는 문서 ({len(extra_in_tsu)}개)')
    else:
        print('✅ TSU에 불필요한 문서 없음')
    
    # source_file 정합성
    tsu_sources = set()
    for recs in tsus_by_doc.values():
        for r in recs:
            src = r.get('source_file')
            if src:
                tsu_sources.add(src)
    
    missing_src = reg_sources - tsu_sources
    if missing_src:
        print(f'\\\\n❌ TSU에 없는 source_file ({len(missing_src)}개):')
        for s in sorted(missing_src):
            print(f'  - {s}')
    else:
        print('✅ Registry와 TSU dataset source_file 일치')
    
    # 중복 확인
    by_source = defaultdict(list)
    for doc_id, src in tsus_by_doc.items():
        for s in src:
            by_source[s].append(doc_id)
    dups_after = {s: ids for s, ids in by_source.items() if len(ids) > 1}
    if dups_after:
        print(f'\\\\n⚠️ TSU에 남은 중복 source_file ({len(dups_after)}개):')
        for s, ids in sorted(dups_after.items()):
            print(f'  - {s}: {len(ids)}개 document_id')
    else:
        print('✅ TSU에 중복 source_file 없음')
    
    print('\\\\n=== 검증 완료 ===')


if __name__ == '__main__':
    main()
