"""관련성 대리 지표: 상위 5건 본문에 질의 핵심 영어 용어(정규식)가 있는 건수.

CUE가 질의별로 정한 용어이며 사람 채점이 아니다. G1~G3(코퍼스에 없어야 할
주제)는 '핵심 용어 적중'이 곧 관련성이 아니므로 별도로 본다.
"""
import json
import re
import sys
from pathlib import Path

S = Path(__file__).resolve().parent
KEY = {
    "A1": r"condemnation",
    "A2": r"image of god|imago",
    "A3": r"all nations|make disciples|great commission|teach all",
    "B1": r"believers?'? baptism|baptism of believers|infant baptism|immersion",
    "B2": r"justification|sanctification",
    "B3": r"church discipline|discipline|excommunicat",
    "C1": r"spirit of life|liberty|romans viii|romans 8",
    "C2": r"hebrews xi|hebrews 11|by faith",
    "C3": r"church covenant|covenant",
    "D1": r"infant baptism|paedobaptis|pedobaptis",
    "D2": r"arminian|calvinis|predestinat|election",
    "D3": r"lord'?s supper|communion|eucharist|consubstantiat|transubstantiat",
    "E1": r"divorce|adulter",
    "E2": r"melanchol|depress|despond|despair",
    "E3": r"bereave|death of (a|his|her|their)? ?(child|children|son|daughter)|lost (a|his|her|their) child",
    "F1": r"deacon",
    "F2": r"marks of (a|the) (true )?church|church order",
    "F3": r"duty of (sinners|all men|every)|duty to believe|worthy of all acceptation",
    "G1": r"artificial intelligence",
    "G2": r"john smith",
    "G3": r"\bmars\b",
    "H1": r"problem of evil|origin of evil|evil and suffering|permit(s|ted)? evil",
    "H2": r"canaanites?",
    "H3": r"evolution|darwin|geolog",
}

labels = sys.argv[1:] or ["none", "main", "dev"]
data = {l: json.loads((S / f"cmp_{l}.json").read_text()) for l in labels}
print("| 질의 | " + " | ".join(labels) + " | main∩dev(top5) |")
print("|---|" + "---|" * (len(labels) + 1))
tot = {l: 0 for l in labels}
tot_ag = {l: 0 for l in labels}
for i, (tag, rx) in enumerate(KEY.items()):
    cells = []
    for l in labels:
        row = data[l][i]
        assert row["tag"] == tag
        hit = sum(1 for t in row["top"] if re.search(rx, t["content"], re.I))
        tot[l] += hit
        if not tag.startswith("G"):
            tot_ag[l] += hit
        cells.append(f"{hit}/{row['top_k']}")
    ov = ""
    if "main" in data and "dev" in data:
        a = {t["tsu_id"] for t in data["main"][i]["top"]}
        b = {t["tsu_id"] for t in data["dev"][i]["top"]}
        ov = str(len(a & b))
    print(f"| {tag} | " + " | ".join(cells) + f" | {ov} |")
print("| 합계(24) | " + " | ".join(f"{tot[l]}/120" for l in labels) + " | |")
print("| 합계(G 제외 21) | " + " | ".join(f"{tot_ag[l]}/105" for l in labels) + " | |")
