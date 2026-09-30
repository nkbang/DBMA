import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd())); sys.path.insert(0, str(Path.cwd()/"scripts"))
from core.hybrid_candidate_pipeline import HybridQueryProcessor
from p0_5_run_all import QUERIES
A = Path(sys.argv[1]); ref = {r["tag"]: r for r in json.load(open(sys.argv[2]))}
p = HybridQueryProcessor(tsu_dataset_path=str(A/"tsu_dataset.jsonl"), candidate_index_dir=str(A/"tantivy_index"),
    bible_index_path=str(A/"bi_ev.sqlite3"), telemetry_path=str(A/"tel_ev.sqlite3"),
    cache_path=str(A/"cache_ev.sqlite3"), tsu_manifest_path=str(A/"tsu_manifest.json"), cache_ttl_seconds=0)
out, match = [], 0
for tag, q in QUERIES:
    r = p.process(q, k=5)
    ev = [{"rank": i+1, "tsu_id": c.tsu_id, "title": c.metadata.get("title"), "author": c.metadata.get("author"),
           "source_file": c.metadata.get("source_file"), "content": c.content} for i, c in enumerate(r.top_k_results)]
    got = [(e["title"] or "")[:80] + "|" + " ".join((e["content"] or "")[:200].split()) for e in ev]
    want = [s["title"][:80] + "|" + s["snippet"] for s in ref[tag]["sources"]]
    ok = got == want; match += ok
    out.append({"tag": tag, "question": q, "matches_appindex_sources": ok, "evidence": ev})
    print(tag, "match" if ok else "MISMATCH", flush=True)
json.dump(out, open(sys.argv[3], "w"), ensure_ascii=False, indent=2)
print("MATCH", match, "/24")
