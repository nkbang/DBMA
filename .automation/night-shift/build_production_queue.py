#!/usr/bin/env python3
"""Build NAE Source Registration task orders from the real raw corpus.

Reads NAE/corpus/raw/**/metadata.json and emits one ADR-022 schema 1.2.0 task
file per raw item into `queue-pending-approval/`.

It writes to `queue-pending-approval/`, NOT `queue/`, on purpose: the runner
only picks up `queue/`. Moving a file from pending-approval to queue is the
explicit human act that authorises production registration of that source.

    python3 .automation/night-shift/build_production_queue.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "NAE" / "corpus" / "raw"
OUT_DIR = Path(__file__).resolve().parent / "queue-pending-approval"


def split_creator(creator: str) -> tuple[str, str]:
    """"Andrew Fuller" -> ("Fuller", "Andrew");  "John L. Dagg" -> ("Dagg", "John L.")"""
    parts = creator.strip().split()
    if len(parts) < 2:
        return creator.strip(), ""
    return parts[-1], " ".join(parts[:-1])


def first_year(value) -> int | None:
    if isinstance(value, int):
        return value
    m = re.search(r"\d{4}", str(value or ""))
    return int(m.group()) if m else None


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for meta_path in sorted(RAW_ROOT.rglob("metadata.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        item_dir = meta_path.parent
        surname, given = split_creator(meta.get("creator", ""))
        source_id = meta.get("source_id") or slugify(item_dir.name)
        task_id = f"NAE-REG-{source_id}"

        task = {
            "schema_version": "1.2.0",
            "task_id": task_id,
            "title": f"NAE Source Registration — {meta.get('title', item_dir.name)}"[:200],
            "owner": "CUE",
            "state": "INITIATED",
            "phase": "REGISTRATION",
            "requires_human_approval": False,
            # ADR-022 schema validation rejects anything else; the production
            # mutation is recorded by ADR-021's own state store, not here.
            "production_mutation": False,
            "evidence": [],
            "audit": {"status": "pending"},
            "document_type": "book",
            "automation": {
                "state": None,
                "failure_code": None,
                "last_transition_id": None,
                "processing_input": {
                    # Host path — see ADR-023 Amendment A (executor runtime).
                    "raw_item_dir": str(item_dir),
                    "surname": surname,
                    "given_name": given,
                    "title": meta.get("title", ""),
                    "edition_slug": slugify(meta.get("edition") or meta.get("edition_id") or "ed"),
                    "publication_year": first_year(meta.get("year") or meta.get("edition")),
                    "copyright_status": "public_domain",
                    "archive_source": "archive_org",
                    "source_id": source_id,
                },
            },
        }
        (OUT_DIR / f"{task_id}.json").write_text(
            json.dumps(task, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        written += 1
        print(f"  {task_id}  <- {item_dir.relative_to(PROJECT_ROOT)}")

    print(f"\n{written} task order(s) written to {OUT_DIR.relative_to(PROJECT_ROOT)}")
    print("HELD: move a file into queue/ to authorise its production registration.")


if __name__ == "__main__":
    main()
