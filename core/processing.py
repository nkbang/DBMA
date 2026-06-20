import os
import shutil
import datetime
from typing import Dict, List, Tuple
from .extractors import extract_text_from_file
from .utils import detect_langs, calculate_noise_score, noise_label, make_safe_stem


def save_md(stem: str, source_name: str, text: str, noise: Dict, output_dir: str) -> str:
    md_path = os.path.join(output_dir, f"{stem}.md")
    lang_list = detect_langs(text)
    has_rtl = "he" in lang_list
    header = f"""---
source: {source_name}
created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
pipeline: DBMA v3.3
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
