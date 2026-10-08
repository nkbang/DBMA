#!/usr/bin/env python
"""scripts/repair_supersession_links.py — NAE-SUPERSESSION-REGISTRY-REPAIR-001.

documents.json 의 supersedes 링크 7개(Spurgeon MTP Vol10~13 의 2-순환 4건,
Vol51~53 의 dangling 3건)만 None 으로 정정한다. 대상은 아래 REPAIRS 에
하드코딩되어 있으며 자동 탐지로 넓히지 않는다. 다른 필드/레코드,
TSU dataset, 색인은 건드리지 않는다.

기본은 dry-run. 실제 반영은 --execute (사용자 승인 후).

  python scripts/repair_supersession_links.py            # dry-run
  python scripts/repair_supersession_links.py --execute

절차(--execute): registry_lock 보유 → 백업 → lock 안에서 재로드·사전조건 재검증
→ 7개 필드만 변경 후 원자적 저장 → 사후 검증 실패 시 같은 lock 안에서 백업 복원.
load_identity_registry()는 migrate_registry_schema()를 적용하므로 쓰지 않고,
raw JSON 을 직접 읽고 쓴다(7개 필드 외 변경 0을 보장하기 위함).
"""

from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import BASE_DIR, DEFAULT_OUTPUT_DIR, registry_path_for
from core.identity_registry import registry_lock

# (document_id, field, expected current value, target value)
REPAIRS: list[tuple[str, str, str, None]] = [
    # Vol10~13: 옛 버전의 supersedes 가 현행본을 가리키는 2-순환
    ("a337c599d94dec532d909d6d731ea152", "supersedes", "ab67ca69f34ee13d51326a72d4515083", None),
    ("5eb26b6929203d297cad8a32ca5b7156", "supersedes", "d7b9cbf96c2c9b3013001d765711054f", None),
    ("5b1f96f75ca8440b5f877dac64427fd3", "supersedes", "bdd4b58cc4ea23ff902590b18d424da0", None),
    ("b1a0ec98ed76db343d2be3165895bdba", "supersedes", "762dc710e9e0112dd03373e530b070f5", None),
    # Vol51~53: registry 에 없는 ID 를 가리키는 dangling
    ("9aa7987eb97e56798fa8b23023c0b277", "supersedes", "189da57613c4b0fce8ac84a82544fb6a", None),
    ("fbdd831a0661e2f89bbff96306a8a162", "supersedes", "704bdae52d3981b42fce618f48134e5c", None),
    ("60f27d33dc98517833e1f8fa87b51d42", "supersedes", "f23cd06e26b324183559623ba2dd50c1", None),
]


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_atomic(data: dict, path: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def check_preconditions(registry: dict) -> tuple[list[tuple], list[tuple], list[str]]:
    """Return (to_change, already_repaired, mismatches)."""
    docs = registry.get("documents", {})
    to_change, done, bad = [], [], []
    for doc_id, field, expected, target in REPAIRS:
        rec = docs.get(doc_id)
        if rec is None:
            bad.append(f"{doc_id[:8]}: record missing")
        elif rec.get(field) == expected:
            to_change.append((doc_id, field, expected, target))
        elif rec.get(field) == target:
            done.append((doc_id, field, expected, target))
        else:
            bad.append(f"{doc_id[:8]}.{field}: expected {expected[:8]!r} or None, found {rec.get(field)!r}")
    return to_change, done, bad


def apply_repairs(registry: dict, to_change: list[tuple]) -> None:
    for doc_id, field, _expected, target in to_change:
        registry["documents"][doc_id][field] = target


def scan_integrity(registry: dict) -> dict:
    """dangling / asymmetric / 2-cycle / multi-current counts + current-id set."""
    docs = registry["documents"]
    dangling = asym = cycles = 0
    for d, r in docs.items():
        for key in ("supersedes", "superseded_by"):
            if r.get(key) and r[key] not in docs:
                dangling += 1
        s = r.get("supersedes")
        if s in docs and docs[s].get("superseded_by") != d:
            asym += 1
        b = r.get("superseded_by")
        if b in docs and docs[b].get("supersedes") != d:
            asym += 1
        if s and s == b:
            cycles += 1
    by_source: dict[str, list[str]] = {}
    for d, r in docs.items():
        by_source.setdefault(r.get("source_file", ""), []).append(d)
    multi = [s for s, ids in by_source.items()
             if sum(docs[i].get("superseded_by") is None for i in ids) > 1]
    current = {d for d, r in docs.items() if r.get("superseded_by") is None}
    return {"dangling": dangling, "asymmetric": asym, "two_cycle": cycles,
            "multi_current": len(multi), "current_ids": current}


def _diff_fields(before: dict, after: dict) -> list[str]:
    """Every leaf-level difference between two registries (dotted paths)."""
    out: list[str] = []

    def walk(a, b, path):
        if isinstance(a, dict) and isinstance(b, dict):
            for k in sorted(set(a) | set(b)):
                if k not in a or k not in b:
                    out.append(f"{path}.{k}")
                else:
                    walk(a[k], b[k], f"{path}.{k}")
        elif a != b:
            out.append(path)

    walk(before, after, "")
    return out


def run(registry_path: str, execute: bool, backup_root: str | None = None,
        watch_paths: list[str] | None = None) -> int:
    registry = _read(registry_path)
    to_change, done, bad = check_preconditions(registry)
    print(f"[repair] registry={registry_path} documents={len(registry['documents'])}")
    print(f"[repair] 사전조건: 정정 대상 {len(to_change)} / 이미 정정됨 {len(done)} / 불일치 {len(bad)}")
    for m in bad:
        print(f"[repair] 불일치: {m}")
    if bad:
        print("[repair] 중단: 사전조건 불일치 — 아무것도 쓰지 않음")
        return 2

    for doc_id, field, expected, target in to_change:
        src = registry["documents"][doc_id].get("source_file")
        print(f"  {src}  {doc_id}.{field}: {expected} -> {target}")
    if not to_change:
        print("[repair] 이미 정정됨 — no-op")
        return 0
    if not execute:
        print("[repair] dry-run 종료 (--execute 로 반영)")
        return 0

    watch_paths = watch_paths or []
    watch_before = {p: _sha256(p) for p in watch_paths if os.path.exists(p)}
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = backup_root or os.path.join(BASE_DIR, "backups")
    backup_dir = os.path.join(backup_root, f"supersession_registry_repair_{ts}")
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, os.path.basename(registry_path))

    rc = 0
    with registry_lock(registry_path):
        shutil.copy2(registry_path, backup_path)
        backup_sha = _sha256(backup_path)
        print(f"[repair] 백업: {backup_path} sha256={backup_sha}")

        fresh = _read(registry_path)
        to_change2, _done2, bad2 = check_preconditions(fresh)
        if bad2 or len(to_change2) != len(to_change):
            print(f"[repair] 중단: lock 안 재검증 실패 {bad2} — 쓰지 않음")
            return 2
        before = copy.deepcopy(fresh)
        pre_scan = scan_integrity(before)
        apply_repairs(fresh, to_change2)
        _write_atomic(fresh, registry_path)

        after = _read(registry_path)
        changed = _diff_fields(before, after)
        expected_paths = sorted(f".documents.{d}.{f}" for d, f, _e, _t in to_change2)
        post = scan_integrity(after)
        ok = (
            sorted(changed) == expected_paths
            and post["dangling"] == 0 and post["asymmetric"] == 0
            and post["two_cycle"] == 0 and post["multi_current"] == 0
            and post["current_ids"] == pre_scan["current_ids"]
        )
        if not ok:
            shutil.copy2(backup_path, registry_path)
            restored = _sha256(registry_path) == backup_sha
            print(f"[repair] 사후 검증 실패 → 백업 복원 (해시 일치={restored})")
            print(f"[repair]   changed={changed}\n[repair]   post={ {k: v for k, v in post.items() if k != 'current_ids'} }")
            rc = 3
        else:
            print(f"[repair] 사후 검증 OK: 변경 필드 {len(changed)}개, 현행본 집합 동일({len(post['current_ids'])}건), "
                  f"dangling/비대칭/2-순환/다중현행 = 0/0/0/0")

    for p, h in watch_before.items():
        same = _sha256(p) == h
        print(f"[repair] 불변 확인 {p}: {'동일' if same else '변경됨!'}")
        if not same:
            rc = rc or 4
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--execute", action="store_true", help="실제 반영 (기본은 dry-run)")
    ap.add_argument("--registry", default=registry_path_for(DEFAULT_OUTPUT_DIR))
    ap.add_argument("--backup-root", default=None)
    ap.add_argument("--watch", nargs="*", default=[
        os.path.join(BASE_DIR, "output/bench/tsu_dataset.jsonl"),
        os.path.join(BASE_DIR, "output/bench/tsu_manifest.json")],
        help="전후 SHA-256 이 동일해야 하는 파일")
    args = ap.parse_args()
    return run(args.registry, args.execute, args.backup_root, args.watch)


if __name__ == "__main__":
    sys.exit(main())
