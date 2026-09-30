"""P6 CUE 독립 검증: 상한 없음, 단어 경계 정규식, 저장소 모듈 import 없음."""
import json, re
CORPUS = "/Users/David/DBMA/output/bench/tsu_dataset.jsonl"
W = "/Users/David/DBMA_wt/fu007/docs/fu007_trial/"
APP = {r["tag"]: r for r in json.load(open(W + "P0_5_RAW_ANSWERS_FU007_COMBINED_APPINDEX.json"))}
EV = {r["tag"]: r for r in json.load(open(W + "P0_5_EVIDENCE_FULLTEXT_APPINDEX.json"))}
TERMS = {
 "image of God": r"\bimage of God\b", "imago": r"\bimago\b", "Genesis i. 26/27": r"\bGen(esis)?\.?\s+i\.?\s*2[67]\b",
 "Dagg(word)": r"\bDagg\b", "church order": r"\bchurch order\b", "marks of the church": r"\bmarks of (a|the) (true )?church\b",
 "infant baptism": r"\binfant[- ]baptism\b", "paedo/pedobaptis": r"\bp(a)?edo-?baptis", "presbyterian": r"\bpresbyterian", "1689": r"\b1689\b",
 "London Confession": r"\bLondon Confession\b",
 "Canaanites": r"\bCanaanites\b", "drive out the Canaanites": r"\bdrive out the Canaanites\b", "Joshua xvii": r"\bJoshua\s+xvii\b",
 "Mars(planet)": r"\bMars\b", "planet": r"\bplanets?\b", "artificial intelligence": r"\bartificial intelligence\b", "John Smith": r"\bJohn Smith\b",
 "evolution": r"\bevolution\b", "Darwin": r"\bDarwin", "Hiscox": r"\bHiscox\b", "Fuller(Andrew)": r"\bAndrew Fuller\b",
 "worthy of all acceptation": r"\bworthy of all acceptation\b", "divorce": r"\bdivorce", "melancholy/depress": r"\b(melancholy|depression)\b",
}
cnt = {k: 0 for k in TERMS}; ids = {k: [] for k in TERMS}; ctx = {k: [] for k in TERMS}
C = {k: re.compile(v, re.I) for k, v in TERMS.items()}
with open(CORPUS) as f:
    for line in f:
        try: d = json.loads(line)
        except Exception: continue
        t = " ".join(str(d.get(x) or "") for x in ("title", "author", "content"))
        for k, rx in C.items():
            m = rx.search(t)
            if m:
                cnt[k] += 1
                if len(ids[k]) < 3:
                    ids[k].append(d.get("tsu_id")); ctx[k].append(" ".join(t[max(0, m.start()-60):m.end()+60].split()))
for k in TERMS: print(f"{k:28s} {cnt[k]:6d}  {ids[k][:2]}")
print("\n--- 문맥 표본")
for k in ["image of God", "Dagg(word)", "church order", "marks of the church", "infant baptism", "Mars(planet)", "Hiscox"]:
    for c in ctx[k][:2]: print(f"[{k}] …{c}…")
