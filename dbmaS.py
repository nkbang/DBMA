import os
import glob
import shutil
import streamlit as st
import warnings
import logging
from bs4 import BeautifulSoup
from docx import Document
from ebooklib import epub, ITEM_DOCUMENT
from striprtf.striprtf import rtf_to_text

# 스타일 및 헤더 설정
def inject_styles():
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

def render_header():
    st.markdown("""
<div class="dbma-header">
    <h1>DBMA</h1>
    <p>David Bang Ministry Archive · RAG 데이터 정제 시스템 v3.2</p>
</div>
""", unsafe_allow_html=True)

# 파일 크기 포맷팅
def fmt_size(b: int):
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1026

# 안전한 파일 이름 생성 함수
def make_safe_stem(filename: str) -> str:
    name, ext = os.path.splitext(filename)
    return f"{name}__{ext.lower().replace('.', '')}"

# 파일 스캔
def scan_directory(directory):
    if not os.path.isdir(directory):
        return []
    
    files = []
    for ext in SUPPORTED_EXTENSIONS:
        for fp in glob.glob(os.path.join(directory, f"*{ext}")):
            if os.path.isfile(fp):
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

# 파일 추출
def extract_text_from_file(path, converter=None):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        full_text = convert_pdf_to_txt(path, converter)
    elif ext == ".txt":
        with open(path, "r", encoding="utf-8") as file:
            full_text = file.read()
    elif ext == ".md":
        with open(path, "r", encoding="utf-8") as file:
            full_text = file.read()
    elif ext in [".html", ".htm"]:
        raw = read_file_content(path)
        soup = BeautifulSoup(raw, 'html.parser')
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        full_text = soup.get_text("\n", strip=True)
    elif ext == ".docx":
        doc = Document(path)
        parts = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                parts.append(text)
        full_text = "\n\n".join(parts).strip()
    elif ext == ".epub":
        book = epub.read_epub(path)
        texts = []
        for item in book.get_items():
            if item.get_type() == ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                for tag in soup(["script", "style", "noscript"]):
                    tag.decompose()
                text = soup.get_text("\n", strip=True)
                if text:
                    texts.append(text)
        full_text = "\n\n".join(texts).strip()
    elif ext == ".rtf":
        raw = read_file_content(path)
        full_text = rtf_to_text(raw.strip())
    
    return full_text

# 파일 처리
def process_one_file(file_info, converter, splitter, output_dir: str):
    logs = []
    name = file_info["name"]
    safe_stem = make_safe_stem(name)
    src_path = file_info["path"]
    ext = os.path.splitext(name)[1].lower()
    
    full_text = extract_text_from_file(src_path, converter=converter)

    if not full_text.strip():
        logs.append({"cls": "log-err", "msg": f"{name} 추출 결과가 비어 있습니다."})
        return logs, False
    
    noise = calculate_noise_score(full_text)
    lang_list = detect_langs(full_text)
    
    md_path = save_md(safe_stem, name, full_text, noise, output_dir)
    
    chunks = splitter.split_documents(full_text)  # 문서를 의미 있는 문단으로 분할
    txt_path = save_chunks(safe_stem, name, [chunk.page_content for chunk in chunks], output_dir)

    shutil.move(src_path, os.path.join(output_dir, name))
    
    logs.append({"cls": "log-ok", "msg": f"MD 저장: {os.path.basename(md_path)}"})
    logs.append({"cls": "log-ok", "msg": f"CHUNKS 저장: {_chunks_path} / {len(chunks)} chunks"})
    logs.append({"cls": "log-ok", "msg": f"원본 이동: {name}"})
    
    return logs, True

# 파일 선택 및 처리
def render_file_selection():
    st.title("파일 선택")
    uploaded_files = st.file_uploader(
        label="파일을 드래그 앤드 드롭 하거나 선택하세요", 
        accept_multiple_files=True,
        type=["pdf", "txt", "md", "html", "htm", "docx", "epub", "rtf"]
    )
    
    if uploaded_files:
        target_dir = os.path.join(os.getcwd(), 'temp')  # 임시 디렉토리 생성
        os.makedirs(target_dir, exist_ok=True)
        
        for file in uploaded_files:
            file_path = os.path.join(target_dir, file.name)
            with open(file_path, "wb") as f:
                f.write(file.read())
            
        st.success(f"파일이 성공적으로 업로드되었습니다. 처리를 시작합니다.")
        
        output_dir = os.path.join(os.getcwd(), 'output')
        os.makedirs(output_dir, exist_ok=True)
    
        use_ocr = st.checkbox("OCR for PDF", value=False)
        chunk_size = 1000
        chunk_overlap = 200

        converter = build_converter(use_ocr) if use_ocr else None
        
        # MarkdownTextSplitter 대신 다른 텍스트 분할기를 사용합니다.
        from langchain.text_splitter import CharacterTextSplitter
        splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        file_list = scan_directory(target_dir)
        
        for file_info in file_list:
            process_one_file(file_info, converter, splitter, output_dir)


if __name__ == "__main__":
    st.set_page_config(page_title="DBMA 파일 처리", layout="wide")
    
    # 스타일 적용
    inject_styles()
    render_header()

    # 파일 선택 및 처리 페이지 렌더링
    render_file_selection()
