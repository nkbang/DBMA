#!/usr/bin/env python3
"""Vol.08 재검수 큐 생성 (FU-004 b-1, ADR-030 Amendment C 일괄승인 재검수).

읽기 전용: tsu.json·decisions는 읽기만 하고 NAE/review/human/requests/ 에
fuller_v08_rereview_batch_NNN_requests.json 만 쓴다.
우선순위: P0=CUE 표본 R, P1=CJK/스크립트/CUE 표본 C, P2=triage 플래그(파일럿 거부율순), P3=무신호.
파일럿·재표본에서 이미 사람이 판정한 레코드는 제외한다.

Usage: python scripts/nae_fuller_vol08_rereview_queue.py [--corpus-root ROOT] [--out-dir DIR]
"""
from __future__ import annotations
import argparse, collections, json, math, re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
V = "Fuller_Complete_Works_Vol08"
BATCH = 200
REJ = {"truncated_fragment": .43, "very_short_fragment": .33, "quote_attribution": .31,
       "rhetorical_question": .29, "conditional_hypothetical": .20}


def _sc_regex():
    src = (REPO / "core/generation.py").read_text(encoding="utf-8")
    m = re.search(r"(_SCRIPT_CONTAMINATION_RE = re\.compile\(.*?\n\))", src, re.S)
    ns = {"re": re}; exec(m.group(1), ns)
    return ns["_SCRIPT_CONTAMINATION_RE"]


def _sample_judgments() -> dict[str, str]:
    doc = (REPO / "docs/NAE_EUAT_001_FU004_VOL08_SAMPLE_CHECK.md").read_text(encoding="utf-8")
    return {m.group(1): m.group(2) for m in re.finditer(r"\| \d+ \| (TSU-\d+) \| ([ACR]) \|", doc)}


def build(corpus_root: Path) -> list[dict]:
    sc = _sc_regex(); j = _sample_judgments()
    recs = json.loads((corpus_root / f"NAE/corpus/tsu/{V}/tsu.json").read_text(encoding="utf-8"))
    flags = {x["tsu_id"]: x["flags"] for x in json.loads(
        (corpus_root / f"NAE/corpus/tsu/{V}/f3_triage_flags.json").read_text(encoding="utf-8"))["items"]}
    done = set()
    for f in ("pilot_sample_001", "vol0408_resample_001"):
        p = corpus_root / f"NAE/review/human/decisions/fuller_f3_{f}_decisions.json"
        done |= {x["tsu_id"] for x in json.loads(p.read_text(encoding="utf-8"))["decisions"]}
    out = []
    for r in recs:
        t = r["id"]
        if r["review_status"] != "verified" or t in done:
            continue
        fl = flags.get(t, []); sig = []
        if r.get("cjk_status") == "residual": sig.append("cjk_residual")
        if sc.search(r["claim"]): sig.append("script_contamination")
        if j.get(t) == "R": sig.append("cue_sample_R")
        if j.get(t) == "C": sig.append("cue_sample_C")
        sig += fl
        if "cue_sample_R" in sig: tier, p = "P0", 1.0
        elif set(sig) & {"cjk_residual", "script_contamination", "cue_sample_C"}: tier, p = "P1", .9
        elif fl: tier, p = "P2", max(REJ[f] for f in fl)
        else: tier, p = "P3", .19
        out.append(dict(gate_id="GATE-" + t, tsu_id=t, source_id="BAP-MISS-FULLER-VOL08", work_id=V,
                        edition_id=V, doctrine=r.get("doctrine"), identifier=V, original_text=r["source_text"],
                        claim=r["claim"], triage_flags=sig, tier=tier, est_reject_prior=p, paragraph=r.get("paragraph")))
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    out.sort(key=lambda x: (order[x["tier"]], -x["est_reject_prior"], x["paragraph"] or 0, x["tsu_id"]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-root", default=str(REPO))
    ap.add_argument("--out-dir", default=str(REPO / "NAE/review/human/requests"))
    a = ap.parse_args()
    out = build(Path(a.corpus_root)); d = Path(a.out_dir); d.mkdir(parents=True, exist_ok=True)
    for b in range(math.ceil(len(out) / BATCH)):
        bid = f"fuller_v08_rereview_batch_{b + 1:03d}"
        (d / f"{bid}_requests.json").write_text(json.dumps(dict(
            schema_version="1.0.0", batch_id=bid, generated_by="CUE-FU004-VOL08-REREVIEW-001",
            note="Amendment C 일괄승인 Vol.08 재검수 (P0~P3 우선순위)", requests=out[b * BATCH:(b + 1) * BATCH]),
            ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(out), dict(collections.Counter(x["tier"] for x in out)))


if __name__ == "__main__":
    main()
