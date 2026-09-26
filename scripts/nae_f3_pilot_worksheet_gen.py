"""fuller_f3_pilot_sample_001_requests.json으로부터 인간검수용 워크시트(.md) 생성.
"""

import json
from pathlib import Path

REPO = Path("/Users/David/DBMA")
req = json.loads((REPO / "NAE/review/human/requests/fuller_f3_pilot_sample_001_requests.json").read_text(encoding="utf-8"))

lines = []
lines.append("# fuller_f3_pilot_sample_001 검토 워크시트 (F3 착수 범위 결정용 표본)")
lines.append("")
lines.append("- 목적: Fuller Vol.01~08 전량(F3) 착수 전, 볼륨당 40건(총 320건) 층화표본으로")
lines.append("  품질 검수 — 특히 **목차/소제목이 본문 주장으로 오분류**되는 비율 확인.")
lines.append("- CJK 미해결(잔존 한자) 레코드는 이 표본에서 제외됨(373건, 별도 트랙).")
lines.append("- Q1 Claim Fidelity: claim이 원문 의미를 정확히 표현하는가?")
lines.append("- Q2 Theological Accuracy: 신학적으로 왜곡/과장되지 않았는가?")
lines.append("- Q3 Context Sufficiency: 제공된 원문 맥락이 판단하기에 충분한가?")
lines.append("- 각 항목에 A(승인)/R(거부)/C(문맥 필요) 표기.")
lines.append("- **목차/소제목으로 의심되면 comment에 '목차의심'이라고 적어주세요**")
lines.append("  (`heading_suspected: true` 표시가 있으면 특히 확인 — 단, 이 표시가 없어도")
lines.append("  목차/소제목으로 보이면 표기해 주세요. 자동 휴리스틱은 참고용일 뿐입니다).")
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
        flag = "  ⚠️ heading_suspected" if r.get("heading_suspected") else ""
        lines.append(f"### {n}. {r['tsu_id']}  [{r['doctrine']}]{flag}")
        lines.append(f"- **원문**: {r['original_text']}")
        lines.append(f"- **claim**: {r['claim']}")
        lines.append("- Q1: [ ]   Q2: [ ]   Q3: [ ]   comment: ")
        lines.append("")
    lines.append("---")
    lines.append("")

out_path = REPO / "NAE/review/human/worksheets/fuller_f3_pilot_sample_001_worksheet.md"
out_path.write_text("\n".join(lines), encoding="utf-8")
print("wrote", out_path, n, "items")
