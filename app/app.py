import streamlit as st
import os
import glob
import shutil
import warnings
import logging
import datetime

# ── 경고 억제 ──────────────────────────────────────────────────────────────
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", message=".*__path__.*")
logging.getLogger("transformers").setLevel(logging.ERROR)

# ── 페이지 설정 ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DBMA 파싱 파이프라인",
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
    display: grid;
    grid-template-columns: 40px 1fr 90px 150px 60px;
    background:#161b22; padding:9px 12px;
    font-size:0.70rem; color:#8b949e;
    font-family:'JetBrains Mono',monospace;
    text-transform:uppercase; letter-spacing:0.08em;
    border:1px solid #21262d; border-radius:8px 8px 0 0;
    margin-bottom:0;
}
.file-row {
    display:grid;
    grid-template-columns: 40px 1fr 90px 150px 60px;
    padding:9px 12px; border:1px solid #21262d; border-top:none;
    align-items:center; font-size:0.80rem; background:#0d1117;
}
.file-row:last-child { border-radius:0 0 8px 8px; }
.file-row:hover      { background:#161b22; }
.fname  { color:#58a6ff; font-family:'JetBrains Mono',monospace; font-size:0.76rem; word-break:break-all; }
.fsize  { color:#3fb950; font-family:'JetBrains Mono',monospace; font-size:0.74rem; }
.fdate  { color:#8b949e; font-family:'JetBrains Mono',monospace; font-size:0.72rem; }
.fbadge { display:inline-block; background:#1f3a5f; color:#58a6ff; border-radius:4px;
          padding:1px 7px; font-size:0.66rem; font-family:'JetBrains Mono',monospace; font-weight:500; }

.stat-row  { display:flex; gap:12px; margin-bottom:16px; }
.stat-card { flex:1; background:#161b22; border:1px solid #21262d; border-radius:8px; padding:13px 17px; }
.stat-label{ font-size:0.67rem; color:#8b949e; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:3px; font-family:'JetBrains Mono',monospace; }
.stat-value{ font-size:1.35rem; font-weight:700; color:#e6edf3; font-family:'JetBrains Mono',monospace; }
.blue  { color:#58a6ff; } .green{ color:#3fb950; } .orange{ color:#d29922; }

.log-box {
    background:#0d1117; border:1px solid #21262d; border-radius:8px;
    padding:13px 17px; font-family:'JetBrains Mono',monospace;
    font-size:0.75rem; color:#c9d1d9; max-height:320px;
    overflow-y:auto; line-height:1.9;
}
.log-ok  { color:#3fb950; } .log-warn{ color:#d29922; }
.log-err { color:#f85149; } .log-info{ color:#58a6ff; }

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
/* 개별 체크박스 여백 축소 */
div[data-testid="stCheckbox"] { margin-bottom:0 !important; padding:2px 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── 헤더 ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="dbma-header">
  <h1>📚 DBMA 파싱 파이프라인</h1>
  <p>David Bang Ministry Archive · RAG 데이터 정제 시스템 v2.2</p>
</div>
""", unsafe_allow_html=True)


# ── 유틸리티 ───────────────────────────────────────────────────────────────
def fmt_size(b: int) -> str:
    for u in ("B","KB","MB","GB"):
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"

def scan_directory(directory: str) -> list[dict]:
    if not os.path.isdir(directory):
        return []
    files = []
    for fp in sorted(glob.glob(os.path.join(directory, "*.pdf"))):
        s = os.stat(fp)
        files.append({
            "path":     fp,
            "name":     os.path.basename(fp),
            "size_b":   s.st_size,
            "size_str": fmt_size(s.st_size),
            "mtime":    datetime.datetime.fromtimestamp(s.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return files


# ── session_state 초기화 ────────────────────────────────────────────────────
# 선택 상태를 session_state["sel_{name}"] 키로 관리
# 전체선택 토글도 session_state로 관리하여 on_change 콜백으로 전파

def _apply_select_all():
    """전체선택 체크박스 변경 시 → 모든 개별 항목에 동일 값 적용."""
    new_val = st.session_state["_select_all"]
    for key in list(st.session_state.keys()):
        if key.startswith("sel_"):
            st.session_state[key] = new_val

def _on_item_change():
    """개별 항목 변경 시 → 전체선택 체크박스 상태 재계산."""
    sel_keys = [k for k in st.session_state if k.startswith("sel_")]
    if sel_keys:
        all_checked = all(st.session_state[k] for k in sel_keys)
        st.session_state["_select_all"] = all_checked


# ── 사이드바 ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 파이프라인 설정")
    st.markdown("---")
    target_dir = st.text_input("RAW 폴더 경로",    value="/Users/David/DBMA/RAW")
    output_dir = st.text_input("완성본 폴더 경로", value="/Users/David/DBMA/제련완성본")
    st.markdown("---")
    st.markdown("### 🔪 청크 설정")
    chunk_size    = st.number_input("Chunk Size",    value=1000, min_value=100, step=100)
    chunk_overlap = st.number_input("Chunk Overlap", value=200,  min_value=0,   step=50)
    st.markdown("---")
    st.markdown("### 🔍 OCR 설정")
    use_ocr = st.checkbox(
        "OCR 활성화 (스캔본 PDF 전용)", value=False,
        help="디지털 PDF는 해제. 스캔 이미지 PDF만 활성화."
    )
    if use_ocr:
        st.info("EasyOCR (한국어 + 영어) 사용")
    st.markdown("---")
    st.markdown(
        "<div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;"
        "color:#3fb950;padding:8px 10px;background:#0d2b1a;border-radius:6px;"
        "border:1px solid #1a4a2a;'>"
        "✓ 파싱 완료 후 원본 PDF는<br>자동으로 제련완성본 폴더로<br>이동됩니다.</div>",
        unsafe_allow_html=True,
    )


# ── 메인 레이아웃 ──────────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2], gap="large")

with col_left:
    st.markdown("#### 📂 파일 탐색기")

    ref_col, path_col = st.columns([1, 4])
    with ref_col:
        st.button("🔄 새로고침")   # 클릭만 해도 Streamlit이 재실행됨
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
        # ── 파일 목록이 바뀌면 session_state 키 동기화 ─────────────────
        current_names = {f["name"] for f in file_list}

        # 더 이상 없는 파일의 상태 제거
        for key in list(st.session_state.keys()):
            if key.startswith("sel_") and key[4:] not in current_names:
                del st.session_state[key]

        # 새로 등장한 파일은 기본값 True로 추가
        for f in file_list:
            key = f"sel_{f['name']}"
            if key not in st.session_state:
                st.session_state[key] = True

        # _select_all 초기화
        if "_select_all" not in st.session_state:
            st.session_state["_select_all"] = True

        # ── 통계 카드 ──────────────────────────────────────────────────
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

        # ── 전체 선택/해제 체크박스 (on_change 콜백으로 개별 항목에 전파) ──
        st.checkbox(
            "전체 선택 / 해제",
            key="_select_all",
            on_change=_apply_select_all,
        )

        # ── 테이블 헤더 ────────────────────────────────────────────────
        st.markdown("""
        <div class="file-table-header">
          <span>✓</span><span>파일명</span>
          <span>크기</span><span>수정일</span><span>형식</span>
        </div>
        """, unsafe_allow_html=True)

        # ── 파일별 행: 체크박스 + 정보 ────────────────────────────────
        selected_files = []
        for f in file_list:
            c1, c2 = st.columns([1, 12])
            with c1:
                st.checkbox(
                    label="",
                    key=f"sel_{f['name']}",      # session_state로 직접 관리
                    on_change=_on_item_change,   # 개별 변경 시 전체선택 재계산
                    label_visibility="collapsed",
                )
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

            if st.session_state.get(f"sel_{f['name']}", False):
                selected_files.append(f)

        # ── 선택 요약 ──────────────────────────────────────────────────
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


# ── 오른쪽: 실행 패널 ──────────────────────────────────────────────────────
with col_right:
    st.markdown("#### 🚀 파싱 실행")

    ocr_label = "EasyOCR (ko+en)" if use_ocr else "비활성화"
    n_sel = len(selected_files) if file_list else 0

    st.markdown(f"""
    <div style="background:#161b22;border:1px solid #21262d;border-radius:8px;
         padding:14px 18px;margin-bottom:16px;font-family:'JetBrains Mono',monospace;
         font-size:0.75rem;line-height:2.1;">
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
    log_ph  = st.empty()
    prog_ph = st.empty()

    # ── 파싱 실행 ──────────────────────────────────────────────────────────
    if start_btn and selected_files:

        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        os.makedirs(output_dir, exist_ok=True)

        pipeline_options = PdfPipelineOptions()
        if use_ocr:
            pipeline_options.do_ocr = True
            pipeline_options.ocr_options = EasyOcrOptions(lang=["ko","en"], use_gpu=False)
        else:
            pipeline_options.do_ocr = False

        converter = DocumentConverter(
            format_options={"pdf": PdfFormatOption(pipeline_options=pipeline_options)}
        )
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(chunk_size), chunk_overlap=int(chunk_overlap)
        )

        logs, ok_count, fail_count = [], 0, 0
        total = len(selected_files)

        def render_logs(entries):
            html = '<div class="log-box">'
            for e in entries:
                html += f'<div class="{e["cls"]}">{e["msg"]}</div>'
            html += "</div>"
            log_ph.markdown(html, unsafe_allow_html=True)

        def save_md(stem: str, text: str) -> str:
            """마크다운 전문을 {stem}.md 로 저장 → 저장 경로 반환."""
            md_path = os.path.join(output_dir, f"{stem}.md")
            header = (
                f"---\n"
                f"source: {stem}.pdf\n"
                f"created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"pipeline: DBMA v2.2\n"
                f"---\n\n"
            )
            with open(md_path, "w", encoding="utf-8") as fh:
                fh.write(header + text)
            return md_path

        def save_chunks(stem: str, chunks: list[str]) -> str:
            """청크 목록을 {stem}_chunks.txt 로 저장 → 저장 경로 반환.

            형식:
                ════════ CHUNK 001 / 042 ════════
                (청크 본문)
                ─────────────────────────────────
            """
            txt_path = os.path.join(output_dir, f"{stem}_chunks.txt")
            total_c  = len(chunks)
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

        logs.append({"cls":"log-info","msg":f"[시작] {total}개 파일 처리 예정"})
        logs.append({"cls":"log-info","msg":f"[출력] {output_dir}"})
        if use_ocr:
            logs.append({"cls":"log-info","msg":"[OCR] EasyOCR (ko+en) 활성화"})
        render_logs(logs)

        for idx, f in enumerate(selected_files):
            prog_ph.progress(idx / total, text=f"처리 중 ({idx+1}/{total}): {f['name']}")
            stem      = os.path.splitext(f["name"])[0]
            src_path  = f["path"]
            dest_path = os.path.join(output_dir, f["name"])
            logs.append({"cls":"log-info","msg":f"[{idx+1}/{total}] {f['name']}"})
            render_logs(logs)

            try:
                # Step 1: 원본 위치에서 직접 변환 (복사 없음)
                result = converter.convert(src_path)

                if not (result and result.document):
                    logs.append({"cls":"log-err","msg":"  ✗ 변환 결과 없음 — 원본 유지"})
                    fail_count += 1
                    render_logs(logs)
                    continue

                full_text = result.document.export_to_markdown()

                if not full_text.strip():
                    logs.append({"cls":"log-warn",
                                 "msg":"  ⚠ 텍스트 비어 있음 — OCR 활성화 필요. 원본 유지"})
                    fail_count += 1
                    render_logs(logs)
                    continue

                # Step 2: .md 저장
                md_path = save_md(stem, full_text)
                logs.append({"cls":"log-ok",
                             "msg":f"  ✓ MD  → {os.path.basename(md_path)}"})

                # Step 3: _chunks.txt 저장
                chunks   = splitter.split_text(full_text)
                txt_path = save_chunks(stem, chunks)
                logs.append({"cls":"log-ok",
                             "msg":f"  ✓ TXT → {os.path.basename(txt_path)}  ({len(chunks)} 청크)"})

                # Step 4: 변환 완전 성공 후에만 원본 PDF 이동
                shutil.move(src_path, dest_path)
                logs.append({"cls":"log-ok",
                             "msg":f"  ✓ PDF → 제련완성본 이동 완료"})

                ok_count += 1

            except Exception as e:
                logs.append({"cls":"log-err","msg":f"  ✗ 오류: {e} — 원본 유지"})
                fail_count += 1

            render_logs(logs)

        prog_ph.progress(1.0, text="완료")
        logs.append({"cls":"log-info","msg":"─"*40})
        logs.append({
            "cls":"log-ok" if fail_count==0 else "log-warn",
            "msg":f"[완료] 성공 {ok_count}개 · 실패 {fail_count}개",
        })
        logs.append({
            "cls":"log-info",
            "msg":f"[산출물] 파일당 .md + _chunks.txt → {output_dir}",
        })
        render_logs(logs)

        if fail_count == 0:
            st.success(f"✅ 전체 {ok_count}개 완료 — .md 및 _chunks.txt 저장됨")
        else:
            st.warning(f"⚠️ 성공 {ok_count}개 / 실패 {fail_count}개")
