"""registry에 저장된 noise_score를 현재 calculate_noise_score() 로직으로
재계산해 output/noise_recompute/ 에 리포트만 남긴다.

registry(data/제련완성본/registry/documents.json)와 각 문서의 MD 파일은
읽기 전용으로만 연다 — 이 스크립트는 어떤 기존 파일도 수정하지 않는다.

사용법:
    python scripts/recompute_noise_scores.py
"""

import json
from datetime import datetime
from pathlib import Path

from core.config import DEFAULT_REGISTRY_PATH, DEFAULT_OUTPUT_DIR
from core.utils import calculate_noise_score, make_safe_stem

REPORT_DIR = Path("output/noise_recompute")


def strip_front_matter(text: str) -> str:
    """'---'로 감싼 YAML front-matter를 제거하고 본문만 반환."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2]
    return text


def recompute_all() -> list[dict]:
    registry = json.loads(Path(DEFAULT_REGISTRY_PATH).read_text(encoding="utf-8"))
    documents = registry.get("documents", {})
    output_dir = Path(DEFAULT_OUTPUT_DIR)

    results = []
    for doc_id, record in documents.items():
        if record.get("status") != "processed":
            continue

        source_file = record.get("source_file", "")
        source_type = record.get("source_type", "")
        is_ocr = record.get("is_ocr", False)
        old_score = record.get("noise_score")
        old_mode = record.get("noise_mode")

        stem = make_safe_stem(source_file)
        md_path = output_dir / f"{stem}.md"

        if not md_path.exists():
            results.append({
                "document_id": doc_id,
                "source_file": source_file,
                "status": "md_missing",
                "md_path": str(md_path),
            })
            continue

        text = md_path.read_text(encoding="utf-8")
        body = strip_front_matter(text)
        new_result = calculate_noise_score(body, file_type=source_type, is_ocr=is_ocr)

        results.append({
            "document_id": doc_id,
            "source_file": source_file,
            "status": "recomputed",
            "old_noise_score": old_score,
            "new_noise_score": new_result["score"],
            "delta": round(new_result["score"] - old_score, 3) if old_score is not None else None,
            "old_mode": old_mode,
            "new_mode": new_result["mode"],
        })

    return results


def write_report(results: list[dict]) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")

    json_path = REPORT_DIR / f"recompute_report_{timestamp}.json"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    recomputed = [r for r in results if r["status"] == "recomputed"]
    missing = [r for r in results if r["status"] == "md_missing"]
    changed = [r for r in recomputed if r["delta"] not in (None, 0)]
    top_10 = sorted(changed, key=lambda r: abs(r["delta"]), reverse=True)[:10]

    lines = [
        "# Noise Score 재계산 요약",
        "",
        f"- 실행 시각: {timestamp}",
        f"- 총 처리 대상 문서: {len(results)}",
        f"- 재계산 완료: {len(recomputed)}",
        f"- MD 없어서 건너뜀: {len(missing)}",
        f"- 값이 바뀐 문서: {len(changed)}",
        "",
        "## Delta 상위 10개",
        "",
        "| 문서 | old → new | delta |",
        "|---|---|---|",
    ]
    for r in top_10:
        lines.append(
            f"| {r['source_file']} | {r['old_noise_score']} → {r['new_noise_score']} | {r['delta']:+.3f} |"
        )

    if missing:
        lines.append("")
        lines.append("## MD 없어서 건너뛴 문서")
        lines.append("")
        for r in missing:
            lines.append(f"- {r['source_file']} ({r['md_path']})")

    md_path = REPORT_DIR / f"recompute_summary_{timestamp}.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return json_path, md_path


def main() -> None:
    results = recompute_all()
    json_path, md_path = write_report(results)

    recomputed = [r for r in results if r["status"] == "recomputed"]
    missing = [r for r in results if r["status"] == "md_missing"]
    changed = [r for r in recomputed if r["delta"] not in (None, 0)]

    print(f"총 처리 대상 문서: {len(results)}")
    print(f"재계산 완료: {len(recomputed)}")
    print(f"MD 없어서 건너뜀: {len(missing)}")
    print(f"값이 바뀐 문서: {len(changed)}")
    print(f"JSON 리포트: {json_path}")
    print(f"MD 요약: {md_path}")


if __name__ == "__main__":
    main()
