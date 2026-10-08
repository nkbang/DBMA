"""F3 2차 표본 — triage 플래그 유형별 층화표본(유형당 ~55건, 세부 doctrine 무관 랜덤).
목적: 9,207건 전량 개별검수 대신, 플래그 유형별 결함률을 추정해 유형 단위
승인/반려/추가검수 정책을 정하기 위한 표본. seed=20260926b 고정.
입력: NAE/review/human/requests/fuller_f3_full_queue_Fuller_Complete_Works_Vol0*_requests.json
출력: NAE/review/human/requests/fuller_f3_flagtype_sample_001_requests.json
      NAE/review/human/worksheets/fuller_f3_flagtype_sample_001_worksheet.md
"""

import json, random
from pathlib import Path
from collections import defaultdict

REPO = Path("/Users/David/DBMA")
PER_FLAG_N = 55
SEED = 20260926

random.seed(SEED)

all_items = []
for i in range(1, 9):
    vol = f"Fuller_Complete_Works_Vol0{i}"
    req = json.loads((REPO / f"NAE/review/human/requests/fuller_f3_full_queue_{vol}_requests.json").read_text(encoding="utf-8"))
    all_items.extend(req["requests"])

print("total queued pool:", len(all_items))

by_flag = defaultdict(list)
for r in all_items:
    primary = r["triage_flags"][0] if r["triage_flags"] else "unknown"
    by_flag[primary].append(r)

picked_by_flag = {}
sampled = []
for flag, items in by_flag.items():
    random.shuffle(items)
    picked = items[:PER_FLAG_N]
    picked_by_flag[flag] = len(picked)
    sampled.extend(picked)

random.shuffle(sampled)

print("pool by primary flag:", {k: len(v) for k, v in by_flag.items()})
print("sampled by primary flag:", picked_by_flag, "total sampled:", len(sampled))

out = {
    "schema_version": "1.0.0",
    "batch_id": "fuller_f3_flagtype_sample_001",
    "generated_by": "CUE-F3-FLAGTYPE-SAMPLE-001",
    "note": "F3 2단계 게이트 — triage 플래그 유형별 층화표본(유형당 최대 55건, seed=20260926). "
            "목적: 9,207건 개별검수 대신 유형별 결함률을 추정해 유형 단위 승인/반려/추가검수 정책 결정.",
    "requests": sampled,
}
(REPO / "NAE/review/human/requests/fuller_f3_flagtype_sample_001_requests.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

lines = []
lines.append("# fuller_f3_flagtype_sample_001 검토 워크시트 (F3 2차 표본 — 플래그 유형별)")
lines.append("")
lines.append("- 목적: triage 플래그 유형(quote_attribution/rhetorical_question/")
lines.append("  conditional_hypothetical/truncated_fragment/very_short_fragment)별로")
lines.append(f"  최대 {PER_FLAG_N}건씩 표본 추출 — 유형별 결함률 추정 후 9,207건 큐 전체에")
lines.append("  적용할 승인/반려/추가검수 정책 결정.")
lines.append("- Q1 Claim Fidelity / Q2 Theological Accuracy / Q3 Context Sufficiency — A/R/C 표기.")
lines.append("")
lines.append("---")
lines.append("")
for n, r in enumerate(sampled, 1):
    flags = ", ".join(r["triage_flags"])
    lines.append(f"### {n}. {r['tsu_id']}  [{r['doctrine']}]  ({r['identifier']})  (flags: {flags})")
    lines.append(f"- **원문**: {r['original_text']}")
    lines.append(f"- **claim**: {r['claim']}")
    lines.append("- Q1: [ ]   Q2: [ ]   Q3: [ ]   comment: ")
    lines.append("")
(REPO / "NAE/review/human/worksheets/fuller_f3_flagtype_sample_001_worksheet.md").write_text(
    "\n".join(lines), encoding="utf-8")
print("wrote requests + worksheet,", len(sampled), "items")
