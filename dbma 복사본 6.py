import streamlit as st
import os
import glob
import shutil
import warnings
import logging
import datetime
import re
import unicodedata

# ── 버전 정보 ──────────────────────────────────────────────────────────────
APP_VERSION = "0.2.0"
APP_NAME = "DBMA 파싱 파이프라인"

# Version 0.2.0
# - 품질 분석 탭에서 단일/다중 파일 재파싱 지원
# - .md → source.pdf 역추적 함수 추가
# - 재파싱 전용 OCR / chunk 옵션 추가
# - 기존 산출물 덮어쓰기 / 백업 후 재생성 모드 추가
# - 파싱 실행 로직 공용 함수화
# - 기존 v0.1.1 안정화 항목 유지

# ── 경고 억제 ──────────────────────────────────────────────────────────────
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", message=".*__path__.*")
logging.getLogger("transformers").setLevel(logging.ERROR)

# ── 페이지 설정 ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"{APP_NAME} v{APP_VERSION}",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Noto Serif KR', serif; }

.dbma-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 12px; padding: 28px 36px; margin-bottom: 24px;
    border-left: 5px solid #e94560;
}
.dbma-header h1 { color:#fff; font-size:1.8rem; font-weight:700; margin:0 0 4px 0; letter-spacing:-0.02em; }
.dbma-header p  { color:#a8b2d8; font-size:0.85rem; margin:0; font-family:'JetBrains Mono',monospace; }

.file-table-header {
    display:grid; grid-template-columns:40px 1fr 90px 150px 60px;
    background:#161b22; padding:9px 12px; font-size:0.70rem; color:#8b949e;
    font-family:'JetBrains Mono',monospace; text-transform:uppercase;
    letter-spacing:0.08em; border:1px solid #21262d; border-radius:8px 8px 0 0;
}
.file-row {
    display:grid; grid-template-columns:40px 1fr 90px 150px 60px;
    padding:9px 12px; border:1px solid #21262d; border-top:none;
    align-items:center; font-size:0.80rem; background:#0d1117;
}
.file-row:last-child { border-radius:0 0 8px 8px; }
.file-row:hover { background:#161b22; }
.fname  { color:#58a6ff; font-family:'JetBrains Mono',monospace; font-size:0.76rem; word-break:break-all; }
.fsize  { color:#3fb950; font-family:'JetBrains Mono',monospace; font-size:0.74rem; }
.fdate  { color:#8b949e; font-family:'JetBrains Mono',monospace; font-size:0.72rem; }
.fbadge { display:inline-block; background:#1f3a5f; color:#58a6ff; border-radius:4px;
          padding:1px 7px; font-size:0.66rem; font-family:'JetBrains Mono',monospace; font-weight:500; }

.stat-row  { display:flex; gap:12px; margin-bottom:16px; }
.stat-card { flex:1; background:#161b22; border:1px solid #21262d; border-radius:8px; padding:13px 17px; }
.stat-label{ font-size:0.67rem; color:#8b949e; text-transform:uppercase; letter-spacing:0.1em;
             margin-bottom:3px; font-family:'JetBrains Mono',monospace; }
.stat-value{ font-size:1.35rem; font-weight:700; color:#e6edf3; font-family:'JetBrains Mono',monospace; }
.blue  { color:#58a6ff; } .green{ color:#3fb950; } .orange{ color:#d29922; } .red{ color:#f85149; }

.log-box {
    background:#0d1117; border:1px solid #21262d; border-radius:8px;
    padding:13px 17px; font-family:'JetBrains Mono',monospace;
    font-size:0.75rem; color:#c9d1d9; max-height:320px; overflow-y:auto; line-height:1.9;
}
.log-ok  { color:#3fb950; } .log-warn{ color:#d29922; }
.log-err { color:#f85149; } .log-info{ color:#58a6ff; }

.noise-bar-wrap { background:#21262d; border-radius:6px; height:14px; overflow:hidden; margin:6px 0 2px; }
.noise-bar { height:14px; border-radius:6px; transition:width 0.4s; }

.analysis-card {
    background:#161b22; border:1px solid #21262d; border-radius:10px;
    padding:16px 20px; margin-bottom:12px;
}
.analysis-card h4 { color:#e6edf3; font-size:0.9rem; margin:0 0 10px; font-weight:600; }

.chunk-box {
    background:#0d1117; border-left:3px solid #58a6ff; border-radius:0 6px 6px 0;
    padding:10px 14px; margin:8px 0; font-family:'JetBrains Mono',monospace;
    font-size:0.73rem; color:#c9d1d9; line-height:1.7;
}

.reparse-row {
    padding:8px 10px; border:1px solid #21262d; border-radius:8px; margin-bottom:6px; background:#0d1117;
    font-family:'JetBrains Mono',monospace; font-size:0.73rem; color:#c9d1d9;
}

div[data-testid="stButton"] > button {
    background:linear-gradient(135deg,#e94560,#c23152)!important;
    color:white!important; border:none!important; border-radius:8px!important;
    font-family:'Noto Serif KR',serif!important; font-weight:600!important;
    padding:10px 28px!important; font-size:0.95rem!important;
}
section[data-testid="stSidebar"] { background:#0d1117; border-right:1px solid #21262d; }
section[data-testid="stSidebar"] label { color:#c9d1d9!important; }
section[data-testid="stSidebar"] .stTextInput input,
section[data-testid="stSidebar"] .stNumberInput input {
    background:#161b22!important; border-color:#30363d!important;
    color:#e6edf3!important; font-family:'JetBrains Mono',monospace!important; font-size:0.82rem!important;
}
div[data-testid="stCheckbox"] { margin-bottom:0 !important; padding:2px 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── 헤더 ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="dbma-header">
  <h1>📚 {APP_NAME} v{APP_VERSION}</h1>
  <p>David Bang Ministry Archive · RAG 데이터 정제 시스템</p>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 공통 유틸리티
# ════════════════════════════════════════════════════════════════

def fmt_size(b: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"

@st.cache_data(ttl=5, show_spinner=False)
def scan_directory(directory: str) -> list[dict]:
    if not os.path.isdir(directory):
        return []
    files = []
    for fp in sorted(glob.glob(os.path.join(directory, "*.pdf"))):
        s = os.stat(fp)
        files.append({
            "path": fp,
            "name": os.path.basename(fp),
            "size_b": s.st_size,
            "size_str": fmt_size(s.st_size),
            "mtime": datetime.datetime.fromtimestamp(s.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return files

def calculate_noise_score(text: str) -> dict:
    if not text or len(text) < 50:
        return {
            "total": 100.0,
            "symbol_ratio": 40.0,
            "short_line": 30.0,
            "blank_ratio": 15.0,
            "repeat_ratio": 15.0,
            "char_count": len(text),
            "line_count": 1,
            "word_count": 0,
            "lang_detected": []
        }

    text = unicodedata.normalize("NFC", text)
    lines = text.split("\n")
    char_count = len(text)
    word_count = len(text.split())
    line_count = len(lines)

    has_korean = bool(re.search(r"[가-힣]", text))
    has_hebrew = bool(re.search(r"[\u05b0-\u05ea\ufb1d-\ufb4e]", text))
    has_greek = bool(re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", text))
    has_english = bool(re.search(r"[a-zA-Z]", text))
    lang_detected = (
        (["한국어"] if has_korean else []) +
        (["히브리어"] if has_hebrew else []) +
        (["헬라어"] if has_greek else []) +
        (["영어"] if has_english else [])
    )

    allowed = re.compile(
        r"["
        r"가-힣"
        r"a-zA-Z"
        r"\u05b0-\u05ea"
        r"\ufb1d-\ufb4e"
        r"\u0370-\u03ff"
        r"\u1f00-\u1fff"
        r"0-9\s"
        r".,!?;:\'\"\-–—·•※"
        r"\[\]\(\)\{\}"
        r"]"
    )
    non_allowed = sum(1 for ch in text if not allowed.match(ch))
    sym_score = min((non_allowed / char_count) * 40 * 5, 40.0)

    short_lines = sum(1 for ln in lines if 0 < len(ln.strip()) < 20)
    sl_score = min((short_lines / (line_count + 1)) * 30 * 2, 30.0)

    blank_lines = sum(1 for ln in lines if not ln.strip())
    bl_score = min((blank_lines / (line_count + 1)) * 15 * 3, 15.0)

    repeats = len(re.findall(r"(.{3,})\1{4,}", text))
    rp_score = min(repeats * 3.0, 15.0)

    total = sym_score + sl_score + bl_score + rp_score
    return {
        "total": round(total, 2),
        "symbol_ratio": round(sym_score, 2),
        "short_line": round(sl_score, 2),
        "blank_ratio": round(bl_score, 2),
        "repeat_ratio": round(rp_score, 2),
        "char_count": char_count,
        "line_count": line_count,
        "word_count": word_count,
        "lang_detected": lang_detected,
    }

def noise_color(score: float) -> str:
    if score < 20:
        return "#3fb950"
    if score < 40:
        return "#d29922"
    return "#f85149"

def noise_label(score: float) -> str:
    if score < 20:
        return "우수 ✓"
    if score < 40:
        return "주의 ⚠"
    return "재정제 필요 ✗"

@st.cache_data(ttl=5, show_spinner=False)
def scan_md_files(directory: str) -> list[dict]:
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

def load_chunks_info(directory: str, stem: str) -> list[str] | None:
    txt_path = os.path.join(directory, f"{stem}_chunks.txt")
    if not os.path.exists(txt_path):
        return None
    with open(txt_path, encoding="utf-8") as fh:
        raw = fh.read()
    blocks = re.split(r"═{8} CHUNK \d+ / \d+ ═{8}\n", raw)
    chunks = [b.strip().rstrip("─").strip() for b in blocks if b.strip() and not b.startswith("#")]
    return chunks if chunks else None

def ensure_log_dir(output_dir: str) -> str:
    log_dir = os.path.join(output_dir, "_logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def append_result_csv(output_dir: str, row: dict):
    log_dir = ensure_log_dir(output_dir)
    csv_path = os.path.join(log_dir, "parse_results.csv")
    write_header = not os.path.exists(csv_path)
    columns = [
        "timestamp", "version", "source_file", "ocr_used",
        "status", "noise_score", "chunk_count", "error"
    ]
    with open(csv_path, "a", encoding="utf-8-sig") as fh:
        if write_header:
            fh.write(",".join(columns) + "\n")
        vals = [str(row.get(col, "")).replace(",", " ") for col in columns]
        fh.write(",".join(vals) + "\n")

def write_batch_log(output_dir: str, logs: list[dict]) -> str:
    log_dir = ensure_log_dir(output_dir)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"batch_{ts}.log")
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write(f"{APP_NAME} v{APP_VERSION}\n")
        fh.write(f"created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for item in logs:
            fh.write(item["msg"] + "\n")
    return log_path

def append_retry_candidate(output_dir: str, file_name: str, reason: str):
    log_dir = ensure_log_dir(output_dir)
    retry_path = os.path.join(log_dir, "_retry_candidates.txt")
    with open(retry_path, "a", encoding="utf-8") as fh:
        fh.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {file_name} | {reason}\n")

def detect_langs(text: str) -> list[str]:
    found = []
    if any("\u05b0" <= c <= "\u05ea" or "\ufb1d" <= c <= "\ufb4e" for c in text):
        found.append("he")
    if any("\u0370" <= c <= "\u03ff" or "\u1f00" <= c <= "\u1fff" for c in text):
        found.append("el")
    if any("\uac00" <= c <= "\ud7a3" for c in text):
        found.append("ko")
    if any(c.isascii() and c.isalpha() for c in text[:500]):
        found.append("en")
    return found

def extract_source_pdf_from_md(md_path: str) -> str | None:
    if not os.path.exists(md_path):
        return None
    with open(md_path, encoding="utf-8") as fh:
        head = fh.read(800)
    m = re.search(r"^source:\s*(.+\.pdf)\s*$", head, flags=re.MULTILINE)
    return m.group(1).strip() if m else None

def resolve_pdf_path(source_pdf: str, target_dir: str, output_dir: str) -> str | None:
    candidates = [
        os.path.join(output_dir, source_pdf),
        os.path.join(target_dir, source_pdf),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def backup_existing_outputs(output_dir: str, stem: str):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(output_dir, f"{stem}.md")
    txt_path = os.path.join(output_dir, f"{stem}_chunks.txt")
    if os.path.exists(md_path):
        shutil.copy2(md_path, os.path.join(output_dir, f"{stem}.{ts}.bak.md"))
    if os.path.exists(txt_path):
        shutil.copy2(txt_path, os.path.join(output_dir, f"{stem}.{ts}.bak_chunks.txt"))

def build_converter(use_ocr: bool):
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions

    pipeline_options = PdfPipelineOptions()
    if use_ocr:
        pipeline_options.do_ocr = True
        pipeline_options.ocr_options = EasyOcrOptions(
            lang=["ko", "en", "he", "el"],
            use_gpu=False,
        )
    else:
        pipeline_options.do_ocr = False

    return DocumentConverter(
        format_options={"pdf": PdfFormatOption(pipeline_options=pipeline_options)}
    )

def build_splitter(chunk_size: int, chunk_overlap: int):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    multilang_separators = [
        "\n\n",
        "\n",
        "\u05c3",
        "\u00b7",
        ". ",
        "\u3002",
        "? ", "! ",
        "; ",
        ", ",
        " ",
        "",
    ]
    return RecursiveCharacterTextSplitter(
        chunk_size=int(chunk_size),
        chunk_overlap=int(chunk_overlap),
        separators=multilang_separators,
        keep_separator=True,
    )

def save_md(output_dir: str, stem: str, text: str, noise: dict) -> str:
    md_path = os.path.join(output_dir, f"{stem}.md")
    lang_list = detect_langs(text)
    has_rtl = "he" in lang_list

    header = (
        f"---\n"
        f"source: {stem}.pdf\n"
        f"created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"pipeline: DBMA v{APP_VERSION}\n"
        f"languages: {', '.join(lang_list) if lang_list else 'unknown'}\n"
        f"rtl_content: {'true' if has_rtl else 'false'}\n"
        f"noise_score: {noise['total']}\n"
        f"noise_status: {noise_label(noise['total'])}\n"
        f"char_count: {noise['char_count']}\n"
        f"word_count: {noise['word_count']}\n"
        f"---\n\n"
    )

    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(header + text)
    return md_path

def save_chunks(output_dir: str, stem: str, chunks: list[str], chunk_size: int, chunk_overlap: int) -> str:
    txt_path = os.path.join(output_dir, f"{stem}_chunks.txt")
    total_c = len(chunks)

    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write(
            f"# DBMA Chunk File\n"
            f"# source : {stem}.pdf\n"
            f"# created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"# chunks : {total_c}\n"
            f"# chunk_size / overlap : {int(chunk_size)} / {int(chunk_overlap)}\n\n"
        )
        for i, chunk in enumerate(chunks, 1):
            fh.write(f"{'═'*8} CHUNK {i:03d} / {total_c:03d} {'═'*8}\n")
            fh.write(chunk.strip())
            fh.write(f"\n{'─'*40}\n\n")
    return txt_path

def run_parsing_batch(
    file_batch: list[dict],
    output_dir: str,
    use_ocr: bool,
    chunk_size: int,
    chunk_overlap: int,
    log_ph,
    prog_ph,
    backup_mode: bool = False,
):
    os.makedirs(output_dir, exist_ok=True)
    ensure_log_dir(output_dir)

    converter = build_converter(use_ocr)
    splitter = build_splitter(chunk_size, chunk_overlap)

    logs, ok_count, fail_count = [], 0, 0
    total = len(file_batch)

    def render_logs(entries):
        html = '<div class="log-box">'
        for e in entries:
            html += f'<div class="{e["cls"]}">{e["msg"]}</div>'
        html += "</div>"
        log_ph.markdown(html, unsafe_allow_html=True)

    logs.append({"cls": "log-info", "msg": f"[시작] {total}개 파일 처리 예정"})
    logs.append({"cls": "log-info", "msg": f"[버전] v{APP_VERSION}"})
    logs.append({"cls": "log-info", "msg": f"[출력] {output_dir}"})
    if use_ocr:
        logs.append({"cls": "log-info", "msg": "[OCR] EasyOCR 활성화 — ko · en · he · el"})
    render_logs(logs)

    for idx, f in enumerate(file_batch):
        prog_ph.progress((idx / total) if total else 0.0, text=f"처리 중 ({idx+1}/{total}): {f['name']}")
        stem = os.path.splitext(f["name"])[0]
        src_path = f["path"]
        dest_path = os.path.join(output_dir, f["name"])

        logs.append({"cls": "log-info", "msg": f"[{idx+1}/{total}] {f['name']}"})
        render_logs(logs)

        try:
            if backup_mode:
                backup_existing_outputs(output_dir, stem)

            result = converter.convert(src_path)
            document = getattr(result, "document", None)

            if document is None:
                logs.append({"cls": "log-err", "msg": "  ✗ 변환 결과 없음 — 원본 유지"})
                append_retry_candidate(output_dir, f["name"], "변환 결과 없음")
                append_result_csv(output_dir, {
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "version": APP_VERSION,
                    "source_file": f["name"],
                    "ocr_used": use_ocr,
                    "status": "failed",
                    "noise_score": "",
                    "chunk_count": "",
                    "error": "변환 결과 없음",
                })
                fail_count += 1
                render_logs(logs)
                continue

            full_text = document.export_to_markdown()
            if not full_text or not full_text.strip():
                logs.append({"cls": "log-warn", "msg": "  ⚠ 텍스트 비어 있음 — OCR 활성화 필요. 원본 유지"})
                append_retry_candidate(output_dir, f["name"], "텍스트 비어 있음 / OCR 재시도 필요")
                append_result_csv(output_dir, {
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "version": APP_VERSION,
                    "source_file": f["name"],
                    "ocr_used": use_ocr,
                    "status": "failed",
                    "noise_score": "",
                    "chunk_count": "",
                    "error": "텍스트 비어 있음",
                })
                fail_count += 1
                render_logs(logs)
                continue

            noise = calculate_noise_score(full_text)
            lang_list = detect_langs(full_text)
            lang_found = " · ".join(
                {"ko": "한국어", "en": "영어", "he": "히브리어", "el": "헬라어"}.get(l, l)
                for l in lang_list
            ) or "감지 없음"

            logs.append({"cls": "log-info", "msg": f"  ◎ 감지 언어: {lang_found}"})
            logs.append({"cls": "log-info", "msg": f"  ◎ 노이즈 점수: {noise['total']:.1f}  [{noise_label(noise['total'])}]"})

            md_path = save_md(output_dir, stem, full_text, noise)
            logs.append({"cls": "log-ok", "msg": f"  ✓ MD  → {os.path.basename(md_path)}"})

            chunks = splitter.split_text(full_text)
            if not chunks:
                logs.append({"cls": "log-warn", "msg": "  ⚠ 청크 결과가 비어 있음"})
            txt_path = save_chunks(output_dir, stem, chunks, chunk_size, chunk_overlap)
            logs.append({"cls": "log-ok", "msg": f"  ✓ TXT → {os.path.basename(txt_path)}  ({len(chunks)} 청크)"})

            if os.path.abspath(src_path) != os.path.abspath(dest_path):
                if os.path.exists(dest_path):
                    logs.append({"cls": "log-warn", "msg": "  ⚠ 출력 폴더에 같은 PDF 이름이 이미 있어 덮어쓰지 않음"})
                else:
                    shutil.move(src_path, dest_path)
                    logs.append({"cls": "log-ok", "msg": "  ✓ PDF → 제련완성본 이동 완료"})
            else:
                logs.append({"cls": "log-info", "msg": "  ◎ 원본과 대상 경로가 같아 이동 생략"})

            append_result_csv(output_dir, {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": APP_VERSION,
                "source_file": f["name"],
                "ocr_used": use_ocr,
                "status": "success",
                "noise_score": noise["total"],
                "chunk_count": len(chunks),
                "error": "",
            })

            ok_count += 1

            if noise["total"] >= 40:
                logs.append({"cls": "log-warn", "msg": "  ⚠ 재정제 권장 — 품질 분석 탭에서 확인하세요"})
                append_retry_candidate(output_dir, f["name"], f"노이즈 점수 높음: {noise['total']}")

        except Exception as e:
            logs.append({"cls": "log-err", "msg": f"  ✗ 오류: {type(e).__name__}: {e} — 원본 유지"})
            append_result_csv(output_dir, {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": APP_VERSION,
                "source_file": f["name"],
                "ocr_used": use_ocr,
                "status": "failed",
                "noise_score": "",
                "chunk_count": "",
                "error": f"{type(e).__name__}: {e}",
            })
            append_retry_candidate(output_dir, f["name"], f"예외 발생: {type(e).__name__}")
            fail_count += 1

        render_logs(logs)

    prog_ph.progress(1.0, text="완료")
    logs.append({"cls": "log-info", "msg": "─" * 40})
    logs.append({
        "cls": "log-ok" if fail_count == 0 else "log-warn",
        "msg": f"[완료] 성공 {ok_count}개 · 실패 {fail_count}개",
    })
    logs.append({"cls": "log-info", "msg": f"[산출물] .md + _chunks.txt → {output_dir}"})

    batch_log_path = write_batch_log(output_dir, logs)
    logs.append({"cls": "log-info", "msg": f"[배치로그] {os.path.basename(batch_log_path)}"})
    render_logs(logs)

    scan_directory.clear()
    scan_md_files.clear()

    return {
        "ok_count": ok_count,
        "fail_count": fail_count,
        "logs": logs,
        "batch_log_path": batch_log_path,
    }

# ════════════════════════════════════════════════════════════════
# session_state 콜백
# ════════════════════════════════════════════════════════════════

def _sel_key(name: str) -> str:
    return f"sel_{name}"

def _current_sel_keys(file_list: list[dict]) -> list[str]:
    return [_sel_key(f["name"]) for f in file_list]

def _apply_select_all(file_list: list[dict]):
    new_val = st.session_state.get("_select_all", False)
    for key in _current_sel_keys(file_list):
        st.session_state[key] = new_val

def _on_item_change(file_list: list[dict]):
    sel_keys = _current_sel_keys(file_list)
    if sel_keys:
        st.session_state["_select_all"] = all(st.session_state.get(k, False) for k in sel_keys)

# ════════════════════════════════════════════════════════════════
# 사이드바
# ════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### ⚙️ 파이프라인 설정")
    st.markdown("---")
    target_dir = st.text_input("RAW 폴더 경로", value="/Users/David/DBMA/RAW")
    output_dir = st.text_input("완성본 폴더 경로", value="/Users/David/DBMA/제련완성본")
    st.markdown("---")
    st.markdown("### 🔪 청크 설정")
    chunk_size = st.number_input("Chunk Size", value=1000, min_value=100, step=100)
    chunk_overlap = st.number_input("Chunk Overlap", value=200, min_value=0, step=50)
    st.markdown("---")
    st.markdown("### 🔍 OCR 설정")
    use_ocr = st.checkbox(
        "OCR 활성화 (스캔본 PDF 전용)",
        value=False,
        help="디지털 PDF는 해제. 스캔 이미지 PDF만 활성화."
    )
    if use_ocr:
        st.info("EasyOCR — 한국어 · 영어 · 히브리어 · 헬라어")
    st.markdown("---")
    st.markdown(
        "<div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;"
        "color:#3fb950;padding:8px 10px;background:#0d2b1a;border-radius:6px;"
        "border:1px solid #1a4a2a;'>"
        "✓ 파싱 완료 후 원본 PDF는<br>자동으로 제련완성본 폴더로<br>이동됩니다.</div>",
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════════════════
# 탭 구성
# ════════════════════════════════════════════════════════════════

tab1, tab2 = st.tabs(["🚀 파싱 실행", "📊 품질 분석"])

# ════════════════════════════════════════════════════════════════
# TAB 1 — 파싱 실행
# ════════════════════════════════════════════════════════════════

with tab1:
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.markdown("#### 📂 파일 탐색기")

        ref_col, path_col = st.columns([1, 4])
        with ref_col:
            if st.button("🔄 새로고침"):
                scan_directory.clear()
                scan_md_files.clear()
                st.rerun()
        with path_col:
            st.markdown(
                f"<div style='font-family:JetBrains Mono,monospace;font-size:0.76rem;"
                f"color:#8b949e;padding-top:10px;overflow:hidden;text-overflow:ellipsis;"
                f"white-space:nowrap;'>{target_dir}</div>",
                unsafe_allow_html=True,
            )

        file_list = scan_directory(target_dir)

        if not file_list:
            st.warning(f"'{target_dir}' 폴더에 PDF 파일이 없거나 경로가 잘못되었습니다.")
            selected_files = []
        else:
            current_names = {f["name"] for f in file_list}
            for key in list(st.session_state.keys()):
                if key.startswith("sel_") and key[4:] not in current_names:
                    del st.session_state[key]

            for f in file_list:
                key = _sel_key(f["name"])
                if key not in st.session_state:
                    st.session_state[key] = True

            sel_keys = _current_sel_keys(file_list)
            st.session_state["_select_all"] = all(st.session_state.get(k, False) for k in sel_keys) if sel_keys else False

            total_size = sum(f["size_b"] for f in file_list)
            st.markdown(f"""
            <div class="stat-row">
              <div class="stat-card">
                <div class="stat-label">총 파일 수</div>
                <div class="stat-value blue">{len(file_list)}</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">총 용량</div>
                <div class="stat-value orange">{fmt_size(total_size)}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            select_all_val = st.checkbox("전체 선택 / 해제", value=st.session_state["_select_all"])
            if select_all_val != st.session_state.get("_select_all", False):
                st.session_state["_select_all"] = select_all_val
                _apply_select_all(file_list)
                st.rerun()

            st.markdown("""
            <div class="file-table-header">
              <span>✓</span><span>파일명</span>
              <span>크기</span><span>수정일</span><span>형식</span>
            </div>
            """, unsafe_allow_html=True)

            selected_files = []
            for f in file_list:
                c1, c2 = st.columns([1, 12])
                key = _sel_key(f["name"])
                with c1:
                    prev = st.session_state.get(key, False)
                    new_val = st.checkbox(label="", value=prev, key=f"ui_{key}", label_visibility="collapsed")
                    if new_val != prev:
                        st.session_state[key] = new_val
                        _on_item_change(file_list)
                        st.rerun()
                with c2:
                    st.markdown(f"""
                    <div class="file-row">
                      <span></span>
                      <span class="fname">📄 {f['name']}</span>
                      <span class="fsize">{f['size_str']}</span>
                      <span class="fdate">{f['mtime']}</span>
                      <span class="fbadge">PDF</span>
                    </div>
                    """, unsafe_allow_html=True)
                if st.session_state.get(key, False):
                    selected_files.append(f)

            if selected_files:
                sel_size = sum(f["size_b"] for f in selected_files)
                st.markdown(
                    f"<div style='font-size:0.77rem;color:#3fb950;padding:7px 4px;"
                    f"font-family:JetBrains Mono,monospace;'>"
                    f"✅ {len(selected_files)}개 선택 · {fmt_size(sel_size)}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='font-size:0.77rem;color:#d29922;padding:7px 4px;"
                    "font-family:JetBrains Mono,monospace;'>⚠️ 선택된 파일 없음</div>",
                    unsafe_allow_html=True,
                )

    with col_right:
        st.markdown("#### 🚀 파싱 실행")

        ocr_label = "EasyOCR (ko·en·he·el)" if use_ocr else "비활성화"
        n_sel = len(selected_files) if file_list else 0

        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #21262d;border-radius:8px;
             padding:14px 18px;margin-bottom:16px;font-family:'JetBrains Mono',monospace;
             font-size:0.75rem;line-height:2.1;">
          <span style="color:#8b949e;">VERSION     </span><span style="color:#58a6ff;">{APP_VERSION}</span><br>
          <span style="color:#8b949e;">CHUNK SIZE  </span><span style="color:#e6edf3;">{int(chunk_size)}</span><br>
          <span style="color:#8b949e;">OVERLAP     </span><span style="color:#e6edf3;">{int(chunk_overlap)}</span><br>
          <span style="color:#8b949e;">OCR         </span>
          <span style="color:#{'3fb950' if use_ocr else '8b949e'};">{ocr_label}</span><br>
          <span style="color:#8b949e;">원본 처리   </span>
          <span style="color:#3fb950;">파싱 완료 후 이동</span><br>
          <span style="color:#8b949e;">선택 파일   </span>
          <span style="color:#58a6ff;">{n_sel}개</span>
        </div>
        """, unsafe_allow_html=True)

        start_btn = st.button(
            f"▶  {n_sel}개 파일 파싱 시작",
            disabled=(not file_list or n_sel == 0),
        )

        st.markdown("#### 📋 실행 로그")
        log_ph = st.empty()
        prog_ph = st.empty()

        if start_btn and selected_files:
            result = run_parsing_batch(
                file_batch=selected_files,
                output_dir=output_dir,
                use_ocr=use_ocr,
                chunk_size=int(chunk_size),
                chunk_overlap=int(chunk_overlap),
                log_ph=log_ph,
                prog_ph=prog_ph,
                backup_mode=False,
            )

            if result["fail_count"] == 0:
                st.success(f"✅ 전체 {result['ok_count']}개 완료 — 품질 분석 탭에서 결과를 확인하세요.")
            else:
                st.warning(f"⚠️ 성공 {result['ok_count']}개 / 실패 {result['fail_count']}개")

# ════════════════════════════════════════════════════════════════
# TAB 2 — 품질 분석
# ════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("#### 📊 데이터 정제 품질 분석기")

    md_files = scan_md_files(output_dir)

    if not md_files:
        st.warning(f"'{output_dir}' 폴더에 .md 파일이 없습니다. 먼저 파싱을 실행하세요.")
    else:
        st.markdown("##### 전체 파일 노이즈 요약")

        all_scores = []
        for mf in md_files:
            with open(mf["path"], encoding="utf-8") as fh:
                content = fh.read()
            ns = calculate_noise_score(content)
            all_scores.append({**mf, "noise": ns})

        avg_noise = sum(x["noise"]["total"] for x in all_scores) / len(all_scores)
        good_count = sum(1 for x in all_scores if x["noise"]["total"] < 20)
        warn_count = sum(1 for x in all_scores if 20 <= x["noise"]["total"] < 40)
        bad_count = sum(1 for x in all_scores if x["noise"]["total"] >= 40)

        st.markdown(f"""
        <div class="stat-row">
          <div class="stat-card">
            <div class="stat-label">파일 수</div>
            <div class="stat-value blue">{len(all_scores)}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">평균 노이즈</div>
            <div class="stat-value" style="color:{noise_color(avg_noise)};">{avg_noise:.1f}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">우수</div>
            <div class="stat-value green">{good_count}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">주의</div>
            <div class="stat-value orange">{warn_count}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">재정제 필요</div>
            <div class="stat-value red">{bad_count}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### 재파싱 대상 선택")

        auto_select_bad = st.checkbox("재정제 필요(노이즈 40 이상) 파일만 기본 선택", value=False, key="auto_select_bad")

        analysis_sel = []
        for x in sorted(all_scores, key=lambda v: v["noise"]["total"], reverse=True):
            md_name = x["name"]
            score = x["noise"]["total"]
            key = f"reparse_{md_name}"

            if key not in st.session_state:
                st.session_state[key] = score >= 40 if auto_select_bad else False

            row_col1, row_col2 = st.columns([1, 10])
            with row_col1:
                checked = st.checkbox("", key=key, label_visibility="collapsed")
            with row_col2:
                st.markdown(
                    f"<div class='reparse-row'>📄 {md_name} &nbsp;|&nbsp; "
                    f"노이즈 {score:.1f} &nbsp;|&nbsp; {noise_label(score)}</div>",
                    unsafe_allow_html=True,
                )

            if checked:
                analysis_sel.append(x)

        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 3])
        with btn_col1:
            if st.button("재정제 필요만 선택"):
                for x in all_scores:
                    st.session_state[f"reparse_{x['name']}"] = x["noise"]["total"] >= 40
                st.rerun()
        with btn_col2:
            if st.button("선택 해제"):
                for x in all_scores:
                    st.session_state[f"reparse_{x['name']}"] = False
                st.rerun()

        st.markdown("##### 재파싱 옵션")
        re_ocr = st.checkbox("재파싱 시 OCR 사용", value=False, key="reparse_use_ocr")
        re_chunk_size = st.number_input("재파싱 Chunk Size", value=int(chunk_size), min_value=100, step=100, key="reparse_chunk_size")
        re_chunk_overlap = st.number_input("재파싱 Chunk Overlap", value=int(chunk_overlap), min_value=0, step=50, key="reparse_chunk_overlap")
        overwrite_mode = st.radio("기존 결과 처리", ["덮어쓰기", "백업 후 재생성"], horizontal=True)

        reparse_log_ph = st.empty()
        reparse_prog_ph = st.empty()

        if st.button(f"선택 파일 재파싱 ({len(analysis_sel)}개)", disabled=(len(analysis_sel) == 0)):
            reparse_targets = []
            pre_logs = []

            for item in analysis_sel:
                source_pdf = extract_source_pdf_from_md(item["path"])
                if not source_pdf:
                    pre_logs.append({"cls": "log-err", "msg": f"[스킵] {item['name']} → source 정보 없음"})
                    continue

                pdf_path = resolve_pdf_path(source_pdf, target_dir, output_dir)
                if not pdf_path:
                    pre_logs.append({"cls": "log-err", "msg": f"[스킵] {item['name']} → 원본 PDF 없음 ({source_pdf})"})
                    continue

                reparse_targets.append({
                    "name": source_pdf,
                    "path": pdf_path,
                })

            if pre_logs:
                html = '<div class="log-box">' + "".join(f'<div class="{e["cls"]}">{e["msg"]}</div>' for e in pre_logs) + "</div>"
                reparse_log_ph.markdown(html, unsafe_allow_html=True)

            if not reparse_targets:
                st.error("재파싱 가능한 원본 PDF를 찾지 못했습니다.")
            else:
                result = run_parsing_batch(
                    file_batch=reparse_targets,
                    output_dir=output_dir,
                    use_ocr=re_ocr,
                    chunk_size=int(re_chunk_size),
                    chunk_overlap=int(re_chunk_overlap),
                    log_ph=reparse_log_ph,
                    prog_ph=reparse_prog_ph,
                    backup_mode=(overwrite_mode == "백업 후 재생성"),
                )
                st.success(f"재파싱 완료 — 성공 {result['ok_count']}개 / 실패 {result['fail_count']}개")

        st.markdown("---")

        for x in sorted(all_scores, key=lambda v: v["noise"]["total"], reverse=True):
            sc = x["noise"]["total"]
            col = noise_color(sc)
            bar_pct = int(sc)

            with open(x["path"], encoding="utf-8") as _f:
                _fm = _f.read(500)
            _lm = re.search(r"languages: *(.+)", _fm)
            langs = _lm.group(1).strip() if _lm else "—"

            st.markdown(f"""
            <div style="margin-bottom:8px;">
              <div style="display:flex;justify-content:space-between;
                   font-family:'JetBrains Mono',monospace;font-size:0.73rem;margin-bottom:2px;">
                <span style="color:#c9d1d9;">📄 {x['name']}
                  <span style="color:#8b949e;font-size:0.66rem;margin-left:8px;">[{langs}]</span>
                </span>
                <span style="color:{col};font-weight:600;">{sc:.1f} &nbsp;{noise_label(sc)}</span>
              </div>
              <div class="noise-bar-wrap">
                <div class="noise-bar" style="width:{bar_pct}%;background:{col};"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("##### 개별 파일 상세 분석")

        file_names = [x["name"] for x in all_scores]
        selected_md = st.selectbox("분석할 파일 선택", file_names)

        if selected_md:
            sel_data = next((x for x in all_scores if x["name"] == selected_md), None)
            if not sel_data:
                st.error("선택한 파일 정보를 찾을 수 없습니다.")
                st.stop()

            ns = sel_data["noise"]
            stem = os.path.splitext(selected_md)[0]

            with open(sel_data["path"], encoding="utf-8") as fh:
                content = fh.read()

            col_a, col_b = st.columns([1, 1], gap="medium")

            with col_a:
                sc = ns["total"]
                col = noise_color(sc)
                st.markdown(f"""
                <div class="analysis-card">
                  <h4>종합 노이즈 점수</h4>
                  <div style="font-size:2.8rem;font-weight:700;color:{col};
                       font-family:'JetBrains Mono',monospace;line-height:1.1;">
                    {sc:.1f}
                  </div>
                  <div style="font-size:0.82rem;color:{col};margin-top:4px;">{noise_label(sc)}</div>
                  <div class="noise-bar-wrap" style="margin-top:12px;">
                    <div class="noise-bar" style="width:{int(sc)}%;background:{col};"></div>
                  </div>
                  <div style="font-family:'JetBrains Mono',monospace;font-size:0.71rem;
                       color:#8b949e;margin-top:10px;line-height:1.9;">
                    문자 수: {ns['char_count']:,}<br>
                    단어 수: {ns['word_count']:,}<br>
                    줄   수: {ns['line_count']:,}<br>
                    감지 언어: {' · '.join(ns.get('lang_detected', [])) or '—'}
                  </div>
                </div>
                """, unsafe_allow_html=True)

            with col_b:
                def mini_bar(label, val, max_val, color):
                    pct = int(min(val / max_val * 100, 100))
                    return (
                        f"<div style='margin-bottom:10px;'>"
                        f"<div style='display:flex;justify-content:space-between;"
                        f"font-family:JetBrains Mono,monospace;font-size:0.70rem;"
                        f"color:#8b949e;margin-bottom:2px;'>"
                        f"<span>{label}</span><span style='color:{color};'>{val:.1f} / {max_val}</span></div>"
                        f"<div class='noise-bar-wrap'>"
                        f"<div class='noise-bar' style='width:{pct}%;background:{color};'></div>"
                        f"</div></div>"
                    )

                st.markdown(f"""
                <div class="analysis-card">
                  <h4>세부 지표 분석</h4>
                  {mini_bar("특수문자 비율", ns['symbol_ratio'], 40, "#f85149")}
                  {mini_bar("짧은 줄 비율", ns['short_line'], 30, "#d29922")}
                  {mini_bar("공백 줄 비율", ns['blank_ratio'], 15, "#58a6ff")}
                  {mini_bar("반복 패턴", ns['repeat_ratio'], 15, "#a371f7")}
                </div>
                """, unsafe_allow_html=True)

            chunks = load_chunks_info(output_dir, stem)
            if chunks:
                st.markdown(f"""
                <div class="analysis-card">
                  <h4>청크 미리보기 &nbsp;<span style='color:#8b949e;font-size:0.75rem;
                  font-family:JetBrains Mono,monospace;font-weight:400;'>
                  총 {len(chunks)}개</span></h4>
                </div>
                """, unsafe_allow_html=True)

                preview_n = st.slider("미리볼 청크 수", 1, min(len(chunks), 10), 3)
                for i, chunk in enumerate(chunks[:preview_n], 1):
                    preview = chunk[:400] + ("…" if len(chunk) > 400 else "")
                    st.markdown(f"""
                    <div class="chunk-box">
                      <span style="color:#8b949e;font-size:0.67rem;">CHUNK {i:03d}</span><br>
                      {preview}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("_chunks.txt 파일이 없습니다. 파싱 후 생성됩니다.")

            with st.expander("📄 MD 본문 전체 보기"):
                body = re.sub(r"^---.*?---\s*", "", content, flags=re.DOTALL)
                st.text_area(
                    "",
                    body[:3000] + ("…" if len(body) > 3000 else ""),
                    height=300,
                    label_visibility="collapsed"
                )