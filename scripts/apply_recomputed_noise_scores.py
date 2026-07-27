"""output/noise_recompute/ 의 최신 재계산 리포트를 registry에 반영한다.

registry의 noise_score / noise_mode 필드만 갱신한다 — 그 외 어떤 필드도
건드리지 않는다. 실행 전 반드시 documents.json.bak.{timestamp}로 백업한다.

사용법:
    python -m scripts.apply_recomputed_noise_scores
"""

import glob
import json
from datetime import datetime
from pathlib import Path

from core.config import DEFAULT_REGISTRY_PATH

REPORT_GLOB = "output/noise_recompute/recompute_report_*.json"


def latest_report_path() -> Path:
    files = sorted(glob.glob(REPORT_GLOB))
    if not files:
        raise FileNotFoundError("output/noise_recompute/ 에 recompute_report_*.json이 없습니다.")
    return Path(files[-1])


def main() -> None:
    registry_path = Path(DEFAULT_REGISTRY_PATH)
    backup_path = registry_path.with_suffix(
        registry_path.suffix + f".bak.{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    )
    backup_path.write_text(registry_path.read_text(encoding="utf-8"), encoding="utf-8")

    report_path = latest_report_path()
    report = json.loads(report_path.read_text(encoding="utf-8"))

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    documents = registry.get("documents", {})

    applied = 0
    skipped_missing = 0
    unchanged = 0

    for entry in report:
        if entry.get("status") != "recomputed":
            skipped_missing += 1
            continue
        doc_id = entry["document_id"]
        record = documents.get(doc_id)
        if record is None:
            skipped_missing += 1
            continue

        new_score = entry["new_noise_score"]
        new_mode = entry["new_mode"]
        if record.get("noise_score") == new_score and record.get("noise_mode") == new_mode:
            unchanged += 1
            continue

        record["noise_score"] = new_score
        record["noise_mode"] = new_mode
        applied += 1

    registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"리포트: {report_path}")
    print(f"백업: {backup_path}")
    print(f"갱신된 문서: {applied}")
    print(f"변화 없음: {unchanged}")
    print(f"registry에 매칭 안 됨: {skipped_missing}")


if __name__ == "__main__":
    main()
