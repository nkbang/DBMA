"""fuller_f3_vol0408_resample_001_requests.json으로부터 인간검수용 워크시트(.md) 생성 (F3 옵션③)."""

import json
from pathlib import Path

REPO = Path("/Users/David/DBMA")
req = json.loads((REPO / "NAE/review/human/requests/fuller_f3_vol0408_resample_001_requests.json").read_text(encoding="utf-8"))

lines = []
lines.append("# fuller_f3_vol0408_resample_001 검토 워크시트 (F3 옵션③ — Vol04-08 재표본)")
lines.append("")
lines.append("- 목적: 파일럿(320건) 결론에서 확인된 Vol01-03(rigorous, 45% reject) vs")
lines.append("  Vol04-08(light, 16% reject) 검수 rigor 격차 해소 — Vol04-08 볼륨당 40건")
lines.append("  (총 200건) 신규 층화표본으로 동일 수준 rigor 재검수.")
lines.append("- 파일럿 320건과 중복 없음(이미 뽑힌 tsu_id 제외), CJK/스크립트 미해결 레코드 제외.")
lines.append("- Q1 Claim Fidelity: claim이 원문 의미를 정확히 표현하는가?")
lines.append("- Q2 Theological Accuracy: 신학적으로 왜곡/과장되지 않았는가?")
lines.append("- Q3 Context Sufficiency: 제공된 원문 맥락이 판단하기에 충분한가?")
lines.append("- 각 항목에 A(승인)/R(거부)/C(문맥 필요) 표기.")
lines.append("")
lines.append("---")
lines.append("")

by_vol = {}
for r in req["requests"]:
    by_vol.setdefault(r["identifier"], []).append(r)

n = 0
for vol, items in by_vol.items():
    lines.append(f"## {vol}  ({len(items)}건)")
    lines.append("")
    for r in items:
        n += 1
        lines.append(f"### {n}. {r['tsu_id']}  [{r['doctrine']}]")
        lines.append(f"- **원문**: {r['original_text']}")
        lines.append(f"- **claim**: {r['claim']}")
        lines.append("- Q1: [ ]   Q2: [ ]   Q3: [ ]   comment: ")
        lines.append("")
    lines.append("---")
    lines.append("")

out_path = REPO / "NAE/review/human/worksheets/fuller_f3_vol0408_resample_001_worksheet.md"
out_path.write_text("\n".join(lines), encoding="utf-8")
print("wrote", out_path, n, "items")
