"""NAE Incremental Ingestion CLI (NAE-INCREMENTAL-INGESTION-001).

사용 예:
    python scripts/nae_incremental_ingest.py --identifier Dagg_Church_Order --dry-run
    python scripts/nae_incremental_ingest.py --identifier Dagg_Church_Order --apply

`--dry-run`이 기본값이다(안전). `--apply`를 명시적으로 줘야만 실제
embedding/Qdrant 쓰기가 발생한다. 두 플래그를 혼동하지 않도록 동시 지정은
거부한다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from NAE.pipeline.ingest import pipeline
from NAE.pipeline.ingest.state import IncrementalStateStore
from NAE.pipeline.tsu.config import TSU_ROOT


def load_records(identifier: str, tsu_root: Path = TSU_ROOT) -> list[dict]:
    path = tsu_root / identifier / "tsu.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    # 이 계층은 verified TSU만 대상으로 한다 — generated/rejected는
    # Human Review Gate 이전이므로 embedding/indexing 대상이 아니다.
    return [r for r in data if r.get("review_status") == "verified"]


def main() -> None:
    parser = argparse.ArgumentParser(description="NAE Incremental Ingestion")
    parser.add_argument("--identifier", required=True, help="TSU corpus identifier (e.g. Dagg_Church_Order)")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", default=False)
    parser.add_argument("--state-path", default=None, help="상태 저장소 경로 override(테스트용)")
    args = parser.parse_args()

    if args.apply and args.dry_run and "--dry-run" in sys.argv and "--apply" in sys.argv:
        parser.error("--dry-run과 --apply를 동시에 지정할 수 없습니다.")

    records = load_records(args.identifier)
    state_store = IncrementalStateStore(Path(args.state_path)) if args.state_path else IncrementalStateStore()

    if args.apply:
        result = pipeline.apply(records, state_store=state_store)
    else:
        result = pipeline.dry_run(records, state_store=state_store)

    print(json.dumps({k: v for k, v in result.items() if k not in ("change_status", "embed_plan", "index_lifecycle")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
