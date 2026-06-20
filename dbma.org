import streamlit as st
import os
import glob
import shutil
import warnings
import logging
import datetime
import re
import unicodedata
from typing import List, Dict, Optional, Tuple

from bs4 import BeautifulSoup
from docx import Document
from ebooklib import epub, ITEM_DOCUMENT
from striprtf.striprtf import rtf_to_text

# ── 환경 / 설정 ────────────────────────────────────────────────────────────
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", message=".*__path__.*")
logging.getLogger("transformers").setLevel(logging.ERROR)

st.set_page_config(
    page_title="DBMA 파싱 파이프라인",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RAW_DIR = os.path.join(BASE_DIR, "data", "RAW")
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "data", "제련완성본")
SUPPORTED_EXTENSIONS = [".pdf", ".txt", ".md", ".docx", ".epub", ".html", ".htm", ".rtf"]


# ── 스타일 / 헤더 ─────────────────────────────────────────────────────────
def inject_styles() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Noto Serif KR', serif; }
.dbma-header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); border-radius: 12px; padding: 28px 36px; margin-bottom: 24px; border-left: 5px solid #e94560; }
.dbma-header h1 { color: #fff; font-size: 1.8rem; font-weight: 700; margin: 0 0 4px 0; letter-spacing: -0.02em; }
.dbma-header p { color: #a8b2d8; font-size: 0.85rem; margin: 0; font-family: 'JetBrains Mono', monospace; }
.file-table-header { display: grid; grid-template-columns: 40px 1fr 90px 150px 80px; background: #161b22; padding: 9px 12px; font-size: 0.70rem; color: #8b949e; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 0.08em; border: 1px solid #21262d; border-radius: 8px 8px 0 0; }
.file-row { display: grid; grid-template-columns: 40px 1fr 90px 150px 80px; padding: 9px 12px; border: 1px solid #21262d; border-top: none; align-items: center; font-size: 0.80rem; background: #0d1117; }
.file-row:last-child { border-radius: 0 0 8px 8px; }
.file-row:hover { background: #161b22; }
.fname { color: #58a6ff; font-family: 'JetBrains Mono', monospace; font-size: 0.76rem; word-break: break-all; }
.fsize { color: #3fb950; font-family: 'JetBrains Mono', monospace; font-size: 0.74rem; }
.fdate { color: #8b949e; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; }
.fbadge { display: inline-block; background: #1f3a5f; color: #58a6ff; border-radius: 4px; padding: 1px 7px; font-size: 0.66rem; font-family: 'JetBrains Mono', monospace; font-weight: 500; text-align: center; min-width: 54px; }
.stat-row { display: flex; gap: 12px; margin-bottom: 16px; }
.stat-card { flex: 1; background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 13px 17px; }
.stat-label { font-size: 0.67rem; color: #8b949e; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 3px; font-family: 'JetBrains Mono', monospace; }
.stat-value { font-size: 1.35rem; font-weight: 700; color: #e6edf3; font-family: 'JetBrains Mono', monospace; }
.blue { color: #58a6ff; } .green { color: #3fb950; } .orange { color: #d29922; } .red { color: #f85149; }
.log-box { background: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 13px 17px; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #c9d1d9; max-height: 320px; overflow-y: auto; line-height: 1.9; }
.log-ok { color: #3fb950; } .log-warn { color: #d29922; } .log-err { color: #f85149; } .log-info { color: #58a6ff; }
.noise-bar-wrap { background: #21262d; border-radius: 6px; height: 14px; overflow: hidden; margin: 6px 0 2px; }
.noise-bar { height: 14px; border-radius: 6px; transition: width 0.4s; }
.analysis-card { background: #161b22; border: 1px solid #21262d; border-radius: 10px; padding: 16px 20px; margin-bottom: 12px; }
.analysis-card h4 { color: #e6edf3; font-size: 0.9rem; margin: 0 0 10px; font-weight: 600; }
.chunk-box { background: #0d1117; border-left: 3px solid #58a6ff; border-radius: 0 6px 6px 0; padding: 10px 14px; margin: 8px 0; font-family: 'JetBrains Mono', monospace; font-size: 0.73rem; color: #c9d1d9; line-height: 1.7; }
div[data-testid="stButton"] button { background: linear-gradient(135deg, #e94560, #c23152) !important; color: white !important; border: none !important; border-radius: 8px !important; font-family: 'Noto Serif KR', serif !important; font-weight: 600 !important; padding: 10px 28px !important; font-size: 0.95rem !important; }
section[data-testid="stSidebar"] { background: #0d1117; border-right: 1px solid #21262d; }
section[data-testid="stSidebar"] label { color: #c9d1d9 !important; }
section[data-testid="stSidebar"] .stTextInput input, section[data-testid="stSidebar"] .stNumberInput input { background: #161b22 !important; border-color: #30363d !important; color: #e6edf3 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.82rem !important; }
div[data-testid="stCheckbox"] { margin-bottom: 0 !important; padding: 2px 0 !important; }
</style>
""",
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
<div class="dbma-header">
    <h1>DBMA</h1>
    <p>David Bang Ministry Archive · RAG 데이터 정제 시스템 v3.2</p>
</div>
""",
        unsafe_allow_html=True,
    )


# ── 유틸리티 ──────────────────────────────────────────────────────────────
def fmt_size(b: int) -> str:
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


def make_safe_stem(filename: str) -> str:
    name, ext = os.path.splitext(filename)
    return f"{name}__{ext.lower().replace('.', '')}"


def noise_color(score: float) -> str:
    if score <= 20:
        return "#3fb950"
    if score <= 40:
        return "#d29922"
    return "#f85149"


def noise_label(score: float) -> str:
    if score <= 20:
        return "GOOD"
    if score <= 40:
        return "WARN"
    return "BAD"


def apply_select_all() -> None:
    newval = st.session_state.select_all
    for key in list(st.session_state.keys()):
        if key.startswith("sel_"):
            st.session_state[key] = newval


def on_item_change() -> None:
    selkeys = [k for k in st.session_state if k.startswith("sel_")]
    if selkeys:
        st.session_state.select_all = all(st.session_state[k] for k in selkeys)


# ── 파일 / 스캔 ───────────────────────────────────────────────────────────
def scan_directory(directory: str) -> List[Dict]:
    if not os.path.isdir(directory):
        return []

    files = []
    for ext in SUPPORTED_EXTENSIONS:
        for fp in glob.glob(os.path.join(directory, f"*{ext}")):
            if not os.path.isfile(fp):
                continue
            s = os.stat(fp)
            files.append({
                "path": fp,
                "name": os.path.basename(fp),
                "size_b": s.st_size,
                "size_str": fmt_size(s.st_size),
                "mtime": datetime.datetime.fromtimestamp(s.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "ext": os.path.splitext(fp)[1].lower().replace(".", ""),
            })
    files.sort(key=lambda x: x["name"].lower())
    return files


def scan_md_files(directory: str) -> List[Dict]:
    if not os.path.isdir(directory):
        return []
    result = []
    for fp in sorted(glob.glob(os.path.join(directory, "*.md"))):
        s = os.stat(fp)
        result.append({
            "path": fp,
            "name": os.path.basename(fp),
            "size_str": fmt_size(s.st_size),
            "mtime": datetime.datetime.fromtimestamp(s.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return result


def load_chunks_info(directory: str, stem: str) -> Optional[List[str]]:
    txt_path = os.path.join(directory, f"{stem}_chunks.txt")
    if not os.path.exists(txt_path):
        return None
    with open(txt_path, encoding="utf-8") as fh:
        raw = fh.read()
    blocks = re.split(r"======== CHUNK \d+/\d+ ========", raw)
    chunks = [b.strip().rstrip("=").strip() for b in blocks if b.strip() and not b.startswith("DBMA Chunk File")]
    return chunks if chunks else None


# ── 품질 / 언어 분석 ──────────────────────────────────────────────────────
def calculate_noise_score(text: str) -> Dict:
    if not text or len(text) < 50:
        return {
            "total": 100.0,
            "symbolratio": 40.0,
            "shortline": 30.0,
            "blankratio": 15.0,
            "repeatratio": 15.0,
            "charcount": len(text) if text else 0,
            "linecount": 1,
            "wordcount": 0,
            "langdetected": "",
        }

    text = unicodedata.normalize("NFC", text)
    lines = text.splitlines()
    charcount = len(text)
    wordcount = len(text.split())
    linecount = len(lines)

    has_korean = bool(re.search(r"[가-힣]", text))
    has_hebrew = bool(re.search(r"[\u05b0-\u05ea\u0591-\u05f4]", text))
    has_greek = bool(re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", text))
    has_english = bool(re.search(r"[a-zA-Z]", text))
    langdetected = "ko" if has_korean else "he" if has_hebrew else "el" if has_greek else "en" if has_english else ""

    allowed = re.compile(r"[가-힣a-zA-Z\u05b0-\u05ea\u0591-\u05f4\u0370-\u03ff\u1f00-\u1fff0-9\s\.,!?\-:;\(\)\[\]\{\}\'\"/\\%&@#\*\+=_]")
    nonallowed = sum(1 for ch in text if not allowed.match(ch))
    symscore = min((nonallowed / max(charcount, 1)) * 40 * 5, 40.0)

    shortlines = sum(1 for ln in lines if 0 < len(ln.strip()) < 20)
    slscore = min((shortlines / max(linecount, 1)) * 30 * 2, 30.0)

    blanklines = sum(1 for ln in lines if not ln.strip())
    blscore = min((blanklines / max(linecount, 1)) * 15 * 3, 15.0)

    repeats = len(re.findall(r"(.)\1{3,14}", text))
    rpscore = min(repeats * 3.0, 15.0)

    total = symscore + slscore + blscore + rpscore
    return {
        "total": round(total, 2),
        "symbolratio": round(symscore, 2),
        "shortline": round(slscore, 2),
        "blankratio": round(blscore, 2),
        "repeatratio": round(rpscore, 2),
        "charcount": charcount,
        "linecount": linecount,
        "wordcount": wordcount,
        "langdetected": langdetected,
    }


def detect_langs(text: str) -> List[str]:
    found = []
    if any("\u0600" <= c <= "\u06ff" or "\u05b0" <= c <= "\u05ea" for c in text):
        found.append("he")
    if any("\u0370" <= c <= "\u03ff" or "\u1f00" <= c <= "\u1fff" for c in text):
        found.append("el")
    if any("가" <= c <= "힣" for c in text):
        found.append("ko")
    if any(c.isascii() and c.isalpha() for c in text[:5000]):
        found.append("en")
    return found


# ── 추출기 ────────────────────────────────────────────────────────────────
def read_text_file(path: str) -> str:
    encodings = ["utf-8", "utf-8-sig", "cp949", "euc-kr"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as fh:
                return fh.read()
        except Exception:
            continue
    raise ValueError(f"텍스트 파일 인코딩을 읽을 수 없습니다: {os.path.basename(path)}")


def extract_text_from_txt(path: str) -> str:
    return read_text_file(path)


def extract_text_from_md(path: str) -> str:
    return read_text_file(path)


def extract_text_from_html(path: str) -> str:
    raw = read_text_file(path)
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def extract_text_from_docx(path: str) -> str:
    doc = Document(path)
    parts = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            parts.append(text)
    for table in doc.tables:
        for row in table.rows:
            row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_text:
                parts.append(" | ".join(row_text))
    return "\n\n".join(parts).strip()


def extract_text_from_epub(path: str) -> str:
    book = epub.read_epub(path)
    texts = []
    for item in book.get_items():
        if item.get_type() == ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text("\n", strip=True)
            if text:
                texts.append(text)
    return "\n\n".join(texts).strip()


def extract_text_from_rtf(path: str) -> str:
    raw = read_text_file(path)
    return rtf_to_text(raw).strip()


def extract_text_from_pdf(path: str, converter) -> str:
    result = converter.convert(path)
    if not result or not result.document:
        raise ValueError("PDF 변환 실패")
    full_text = result.document.export_to_markdown()
    if not full_text or not full_text.strip():
        raise ValueError("PDF/OCR 결과가 비어 있습니다")
    return full_text


def extract_text_from_file(path: str, converter=None) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        if converter is None:
            raise ValueError("PDF 처리에 converter가 필요합니다")
        return extract_text_from_pdf(path, converter)
    if ext == ".txt":
        return extract_text_from_txt(path)
    if ext == ".md":
        return extract_text_from_md(path)
    if ext in [".html", ".htm"]:
        return extract_text_from_html(path)
    if ext == ".docx":
        return extract_text_from_docx(path)
    if ext == ".epub":
        return extract_text_from_epub(path)
    if ext == ".rtf":
        return extract_text_from_rtf(path)
    raise ValueError(f"지원하지 않는 형식: {ext}")


# ── 저장 / 처리 ───────────────────────────────────────────────────────────
def save_md(stem: str, source_name: str, text: str, noise: Dict, output_dir: str) -> str:
    md_path = os.path.join(output_dir, f"{stem}.md")
    lang_list = detect_langs(text)
    has_rtl = "he" in lang_list
    header = f"""---
source: {source_name}
created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
pipeline: DBMA v3.2
languages: {', '.join(lang_list) if lang_list else 'unknown'}
rtl_content: {'true' if has_rtl else 'false'}
noise_score: {noise['total']}
noise_status: {noise_label(noise['total'])}
char_count: {noise['charcount']}
word_count: {noise['wordcount']}
---

"""
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(header + text)
    return md_path


def save_chunks(stem: str, source_name: str, chunks: List[str], output_dir: str, chunk_size: int, chunk_overlap: int) -> str:
    txt_path = os.path.join(output_dir, f"{stem}_chunks.txt")
    total_c = len(chunks)
    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write(
            f"DBMA Chunk File\n"
            f"source: {source_name}\n"
            f"created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"chunks: {total_c}\n"
            f"chunk_size: {int(chunk_size)}\n"
            f"overlap: {int(chunk_overlap)}\n\n"
        )
        for i, chunk in enumerate(chunks, 1):
            fh.write(f"======== CHUNK {i:03d}/{total_c:03d} ========\n")
            fh.write(chunk.strip())
            fh.write("\n\n")
    return txt_path


def build_converter(use_ocr: bool):
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions

    pipeline_options = PdfPipelineOptions()
    if use_ocr:
        pipeline_options.do_ocr = True
        pipeline_options.ocr_options = EasyOcrOptions(lang=["ko", "en", "he", "el"], use_gpu=False)
    else:
        pipeline_options.do_ocr = False

    return DocumentConverter(format_options={"pdf": PdfFormatOption(pipeline_options=pipeline_options)})


def build_splitter(chunk_size: int, chunk_overlap: int):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    separators = ["\n\n", "\n", ". ", "。", "? ", "! ", ", ", " ", ""]
    return RecursiveCharacterTextSplitter(
        chunk_size=int(chunk_size),
        chunk_overlap=int(chunk_overlap),
        separators=separators,
        keep_separator=True,
    )


def process_one_file(file_info: Dict, converter, splitter, output_dir: str, chunk_size: int, chunk_overlap: int) -> Tuple[List[Dict], bool]:
    logs = []
    name = file_info["name"]
    safe_stem = make_safe_stem(name)
    src_path = file_info["path"]
    ext = os.path.splitext(name)[1].lower()
    dest_path = os.path.join(output_dir, name)

    full_text = extract_text_from_file(src_path, converter=converter)
    if not full_text.strip():
        raise ValueError(f"{name} 추출 결과가 비어 있습니다.")

    noise = calculate_noise_score(full_text)
    lang_list = detect_langs(full_text)
    lang_found = ", ".join({"ko": "KO", "en": "EN", "he": "HE", "el": "EL"}.get(l, l) for l in lang_list) or "-"

    logs.append({"cls": "log-info", "msg": f"형식: {ext}"})
    logs.append({"cls": "log-info", "msg": f"언어: {lang_found}"})
    logs.append({"cls": "log-info", "msg": f"노이즈: {noise['total']:.1f} / {noise_label(noise['total'])}"})

    md_path = save_md(safe_stem, name, full_text, noise, output_dir)
    logs.append({"cls": "log-ok", "msg": f"MD 저장: {os.path.basename(md_path)}"})

    chunks = splitter.split_text(full_text)
    txt_path = save_chunks(safe_stem, name, chunks, output_dir, int(chunk_size), int(chunk_overlap))
    logs.append({"cls": "log-ok", "msg": f"CHUNKS 저장: {os.path.basename(txt_path)} / {len(chunks)} chunks"})

    shutil.move(src_path, dest_path)
    logs.append({"cls": "log-ok", "msg": f"원본 이동: {name}"})

    if noise["total"] > 40:
        logs.append({"cls": "log-warn", "msg": f"{name} 노이즈 높음"})

    return logs, True


# ── UI 렌더링 ─────────────────────────────────────────────────────────────
def render_sidebar() -> Tuple[str, str, int, int, bool]:
    with st.sidebar:
        st.markdown("### 경로 설정")
        st.markdown("---")
        target_dir = st.text_input("RAW 폴더", value=DEFAULT_RAW_DIR)
        output_dir = st.text_input("출력 폴더", value=DEFAULT_OUTPUT_DIR)
        st.caption("지원 형식: PDF, TXT, MD, DOCX, EPUB, HTML, HTM, RTF")
        st.markdown("---")

        st.markdown("### 분절 설정")
        chunk_size = st.number_input("Chunk Size", value=1000, min_value=100, step=100)
        chunk_overlap = st.number_input("Chunk Overlap", value=200, min_value=0, step=50)
        st.markdown("---")

        st.markdown("### OCR")
        use_ocr = st.checkbox("OCR for PDF", value=False, help="스캔형 PDF나 이미지 기반 PDF에만 사용하세요.")
        if use_ocr:
            st.info("EasyOCR: ko, en, he, el")

        st.markdown("---")
        st.markdown(
            """
<div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;color:#3fb950;padding:8px 10px;background:#0d2b1a;border-radius:6px;border:1px solid #1a4a2a;">
다중 문서 형식 지원<br><br>
PDF / TXT / MD / DOCX / EPUB / HTML / RTF
</div>
""",
            unsafe_allow_html=True,
        )

    return target_dir, output_dir, int(chunk_size), int(chunk_overlap), use_ocr


def render_file_table(file_list: List[Dict]) -> List[Dict]:
    if not file_list:
        return []

    current_names = {f["name"] for f in file_list}
    for key in list(st.session_state.keys()):
        if key.startswith("sel_") and key[4:] not in current_names:
            del st.session_state[key]

    for f in file_list:
        if f"sel_{f['name']}" not in st.session_state:
            st.session_state[f"sel_{f['name']}"] = True
    if "select_all" not in st.session_state:
        st.session_state.select_all = True

    total_size = sum(f["size_b"] for f in file_list)
    st.markdown(
        f"""
<div class="stat-row">
    <div class="stat-card"><div class="stat-label">Files</div><div class="stat-value blue">{len(file_list)}</div></div>
    <div class="stat-card"><div class="stat-label">Total Size</div><div class="stat-value orange">{fmt_size(total_size)}</div></div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.checkbox("전체 선택", key="select_all", on_change=apply_select_all)
    st.markdown(
        """
<div class="file-table-header">
    <span></span><span>이름</span><span>크기</span><span>수정일</span><span>형식</span>
</div>
""",
        unsafe_allow_html=True,
    )

    selected_files = []
    for f in file_list:
        c1, c2 = st.columns((1, 12))
        with c1:
            st.checkbox("label", key=f"sel_{f['name']}", on_change=on_item_change, label_visibility="collapsed")
        with c2:
            st.markdown(
                f"""
<div class="file-row">
    <span></span>
    <span class="fname">{f['name']}</span>
    <span class="fsize">{f['size_str']}</span>
    <span class="fdate">{f['mtime']}</span>
    <span class="fbadge">{f['ext'].upper()}</span>
</div>
""",
                unsafe_allow_html=True,
            )
        if st.session_state.get(f"sel_{f['name']}", False):
            selected_files.append(f)

    if selected_files:
        sel_size = sum(f["size_b"] for f in selected_files)
        st.markdown(
            f"<div style='font-size:0.77rem;color:#3fb950;padding:7px 4px;font-family:JetBrains Mono,monospace'>{len(selected_files)}개 선택 / {fmt_size(sel_size)}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='font-size:0.77rem;color:#d29922;padding:7px 4px;font-family:JetBrains Mono,monospace'>선택된 파일이 없습니다.</div>",
            unsafe_allow_html=True,
        )

    return selected_files


def render_logs(log_ph, entries: List[Dict]) -> None:
    html = '<div class="log-box">'
    for e in entries:
        html += f'<div class="{e["cls"]}">{e["msg"]}</div>'
    html += '</div>'
    log_ph.markdown(html, unsafe_allow_html=True)


def render_processing_tab(target_dir: str, output_dir: str, chunk_size: int, chunk_overlap: int, use_ocr: bool) -> None:
    colleft, colright = st.columns((3, 2), gap="large")

    with colleft:
        st.markdown("")
        refcol, pathcol = st.columns((1, 4))
        with refcol:
            st.button("↻")
        with pathcol:
            st.markdown(
                f"<div style='font-family:JetBrains Mono,monospace;font-size:0.76rem;color:#8b949e;padding-top:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>{target_dir}</div>",
                unsafe_allow_html=True,
            )

        file_list = scan_directory(target_dir)
        if not file_list:
            st.warning(f"{target_dir} 에 지원 형식 파일이 없습니다.")
            selected_files = []
        else:
            selected_files = render_file_table(file_list)

    with colright:
        n_sel = len(selected_files) if file_list else 0
        ocr_label = "EasyOCR ko·en·he·el" if use_ocr else "OFF"
        st.markdown(
            f"""
<div style="background:#161b22;border:1px solid #21262d;border-radius:8px; padding:14px 18px;margin-bottom:16px;font-family:JetBrains Mono,monospace; font-size:0.75rem;line-height:2.1">
<span style="color:#8b949e">CHUNK SIZE</span> <span style="color:#e6edf3">{int(chunk_size)}</span><br>
<span style="color:#8b949e">OVERLAP</span> <span style="color:#e6edf3">{int(chunk_overlap)}</span><br>
<span style="color:#8b949e">OCR</span> <span style="color:{'#3fb950' if use_ocr else '#8b949e'}">{ocr_label}</span><br>
<span style="color:#8b949e">지원 형식</span> <span style="color:#3fb950">{', '.join([x.replace('.', '').upper() for x in SUPPORTED_EXTENSIONS])}</span><br>
<span style="color:#8b949e">선택 파일</span> <span style="color:#58a6ff">{n_sel}</span>
</div>
""",
            unsafe_allow_html=True,
        )

        start_btn = st.button(f"선택 파일 처리 ({n_sel}개)", disabled=not file_list or n_sel == 0)
        st.markdown("---")
        log_ph = st.empty()
        prog_ph = st.empty()

        if start_btn and selected_files:
            os.makedirs(output_dir, exist_ok=True)
            converter = build_converter(use_ocr)
            splitter = build_splitter(chunk_size, chunk_overlap)
            logs, ok_count, fail_count = [], 0, 0
            total = len(selected_files)

            logs.append({"cls": "log-info", "msg": f"총 {total}개 파일 처리 시작"})
            logs.append({"cls": "log-info", "msg": f"출력 폴더: {output_dir}"})
            if use_ocr:
                logs.append({"cls": "log-info", "msg": "OCR 활성화: EasyOCR ko/en/he/el"})
            render_logs(log_ph, logs)

            for idx, f in enumerate(selected_files):
                prog_ph.progress(idx / total, text=f"{idx+1}/{total} {f['name']}")
                logs.append({"cls": "log-info", "msg": f"[{idx+1}/{total}] {f['name']}"})
                try:
                    file_logs, success = process_one_file(f, converter, splitter, output_dir, chunk_size, chunk_overlap)
                    logs.extend(file_logs)
                    if success:
                        ok_count += 1
                except Exception as e:
                    logs.append({"cls": "log-err", "msg": f"{f['name']} 오류: {e}"})
                    fail_count += 1
                render_logs(log_ph, logs)

            prog_ph.progress(1.0, text="완료")
            logs.append({"cls": "log-ok" if fail_count == 0 else "log-warn", "msg": f"완료: 성공 {ok_count} / 실패 {fail_count}"})
            logs.append({"cls": "log-info", "msg": f"결과물은 .md / _chunks.txt / 원본 파일 형태로 {output_dir}에 저장됩니다."})
            render_logs(log_ph, logs)

            if fail_count == 0:
                st.success(f"총 {ok_count}개 파일 처리 완료")
            else:
                st.warning(f"성공 {ok_count}개 / 실패 {fail_count}개")


def render_analysis_tab(output_dir: str) -> None:
    st.markdown("")
    md_files = scan_md_files(output_dir)
    if not md_files:
        st.warning(f"{output_dir}에 분석 가능한 .md 파일이 없습니다.")
        return

    all_scores = []
    for mf in md_files:
        with open(mf["path"], encoding="utf-8") as fh:
            content = fh.read()
        ns = calculate_noise_score(content)
        all_scores.append({**mf, "noise": ns})

    avg_noise = sum(x["noise"]["total"] for x in all_scores) / len(all_scores)
    good_count = sum(1 for x in all_scores if x["noise"]["total"] <= 20)
    warn_count = sum(1 for x in all_scores if 20 < x["noise"]["total"] <= 40)
    bad_count = sum(1 for x in all_scores if x["noise"]["total"] > 40)

    st.markdown(
        f"""
<div class="stat-row">
    <div class="stat-card"><div class="stat-label">문서 수</div><div class="stat-value blue">{len(all_scores)}</div></div>
    <div class="stat-card"><div class="stat-label">평균 노이즈</div><div class="stat-value" style="color:{noise_color(avg_noise)}">{avg_noise:.1f}</div></div>
    <div class="stat-card"><div class="stat-label">GOOD</div><div class="stat-value green">{good_count}</div></div>
    <div class="stat-card"><div class="stat-label">WARN</div><div class="stat-value orange">{warn_count}</div></div>
    <div class="stat-card"><div class="stat-label">BAD</div><div class="stat-value red">{bad_count}</div></div>
</div>
""",
        unsafe_allow_html=True,
    )

    filenames = [x["name"] for x in all_scores]
    selected_md = st.selectbox("문서 선택", filenames)
    if selected_md:
        sel_data = next(x for x in all_scores if x["name"] == selected_md)
        ns = sel_data["noise"]
        stem = os.path.splitext(selected_md)[0]

        with open(sel_data["path"], encoding="utf-8") as fh:
            content = fh.read()
        with open(sel_data["path"], encoding="utf-8") as f:
            fm = f.read(500)
        lm = re.search(r"languages:\s*(.+)", fm)
        langs = lm.group(1).strip() if lm else "-"

        sc = ns["total"]
        col = noise_color(sc)
        barpct = int(sc)
        st.markdown(
            f"""
<div style="margin-bottom:8px">
    <div style="display:flex;justify-content:space-between; font-family:JetBrains Mono,monospace;font-size:0.73rem;margin-bottom:2px">
        <span style="color:#c9d1d9">{selected_md}<span style="color:#8b949e;font-size:0.66rem;margin-left:8px">{langs}</span></span>
        <span style="color:{col};font-weight:600">{sc:.1f} &nbsp;{noise_label(sc)}</span>
    </div>
    <div class="noise-bar-wrap"><div class="noise-bar" style="width:{barpct}%;background:{col}"></div></div>
</div>
""",
            unsafe_allow_html=True,
        )

        chunks = load_chunks_info(output_dir, stem)
        if chunks:
            st.markdown(
                f"<div class='analysis-card'><h4>청크 미리보기 <span style='color:#8b949e;font-size:0.75rem;font-family:JetBrains Mono,monospace;font-weight:400'>총 {len(chunks)}개</span></h4></div>",
                unsafe_allow_html=True,
            )
            preview_n = st.slider("미리보기 개수", 1, min(len(chunks), 10), 3)
            for i, chunk in enumerate(chunks[:preview_n], 1):
                preview = chunk[:400] + " ..." if len(chunk) > 400 else chunk
                st.markdown(
                    f"<div class='chunk-box'><span style='color:#8b949e;font-size:0.67rem'>CHUNK {i:03d}</span><br>{preview}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("_chunks.txt 파일이 없거나 청크를 읽을 수 없습니다.")

        body = re.sub(r"---.*?---", "", content, flags=re.DOTALL)
        st.text_area("본문 미리보기", body[:3000] if len(body) > 3000 else body, height=300, label_visibility="collapsed")

    with st.expander("MD 품질 순위"):
        for x in sorted(all_scores, key=lambda v: v["noise"]["total"], reverse=True):
            sc = x["noise"]["total"]
            col = noise_color(sc)
            barpct = int(sc)
            st.markdown(
                f"""
<div style="margin-bottom:10px">
    <div style="display:flex;justify-content:space-between;font-family:JetBrains Mono,monospace;font-size:0.70rem;color:#8b949e;margin-bottom:2px">
        <span>{x['name']}</span><span style="color:{col}">{sc:.1f} / 100</span>
    </div>
    <div class="noise-bar-wrap"><div class="noise-bar" style="width:{barpct}%;background:{col}"></div></div>
</div>
""",
                unsafe_allow_html=True,
            )


# ── 메인 ──────────────────────────────────────────────────────────────────
def main() -> None:
    inject_styles()
    render_header()
    target_dir, output_dir, chunk_size, chunk_overlap, use_ocr = render_sidebar()
    tab1, tab2 = st.tabs(["처리", "분석"])
    with tab1:
        render_processing_tab(target_dir, output_dir, chunk_size, chunk_overlap, use_ocr)
    with tab2:
        render_analysis_tab(output_dir)


if __name__ == "__main__":
    main()
