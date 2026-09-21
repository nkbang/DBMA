"""scripts/backfill_baseline_metadata.py — 사이드카로 채운 title/author/
metadata_source를 기존 registry + TSU dataset에 반영한다(백필).

`scripts/generate_baseline_sidecars.py --apply`로 data/RAW/<file>.meta.json
사이드카를 먼저 만들어야 한다. 이 스크립트는 재추출·재청킹·재임베딩을
하지 않는다 — registry record와 TSU record의 title/author/metadata_source
3개 필드만 in-place로 갱신한다(청크 본문·임베딩·Qdrant 인덱스는 무변경).

**Production Registry 대량 변경 + Corpus 전체 Migration류 작업** —
CLAUDE.md 예외 규정상 실행 전 사용자 승인이 필요하다. 기본은 dry-run.

사용:
    python3 scripts/backfill_baseline_metadata.py \
        --registry-path <documents.json> \
        --tsu-path <tsu_dataset.jsonl> \
        --raw-dir <data/RAW> \
        [--apply]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.processing import resolve_title_author  # noqa: E402
from core.identity_registry import load_identity_registry, save_identity_registry  # noqa: E402

MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts",
    "baseline_corpus_manifest.json",
)


def _compute_updates(raw_dir: str) -> dict:
    """filename -> {"title":..., "author":..., "metadata_source":...}"""
    manifest = json.load(open(MANIFEST_PATH, "r", encoding="utf-8"))
    updates = {}
    for entry in manifest["entries"]:
        filename = entry["filename"]
        src_path = os.path.join(raw_dir, filename)
        title, author, metadata_source = resolve_title_author(None, None, src_path)
        if metadata_source is None:
            continue
        updates[filename] = {"title": title, "author": author, "metadata_source": metadata_source}
    return updates


def _backup(path: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = f"{path}.backfill_backup_{ts}"
    shutil.copy2(path, backup_path)
    return backup_path


def patch_registry(registry_path: str, updates: dict, apply: bool) -> int:
    registry = load_identity_registry(registry_path)
    docs = registry.get("documents", registry) if isinstance(registry, dict) else registry
    changed = 0
    for doc_id, record in docs.items():
        source_file = record.get("source_file")
        if source_file not in updates:
            continue
        u = updates[source_file]
        if record.get("title") == u["title"] and record.get("author") == u["author"] and record.get(
            "metadata_source"
        ) == u["metadata_source"]:
            continue
        print(f"  [registry] {source_file}: title={u['title']!r} author={u['author']!r} metadata_source={u['metadata_source']!r}")
        if apply:
            record["title"] = u["title"]
            record["author"] = u["author"]
            record["metadata_source"] = u["metadata_source"]
        changed += 1
    if apply and changed:
        backup = _backup(registry_path)
        print(f"  registry 백업: {backup}")
        save_identity_registry(registry, registry_path)
    return changed


def patch_tsu_dataset(tsu_path: str, updates: dict, apply: bool) -> int:
    changed = 0
    tmp_path = f"{tsu_path}.backfill_tmp"
    with open(tsu_path, "r", encoding="utf-8") as fin, open(tmp_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.rstrip("\n")
            if not line:
                continue
            record = json.loads(line)
            source_file = record.get("source_file")
            u = updates.get(source_file)
            if u is not None and (
                record.get("title") != u["title"]
                or record.get("author") != u["author"]
                or record.get("metadata_source") != u["metadata_source"]
            ):
                record["title"] = u["title"]
                record["author"] = u["author"]
                record["metadata_source"] = u["metadata_source"]
                changed += 1
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")

    if not apply:
        os.remove(tmp_path)
        return changed

    if changed:
        backup = _backup(tsu_path)
        print(f"  tsu_dataset 백업: {backup}")
        os.replace(tmp_path, tsu_path)
    else:
        os.remove(tmp_path)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-path", required=True)
    parser.add_argument("--tsu-path", required=True)
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--apply", action="store_true", help="실제로 registry/TSU를 갱신한다 (기본: dry-run)")
    args = parser.parse_args()

    updates = _compute_updates(args.raw_dir)
    print(f"사이드카 기반 갱신 대상: {len(updates)}건\n")

    print("[registry 대조]")
    reg_changed = patch_registry(args.registry_path, updates, args.apply)
    print(f"  -> {reg_changed}건 {'갱신됨' if args.apply else '갱신 예정'}\n")

    print("[tsu_dataset 대조 — 파일이 크므로 시간이 걸릴 수 있음]")
    tsu_changed = patch_tsu_dataset(args.tsu_path, updates, args.apply)
    print(f"  -> {tsu_changed}건 {'갱신됨' if args.apply else '갱신 예정'}\n")

    if not args.apply:
        print("(dry-run — 실제로 반영하려면 --apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
