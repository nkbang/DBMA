"""FU-007 번역 방식 비교 하네스 — 검색 단계만(생성 없음).

실행: cd <variant worktree> && python fu007_compare.py <label> <out.json>
모든 경로는 scratchpad/bench로 고정 — 메인 체크아웃·output/bench를 건드리지 않는다.
P0-5 24건 질의는 scripts/p0_5_run_all.py::QUERIES를 그대로 import한다.
evidence_hold 판정 = p0_5_run_all.py와 동일(top-k 결과 0건), k=5.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / "scripts"))

from core.hybrid_candidate_pipeline import HybridQueryProcessor  # noqa: E402
from p0_5_run_all import QUERIES  # noqa: E402

B = Path(__file__).resolve().parent / "bench"
label, out = sys.argv[1], sys.argv[2]

proc = HybridQueryProcessor(
    tsu_dataset_path=str(B / "tsu_dataset.jsonl"),
    candidate_index_dir=str(B / "tantivy_index"),
    bible_index_path=str(B / f"bible_index_{label}.sqlite3"),
    telemetry_path=str(B / f"telemetry_{label}.sqlite3"),
    cache_path=str(B / f"cache_{label}.sqlite3"),
    tsu_manifest_path=str(B / "tsu_manifest.json"),
)

rows = []
for tag, q in QUERIES:
    parsed = proc.parser.parse(q)
    tel: dict = {}
    t0 = time.perf_counter()
    ranked = proc.retriever.retrieve(parsed, k_output=5, telemetry_out=tel)
    ms = (time.perf_counter() - t0) * 1000
    rows.append({
        "tag": tag,
        "query": q,
        "route": tel.get("route"),
        "candidate_count": tel.get("candidate_count", 0),
        "top_k": len(ranked),
        "evidence_hold": len(ranked) == 0,
        "translation_used": bool(tel.get("translation_used")),
        "translated_query": tel.get("translated_query"),
        "translated_terms": parsed.translated_terms,
        "latency_ms": round(ms, 1),
        "top": [
            {
                "tsu_id": r.tsu_id,
                "title": (r.metadata.get("title") or r.metadata.get("source_file") or "")[:80],
                "author": (r.metadata.get("author") or "")[:40],
                "snippet": " ".join((r.content or "")[:220].split()),
                "content": r.content or "",
            }
            for r in ranked
        ],
    })
    print(f"[{label}] {tag} cand={rows[-1]['candidate_count']} top={len(ranked)} "
          f"tr={rows[-1]['translation_used']} {ms:.0f}ms", flush=True)

Path(out).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print("DONE", out)
