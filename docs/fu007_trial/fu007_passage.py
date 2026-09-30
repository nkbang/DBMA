"""구절 질의 5건: 상위 5건 본문에 대상 장 표기(로마숫자·아라비아)가 있는 건수. 서수 접두(1 John 등) 미구분."""
import json, re, sys
REF = {
    "A1": r"\bRom(ans)?\.?[\s.,]+(viii|8)\b",
    "A2": r"\bGen(esis)?\.?[\s.,]+(i|1)[\s.,:]+2[67]\b",
    "A3": r"\bMatt?(hew)?\.?[\s.,]+(xxviii|28)\b",
    "C1": r"\bRom(ans)?\.?[\s.,]+(viii|8)\b",
    "C2": r"\bHeb(rews)?\.?[\s.,]+(xi|11)\b",
}
labels = sys.argv[1:]
d = {l: {r["tag"]: r for r in json.load(open(f"cmp_{l}.json"))} for l in labels}
print("| 질의 | " + " | ".join(labels) + " |\n|---|" + "---|" * len(labels))
tot = {l: 0 for l in labels}
for tag, rx in REF.items():
    cells = []
    for l in labels:
        n = sum(1 for t in d[l][tag]["top"] if re.search(rx, t["content"], re.I))
        tot[l] += n; cells.append(f"{n}/5")
    print(f"| {tag} | " + " | ".join(cells) + " |")
print("| 합계 | " + " | ".join(f"{tot[l]}/25" for l in labels) + " |")
