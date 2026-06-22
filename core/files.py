import os
import glob
import json
import streamlit as st

from core.config import SUPPORTED_EXTENSIONS
from core.utils import fmt_size


@st.cache_data(show_spinner=False)
def scan_directory(target_dir):
    if not os.path.isdir(target_dir):
        return []

    files = []
    for name in os.listdir(target_dir):
        path = os.path.join(target_dir, name)
        if not os.path.isfile(path):
            continue

        ext = os.path.splitext(name)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue

        stat = os.stat(path)
        files.append({
            "name": name,
            "path": path,
            "size": stat.st_size,
            "size_str": fmt_size(stat.st_size),
            "mtime": str(int(stat.st_mtime)),
            "ext": ext.replace(".", ""),
        })

    files.sort(key=lambda x: x["name"].lower())
    return files


@st.cache_data(show_spinner=False)
def scan_md_files(output_dir):
    if not os.path.isdir(output_dir):
        return []

    md_files = []
    for path in glob.glob(os.path.join(output_dir, "*.md")):
        name = os.path.basename(path)
        stat = os.stat(path)
        md_files.append({
            "name": name,
            "path": path,
            "size": stat.st_size,
            "size_str": fmt_size(stat.st_size),
            "mtime": str(int(stat.st_mtime)),
        })

    md_files.sort(key=lambda x: x["name"].lower())
    return md_files


def load_chunks_info(output_dir, md_name):
    stem = os.path.splitext(md_name)[0]
    meta_path = os.path.join(output_dir, f"{stem}_chunks_meta.json")
    if not os.path.exists(meta_path):
        return None

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
