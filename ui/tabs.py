import os
import streamlit as st

from core.files import scan_directory, scan_md_files, load_chunks_info
from core.processing import build_converter, build_splitter, process_one_file
from core.utils import (
    fmt_size,
    noise_color,
    noise_label,
    calculate_noise_score,
    file_checkbox_key,
)


def parse_frontmatter(content: str):
    meta = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            raw_meta = parts[1].strip()
            body = parts[2].strip()

            for line in raw_meta.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()

    return meta, body


def render_processing_tab(target_dir, output_dir, chunk_size, chunk_overlap, use_ocr):
    st.subheader("처리")

    # Log entry point
    st.info("render_processing_tab 시작")
    
    if not os.path.isdir(target_dir):
        st.error(f"RAW 폴더가 없습니다: {target_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)
    file_list = scan_directory(target_dir)
    
    # Log file list
    st.info(f"파일 목록 수집 완료: {len(file_list)} 파일")

    if "selected_names" not in st.session_state:
        st.session_state["selected_names"] = []

    if not file_list:
        st.warning(f"{target_dir} 에 지원 형식 파일이 없습니다.")
        return

    selected_set = set(st.session_state.get("selected_names", []))

    for f in file_list:
        key = file_checkbox_key(f)
        if key not in st.session_state:
            st.session_state[key] = f["name"] in selected_set

    b1, b2, b3 = st.columns([1, 1, 3])
    with b1:
        if st.button("전체 선택", use_container_width=True):
            all_names = [f["name"] for f in file_list]
            st.session_state["selected_names"] = all_names
            for f in file_list:
                st.session_state[file_checkbox_key(f)] = True
            st.rerun()

    with b2:
        if st.button("전체 해제", use_container_width=True):
            st.session_state["selected_names"] = []
            for f in file_list:
                st.session_state[file_checkbox_key(f)] = False
            st.rerun()

    with b3:
        st.caption("개별 선택은 즉시 반영됩니다 → 바로 파싱 시작 가능")

    current_selected = []

    for f in file_list:
        key = file_checkbox_key(f)
        checked = st.checkbox(
            f"{f['name']} | {f.get('size_str', '-')} | {f.get('mtime', '-')} | {f.get('ext', '').upper()}",
            key=key,
        )
        if checked:
            current_selected.append(f["name"])

    st.session_state["selected_names"] = current_selected
    selected_files = [f for f in file_list if f["name"] in set(current_selected)]

    total_bytes = sum(f.get("size", 0) for f in file_list)
    selected_count = len(current_selected)

    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        st.metric("대상 파일", len(file_list))
    with c2:
        st.metric("총 용량", fmt_size(total_bytes))
    with c3:
        st.metric("선택 수", selected_count)

    st.divider()

    if st.button("파싱 시작", type="primary", use_container_width=True):
        if not selected_files:
            st.warning("선택된 파일이 없습니다.")
            return

        # Log before creating converter and splitter
        st.info(f"파싱 시작: {len(selected_files)} 파일")
        
        converter = build_converter(use_ocr)
        splitter = build_splitter(chunk_size, chunk_overlap)

        progress = st.progress(0)
        status_box = st.empty()

        ok_count = 0
        fail_count = 0

        for idx, file_info in enumerate(selected_files, 1):
            status_box.info(f"[{idx}/{len(selected_files)}] 처리 중: {file_info['name']}")
            
            # Log before calling process_one_file
            st.info(f"process_one_file 호출 시작: {file_info['name']}")
            
            try:
                logs, success = process_one_file(
                    file_info=file_info,
                    converter=converter,
                    splitter=splitter,
                    output_dir=output_dir,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                
                # Log after process_one_file returns
                st.info(f"process_one_file 호출 완료: {file_info['name']}")

                for log in logs:
                    if log["cls"] == "log-ok":
                        st.success(log["msg"])
                    elif log["cls"] == "log-warn":
                        st.warning(log["msg"])
                    else:
                        st.info(log["msg"])

                # --- 추가: 청킹 품질 표시 (선택적) ---
                if success:
                    st.info("✅ 파싱 완료")
                    # process_one_file 이 logs 밖으로 chunk_params 를 반환하지 않으므로,
                    # 현재 단계에서는 logs 속에 이미 들어있는 "청크 최적화 MD" / "청크 수" 로그만 표시됨.
                    # UI 에서 직접 chunk_params 를 보려면 process_one_file 결과를 dict 로 받도록
                    # dbma.py 파이프라인만 수정하고, tabs.py 는 기존 로그 출력만 유지해도 충분합니다.

                if success:
                    ok_count += 1
                else:
                    fail_count += 1

            except Exception as e:
                fail_count += 1
                st.error(f"{file_info['name']} 실패: {e}")

            progress.progress(idx / len(selected_files))

        status_box.success(f"완료: 성공 {ok_count} / 실패 {fail_count}")

        scan_directory.clear()
        scan_md_files.clear()
        st.session_state["selected_names"] = []

        for f in file_list:
            key = file_checkbox_key(f)
            if key in st.session_state:
                st.session_state[key] = False

        st.rerun()


def render_analysis_tab(output_dir):
    st.subheader("분석")

    if not os.path.isdir(output_dir):
        st.warning(f"결과 폴더가 없습니다: {output_dir}")
        return

    md_files = scan_md_files(output_dir)

    if not md_files:
        st.info("분석할 md 파일이 없습니다.")
        return

    selected_md = st.selectbox("파일 선택", options=[m["name"] for m in md_files])
    item = next((m for m in md_files if m["name"] == selected_md), None)

    if item is None:
        st.warning("선택한 파일을 찾을 수 없습니다.")
        return

    with open(item["path"], "r", encoding="utf-8") as fh:
        content = fh.read()

    meta, body = parse_frontmatter(content)
    source_type = meta.get("source_type", "md").lower()
    is_ocr = "ocr" in meta.get("noise_mode", "").lower()

    noise = calculate_noise_score(body, file_type=source_type, is_ocr=is_ocr)
    chunks_info = load_chunks_info(output_dir, item["name"])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("노이즈", f"{noise['score']:.1f}")
    with c2:
        st.metric("상태", noise_label(noise["score"]))
    with c3:
        st.metric("문자수", noise["charcount"])

    st.markdown(
        f"""
<div style="margin:8px 0 16px 0;">
    <span style="display:inline-block;padding:6px 12px;border-radius:12px;background:{noise_color(noise['score'])};color:white;font-weight:600;">
        {noise_label(noise['score'])}
    </span>
</div>
""",
        unsafe_allow_html=True,
    )

    st.caption(
        f"source_type={source_type}, "
        f"mode={noise.get('mode', '-')}, "
        f"symbol={noise.get('symbol_ratio', 0):.1f}%, "
        f"short_line={noise.get('short_line_ratio', 0):.1f}%, "
        f"broken_line={noise.get('broken_line_ratio', 0):.1f}%, "
        f"repeated={noise.get('repeated_punct_ratio', 0):.1f}%"
    )

   if chunks_info:
        c4, c5, c6 = st.columns(3)
        with c4:
            st.metric("청크 수", chunks_info.get("chunks", "-"))
        with c5:
            st.metric("Chunk Size", chunks_info.get("chunk_size", "-"))
        with c6:
            st.metric("Chunk Overlap", chunks_info.get("chunk_overlap", "-"))

        with st.expander("본문 미리보기", expanded=True):
            st.text_area("preview", body[:5000], height=320, label_visibility="collapsed")
