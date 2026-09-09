"""NAE Fuller — SANDBOX retrieval test app (isolated, non-production).

Streamlit search UI over `nae_tsu_fuller_sandbox_v0` (Fuller Vol.01 TSU,
3,643 claims embedded with bge-m3, the production embed path). Optionally
shows `nae_tsu_v1` (Dagg/Hiscox baseline, 3,319) side-by-side, READ-ONLY.

Optional "답변 생성" (grounded RAG) mode: the top retrieved claims are handed
to a local model which answers the question using ONLY those claims, with
[TSU-ID] references. This mirrors the production RAG answer step but stays in
the sandbox — no generation is written back anywhere.

This is NOT the production app. It does not enable `nae_pd`, does not touch
`nae_tsu_v1` / `nae_ref_v1`, and is not gated by Amendment A (which governs
F4/F5/F6 into `nae_tsu_v1`). `review_status` is `generated` (no human
review) and CJK contamination (~10% of Vol.01 claims) is NOT yet repaired.

Run:
  ~/envs/dbma311/bin/streamlit run scripts/nae_fuller_sandbox_search_app.py --server.port 8710
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import ollama
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from NAE.pipeline.embed import client as embed_client  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402

QDRANT_URL = "http://localhost:7333"
FULLER_COLL = "nae_tsu_fuller_sandbox_v0"
BASELINE_COLL = "nae_tsu_v1"
HAN = re.compile(r"[㐀-䶿一-鿿豈-﫿]")


# my-theology-bot-v2 is already GPU-resident (F2 uses it) — no extra VRAM.
# llama3.1:8b is tiny; picking it co-loads a 3rd model but adds little compute
# contention. Both share the GPU with the running F2 job.
GEN_MODELS = ["my-theology-bot-v2:latest", "llama3.1:8b", "qwen3.8:27b"]

_ANSWER_PROMPT = """너는 Andrew Fuller의 『The Gospel Worthy of All Acceptation』(전집 제1권)에서
검색된 신학적 주장(근거)들을 바탕으로 질문에 답하는 조수다.

질문: {query}

[검색된 근거]
{evidence}

규칙:
- 위 [검색된 근거]에 담긴 내용만으로 답한다. 근거에 없는 내용은 추측하거나 지어내지 않는다.
- 근거가 질문에 답하기에 부족하면 그렇게 말한다("제공된 자료로는 충분히 답하기 어렵다").
- 답변에 사용한 근거는 해당 문장 뒤에 [TSU-ID] 형식으로 표기한다.
- 한국어로, 3~6문장으로 간결하게 답한다. 한자·중국어를 쓰지 않는다.

답변:"""


@st.cache_resource
def _client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, timeout=30)


def _generate_answer(query: str, hits, model: str) -> str | None:
    if not hits:
        return None
    lines = []
    for h in hits:
        p = h.payload
        lines.append(f"[{p.get('tsu_id')}] ({p.get('doctrine') or '—'}) {p.get('claim') or ''}")
        src = (p.get("source_text") or "").strip()
        if src:
            lines.append(f"    원문: {src[:300]}")
    prompt = _ANSWER_PROMPT.format(query=query, evidence="\n".join(lines))
    try:
        r = ollama.generate(model=model, prompt=prompt, options={"temperature": 0.0})
        return (r.get("response") or "").strip() or None
    except Exception as e:  # noqa: BLE001
        return f"__ERROR__ {e}"


def _embed_query(text: str) -> list[float] | None:
    h = "sbxq_" + hashlib.sha1(text.encode("utf-8")).hexdigest()
    return embed_client.embed_text(text, content_hash=h)


def _search(coll: str, qv: list[float], k: int, doctrine: str | None):
    from qdrant_client import models as qm
    flt = None
    if doctrine and doctrine != "(전체)":
        flt = qm.Filter(must=[qm.FieldCondition(key="doctrine", match=qm.MatchValue(value=doctrine))])
    return _client().query_points(coll, query=qv, limit=k, with_payload=True, query_filter=flt).points


def _render_hit(h, rank: int):
    p = h.payload
    claim = p.get("claim") or ""
    cjk = " 🈲CJK" if HAN.search(claim) else ""
    st.markdown(f"**{rank}. `{h.score:.3f}`  ·  {p.get('doctrine') or '—'}{cjk}**")
    st.markdown(f"> {claim}")
    meta = f"{p.get('tsu_id')} · {p.get('book') or ''} p.{p.get('page')}"
    sc = p.get("scriptures") or []
    if sc:
        meta += " · " + ", ".join(sc)
    st.caption(meta)
    with st.expander("source_text"):
        st.write(p.get("source_text") or "")
    st.divider()


def main() -> None:
    st.set_page_config(page_title="Fuller Sandbox Search", layout="wide")
    st.title("NAE Fuller — Sandbox Retrieval Test")
    st.warning(
        "SANDBOX · 프로덕션 아님 · `review_status=generated`(인간 검수 전) · "
        "CJK 오염 미수정(claim 약 10%에 한자 잔존, 🈲 표시) · "
        "`nae_tsu_v1`/`nae_ref_v1` baseline 무접촉",
        icon="⚠️",
    )

    try:
        info = _client().get_collection(FULLER_COLL)
        st.caption(f"collection `{FULLER_COLL}` · {info.points_count} points · bge-m3 1024d cosine")
    except Exception as e:  # noqa: BLE001
        st.error(f"{FULLER_COLL} 컬렉션을 찾을 수 없음 ({e}). 먼저 샌드박스 임베딩을 생성하세요.")
        st.stop()

    with st.sidebar:
        st.header("옵션")
        k = st.slider("top-k", 3, 20, 8)
        doctrine = st.selectbox("doctrine 필터", [
            "(전체)", "Soteriology", "Ecclesiology", "Justification", "Sanctification",
            "Election", "Providence", "Eschatology", "Trinity", "Scripture / Authority",
            "Baptism", "Lord's Supper", "Church Discipline", "Other",
        ])
        show_baseline = st.checkbox("Dagg/Hiscox baseline 대조 표시", value=True)
        st.caption("baseline은 읽기 전용 조회입니다.")
        st.divider()
        answer_mode = st.checkbox("답변 생성 (RAG)", value=False)
        gen_model = st.selectbox("생성 모델", GEN_MODELS, disabled=not answer_mode)
        st.caption("Fuller Vol.01 상위 결과만 근거로 답을 생성합니다. "
                   "F2와 GPU 공유 — 응답 10~40초, F2 소폭 지연 가능.")

    examples = [
        "믿음은 모든 사람의 의무인가",
        "구원은 오직 은혜로 말미암는가",
        "그리스도의 속죄의 범위",
        "믿음으로 의롭다 하심을 받음",
        "하나님의 섭리와 고난",
    ]
    ex = st.selectbox("예시 질의", ["(직접 입력)"] + examples)
    default_q = "" if ex == "(직접 입력)" else ex
    query = st.text_input("신학 질의", value=default_q, placeholder="예: 회심하지 못한 죄인도 믿으라는 명령을 받는가")

    if not query.strip():
        st.info("질의를 입력하면 Fuller Vol.01 TSU에서 의미 검색합니다.")
        return

    with st.spinner("bge-m3 임베딩 + 검색..."):
        qv = _embed_query(query)
    if qv is None:
        st.error("임베딩 실패 (Ollama bge-m3 확인).")
        return

    fuller_hits = _search(FULLER_COLL, qv, k, doctrine)

    if answer_mode:
        st.subheader("생성 답변")
        with st.spinner(f"{gen_model} 답변 생성 중..."):
            ans = _generate_answer(query, fuller_hits[:8], gen_model)
        if ans is None:
            st.info("검색 결과가 없어 답변을 생성할 수 없습니다.")
        elif ans.startswith("__ERROR__"):
            st.error(f"생성 실패: {ans[9:].strip()}")
        else:
            if HAN.search(ans):
                st.caption("⚠️ 생성 답변에 한자 잔존 (모델 코드스위칭)")
            st.info(ans)
        st.caption("※ 위 답변은 아래 Fuller Vol.01 상위 결과만을 근거로 한 생성물입니다. "
                   "SANDBOX — 검증되지 않음.")
        st.divider()

    if show_baseline:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Fuller Vol.01")
            for i, h in enumerate(fuller_hits, 1):
                _render_hit(h, i)
        with c2:
            st.subheader("Dagg / Hiscox (baseline)")
            try:
                for i, h in enumerate(_search(BASELINE_COLL, qv, k, doctrine), 1):
                    _render_hit(h, i)
            except Exception as e:  # noqa: BLE001
                st.caption(f"baseline 조회 불가: {e}")
    else:
        st.subheader("Fuller Vol.01")
        for i, h in enumerate(fuller_hits, 1):
            _render_hit(h, i)


main()
