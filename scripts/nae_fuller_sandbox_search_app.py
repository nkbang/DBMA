"""NAE Fuller — SANDBOX retrieval test app (isolated, non-production).

Streamlit search UI over `nae_tsu_fuller_sandbox_v0` (Fuller Vol.01 TSU,
3,643 claims embedded with bge-m3, the production embed path). Optionally
shows `nae_tsu_v1` (Dagg/Hiscox baseline, 3,319) side-by-side, READ-ONLY.

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

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from NAE.pipeline.embed import client as embed_client  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402

QDRANT_URL = "http://localhost:7333"
FULLER_COLL = "nae_tsu_fuller_sandbox_v0"
BASELINE_COLL = "nae_tsu_v1"
HAN = re.compile(r"[㐀-䶿一-鿿豈-﫿]")


@st.cache_resource
def _client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, timeout=30)


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

    if show_baseline:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Fuller Vol.01")
            for i, h in enumerate(_search(FULLER_COLL, qv, k, doctrine), 1):
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
        for i, h in enumerate(_search(FULLER_COLL, qv, k, doctrine), 1):
            _render_hit(h, i)


main()
