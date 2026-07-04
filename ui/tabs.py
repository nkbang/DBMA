import os
from pathlib import Path

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


def get_converter(use_ocr: bool = False):
    return build_converter(use_ocr=use_ocr)


def get_splitter(chunk_size: int, chunk_overlap: int):
    return build_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


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


def _render_noise_badge(score: float):
    label = noise_label(score)
    color = noise_color(score)
    st.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:0.45rem 0.75rem;
            border-radius:0.6rem;
            border:1px solid {color};
            background:{color}22;
            color:{color};
            font-weight:700;
            line-height:1.2;
        ">
            노이즈 {label} ({score:.1f})
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_processing_tab(target_dir, output_dir, chunk_size, chunk_overlap, use_ocr):
    st.subheader("처리")

    if not os.path.isdir(target_dir):
        st.error(f"RAW 폴더가 없습니다: {target_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)

    converter = get_converter(use_ocr=use_ocr)
    splitter = get_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    file_list = scan_directory(target_dir)
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
            st.session_state["selected_names"] = [f["name"] for f in file_list]
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

    progress_bar = st.progress(0)
    status_box = st.empty()

    def report(stage, message, progress=None):
        status_box.info(f"[{stage}] {message}")
        if progress is not None:
            progress_bar.progress(min(max(progress, 0.0), 1.0))

    if st.button("파싱 시작", type="primary", use_container_width=True):
        if not selected_files:
            st.warning("선택된 파일이 없습니다.")
        else:
            ok_count = 0
            fail_count = 0

            for idx, file_info in enumerate(selected_files, 1):
                status_box.info(f"[{idx}/{len(selected_files)}] 처리 중: {file_info['name']}")
                st.info(f"process_one_file 호출 시작: {file_info['name']}")

                try:
                    result = process_one_file(
                        file_info=file_info,
                        converter=converter,
                        splitter=splitter,
                        output_dir=output_dir,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        report=report,
                    )

                    st.info(f"process_one_file 호출 완료: {file_info['name']}")

                    for log in result["logs"]:
                        if log["cls"] == "log-ok":
                            st.success(log["msg"])
                        elif log["cls"] == "log-warn":
                            st.warning(log["msg"])
                        else:
                            st.info(log["msg"])

                    if result["success"]:
                        st.info("✅ 파싱 완료")
                        noise = result["metrics"]["noise"]
                        c_noise, c_mode = st.columns([1, 1])
                        with c_noise:
                            _render_noise_badge(noise["score"])
                        with c_mode:
                            st.metric("노이즈 모드", noise["mode"])
                        st.caption(
                            f"chunks={result['metrics']['chunk_count']}, "
                            f"language={result['metrics']['language']}"
                        )
                        if result["artifacts"].get("opt_md_path"):
                            st.caption(f"RAG 대상 MD: {result['artifacts']['opt_md_path']}")
                        ok_count += 1
                    else:
                        fail_count += 1
                        st.error(
                            f"❌ 처리 실패 | stage={result.get('failed_stage')} | reason={result.get('reason')}"
                        )

                except Exception as e:
                    fail_count += 1
                    st.error(f"{file_info['name']} 실패: {e}")

                progress_bar.progress(idx / len(selected_files))

            status_box.success(f"완료: 성공 {ok_count} / 실패 {fail_count}")
