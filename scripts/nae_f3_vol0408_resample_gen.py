"""F3 옵션③ — Vol04-08 재표본(볼륨당 40건, doctrine 비례), 기존 320건 표본과 중복 제외.
CJK/스크립트 미해결(cjk_status=residual 등) 레코드는 제외. seed=20260926 고정(파일럿과 다른 시드 — 재표본 목적).
입력: NAE/corpus/tsu/Fuller_Complete_Works_Vol0{4-8}/tsu.json,
      NAE/review/human/requests/fuller_f3_pilot_sample_001_requests.json (중복 제외용)
출력: NAE/review/human/requests/fuller_f3_vol0408_resample_001_requests.json
"""

import json, random, sys
from pathlib import Path
from collections import defaultdict

REPO = Path("/Users/David/DBMA")
sys.path.insert(0, str(REPO))
from scripts.nae_fuller_cjk_reextract import HAN  # widened v1.1.0 regex

TSU_ROOT = REPO / "NAE/corpus/tsu"
PER_VOLUME_N = 40
SEED = 20260926

random.seed(SEED)
vols = [f"Fuller_Complete_Works_Vol0{i}" for i in range(4, 9)]

pilot = json.loads((REPO / "NAE/review/human/requests/fuller_f3_pilot_sample_001_requests.json").read_text(encoding="utf-8"))
already_sampled = {r["tsu_id"] for r in pilot["requests"]}

all_requests = []
pool_stats = {}
sample_counts = {}

for vol in vols:
    records = json.loads((TSU_ROOT / vol / "tsu.json").read_text(encoding="utf-8"))
    clean = [r for r in records
             if not HAN.search(r.get("claim", ""))
             and r.get("cjk_status") != "residual"
             and r.get("needs_review") != "cjk_residual"
             and r["id"] not in already_sampled]
    pool_stats[vol] = {
        "total": len(records),
        "excluded_pilot_overlap_or_unresolved": len(records) - len(clean),
        "pool": len(clean),
    }

    by_doc = defaultdict(list)
    for r in clean:
        by_doc[r.get("doctrine") or "미분류"].append(r)
    total_clean = len(clean)
    picked = []
    for d, items in by_doc.items():
        n_d = max(1, round(PER_VOLUME_N * len(items) / total_clean)) if total_clean else 0
        random.shuffle(items)
        picked.extend(items[:n_d])
    random.shuffle(picked)
    picked = picked[:PER_VOLUME_N]
    sample_counts[vol] = len(picked)

    for r in picked:
        all_requests.append({
            "gate_id": f"GATE-{r['id']}",
            "tsu_id": r["id"],
            "source_id": f"BAP-MISS-{vol.upper()}",
            "work_id": vol,
            "edition_id": vol,
            "doctrine": r.get("doctrine") or "미분류",
            "identifier": vol,
            "original_text": r.get("source_text", ""),
            "claim": r.get("claim", ""),
        })

print("=== 볼륨별 풀 통계(파일럿 중복/미해결 제외) ===")
for vol, s in pool_stats.items():
    print(vol, s)
print("\n=== 표본 추출 건수 ===", sample_counts, "총", sum(sample_counts.values()))

out = {
    "schema_version": "1.0.0",
    "batch_id": "fuller_f3_vol0408_resample_001",
    "generated_by": "CUE-F3-VOL0408-RESAMPLE-001",
    "note": "F3 착수범위 옵션③ — Vol04-08 재표본(볼륨당 40건, doctrine 비례추출, seed=20260926). 파일럿(fuller_f3_pilot_sample_001)에서 이미 뽑힌 tsu_id 및 CJK/스크립트 미해결(cjk_status=residual, needs_review=cjk_residual) 레코드는 표본풀에서 제외. 목적: Vol01-03(rigorous, 45% reject)과 Vol04-08(light, 16% reject) 간 검수 rigor 격차 해소.",
    "requests": all_requests,
}
out_path = REPO / "NAE/review/human/requests/fuller_f3_vol0408_resample_001_requests.json"
out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nwrote", out_path, len(all_requests), "records")
