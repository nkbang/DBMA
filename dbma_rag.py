"""
DBMA-RAG : dbma.py가 만들어낸 {stem}.md / {stem}_chunks.txt 산출물을
색인(임베딩→벡터DB)하고, 질의에 대해 검색-증강 답변을 생성하는 2단계 파이프라인.

실행: streamlit run dbma_rag.py

설계 원칙
─────────
1) dbma.py의 출력 형식을 그대로 소비한다 (새 포맷을 만들지 않음).
   - {stem}.md          : YAML 유사 프런트매터(문서 단위 메타데이터) + 정제된 본문
   - {stem}_chunks.txt  : "════ CHUNK NNN/NNN ════" 구분자로 나뉜 청크 텍스트
2) 청크는 dbma.py가 이미 만든 것을 그대로 임베딩 단위로 사용한다 (재청킹하지 않음).
3) 노이즈 점수는 문서 단위 메타데이터로 각 청크에 함께 저장하고,
   "삭제"가 아니라 "질의 시점 필터"로 다룬다 (나중에 기준을 바꿔도 재색인이 필요 없음).
4) 임베딩과 생성(답변 작성) 모두 로컬에서 처리한다 (성경/설교 원고를 외부로 보내지 않음).
   생성 단계는 외부 API 대신 로컬에서 구동 중인 Ollama 서버를 호출한다.
"""

# ════════════════════════════════════════════════════════════════
# STANDALONE: 독립 RAG 실험용. 프로덕션 엔트리는 dbma.py
# ════════════════════════════════════════════════════════════════

import os
import re
import json
import glob
import logging

import streamlit as st


# ════════════════════════════════════════════════════════════════
# 설정
# ════════════════════════════════════════════════════════════════

APP_NAME = "DBMA-RAG"
APP_VERSION = "0.2.1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "data", "제련완성본")
DEFAULT_PERSIST_DIR = os.path.join(BASE_DIR, "data", "rag_index")

EMBED_MODEL_NAME = "intfloat/multilingual-e5-large"
EMBED_USES_E5_PREFIX = True

DEFAULT_OLLAMA_MODEL = "qwen2.5:14b"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"

CHUNK_HEADER_RE = re.compile(
    r"═+\s*CHUNK\s+(\d+)\s*/\s*(\d+)\s*═+\n(.*?)\n─+\n",
    re.DOTALL,
)


# ════════════════════════════════════════════════════════════════
# 디렉터리 보장 (import 시 안전, UI 이전에 실행)
# ════════════════════════════════════════════════════════════════

def ensure_dirs():
    os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    os.makedirs(DEFAULT_PERSIST_DIR, exist_ok=True)

ensure_dirs()


# ════════════════════════════════════════════════════════════════
# 로깅 (ensure_dirs 이후 설정)
# ════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "logs", "dbma_rag_streamlit.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# 산출물 파싱 (dbma.py 출력 형식 전용)
# ════════════════════════════════════════════════════════════════

def parse_chunks_file(path: str) -> list[str]:
    """{stem}_chunks.txt 를 읽어 청크 텍스트 리스트로 변환."""
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    chunks = []
    for _, _, body in CHUNK_HEADER_RE.findall(content):
        body = body.strip()
        if body:
            chunks.append(body)
    return chunks


def parse_md_frontmatter(path: str) -> dict:
    """{stem}.md 의 --- ... --- 프런트매터를 dict로 변환 (없으면 빈 dict)."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        head = fh.read(2000)
    m = re.match(r"^---\n(.*?)\n---\n", head, re.DOTALL)
    if not m:
        return {}
    meta = {}
    for line in m.group(1).split("\n"):
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
    return meta


def _to_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def discover_documents(output_dir: str) -> list[dict]:
    """output_dir 안의 {stem}_chunks.txt 와 짝이 되는 {stem}.md 메타데이터를 모아 반환."""
    docs = []
    for chunks_path in sorted(glob.glob(os.path.join(output_dir, "*_chunks.txt"))):
        stem = os.path.basename(chunks_path)[: -len("_chunks.txt")]
        md_path = os.path.join(output_dir, f"{stem}.md")
        meta = parse_md_frontmatter(md_path)
        docs.append(
            {
                "stem": stem,
                "chunks_path": chunks_path,
                "md_path": md_path,
                "mtime": os.path.getmtime(chunks_path),
                "source": meta.get("source", f"{stem}.pdf"),
                "languages": meta.get("languages", "unknown"),
                "noise_score": _to_float(meta.get("noise_score"), 0.0),
                "noise_status": meta.get("noise_status", "미평가"),
                "footnote_ratio": _to_float(meta.get("footnote_ratio"), 0.0),
            }
        )
    return docs


# ════════════════════════════════════════════════════════════════
# 임베딩 / 벡터DB
# ════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner="임베딩 모델 로딩 중... (최초 1회만 소요됩니다)")
def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL_NAME)


def embed_passages(embedder, texts: list[str]):
    prefixed = [f"passage: {t}" for t in texts] if EMBED_USES_E5_PREFIX else texts
    return embedder.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)


def embed_query(embedder, text: str):
    prefixed = f"query: {text}" if EMBED_USES_E5_PREFIX else text
    return embedder.encode([prefixed], normalize_embeddings=True, show_progress_bar=False)[0]


@st.cache_resource(show_spinner=False)
def get_collection(persist_dir: str):
    import chromadb
    os.makedirs(persist_dir, exist_ok=True)
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(name="dbma_chunks", metadata={"hnsw:space": "cosine"})


def load_index_state(persist_dir: str) -> dict:
    state_path = os.path.join(persist_dir, "_index_state.json")
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_index_state(persist_dir: str, state: dict):
    state_path = os.path.join(persist_dir, "_index_state.json")
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def build_index(output_dir: str, persist_dir: str, force: bool = False) -> list[str]:
    """변경되었거나 새로 생긴 문서만 (재)임베딩하여 색인. 로그 메시지 리스트 반환."""
    logs = []
    docs = discover_documents(output_dir)
    if not docs:
        return [f"⚠️  {output_dir} 에서 *_chunks.txt 파일을 찾지 못했습니다."]

    embedder = get_embedder()
    collection = get_collection(persist_dir)
    state = {} if force else load_index_state(persist_dir)

    for doc in docs:
        stem = doc["stem"]
        last_mtime = state.get(stem)
        if not force and last_mtime == doc["mtime"]:
            continue

        chunks = parse_chunks_file(doc["chunks_path"])
        if not chunks:
            logs.append(f"⚠️  {stem}: 청크를 찾지 못해 건너뜀")
            continue

        existing = collection.get(where={"stem": stem})
        if existing and existing.get("ids"):
            collection.delete(ids=existing["ids"])

        embeddings = embed_passages(embedder, chunks)
        ids = [f"{stem}__{i:03d}" for i in range(1, len(chunks) + 1)]
        metadatas = [
            {
                "stem": stem,
                "source": doc["source"],
                "chunk_index": i,
                "total_chunks": len(chunks),
                "languages": doc["languages"],
                "noise_score": doc["noise_score"],
                "noise_status": doc["noise_status"],
                "footnote_ratio": doc["footnote_ratio"],
            }
            for i in range(1, len(chunks) + 1)
        ]

        collection.upsert(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=chunks,
            metadatas=metadatas,
        )
        state[stem] = doc["mtime"]
        logs.append(f"✅ {stem}: {len(chunks)}개 청크 색인 완료 (noise={doc['noise_score']})")

    save_index_state(persist_dir, state)
    if not logs:
        logs.append("변경된 문서가 없어 색인을 갱신하지 않았습니다. (강제 재색인은 옆 버튼을 사용)")
    return logs


# ════════════════════════════════════════════════════════════════
# 검색 + 생성
# ════════════════════════════════════════════════════════════════

def retrieve(
    question: str,
    persist_dir: str,
    top_k: int,
    exclude_noisy: bool,
    noise_threshold: float,
) -> list[dict]:
    embedder = get_embedder()
    collection = get_collection(persist_dir)
    qvec = embed_query(embedder, question)

    where = {"noise_score": {"$lt": noise_threshold}} if exclude_noisy else None
    res = collection.query(query_embeddings=[qvec.tolist()], n_results=top_k, where=where)

    hits = []
    docs_ = res.get("documents", [[]])[0]
    metas_ = res.get("metadatas", [[]])[0]
    dists_ = res.get("distances", [[]])[0]
    for text, meta, dist in zip(docs_, metas_, dists_):
        hits.append({"text": text, "meta": meta, "distance": dist})
    return hits


def build_prompt(question: str, hits: list[dict]) -> str:
    context_blocks = []
    for i, h in enumerate(hits, 1):
        m = h["meta"]
        tag = f"[{i}] {m.get('source', '?')} · 청크 {m.get('chunk_index', '?')}/{m.get('total_chunks', '?')}"
        context_blocks.append(f"{tag}\n{h['text']}")
    context = "\n\n---\n\n".join(context_blocks)
    return (
        f"아래는 자료 검색 결과입니다. 이 자료에 근거해서만 답변하십시오.\n"
        f"자료에 없는 내용은 추측하지 말고 '제공된 자료에는 해당 내용이 없습니다'라고 밝히십시오.\n"
        f"답변 안에서 근거로 사용한 부분은 [번호] 형식으로 표시하십시오.\n\n"
        f"=== 검색된 자료 ===\n{context}\n\n"
        f"=== 질문 ===\n{question}\n"
    )


def generate_answer(question: str, hits: list[dict], model: str, host: str) -> str:
    import ollama
    client = ollama.Client(host=host)
    prompt = build_prompt(question, hits)
    resp = client.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 성경신학·원어(헬라어/히브리어) 연구를 돕는 보조 연구원입니다. "
                    "제공된 자료에 충실하게, 정확하고 신중하게 답하십시오."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        options={"temperature": 0.2},
        stream=False,
    )
    return resp["message"]["content"]


# ════════════════════════════════════════════════════════════════
# page_config — 독립 실행 시에만 호출 (import 시 충돌 방지)
# ════════════════════════════════════════════════════════════════

def configure_page():
    st.set_page_config(page_title=APP_NAME, layout="wide")


# ════════════════════════════════════════════════════════════════
# UI (독립 실행 전용)
# ════════════════════════════════════════════════════════════════

def main():
    configure_page()

    st.title(f"📚 {APP_NAME}  v{APP_VERSION}")
    st.caption("dbma.py 산출물(.md / _chunks.txt) → 임베딩 색인 → 질의응답")

    with st.sidebar:
        st.subheader("경로 설정")
        output_dir = st.text_input("DBMA 완성본 폴더", value=DEFAULT_OUTPUT_DIR)
        persist_dir = st.text_input("벡터DB 저장 폴더", value=DEFAULT_PERSIST_DIR)

        st.subheader("질의 설정")
        top_k = st.slider("검색 결과 개수 (top-k)", 1, 15, 5)
        exclude_noisy = st.checkbox("노이즈 심한 문서 제외", value=True)
        noise_threshold = st.slider(
            "노이즈 제외 기준 (이상이면 제외)",
            0, 100, 40,
            disabled=not exclude_noisy,
        )

        st.subheader("Ollama (로컬 LLM)")
        ollama_host = st.text_input("Ollama 서버 주소", value=DEFAULT_OLLAMA_HOST)
        ollama_model = st.text_input(
            "모델 이름",
            value=DEFAULT_OLLAMA_MODEL,
            help="미리 `ollama pull <모델명>`으로 받아둔 모델 이름을 입력하십시오.",
        )
        if st.button("🔌 Ollama 연결 확인"):
            try:
                import ollama
                available = ollama.Client(host=ollama_host).list()
                names = [m.get("model", m.get("name", "?")) for m in available.get("models", [])]
                st.success(f"연결 성공. 로컬 모델: {', '.join(names) if names else '없음'}")
            except Exception as e:
                st.error(f"Ollama 연결 실패: {e}\n`ollama serve`가 실행 중인지 확인하세요.")

    tab1, tab2 = st.tabs(["① 색인 구축", "② 질의 (RAG)"])

    with tab1:
        st.subheader("색인 구축")
        docs = discover_documents(output_dir) if os.path.isdir(output_dir) else []
        st.write(f"발견된 문서: **{len(docs)}개** (`*_chunks.txt` 기준)")
        if docs:
            st.dataframe(
                [
                    {
                        "문서": d["stem"],
                        "언어": d["languages"],
                        "노이즈": d["noise_score"],
                        "상태": d["noise_status"],
                    }
                    for d in docs
                ],
                use_container_width=True,
                hide_index=True,
            )

        c1, c2 = st.columns(2)
        if c1.button("🔄 증분 색인 (변경분만)", use_container_width=True):
            with st.spinner("색인 중..."):
                logs = build_index(output_dir, persist_dir, force=False)
            for line in logs:
                st.write(line)
        if c2.button("♻️ 전체 재색인", use_container_width=True):
            with st.spinner("전체 재색인 중..."):
                logs = build_index(output_dir, persist_dir, force=True)
            for line in logs:
                st.write(line)

        if os.path.isdir(persist_dir):
            try:
                collection = get_collection(persist_dir)
                st.info(f"현재 벡터DB에 색인된 청크 수: {collection.count()}개")
            except Exception as e:
                st.warning(f"벡터DB 상태를 읽을 수 없습니다: {e}")

    with tab2:
        st.subheader("질의 (검색-증강 답변)")
        question = st.text_area(
            "질문을 입력하십시오",
            height=100,
            placeholder="예) 신명기 12장에서 '그의 이름을 두시려고 택하신 곳'이 의미하는 신학적 함의는?",
        )

        if st.button("🔍 검색 + 답변 생성", type="primary"):
            if not os.path.isdir(persist_dir):
                st.error("먼저 ① 탭에서 색인을 구축해 주세요.")
            elif not question.strip():
                st.warning("질문을 입력해 주세요.")
            else:
                with st.spinner("관련 자료 검색 중..."):
                    hits = retrieve(question, persist_dir, top_k, exclude_noisy, noise_threshold)

                if not hits:
                    st.warning("검색된 자료가 없습니다. 노이즈 제외 기준을 완화하거나 색인을 확인해 주세요.")
                else:
                    with st.expander(f"검색된 자료 {len(hits)}건 (참고용 원문)", expanded=False):
                        for i, h in enumerate(hits, 1):
                            m = h["meta"]
                            st.markdown(
                                f"**[{i}] {m.get('source')}** · 청크 {m.get('chunk_index')}/{m.get('total_chunks')} "
                                f"· 유사도거리 {h['distance']:.3f} · 노이즈 {m.get('noise_score')}"
                            )
                            st.text(h["text"][:600] + ("..." if len(h["text"]) > 600 else ""))
                            st.divider()

                    if not ollama_model.strip():
                        st.warning("사이드바에 Ollama 모델 이름을 입력하면 답변까지 생성됩니다.")
                    else:
                        with st.spinner(f"{ollama_model} 로 답변 작성 중..."):
                            try:
                                answer = generate_answer(question, hits, ollama_model, ollama_host)
                                st.markdown("### 답변")
                                st.markdown(answer)
                            except Exception as e:
                                st.error(
                                    f"답변 생성 실패: {e}\n"
                                    f"`ollama serve` 실행 여부, `ollama pull {ollama_model}` 여부를 확인하세요."
                                )


# ════════════════════════════════════════════════════════════════
# 진입점
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
