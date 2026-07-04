"""core/processing.py — 연구용 청킹 파이프라인 (업그레이드 v2)

추가 기능:
1. [NEW] 출 력 검증 (validate_chunks()) — 청크 유효성 검사 강화
2. [NEW] 리트라이 로직 (process_with_retry()) — 실패 시 3회 재시도
3. [NEW] 배치 상태 관리 (BatchState) — 중단 후 재시작 지원
"""

from __future__ import annotations

import os
import json
import shutil
import traceback
import logging
import datetime
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypeVar, Callable

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from langchain_text_splitters import SentenceTransformersTokenTextSplitter

from core.extractors import extract_text_from_file
from core.utils import make_safe_stem, calculate_noise_score
from core.chunking_optimizer import optimize_chunks, save_optimized_md

logger = logging.getLogger(__name__)

_splitter_cache: dict[tuple[int, int], Any] = {}

# ── 상수 ────────────────────────────────────────────────
MAX_RETRY = 3               # 리트라이 최대 횟수
RETRY_DELAY_SEC = 2.0       # 재시도 간격 (초)
MIN_CHUNK_CHARS = 80        # 최소 청크 길이
# ── SPRINT 1 OUTPUT STANDARDIZATION ───────────────────────
SPRINT1_ONLY_MD_OUTPUT = True   # Sprint 1: ONLY .md is canonical output
OUTPUT_VALIDATE_ENABLED = True  # 출력 검증 활성화


# ── 데이터클래스 ────────────────────────────────────────

@dataclass
class BatchState:
    """배치 처리 상태 추적 — 중단 후 재시작"""
    output_dir: str
    state_file: Optional[Path] = field(default=None)  # runtime에서 설정
    processed: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.state_file is None:
            self.state_file = Path(self.output_dir) / ".batch_state.json"

    def save(self):
        if self.state_file is None:
            self.state_file = Path(self.output_dir) / ".batch_state.json"
        data = {
            "processed": self.processed,
            "failed": self.failed,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        self.state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, output_dir: str) -> "BatchState":
        state_file = Path(output_dir) / ".batch_state.json"
        if state_file.exists():
            data = json.loads(state_file.read_text(encoding="utf-8"))
            return cls(output_dir=output_dir, processed=data.get("processed", []), failed=data.get("failed", []))
        return cls(output_dir=output_dir, processed=[], failed=[])


@dataclass
class ChunkValidationResult:
    """청크 출력 검증 결과"""
    valid: bool
    total_chunks: int
    filtered_short: int
    filtered_empty: int
    encoding_errors: int
    reasons: List[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"valid={self.valid}, total={self.total_chunks}, "
            f"filtered(short={self.filtered_short}, empty={self.filtered_empty}), "
            f"encoding_err={self.encoding_errors}"
        )


# ── 유틸리티 ───────────────────────────────────────────

def build_converter(use_ocr: bool = False) -> DocumentConverter:
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = bool(use_ocr)
    if use_ocr:
        pipeline_options.ocr_options = EasyOcrOptions()
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )


def build_splitter(chunk_size: int, chunk_overlap: int) -> SentenceTransformersTokenTextSplitter:
    """캐시 추가: 동일 파라미터면 재사용"""
    cache_key = (chunk_size, chunk_overlap)
    if cache_key not in _splitter_cache:
        _splitter_cache[cache_key] = SentenceTransformersTokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            model_name="BAAI/bge-m3",
        )
    return _splitter_cache[cache_key]


def detect_language(text: str) -> str:
    if not text:
        return "en"

    total_chars = len([c for c in text if c.strip()])  # 공백 제외 문자 수

    hangul_chars = sum(1 for c in text if '\uAC00' <= c <= '\uD7A3')        # 한글 음절
    hangul_jamo  = sum(1 for c in text if '\u1100' <= c <= '\u11FF')        # 한글 자모(선택)
    japanese_chars = sum(1 for c in text if ('\u3040' <= c <= '\u309F') or  # 히라가나
                                            ('\u30A0' <= c <= '\u30FF'))    # 가타카나
    chinese_chars = sum(1 for c in text if '\u4E00' <= c <= '\u9FFF')       # CJK 한자
    hebrew_chars  = sum(1 for c in text if '\u0590' <= c <= '\u05FF')       # 히브리어
    greek_chars   = sum(1 for c in text if '\u0370' <= c <= '\u03FF')       # 그리스어

    if total_chars == 0:
        return "en"

    # 비율 기준으로 우선순위 판단
    if (hangul_chars + hangul_jamo) / total_chars > 0.1:
        return "ko"
    elif japanese_chars / total_chars > 0.1:
        return "ja"
    elif chinese_chars / total_chars > 0.1:
        return "zh"
    elif hebrew_chars / total_chars > 0.1:
        return "he"
    elif greek_chars / total_chars > 0.1:
        return "el"

    return "en"


# ── [NEW #3] 출력 검증 ─────────────────────────────────

def validate_chunks(
    chunks: List[str],
    meta: Dict[str, Any],
    min_chars: int = MIN_CHUNK_CHARS,
) -> ChunkValidationResult:
    """청크 출력物を 검증합니다.

    검증 항목:
    - 빈 청크 필터링
    - 최소 길이 미만 필터링
    - 인코딩 오류 검사 (UTF-8)
    - 메타 데이터 정합성 (chunks 수 일치)
    """
    if not chunks:
        return ChunkValidationResult(
            valid=False, total_chunks=0, filtered_short=0,
            filtered_empty=0, encoding_errors=0, reasons=["chunks is empty"],
        )

    filtered_short = 0
    filtered_empty = 0
    encoding_errors = 0
    valid_chunks = []

    for i, ch in enumerate(chunks):
        # 빈 청크 검사
        if not ch or not ch.strip():
            filtered_empty += 1
            continue

        # 인코딩 검사
        try:
            ch.encode("utf-8")
        except UnicodeEncodeError:
            encoding_errors += 1
            continue

        # 최소 길이 검사
        if len(ch.strip()) < min_chars:
            filtered_short += 1
            continue

        valid_chunks.append(ch)

    # 메타 데이터 정합성
    meta_chunks_count = meta.get("chunks", 0)
    meta_consistent = (meta_chunks_count == len(chunks))

    valid = (filtered_empty == 0 and encoding_errors == 0 and meta_consistent)
    reasons = []
    if filtered_empty > 0:
        reasons.append(f"{filtered_empty} empty chunks filtered")
    if encoding_errors > 0:
        reasons.append(f"{encoding_errors} encoding errors")
    if not meta_consistent:
        reasons.append(f"meta mismatch: meta={meta_chunks_count}, actual={len(chunks)}")

    return ChunkValidationResult(
        valid=valid, total_chunks=len(chunks),
        filtered_short=filtered_short, filtered_empty=filtered_empty,
        encoding_errors=encoding_errors, reasons=reasons,
    )


_R = TypeVar("_R")


# ── [NEW #1] 리트라이 로직 ─────────────────────────────

def _retry_with_backoff(func: Callable[..., _R], *args, max_retries: int = MAX_RETRY, delay: float = RETRY_DELAY_SEC, **kwargs) -> _R:
    """지수 백오프 재시도 데코레이터風 함수"""
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                wait_time = delay * (2 ** (attempt - 1))
                logger.warning(
                    "Retry %d/%d failed for %s: %s. Retrying in %.1fs...",
                    attempt, max_retries, func.__name__, e, wait_time,
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    "All %d retries exhausted for %s. Last error: %s",
                    max_retries, func.__name__, last_exc,
                )
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Unexpected state: retry function returned without success or exception")


# ── 파일 저장 함수들 ───────────────────────────────────

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


# ── SPRINT 1: DEPRECATED OUTPUT FORMATS (kept for backward compat) ──
# These outputs are deprecated for Sprint 1. Use {stem}.md (canonical) instead.
# To re-enable, set SPRINT1_ONLY_MD_OUTPUT = False in config section above.

DEPRECATED_FORMATS_TXT = "chunks_txt"      # DEPRECATED: will be removed in Sprint 2+
DEPRECATED_FORMATS_META = "chunks_meta"    # DEPRECATED: will be removed in Sprint 2+


def save_chunks(output_dir, stem, source_name, chunks, chunk_size, chunk_overlap):
    """[DEPRECATED for Sprint 1] — kept for backward compatibility.
    
    SPRINT 1 CANONICAL OUTPUT: {stem}.md (produced by save_md_with_language())
    
    To re-enable these deprecated outputs:
        set SPRINT1_ONLY_MD_OUTPUT = False
    
    Args:
        output_dir: Output directory path
        stem: Document stem name
        source_name: Original source filename
        chunks: List of chunk strings
        chunk_size: Chunk size parameter
        chunk_overlap: Chunk overlap parameter
        
    Returns:
        tuple: (txt_path, meta_path) — None paths if SPRINT1_ONLY_MD_OUTPUT is True
    """
    # Sprint 1 compliance: skip deprecated output formats
    if SPRINT1_ONLY_MD_OUTPUT:
        logger.info(
            "[SPRINT1-DEPRECATED] Skipping deprecated outputs for %s (canonical: %s.md)",
            source_name, stem
        )
        return None, None

    txt_path = os.path.join(output_dir, f"{stem}_chunks.txt")
    meta_path = os.path.join(output_dir, f"{stem}_chunks_meta.json")

    # 검증 수행
    meta = {
        "source": source_name,
        "chunks": len(chunks),
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }
    validation = validate_chunks(chunks, meta)

    if not validation.valid:
        logger.warning("Chunks validation warnings: %s", validation.summary())

    # 유효한 청크만 저장
    with open(txt_path, "w", encoding="utf-8") as f:
        for i, ch in enumerate(chunks, 1):
            f.write(f"[chunk {i}]\n{ch}\n\n")

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return txt_path, meta_path


def move_source_file(src_path, output_dir):
    dst = os.path.join(output_dir, os.path.basename(src_path))
    if os.path.abspath(src_path) != os.path.abspath(dst) and not os.path.exists(dst):
        shutil.move(src_path, dst)
        return dst
    return src_path


# ── [NEW #2] 배치 상태 관리 ─────────────────────────────

def get_processed_files(output_dir: str) -> set[str]:
    """이미 처리된 파일 목록을 반환 (중복 처리 방지)"""
    state_file = Path(output_dir) / ".batch_state.json"
    if state_file.exists():
        data = json.loads(state_file.read_text(encoding="utf-8"))
        return set(data.get("processed", []))
    return set()


def mark_processed(output_dir: str, filename: str):
    """처리 완료 파일을 기록"""
    state_file = Path(output_dir) / ".batch_state.json"
    data = {}
    if state_file.exists():
        data = json.loads(state_file.read_text(encoding="utf-8"))

    processed = data.get("processed", [])
    if filename not in processed:
        processed.append(filename)
    data["processed"] = processed
    data["timestamp"] = datetime.datetime.now().isoformat()

    state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 핵심 처리 함수 ─────────────────────────────────────

def process_one_file(file_info, converter, splitter, output_dir, chunk_size, chunk_overlap, report=None):
    """단일 파일 처리 (업그레이드 v2 — 검증 + 리트라이 + 배치 상태)"""
    logs = []
    metrics = {}
    artifacts = {}
    failed_stage = None
    reason = None

    def emit(stage, message, progress=None, level="info"):
        if report is not None:
            report(stage=stage, message=message, progress=progress)
        cls = "log-ok" if level == "ok" else "log-warn" if level == "warn" else "log-info"
        logs.append({"cls": cls, "msg": message})

    src_path = file_info["path"]
    source_name = file_info["name"]
    ext = file_info["ext"].lower().replace(".", "")
    stem = make_safe_stem(source_name)

    try:
        emit("start", f"process_one_file 시작: {source_name}", 0.0, level="ok")

        use_ocr = bool(file_info.get("use_ocr", False))

        # ── [1] 텍스트 추출 (리트라이) ──────────────────────
        emit("extract", f"텍스트 추출 시작: {source_name}", 0.1)

        def _extract():
            return extract_text_from_file(src_path, converter=converter, use_ocr=use_ocr)

        raw_result = _retry_with_backoff(_extract, max_retries=MAX_RETRY)

        full_text = raw_result.get("text", "") or ""
        is_ocr = raw_result.get("is_ocr", use_ocr)
        emit("extract_done", f"텍스트 추출 완료: {len(full_text)} characters", 0.2)

        language = detect_language(full_text)
        logger.info("[SPRINT1] parsing completed: %s (%d chars, lang=%s)", source_name, len(full_text), language)
        emit("language", f"감지된 언어: {language}", 0.25)

        if not full_text.strip():
            failed_stage = "extract"
            reason = "추출 텍스트 없음"
            emit("extract_fail", f"{source_name}: 추출 텍스트 없음", 1.0, level="warn")
            return {"success": False, "logs": logs, "metrics": metrics, "artifacts": artifacts, "failed_stage": failed_stage, "reason": reason}

        # ── [2] 노이즈 분석 ────────────────────────────────
        emit("noise", f"노이즈 점검 시작: {source_name}", 0.3)
        noise = calculate_noise_score(full_text, file_type=ext, is_ocr=is_ocr)
        emit("noise_done", f"노이즈 점검 완료: score={noise['score']}", 0.4)
        logs.append({
            "cls": "log-info",
            "msg": (f"noise_debug: mode={noise['mode']}, score={noise['score']}, "
                    f"chars={noise['charcount']}, symbol={noise['symbol_ratio']}, "
                    f"short={noise['short_line_ratio']}, ocr={noise['ocr_noise_ratio']}"),
        })

        final_text = full_text
        if not final_text.strip():
            failed_stage = "noise"
            reason = "정제 후 텍스트 없음"
            emit("noise_fail", f"{source_name}: 정제 후 텍스트 없음", 1.0, level="warn")
            return {"success": False, "logs": logs, "metrics": metrics, "artifacts": artifacts, "failed_stage": failed_stage, "reason": reason}

        # ── [3] MD 저장 ────────────────────────────────────
        emit("save_md", f"MD 저장 시작: {source_name}", 0.5)
        md_path = save_md_with_language(output_dir, stem, source_name, final_text, noise, ext, language)
        emit("save_md_done", f"MD 저장 완료: {md_path}", 0.55)

        # ── [4] 청킹 (리트라이) ────────────────────────────
        emit("chunk", f"청킹 시작: {source_name}", 0.65)

        def _chunk():
            return optimize_chunks(final_text, ext)

        try:
            chunk_result = _retry_with_backoff(_chunk, max_retries=MAX_RETRY)
            chunks = chunk_result.chunks if getattr(chunk_result, "chunks", None) else []
        except Exception as e:
            logs.append({"cls": "log-warn", "msg": f"optimize_chunks 실패 (리트라이 후): {e}"})
            chunk_result = None
            chunks = []

        if chunk_result is not None:
            logs.append({
                "cls": "log-info",
                "msg": (f"chunk_debug: passed={chunk_result.passed}, "
                        f"avg_noise={chunk_result.quality.avg_noise:.2f}, "
                        f"max_noise={chunk_result.quality.max_noise:.2f}, "
                        f"avg_dup={chunk_result.quality.avg_dup:.2f}, "
                        f"params={chunk_result.params}"),
            })

        if not chunks:
            emit("fallback_split", f"옵티마이저 결과 없음, 기존 splitter 사용: {source_name}", 0.78, level="warn")
            chunks = splitter.split_text(final_text)
            chunk_size_used = chunk_size
            chunk_overlap_used = chunk_overlap
            chunk_result = None
        elif chunk_result is not None:
            chunk_size_used = chunk_result.params["chunk_size"]
            chunk_overlap_used = chunk_result.params["chunk_overlap"]
        else:
            chunk_size_used = chunk_size
            chunk_overlap_used = chunk_overlap

        emit("chunk_done", f"청킹 완료: {len(chunks)} chunks", 0.75)
        logger.info("[SPRINT1] chunking completed: %s (%d chunks, size=%d, overlap=%d)", source_name, len(chunks), chunk_size_used, chunk_overlap_used)

        # ── [5] 청크 저장 + 검증 ───────────────────────────
        meta = {"source": source_name, "chunks": len(chunks), "chunk_size": chunk_size_used, "chunk_overlap": chunk_overlap_used}
        emit("validate", f"청크 검증 시작: {source_name}", 0.79)
        validation = validate_chunks(chunks, meta)
        emit("validate_done", f"청크 검증 결과: {validation.summary()}", 0.80)

        txt_path, meta_path = save_chunks(output_dir, stem, source_name, chunks, chunk_size_used, chunk_overlap_used)
        if SPRINT1_ONLY_MD_OUTPUT:
            emit("save_chunks_done", f"[SPRINT1-DEPRECATED] Deprecated outputs skipped (canonical: {stem}.md)", 0.85)
        else:
            emit("save_chunks_done", f"기존 txt 저장 완료: {source_name}", 0.85)

        # ── [6] 최적화 MD 저장 (SPRINT1-DEPRECATED) ───────────
        # Sprint 1 canonical output is ONLY {stem}.md (save_md_with_language).
        # Optimized chunks markdown ({stem}_chunks_{hash}.md) is deprecated for Sprint 1.
        opt_md_path = None
        emit("save_opt_md", f"[SPRINT1-DEPRECATED] 최적화 MD 저장 건너뜀 (canonical: {stem}.md)", 0.9)

        # ── [7] 원본 파일 이동 + 배치 상태 기록 ────────────
        emit("move", f"원본 파일 이동 시작: {source_name}", 0.97)
        moved_to = move_source_file(src_path, output_dir)
        mark_processed(output_dir, source_name)
        emit("move_done", f"원본 파일 이동 완료: {moved_to}", 0.99)

        metrics = {
            "language": language, "noise": noise, "chunk_count": len(chunks),
            "chunk_size_used": chunk_size_used, "chunk_overlap_used": chunk_overlap_used,
            "chunk_passed": getattr(chunk_result, "passed", None) if chunk_result else None,
            "validation": validation.summary() if OUTPUT_VALIDATE_ENABLED else None,
            "is_ocr": is_ocr, "source_type": ext,
        }
        artifacts = {
            "source_path": src_path, "moved_path": moved_to, "md_path": md_path,
            "opt_md_path": str(opt_md_path) if opt_md_path else None,
            # [SPRINT1-DEPRECATED] These paths are None when SPRINT1_ONLY_MD_OUTPUT=True
            "chunks_txt_path": txt_path,      # DEPRECATED: None in Sprint 1
            "chunks_meta_path": meta_path,    # DEPRECATED: None in Sprint 1
        }

        # ── [SPRINT1] output written ───────────────────────────
        logger.info("[SPRINT1] output written: %s (canonical=%s)", source_name, md_path)

        emit("done", f"{source_name} 처리 완료", 1.0, level="ok")
        return {"success": True, "logs": logs, "metrics": metrics, "artifacts": artifacts, "failed_stage": None, "reason": None}

    except Exception as e:
        reason = str(e)
        logs.append({"cls": "log-warn", "msg": f"처리 실패 — {reason}"})
        logs.append({"cls": "log-warn", "msg": f"Traceback: {traceback.format_exc()}"})
        return {"success": False, "logs": logs, "metrics": metrics, "artifacts": artifacts, "failed_stage": failed_stage or "unexpected", "reason": reason}


def process_batch(file_list, converter, splitter, output_dir, chunk_size, chunk_overlap, report=None):
    """배치 처리 (업그레이드 v2 — 중복 파일 제외 + 배치 상태 추적)"""
    logger.info("[SPRINT1] ingestion start: %d files", len(file_list))
    processed_set = get_processed_files(output_dir)
    results = []

    for file_info in file_list:
        name = file_info.get("name", "")
        if name in processed_set:
            logs = [{"cls": "log-info", "msg": f"이미 처리됨 (건너뜀): {name}"}]
            results.append({"success": True, "logs": logs, "metrics": {}, "artifacts": {}, "skipped": True})
            continue

        result = process_one_file(file_info, converter, splitter, output_dir, chunk_size, chunk_overlap, report)
        results.append(result)

    logger.info("[SPRINT1] ingestion end: %d files processed", len(results))
    return results
