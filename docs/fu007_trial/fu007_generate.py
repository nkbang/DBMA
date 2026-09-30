"""FU-007 결합안: 생성 단계 포함 P0-5 24건 실행.

scripts/p0_5_run_all.py와 같은 프로덕션 경로(HybridQueryProcessor.process, k=5,
file_scope=None, 근거 0건 하드 게이트 → GenerationService.generate)를 밟되,
모든 검색 산출물 경로는 scratchpad/bench로 고정한다(앱 output/bench 미사용).
실행: cd <worktree> && python fu007_generate.py <label> <out.json>
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / "scripts"))

from core.generation import GenerationService  # noqa: E402
from core.hybrid_candidate_pipeline import HybridQueryProcessor  # noqa: E402
from p0_5_run_all import QUERIES, _K  # noqa: E402

B = Path(__file__).resolve().parent / "bench"
label, out = sys.argv[1], Path(sys.argv[2])

proc = HybridQueryProcessor(
    tsu_dataset_path=str(B / "tsu_dataset.jsonl"),
    candidate_index_dir=str(B / "tantivy_index"),
    bible_index_path=str(B / f"bible_index_{label}.sqlite3"),
    telemetry_path=str(B / f"telemetry_{label}.sqlite3"),
    cache_path=str(B / f"cache_{label}_gen.sqlite3"),
    tsu_manifest_path=str(B / "tsu_manifest.json"),
)
gen = GenerationService()

rows = json.loads(out.read_text()) if out.exists() else []
done = {r["tag"] for r in rows}
for tag, q in QUERIES:
    if tag in done:
        continue
    t0 = time.time()
    resp = proc.process(q, query_id=f"fu007-{tag}", k=_K, file_scope=None)
    row = {"tag": tag, "question": q, "top_k": len(resp.top_k_results),
           "sources": [
               {"title": (c.metadata.get("title") or "")[:80], "author": (c.metadata.get("author") or "")[:40],
                "snippet": " ".join((c.content or "")[:200].split())}
               for c in resp.top_k_results
           ]}
    if not resp.top_k_results:
        row.update(evidence_hold=True, answer=None, gen_seconds=0.0)
    else:
        r = gen.generate(resp)
        cg, cc = r.claim_guard_result, getattr(r, "citation_check", None)
        row.update(
            evidence_hold=False,
            answer=r.answer,
            gen_model=r.gen_model,
            error=r.error,
            citations=len(r.citations or []),
            claim_guard=(cg.risk_level.value if cg else None),
            citation_check=({"found": cc.citations_found, "issues": len(cc.issues)} if cc else None),
            gen_seconds=round(time.time() - t0, 1),
        )
    rows.append(row)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{label}] {tag} top={row['top_k']} hold={row['evidence_hold']} "
          f"{row['gen_seconds']}s chars={len(row['answer'] or '')}", flush=True)
print("DONE", out, flush=True)
