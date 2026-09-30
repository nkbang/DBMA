"""중복 source_file 정리 + TSU rebuild + 정합성 검증.

기본은 dry-run(계획만 출력). `--execute` 시에만 registry_lock 안에서 재계산 →
백업 → 제거(링크 정리 포함) → 사후 무결성 검사(실패 시 백업 복원) → TSU rebuild.
(NAE-REBUILD-TSU-LINK-CLEANUP-001)
"""
import argparse
import datetime
import json
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, '.')
from core.identity_registry import (
    load_identity_registry, remove_document, registry_lock, save_identity_registry,
)

REG_PATH = Path('data/제련완성본/registry/documents.json')
BACKUP_ROOT = Path('backups')
TSU_PATH = Path('output/bench/tsu_dataset.jsonl')


def _is_current(doc: dict) -> bool:
    return doc.get('superseded_by') is None


def find_duplicates(docs: dict) -> dict[str, list]:
    """source_file별 **현행본**(superseded_by is None) document_id 그룹화.

    superseded 문서는 버전 이력이지 중복이 아니므로 제외한다(같은
    source_file을 공유하는 정상 supersession 체인을 지우지 않기 위함)."""
    by_source = defaultdict(list)
    for doc_id, doc in docs.items():
        src = doc.get('source_file', '')
        if src and _is_current(doc):
            by_source[src].append(doc_id)
    return {s: ids for s, ids in by_source.items() if len(ids) > 1}


def pick_winner(docs: dict, doc_ids: list[str]) -> str:
    """현행본 우선, 그 다음 last_processed_at이 가장 **늦은** 문서, 동률은 id 순."""
    return max(
        doc_ids,
        key=lambda d: (_is_current(docs[d]), docs[d].get('last_processed_at', '') or '', d),
    )


def plan_removals(docs: dict) -> list[tuple[str, str, str]]:
    """[(source_file, winner_id, loser_id)] — 순수 함수."""
    plan = []
    for src, ids in sorted(find_duplicates(docs).items()):
        winner = pick_winner(docs, ids)
        plan.extend((src, winner, d) for d in sorted(ids) if d != winner)
    return plan


def link_problems(registry: dict) -> dict:
    """dangling / 비대칭 / 2-순환 개수."""
    docs = registry['documents']
    dangling = asym = cycles = 0
    for d, r in docs.items():
        for key in ('supersedes', 'superseded_by'):
            if r.get(key) and r[key] not in docs:
                dangling += 1
        s, b = r.get('supersedes'), r.get('superseded_by')
        if s in docs and docs[s].get('superseded_by') != d:
            asym += 1
        if b in docs and docs[b].get('supersedes') != d:
            asym += 1
        if s and s == b:
            cycles += 1
    return {'dangling': dangling, 'asymmetric': asym, 'two_cycle': cycles}


def remove_losers(reg_path: Path, backup_root: Path = BACKUP_ROOT) -> tuple[int, int]:
    """lock 안에서 재계산 후 제거. (제거 수, 종료코드) 반환. 0=성공, 3=사후검사 실패·복원."""
    with registry_lock(str(reg_path)):
        reg = load_identity_registry(str(reg_path))
        plan = plan_removals(reg['documents'])
        if not plan:
            return 0, 0
        before = link_problems(reg)
        backup_dir = backup_root / f'rebuild_tsu_manual_{datetime.datetime.now():%Y%m%d_%H%M%S}'
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / 'documents.json'
        shutil.copy2(reg_path, backup)
        for _src, _w, loser in plan:
            remove_document(reg, loser)
        after = link_problems(reg)
        if any(after[k] > before[k] for k in after):
            print(f'[rebuild] 링크 무결성 악화 {before} → {after}: 저장하지 않음, 백업 유지 {backup}')
            return 0, 3
        save_identity_registry(reg, str(reg_path))
        reloaded = json.loads(reg_path.read_text(encoding='utf-8'))
        post = link_problems(reloaded)
        if any(post[k] > before[k] for k in post):
            shutil.copy2(backup, reg_path)
            print(f'[rebuild] 사후 검사 실패 {post}: 백업 복원 {backup}')
            return 0, 3
        print(f'[rebuild] 백업: {backup}')
        return len(plan), 0


def verify(reg_path: Path, tsu_path: Path) -> None:
    print('\n=== 정합성 검증 ===')
    reg_docs = json.loads(reg_path.read_text(encoding='utf-8')).get('documents', {})
    reg_doc_ids = set(reg_docs)
    reg_sources = {d.get('source_file') for d in reg_docs.values() if d.get('source_file')}
    tsus_by_doc = {}
    with open(tsu_path, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                if rec.get('document_id'):
                    tsus_by_doc.setdefault(rec['document_id'], []).append(rec.get('source_file'))
    tsu_doc_ids = set(tsus_by_doc)
    print(f'Registry document_id: {len(reg_doc_ids)}개')
    print(f'TSU dataset document_id: {len(tsu_doc_ids)}개')
    missing = reg_doc_ids - tsu_doc_ids
    if missing:
        print(f'\n❌ Registry에 있지만 TSU에 없는 문서 ({len(missing)}개):')
        for did in sorted(missing):
            print(f'  - {did[:8]} ({reg_docs[did].get("source_file", "")})')
    else:
        print('\n✅ Registry와 TSU dataset document_id 일치')
    print(f'❌ TSU에 있지만 Registry에 없는 문서 ({len(tsu_doc_ids - reg_doc_ids)}개)'
          if tsu_doc_ids - reg_doc_ids else '✅ TSU에 불필요한 문서 없음')
    tsu_sources = {s for recs in tsus_by_doc.values() for s in recs if s}
    missing_src = reg_sources - tsu_sources
    if missing_src:
        print(f'\n❌ TSU에 없는 source_file ({len(missing_src)}개):')
        for s in sorted(missing_src):
            print(f'  - {s}')
    else:
        print('✅ Registry와 TSU dataset source_file 일치')
    by_source = defaultdict(list)
    for doc_id, srcs in tsus_by_doc.items():
        for s in srcs:
            by_source[s].append(doc_id)
    dups_after = {s: ids for s, ids in by_source.items() if len(set(ids)) > 1}
    if dups_after:
        print(f'\n⚠️ TSU에 남은 중복 source_file ({len(dups_after)}개):')
        for s, ids in sorted(dups_after.items()):
            print(f'  - {s}: {len(set(ids))}개 document_id')
    else:
        print('✅ TSU에 중복 source_file 없음')
    print('\n=== 검증 완료 ===')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--execute', action='store_true', help='실제 제거 + rebuild (기본: dry-run)')
    ap.add_argument('--registry', default=str(REG_PATH))
    args = ap.parse_args(argv)
    reg_path = Path(args.registry)

    docs = load_identity_registry(str(reg_path)).get('documents', {})
    print(f'=== Registry 전체 문서: {len(docs)}개 ===')
    plan = plan_removals(docs)
    print(f'\n=== 중복 source_file(현행본 기준): {len({p[0] for p in plan})}개 ===')
    for src, winner, loser in plan:
        print(f'{src}:\n  winner: {winner[:8]}\n  loser:  {loser[:8]} → 제거')
    if not args.execute:
        print('\n[dry-run] 변경 없음. 실행하려면 --execute')
        return 0

    removed, code = remove_losers(reg_path)
    if code:
        return code
    print(f'\n{removed}개 문서 제거 완료 (링크 정리 포함)')
    from core.index_orchestrator import rebuild_tsu_index
    print('\n=== rebuild_tsu_index() 시작 ===')
    for k, v in rebuild_tsu_index().items():
        print(f'{k}: {v}')
    print('=== rebuild 완료 ===')
    verify(reg_path, TSU_PATH)
    return 0


if __name__ == '__main__':
    sys.exit(main())
