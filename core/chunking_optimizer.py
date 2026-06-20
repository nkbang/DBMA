# core/chunking_optimizer.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json
import re

from langchain_text_splitters import RecursiveCharacterTextSplitter


# ─── 프리셋: 문서 유형별 기본 파라미터 ──────────────────────────────────────
PRESETS: dict[str, dict] = {
    "pdf":     {"chunk_size": 800,  "chunk_overlap": 100},
    "txt":     {"chunk_size": 1000, "chunk_overlap": 120},
    "md":      {"chunk_size": 1200, "chunk_overlap": 150},
    "docx":    {"chunk_size": 1000, "chunk_overlap": 120},
    "epub":    {"chunk_size": 1000, "chunk_overlap": 120},
    "html":    {"chunk_size": 1000, "chunk_overlap": 120},
    "htm":     {"chunk_size": 1000, "chunk_overlap": 120},
    "rtf":     {"chunk_size": 1000, "chunk_overlap": 100},
    "default": {"chunk_size": 1200, "chunk_overlap": 200},
}

# ─── 그리드 서치 후보 ──────────────────────────────────────────────────────
GRID_SIZES    = [500, 800, 1000, 1200, 1500]
GRID_OVERLAPS = [50, 100, 150, 200]

# ─── 품질 임계값 ──────────────────────────────────────────────────────────
NOISE_THRESHOLD  = 18.0   # Cleaner Engine 기준
MAX_DUP_RATIO    = 0.30   # 인접 청크 Jaccard 중복 상한
MIN_CHUNK_CHARS  = 80     # 너무 짧은 청크 제외


# ─── 데이터 클래스 ────────────────────────────────────────────────────────
@dataclass
class ChunkQuality:
    noise_scores: list[float] = field(default_factory=list)
    dup_ratios:   list[float] = field(default_factory=list)

    @property
    def avg_noise(self) -> float:
        return sum(self.noise_scores) / len(self.noise_scores) if self.noise_scores else 0.0

    @property
    def max_noise(self) -> float:
        return max(self.noise_scores) if self.noise_scores else 0.0

    @property
    def avg_dup(self) -> float:
        return sum(self.dup_ratios) / len(self.dup_ratios) if self.dup_ratios else 0.0

    @property
    def passed(self) -> bool:
        return self.max_noise <= NOISE_THRESHOLD and self.avg_dup <= MAX_DUP_RATIO


@dataclass
class ChunkResult:
    chunks:  list[str]
    params:  dict
    quality: ChunkQuality

    @property
    def passed(self) -> bool:
        return self.quality.passed

    @property
    def params_hash(self) -> str:
        return hashlib.md5(
            json.dumps(self.params, sort_keys=True).encode()
        ).hexdigest()[:8]

    def to_markdown(self, source_name: str) -> str:
        lines = [
            "---",
            f"source: {source_name}",
            f"chunk_size: {self.params['chunk_size']}",
            f"chunk_overlap: {self.params['chunk_overlap']}",
            f"num_chunks: {len(self.chunks)}",
            f"avg_noise: {self.quality.avg_noise:.1f}",
            f"avg_dup: {self.quality.avg_dup:.2f}",
            f"passed: {self.passed}",
            "---",
            "",
        ]
        for i, ch in enumerate(self.chunks, 1):
            ns = self.quality.noise_scores[i-1] if i-1 < len(self.quality.noise_scores) else 0
            dr = self.quality.dup_ratios[i-1]   if i-1 < len(self.quality.dup_ratios)   else 0
            lines.append(f"## Chunk {i}  _(noise={ns:.1f}, dup={dr:.2f})_")
            lines.append(ch)
            lines.append("")
        return "\n".join(lines)


# ─── 내부 유틸 ────────────────────────────────────────────────────────────
def _separators() -> list[str]:
    """한국어 + 일반 문장 구분자 우선순위"""
    return ["\n\n", "\n", "다.\n", "요.\n", "다. ", "요. ",
            ". ", "! ", "? ", " ", ""]


def _simple_noise(chunk: str) -> float:
    """
    간단 휴리스틱 노이즈 점수 (0~100).
    기존 calculate_noise_score() 결과가 있으면 그것을 우선 사용.
    여기서는 특수문자·짧은 줄·URL 비율로 근사.
    """
    if not chunk:
        return 100.0
    lines = chunk.splitlines()
    if not lines:
        return 100.0
    short   = sum(1 for l in lines if len(l.strip()) < 10) / len(lines)
    special = len(re.findall(r"[^\w\s가-힣]", chunk)) / max(len(chunk), 1)
    urls    = len(re.findall(r"https?://\S+", chunk)) * 5
    score   = (short * 30 + special * 50 + urls)
    return min(round(score, 1), 100.0)


def _dup_ratio(prev: str, curr: str) -> float:
    if not prev:
        return 0.0
    a, b = set(prev.split()), set(curr.split())
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _evaluate(chunks: list[str]) -> ChunkQuality:
    noise = [_simple_noise(c) for c in chunks]
    dups  = [0.0] + [_dup_ratio(chunks[i-1], chunks[i]) for i in range(1, len(chunks))]
    return ChunkQuality(noise_scores=noise, dup_ratios=dups)


def _split(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=_separators(),
        length_function=len,
    )
    return [c for c in splitter.split_text(text) if len(c) >= MIN_CHUNK_CHARS]


# ─── 공개 API ─────────────────────────────────────────────────────────────
def chunk_once(text: str, chunk_size: int, chunk_overlap: int) -> ChunkResult:
    """단일 파라미터 조합으로 청킹 + 품질 평가"""
    params  = {"chunk_size": chunk_size, "chunk_overlap": chunk_overlap}
    chunks  = _split(text, chunk_size, chunk_overlap)
    quality = _evaluate(chunks)
    return ChunkResult(chunks=chunks, params=params, quality=quality)


def optimize_chunks(text: str, doc_type: str) -> ChunkResult:
    """
    1) 문서 유형 프리셋 시도
    2) 실패 시 그리드 서치 → 품질 기준 통과 + 최소 노이즈 조합 반환
    3) 전부 실패해도 최선 결과 반환 (never raise)
    """
    ext    = doc_type.lower().lstrip(".")
    preset = PRESETS.get(ext, PRESETS["default"])
    result = chunk_once(text, preset["chunk_size"], preset["chunk_overlap"])
    if result.passed:
        return result

    best: ChunkResult | None = None
    for cs in GRID_SIZES:
        for co in GRID_OVERLAPS:
            if co >= cs:          # overlap ≥ size 는 의미 없음
                continue
            r = chunk_once(text, cs, co)
            if not r.passed:
                continue
            if best is None or (r.quality.avg_noise, r.quality.avg_dup) < \
                               (best.quality.avg_noise, best.quality.avg_dup):
                best = r
    return best if best else result  # 전부 실패 → 프리셋 결과라도 반환


def save_optimized_md(
    result:      ChunkResult,
    source_name: str,
    output_dir:  Path,
    stem:        str,
) -> Path:
    """
    {stem}_chunks_{params_hash}.md 로 저장.
    기존 {stem}_chunks.txt 와 병존 가능 (덮어쓰지 않음).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{stem}_chunks_{result.params_hash}.md"
    md_path.write_text(result.to_markdown(source_name), encoding="utf-8")
    return md_path