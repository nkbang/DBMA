import os
import json
import shutil
import datetime
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter, SentenceTransformersTokenTextSplitter
from docling.document_converter import DocumentConverter
from sentence_transformers import SentenceTransformer

from core.extractors import extract_text_from_file
from core.utils import make_safe_stem, calculate_noise_score
from core.chunking_optimizer import optimize_chunks, save_optimized_md

_splitter_cache: dict = {}


def build_converter(use_ocr=False):
    return DocumentConverter()


def build_splitter(chunk_size, chunk_overlap):
    """캐시 추가: 동일 파라미터면 재사용"""
    cache_key = (chunk_size, chunk_overlap)
    if cache_key not in _splitter_cache:
        _splitter_cache[cache_key] = SentenceTransformersTokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            model_name="BAAI/bge-m3",
        )
    return _splitter_cache[cache_key]


def detect_language(text):
    """Simple language detection based on script characters"""
    hebrew_chars = sum(1 for c in text if '\u0590' <= c <= '\u05FF')
    greek_chars = sum(1 for c in text if '\u0370' <= c <= '\u03FF')
    total_chars = len(text)
    if total_chars > 0 and hebrew_chars / total_chars > 0.1:
        return "he"
    elif total_chars > 0 and greek_chars / total_chars > 0.1:
        return "grc"
    else:
        return "en"


def save_md_with_language(output_dir, stem, source_name, text, noise, source_type, language):
    """Save markdown with language metadata"""
    path = os.path.join(output_dir, f"{stem}.md")
    frontmatter = [
        "---",
        f"source: {source_name}",
        f"source_type: {source_type}",
        f"language: {language}",
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
    src_path = file_info["path"]
    source_name = file_info["name"]
    ext = file_info["ext"].lower().replace(".", "")
    stem = make_safe_stem(source_name)

    try:
        logs.append({"cls": "log-info", "msg": f"process_one_file 시작: {source_name}"})

        logs.append({"cls": "log-info", "msg": f"텍스트 추출 시작: {source_name}"})
        result = extract_text_from_file(src_path, converter=converter)
        full_text = result.get("text", "") or ""
        is_ocr = result.get("is_ocr", False)
        logs.append({"cls": "log-info", "msg": f"텍스트 추출 완료: {len(full_text)} characters"})

        language = detect_language(full_text)
        logs.append({"cls": "log-info", "msg": f"감지된 언어: {language}"})

        if not full_text.strip():
            logs.append({"cls": "log-warn", "msg": f"{source_name}: 추출 텍스트 없음"})
            return logs, False

        logs.append({"cls": "log-info", "msg": f"노이즈 점검 시작: {source_name}"})
        noise = calculate_noise_score(full_text, file_type=ext, is_ocr=is_ocr)
        final_text = full_text
        logs.append({"cls": "log-info", "msg": f"노이즈 점검 완료: score={noise['score']}"})

        if not final_text.strip():
            logs.append({"cls": "log-warn", "msg": f"{source_name}: 정제 후 텍스트 없음"})
            return logs, False

        logs.append({"cls": "log-info", "msg": f"MD 저장 시작: {source_name}"})
        md_path = save_md_with_language(output_dir, stem, source_name, final_text, noise, ext, language)
        logs.append({"cls": "log-info", "msg": f"MD 저장 완료: {md_path}"})

        logs.append({"cls": "log-info", "msg": f"청킹 시작: {source_name}"})
        chunk_result = optimize_chunks(final_text, ext)
        chunks = chunk_result.chunks
        logs.append({"cls": "log-info", "msg": f"옵티마이저 실행 완료: {len(chunks)} chunks"})

        if not chunks:
            logs.append({"cls": "log-info", "msg": f"옵티마이저 결과 없음, 기존 splitter 사용: {source_name}"})
            chunks = splitter.split_text(final_text)
            chunk_size_used = chunk_size
            chunk_overlap_used = chunk_overlap
        else:
            chunk_size_used = chunk_result.params["chunk_size"]
            chunk_overlap_used = chunk_result.params["chunk_overlap"]

        logs.append({"cls": "log-info", "msg": f"기존 txt 저장 시작: {source_name}"})
        save_chunks(output_dir, stem, source_name, chunks, chunk_size_used, chunk_overlap_used)
        logs.append({"cls": "log-info", "msg": f"기존 txt 저장 완료: {source_name}"})

        logs.append({"cls": "log-info", "msg": f"최적화 MD 저장 시작: {source_name}"})
        if chunks:
            opt_md_path = save_optimized_md(
                result=chunk_result,
                source_name=source_name,
                output_dir=Path(output_dir),
                stem=stem,
            )
            logs.append({"cls": "log-info", "msg": f"최적화 MD 저장 완료: {opt_md_path}"})
            logs.append({"cls": "log-info", "msg": f"MD exists: {Path(opt_md_path).exists()} | {opt_md_path}"})
        else:
            logs.append({"cls": "log-warn", "msg": f"chunks 가 빈하여 MD 저장 건너뜁니다: {source_name}"})

        logs.append({"cls": "log-info", "msg": f"원본 파일 이동 시작: {source_name}"})
        moved_to = move_source_file(src_path, output_dir)
        logs.append({"cls": "log-info", "msg": f"원본 파일 이동 완료: {moved_to}"})

        logs.append({"cls": "log-ok", "msg": f"{source_name} 처리 완료"})

        if chunks and not chunk_result.passed:
            logs.append({
                "cls": "log-warn",
                "msg": (
                    f"⚠️ 청킹 품질 미달 (avg_noise={chunk_result.quality.avg_noise:.1f}, "
                    f"avg_dup={chunk_result.quality.avg_dup:.2f}) — 재검토 권장"
                ),
            })

        return logs, True

    except Exception as e:
        logs.append({"cls": "log-warn", "msg": f"{source_name}: 처리 실패 — {e}"})
        import traceback
        logs.append({"cls": "log-warn", "msg": f"Traceback: {traceback.format_exc()}"})
        return logs, False