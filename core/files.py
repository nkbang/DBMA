import os
import glob
import datetime
import re
from typing import Dict, List, Optional
from .config import SUPPORTED_EXTENSIONS
from .utils import fmt_size


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
