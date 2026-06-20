# core/processing.py
import os
import json
import shutil
import datetime
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from docling.document_converter import DocumentConverter

from core.extractors import extract_text_from_file
from core.utils import make_safe_stem, calculate_noise_score
from core.chunking_optimizer import optimize_chunks, save_optimized_md


def build_converter(use_ocr=False):
    return DocumentConverter()


def build_splitter(chunk_size, chunk_overlap):
    """기존 호환용: UI(tabs.py)에서 여전히 호출 가능"""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def save_md(output_dir, stem, source_name, text, noise, source_type):
    path = os.path.join(output_dir, f"{stem}.md")
    frontmatter = [
        "---",
        f"source: {source_name}",
        f"source_type: {source_type}",
        f"created_at: {datetime.datetime.now().isoformat()}",
        f"noise_score: {noise['score']}",
        f"noise_mode: {noise.get('mode', '-')}",
        "---",
        "",
        text,
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(frontmatter))
    return path


def save_chunks(output_dir, stem, source_name, chunks, chunk_size, chunk_overlap):
    """기존 RAG 파이프라인 호환용: txt + meta.json 저장 유지"""
    txt_path = os.path.join(output_dir, f"{stem}_chunks.txt")
    meta_path = os.path.join(output_dir, f"{stem}_chunks_meta.json")

    with open(txt_path, "w", encoding="utf-8") as f:
        for i, ch in enumerate(chunks, 1):
            f.write(f"[chunk {i}]\n{ch}\n\n")

    meta = {
        "source": source_name,
        "chunks": len(chunks),
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return txt_path, meta_path


def move_source_file(src_path, output_dir):
    dst = os.path.join(output_dir, os.path.basename(src_path))
    if os.path.abspath(src_path) != os.path.abspath(dst) and not os.path.exists(dst):
        shutil.move(src_path, dst)
        return dst
    return src_path


def process_one_file(file_info, converter, splitter, output_dir, chunk_size, chunk_overlap):
    """
    수정된 버전: 옵티마이저 우선, 폴백은 기존 splitter
    반환: (logs, success)
    """
    logs = []
    src_path    = file_info["path"]
    source_name = file_info["name"]
    ext         = file_info["ext"].lower().replace(".", "")
    stem        = make_safe_stem(source_name)

    result    = extract_text_from_file(src_path, converter=converter)
    full_text = result.get("text", "") or ""
    is_ocr    = result.get("is_ocr", False)

    if not full_text.strip():
        logs.append({"cls": "log-warn", "msg": f"{source_name}: 추출 텍스트 없음"})
        return logs, False

    noise      = calculate_noise_score(full_text, file_type=ext, is_ocr=is_ocr)
    final_text = noise["cleaned_text"]

    if not final_text.strip():
        logs.append({"cls": "log-warn", "msg": f"{source_name}: 정제 후 텍스트 없음"})
        return logs, False

    # ── MD 저장 (기존 동일) ──────────────────────────────────────────────
    md_path = save_md(output_dir, stem, source_name, final_text, noise, ext)

    # ── 청킹: 옵티마이저 우선, 폴백은 기존 splitter ─────────────────────
    chunk_result = optimize_chunks(final_text, ext)
    chunks       = chunk_result.chunks
    if not chunks:                          # 옵티마이저 결과가 비어있으면 폴백
        chunks = splitter.split_text(final_text)

    # 기존 txt 저장 (RAG 파이프라인 호환 유지)
    save_chunks(output_dir, stem, source_name, chunks,
                chunk_result.params["chunk_size"],
                chunk_result.params["chunk_overlap"])

    # 최적화 마크다운 저장 (신규)
    opt_md_path = save_optimized_md(
        result      = chunk_result,
        source_name = source_name,
        output_dir  = Path(output_dir),
        stem        = stem,
    )

    moved_to = move_source_file(src_path, output_dir)

    logs.append({"cls": "log-ok",   "msg": f"{source_name} 처리 완료"})
    logs.append({"cls": "log-info", "msg": f"MD 저장: {md_path}"})
    logs.append({"cls": "log-info", "msg": f"청크 최적화 MD: {opt_md_path}"})
    logs.append({"cls": "log-info", "msg": f"청크 수: {len(chunks)} / params: {chunk_result.params}"})
    logs.append({"cls": "log-info", "msg": f"원본 이동: {moved_to}"})

    # 품질 경고
    if not chunk_result.passed:
        logs.append({"cls": "log-warn",
                     "msg": f"⚠️ 청킹 품질 미달 (avg_noise={chunk_result.quality.avg_noise:.1f}, "
                            f"avg_dup={chunk_result.quality.avg_dup:.2f}) — 재검토 권장"})

    return logs, True