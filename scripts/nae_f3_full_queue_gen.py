"""F3 전량 롤아웃 — triage 플래그 9,433건 인적검수 큐 생성 (2단계 게이트 결정, 2026-09-26).

STATE.md 2026-09-26 항목 참고: triage 플래그된 레코드(전체 29,015건 중 9,433건,
32.5%)를 전량 인적검수 대상으로 편입. 이미 판정된(파일럿 320건 + Vol04-08
재표본 7건) tsu_id는 큐에서 제외. 볼륨별로 request/worksheet 파일 생성.

입력: NAE/corpus/tsu/Fuller_Complete_Works_Vol0*/tsu.json, f3_triage_flags.json
출력: NAE/review/human/requests/fuller_f3_full_queue_Vol0{N}_requests.json
      NAE/review/human/worksheets/fuller_f3_full_queue_Vol0{N}_worksheet.md
"""

import json
from pathlib import Path

REPO = Path("/Users/David/DBMA")
TSU_ROOT = REPO / "NAE/corpus/tsu"

already_judged = set()
pilot = json.loads((REPO / "NAE/review/human/requests/fuller_f3_pilot_sample_001_requests.json").read_text(encoding="utf-8"))
already_judged |= {r["tsu_id"] for r in pilot["requests"]}
resample_dec = json.loads((REPO / "NAE/review/human/decisions/fuller_f3_vol0408_resample_001_decisions.json").read_text(encoding="utf-8"))
already_judged |= {d["tsu_id"] for d in resample_dec["decisions"]}

grand_total = 0
grand_queued = 0
per_vol_summary = {}

for i in range(1, 9):
    vol = f"Fuller_Complete_Works_Vol0{i}"
    vol_dir = TSU_ROOT / vol
    records = {r["id"]: r for r in json.loads((vol_dir / "tsu.json").read_text(encoding="utf-8"))}
    triage = json.loads((vol_dir / "f3_triage_flags.json").read_text(encoding="utf-8"))

    queue = []
    for item in triage["items"]:
        tsu_id = item["tsu_id"]
        if tsu_id in already_judged:
            continue
        r = records.get(tsu_id)
        if r is None:
            continue
        if r.get("cjk_status") == "residual" or r.get("needs_review") == "cjk_residual":
            continue
        queue.append({
            "gate_id": f"GATE-{tsu_id}",
            "tsu_id": tsu_id,
            "work_id": vol,
            "edition_id": vol,
            "doctrine": item.get("doctrine") or "미분류",
            "identifier": vol,
            "original_text": r.get("source_text", ""),
            "claim": r.get("claim", ""),
            "triage_flags": item.get("flags", []),
        })

    grand_total += triage["flagged_records"]
    grand_queued += len(queue)
    per_vol_summary[vol] = {"flagged": triage["flagged_records"], "queued": len(queue),
                              "excluded_already_judged_or_cjk": triage["flagged_records"] - len(queue)}

    out = {
        "schema_version": "1.0.0",
        "batch_id": f"fuller_f3_full_queue_{vol}",
        "generated_by": "CUE-F3-FULL-QUEUE-001",
        "note": "F3 2단계 게이트 롤아웃 — triage 플래그(패턴 기반: quote_attribution/rhetorical_question/conditional_hypothetical/truncated_fragment/very_short_fragment) 레코드 인적검수 큐. 파일럿 320건·Vol04-08 재표본 7건과 중복 없음, CJK/스크립트 미해결 레코드 제외.",
        "requests": queue,
    }
    (REPO / f"NAE/review/human/requests/fuller_f3_full_queue_{vol}_requests.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append(f"# fuller_f3_full_queue_{vol} 검토 워크시트 (F3 2단계 게이트 — triage 플래그 큐)")
    lines.append("")
    lines.append(f"- {vol}: triage 플래그 {triage['flagged_records']}건 중 {len(queue)}건 큐 편성")
    lines.append("  (기판정/CJK미해결 제외).")
    lines.append("- Q1 Claim Fidelity / Q2 Theological Accuracy / Q3 Context Sufficiency — A/R/C 표기.")
    lines.append("- triage_flags는 참고용 자동 신호(quote_attribution 등)일 뿐, 최종판단 아님.")
    lines.append("")
    lines.append("---")
    lines.append("")
    for n, r in enumerate(queue, 1):
        flags = ", ".join(r["triage_flags"])
        lines.append(f"### {n}. {r['tsu_id']}  [{r['doctrine']}]  (flags: {flags})")
        lines.append(f"- **원문**: {r['original_text']}")
        lines.append(f"- **claim**: {r['claim']}")
        lines.append("- Q1: [ ]   Q2: [ ]   Q3: [ ]   comment: ")
        lines.append("")
    (REPO / f"NAE/review/human/worksheets/fuller_f3_full_queue_{vol}_worksheet.md").write_text(
        "\n".join(lines), encoding="utf-8")

    print(f"[{vol}] flagged={triage['flagged_records']} queued={len(queue)}")

print(f"\nTOTAL: flagged={grand_total} queued={grand_queued} (excluded already-judged/cjk={grand_total-grand_queued})")
json.dump(per_vol_summary, open("/private/tmp/claude-501/-Users-David-DBMA/e627b9fe-392b-47d7-85a9-ee947da22a4d/scratchpad/full_queue_summary.json", "w"), ensure_ascii=False, indent=2)
