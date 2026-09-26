"""F3 착수범위 결정용 Fuller 층화표본 생성 — 볼륨당 40건(doctrine 비례), seed=20260925 고정.
CJK 미해결 레코드는 제외. heading_suspected는 원문 대문자비율>=70% 참고 신호일 뿐, 최종판단은 인간검수.
입력: NAE/corpus/tsu/Fuller_Complete_Works_Vol0*/tsu.json. 출력: NAE/review/human/requests/fuller_f3_pilot_sample_001_requests.json.
"""

import json, random, sys
from pathlib import Path
from collections import defaultdict

REPO = Path("/Users/David/DBMA")
sys.path.insert(0, str(REPO))
from scripts.nae_fuller_cjk_reextract import HAN  # reuse the real, verified regex

TSU_ROOT = REPO / "NAE/corpus/tsu"
UPPER_RATIO_THRESHOLD = 0.7
PER_VOLUME_N = 40
SEED = 20260925

random.seed(SEED)
vols = [f"Fuller_Complete_Works_Vol0{i}" for i in range(1, 9)]

def upper_ratio(s):
    letters = [c for c in s if c.isalpha() and ord(c) < 256]
    if len(letters) < 8:
        return 0.0
    up = sum(1 for c in letters if c.isupper())
    return up / len(letters)

all_requests = []
heading_stats = {}
sample_counts = {}

for vol in vols:
    records = json.loads((TSU_ROOT / vol / "tsu.json").read_text(encoding="utf-8"))
    clean = [r for r in records if not HAN.search(r.get("claim", ""))]
    excluded_cjk = len(records) - len(clean)

    heading_like = [r for r in clean if upper_ratio(r.get("source_text", "")) >= UPPER_RATIO_THRESHOLD]
    heading_stats[vol] = {
        "total": len(records),
        "excluded_cjk_unresolved": excluded_cjk,
        "clean": len(clean),
        "heading_like_count": len(heading_like),
        "heading_like_pct_of_clean": round(100 * len(heading_like) / len(clean), 1) if clean else 0.0,
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
            "heading_suspected": upper_ratio(r.get("source_text", "")) >= UPPER_RATIO_THRESHOLD,
        })

print("=== 볼륨별 CJK 미해결 제외 + 목차형(대문자비율>=70%) 프로그램적 추정 ===")
for vol, s in heading_stats.items():
    print(vol, s)
print("\n=== 표본 추출 건수 ===", sample_counts, "총", sum(sample_counts.values()))

out = {
    "schema_version": "1.0.0",
    "batch_id": "fuller_f3_pilot_sample_001",
    "generated_by": "CUE-F3-PILOT-SAMPLE-001",
    "note": "F3 착수 범위 결정을 위한 층화표본(볼륨당 최대 40건, doctrine 비례추출, 랜덤시드 20260925). CJK 미해결(잔존 한자) 레코드는 제외. heading_suspected=true는 원문(source_text) 라틴 대문자 비율>=70% 휴리스틱 — 목차/소제목 오분류 의심 신호(참고용, 최종판단 아님).",
    "requests": all_requests,
}
out_path = REPO / "NAE/review/human/requests/fuller_f3_pilot_sample_001_requests.json"
out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nwrote", out_path, len(all_requests), "records")

with open("/private/tmp/claude-501/-Users-David-DBMA/e627b9fe-392b-47d7-85a9-ee947da22a4d/scratchpad/heading_stats.json", "w") as f:
    json.dump(heading_stats, f, ensure_ascii=False, indent=2)
