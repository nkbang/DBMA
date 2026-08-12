"""Legacy Authority Snapshot generator (ADR-021 SS4, Phase A — READ-ONLY).

Derives a read-only Author/Work/Edition snapshot from the existing 4,117
TSU records (all review_status — verified/generated/rejected, since the
snapshot's purpose is historical reference, not a production-status
filter). This is a one-time derivation for reference/audit only:

  - It is NOT the new Authority Registry (NAE/authority/{authors,works}.yaml),
    which stays empty and is the only write target for future registration.
  - It never back-derives values INTO the new registry.
  - It performs zero writes to Production TSU files or Qdrant.

Writes exactly 4 files:
  NAE/authority/legacy_snapshot/authors.yaml
  NAE/authority/legacy_snapshot/works.yaml
  NAE/authority/authors.yaml   (new registry — empty, header only)
  NAE/authority/works.yaml     (new registry — empty, header only)

And one evidence artifact (gitignored, output/):
  output/legacy_authority_snapshot_evidence.json
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TSU_FILES = [
    REPO_ROOT / "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json",
    REPO_ROOT / "NAE/corpus/tsu/Dagg_Church_Order/tsu.json",
]
SNAPSHOT_DIR = REPO_ROOT / "NAE/authority/legacy_snapshot"
REGISTRY_DIR = REPO_ROOT / "NAE/authority"
OUT = REPO_ROOT / "output"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def yaml_str(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def main() -> None:
    # --- Production TSU 파일 무결성(전) ---
    before_hashes = {p.name: sha256_bytes(p.read_bytes()) for p in TSU_FILES}

    records: list[dict] = []
    for p in TSU_FILES:
        records.extend(json.loads(p.read_text(encoding="utf-8")))

    authors: dict[str, dict] = {}
    works: dict[str, dict] = {}

    for r in records:
        author_id = r.get("author_id") or ""
        work_id = r.get("work_id") or ""
        edition_id = r.get("edition_id") or ""
        source_id = r.get("source_id") or r.get("source_identifier") or ""
        canonical_name = r.get("author") or ""
        canonical_title = r.get("book") or ""
        edition_label = str(r.get("publication_year") or "")

        if author_id:
            a = authors.setdefault(author_id, {"author_id": author_id, "canonical_name": canonical_name, "tsu_count": 0})
            a["tsu_count"] += 1
            if canonical_name and not a["canonical_name"]:
                a["canonical_name"] = canonical_name

        if work_id:
            w = works.setdefault(work_id, {
                "work_id": work_id,
                "author_id": author_id,
                "canonical_title": canonical_title,
                "editions": {},
            })
            ed = w["editions"].setdefault(edition_id, {"edition_id": edition_id, "edition": edition_label, "source_ids": set()})
            if source_id:
                ed["source_ids"].add(source_id)

    # --- Legacy snapshot 작성 (read-only 참조용) ---
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    authors_lines = [
        "# Legacy Authority Snapshot — Authors (READ-ONLY, ADR-021 SS4)",
        "# 4,117건 TSU(verified+generated+rejected)에서 파생. 신규 registry의",
        "# write target이 아님 — reference/audit 전용. 이 파일을 재생성해도",
        "# 소스가 바뀌지 않는 한 동일한 내용이 나온다(deterministic derivation).",
        f"generated_at: {yaml_str(now())}",
        f"source_record_count: {len(records)}",
        "authors:",
    ]
    for author_id in sorted(authors):
        a = authors[author_id]
        authors_lines.append(f"  - author_id: {yaml_str(a['author_id'])}")
        authors_lines.append(f"    canonical_name: {yaml_str(a['canonical_name'])}")
        authors_lines.append(f"    tsu_count: {a['tsu_count']}")

    works_lines = [
        "# Legacy Authority Snapshot — Works (READ-ONLY, ADR-021 SS4)",
        "# 4,117건 TSU(verified+generated+rejected)에서 파생. 신규 registry의",
        "# write target이 아님 — reference/audit 전용.",
        f"generated_at: {yaml_str(now())}",
        f"source_record_count: {len(records)}",
        "works:",
    ]
    for work_id in sorted(works):
        w = works[work_id]
        works_lines.append(f"  - work_id: {yaml_str(w['work_id'])}")
        works_lines.append(f"    author_id: {yaml_str(w['author_id'])}")
        works_lines.append(f"    canonical_title: {yaml_str(w['canonical_title'])}")
        works_lines.append("    editions:")
        for edition_id in sorted(w["editions"]):
            ed = w["editions"][edition_id]
            works_lines.append(f"      - edition_id: {yaml_str(ed['edition_id'])}")
            works_lines.append(f"        edition: {yaml_str(ed['edition'])}")
            source_ids_str = ", ".join(yaml_str(s) for s in sorted(ed["source_ids"]))
            works_lines.append(f"        source_ids: [{source_ids_str}]")

    authors_yaml = "\n".join(authors_lines) + "\n"
    works_yaml = "\n".join(works_lines) + "\n"

    (SNAPSHOT_DIR / "authors.yaml").write_text(authors_yaml, encoding="utf-8")
    (SNAPSHOT_DIR / "works.yaml").write_text(works_yaml, encoding="utf-8")

    # --- 신규 Authority Registry: 빈 상태로 신설 (write target) ---
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    new_authors_header = (
        "# NAE Authority Registry — Authors (신규 ingestion 전용 write target)\n"
        "# ADR-021 SS4 Option C: 기존 3,319/4,117 TSU에서 역산하지 않고 빈 상태로\n"
        "# 시작한다. 참고 자료는 NAE/authority/legacy_snapshot/authors.yaml(read-only).\n"
        "authors: []\n"
    )
    new_works_header = (
        "# NAE Authority Registry — Works (신규 ingestion 전용 write target)\n"
        "# ADR-021 SS4 Option C: 기존 3,319/4,117 TSU에서 역산하지 않고 빈 상태로\n"
        "# 시작한다. 참고 자료는 NAE/authority/legacy_snapshot/works.yaml(read-only).\n"
        "works: []\n"
    )
    new_authors_path = REGISTRY_DIR / "authors.yaml"
    new_works_path = REGISTRY_DIR / "works.yaml"
    if not new_authors_path.exists():
        new_authors_path.write_text(new_authors_header, encoding="utf-8")
    if not new_works_path.exists():
        new_works_path.write_text(new_works_header, encoding="utf-8")

    # --- Production TSU 파일 무결성(후) ---
    after_hashes = {p.name: sha256_bytes(p.read_bytes()) for p in TSU_FILES}
    production_unchanged = before_hashes == after_hashes

    evidence = {
        "generated_at": now(),
        "generated_by": "CUE (ADR-021 Phase A, direct execution)",
        "scope": "Legacy Authority Snapshot generation (read-only derivation) + empty new Authority Registry creation",
        "source_record_count": len(records),
        "author_count": len(authors),
        "work_count": len(works),
        "edition_count": sum(len(w["editions"]) for w in works.values()),
        "output_files": {
            "legacy_snapshot_authors_sha256": sha256_bytes((SNAPSHOT_DIR / "authors.yaml").read_bytes()),
            "legacy_snapshot_works_sha256": sha256_bytes((SNAPSHOT_DIR / "works.yaml").read_bytes()),
            "new_authors_registry_sha256": sha256_bytes(new_authors_path.read_bytes()),
            "new_works_registry_sha256": sha256_bytes(new_works_path.read_bytes()),
        },
        "production_tsu_integrity": {
            "before": before_hashes,
            "after": after_hashes,
            "unchanged": production_unchanged,
        },
    }
    evidence["overall_gate"] = "PASS" if production_unchanged else "HOLD"

    OUT.mkdir(exist_ok=True)
    (OUT / "legacy_authority_snapshot_evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps({
        "author_count": evidence["author_count"],
        "work_count": evidence["work_count"],
        "edition_count": evidence["edition_count"],
        "production_tsu_unchanged": production_unchanged,
        "overall_gate": evidence["overall_gate"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
