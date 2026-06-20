import os
import re
import streamlit as st
from core.config import SUPPORTED_EXTENSIONS
from core.files import scan_directory, scan_md_files, load_chunks_info
from core.utils import fmt_size, noise_color, noise_label, apply_select_all, on_item_change, calculate_noise_score
from core.processing import build_converter, build_splitter, process_one_file


def render_logs(log_ph, entries):
    html = '<div class="log-box">'
    for e in entries:
        html += f'<div class="{e["cls"]}">{e["msg"]}</div>'
    html += '</div>'
    log_ph.markdown(html, unsafe_allow_html=True)


def render_file_table(file_list):
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
    return selected_files


def render_processing_tab(target_dir, output_dir, chunk_size, chunk_overlap, use_ocr):
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


def render_analysis_tab(output_dir):
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
