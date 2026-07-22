"""scripts/ingest_logos_export.py — Logos Print/Export 자료 인제스트.

docs/LOCAL_MODEL_SERMON_ALGORITHM_DESIGN.md §9(외부 신학 자료 Logos 소스
확보 전략)의 나머지 구현 항목 — registry에 source_tier/logos_location/
rights/export_method/content_hash/review_status를 실제로 채워 넣는 경로.

책임 범위 (설계 문서 §9.2 흐름 중 이 스크립트가 담당하는 구간):

    Logos Print/Export (HTML/RTF) — inbox/logos_export/
        ↓
    manifest.json (파일별 서지·권리 메타데이터, 사람이 직접 작성)
        ↓
    이 스크립트: 추출 → 청킹 → registry 등록 + provenance 필드 additive 기록
        ↓
    core/tsu_builder.py::build_tsu_records() (registry를 읽어 TSU 생성 —
    수정 불필요, doc.get("source_tier") 등을 이미 additive하게 읽는다)

담당하지 않는 것:
  - Logos에서 Clippings/선택 단락을 실제로 내보내는 작업(사람이 Logos
    앱에서 수행).
  - HTML/RTF 정규화(머리말·각주 제거 등) — 이 스크립트는 core/extractors.py
    의 기존 추출기로 얻은 텍스트를 그대로 청킹한다. 정규화 품질이
    불충분하면 manifest에서 review_status를 "unreviewed"로 남기고, 색인
    이후 core/noise_classifier.py 기반 content_quality로 걸러진다
    (core/tsu_builder.py가 이미 모든 TSU에 대해 수행).
  - RAW 원본 무결성 — 이 스크립트가 다루는 파일은 DEFAULT_RAW_DIR 바깥의
    별도 inbox이므로 scripts/check_raw_only_originals.py 범위 밖이다.

manifest.json 형식 (필수 키: export_filename, title, rights, export_method,
source_tier — 하나라도 없으면 그 항목은 건너뛰고 사유를 기록한다. 원문을
합법적으로 어떤 근거로 가져왔는지 모르는 자료를 색인하지 않기 위한 게이트):

    [
      {
        "export_filename": "2026-07_romans12_moo_clipping.html",
        "title": "The Epistle to the Romans",
        "author": "Douglas J. Moo",
        "resource_type": "commentary",
        "language": "en",
        "logos_location": "Romans 12:1-2, p.748-752",
        "rights": "personal_study_export",
        "export_method": "Logos Print/Export selected text",
        "source_tier": "scholarly_commentary",
        "review_status": "reviewed"
      }
    ]

사용례:
    python scripts/ingest_logos_export.py --manifest data/manifests/logos_manifest.json
    python scripts/ingest_logos_export.py --manifest ... --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_LOGOS_INBOX_DIR,
    DEFAULT_LOGOS_OUTPUT_DIR,
    registry_path_for,
)
from core.document_identity import build_document_metadata
from core.extractors import extract_text_from_html, extract_text_from_rtf
from core.identity_registry import (
    load_identity_registry,
    register_document,
    save_identity_registry,
)
from core.processing import build_splitter, detect_language, save_chunks
from core.utils import make_safe_stem

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ingest_logos_export")

_REQUIRED_MANIFEST_FIELDS = ("export_filename", "title", "rights", "export_method", "source_tier")

# 확장자별 추출기 — Logos 내보내기 형식만 다룬다(설계 문서 §9.2 "HTML 우선,
# RTF 차선" 원칙과 동일 순서로 여기 등록). PDF/DOCX 등 core/processing.py의
# 일반 인제스트가 이미 처리하는 형식은 의도적으로 재사용하지 않는다 — 이
# 스크립트는 Logos 전용 경로다.
_EXTRACTORS = {
    ".html": extract_text_from_html,
    ".htm": extract_text_from_html,
    ".rtf": extract_text_from_rtf,
}


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _EXTRACTORS:
        return _EXTRACTORS[suffix](str(path))
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8")
    raise ValueError(f"지원하지 않는 확장자: {suffix} ({path.name})")


def _validate_entry(entry: dict[str, Any]) -> Optional[str]:
    """필수 서지/권리 필드 검증. 문제 없으면 None, 있으면 건너뛴 사유 문자열."""
    missing = [f for f in _REQUIRED_MANIFEST_FIELDS if not entry.get(f)]
    if missing:
        return f"필수 필드 누락: {', '.join(missing)}"
    return None


def ingest_one(
    entry: dict[str, Any],
    inbox_dir: Path,
    output_dir: Path,
    registry: dict,
    chunk_size: int,
    chunk_overlap: int,
    dry_run: bool,
) -> tuple[Optional[str], Optional[str]]:
    """entry 하나를 처리한다. 반환값: (document_id 또는 None, 실패/건너뜀 사유 또는 None)."""
    reason = _validate_entry(entry)
    if reason is not None:
        return None, reason

    export_filename = entry["export_filename"]
    src_path = inbox_dir / export_filename
    if not src_path.exists():
        return None, f"원본 파일 없음: {src_path}"

    try:
        text = _extract_text(src_path)
    except Exception as e:
        return None, f"추출 실패: {e}"

    if not text.strip():
        return None, "추출된 텍스트가 비어 있음"

    language = entry.get("language") or detect_language(text)
    splitter = build_splitter(chunk_size, chunk_overlap)
    chunks = splitter.split_text(text)
    if not chunks:
        return None, "청킹 결과가 비어 있음"

    stem = make_safe_stem(export_filename)

    metadata = build_document_metadata(
        content=text,
        source_file=export_filename,
        language=language,
        source_type=entry.get("resource_type", "logos_export"),
        chunk_count=len(chunks),
        title=entry.get("title"),
        author=entry.get("author"),
        doc_type="logos_export",
    )

    if dry_run:
        logger.info(
            "[dry-run] %s → document_id=%s chunks=%d lang=%s",
            export_filename, metadata["document_id"], len(chunks), language,
        )
        return metadata["document_id"], None

    save_chunks(str(output_dir), stem, export_filename, chunks, chunk_size, chunk_overlap)

    record, is_new = register_document(registry, metadata, str(output_dir))
    document_id = record["document_id"]

    # [docs/LOCAL_MODEL_SERMON_ALGORITHM_DESIGN.md §9.1] Additive-only —
    # register_document()의 고정 스키마(core/identity_registry.py:109-142)는
    # 이 필드들을 모른다. core/tsu_builder.py는 doc.get("source_tier")로 이
    # 필드가 있을 때만 source_provenance를 채우므로, 여기서 dict를 직접
    # 갱신하는 것이 register_document()를 수정하는 것보다 안전하다(기존
    # 코퍼스의 레코드 스키마를 건드리지 않음).
    registry["documents"][document_id].update({
        "source_tier": entry["source_tier"],
        "logos_location": entry.get("logos_location"),
        "rights": entry["rights"],
        "export_method": entry["export_method"],
        "content_hash": metadata["file_hash"],
        "review_status": entry.get("review_status", "unreviewed"),
    })

    logger.info(
        "[ingest] %s%s → document_id=%s chunks=%d source_tier=%s",
        export_filename, "" if is_new else " (기존 문서 갱신)",
        document_id, len(chunks), entry["source_tier"],
    )
    return document_id, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", required=True, help="Logos 소스 manifest JSON 경로")
    parser.add_argument("--inbox-dir", default=DEFAULT_LOGOS_INBOX_DIR, help="Logos 내보내기 원본 폴더")
    parser.add_argument("--output-dir", default=DEFAULT_LOGOS_OUTPUT_DIR, help="청크/등록 출력 폴더")
    parser.add_argument("--registry-path", default=None, help="registry documents.json 경로 (기본: {output-dir}/registry/documents.json)")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)
    parser.add_argument("--dry-run", action="store_true", help="파일 쓰기/registry 저장 없이 검증만 수행")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        logger.error("[ingest] manifest 파일 없음: %s", manifest_path)
        return 1

    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        logger.error("[ingest] manifest는 JSON 배열이어야 함")
        return 1

    inbox_dir = Path(args.inbox_dir)
    output_dir = Path(args.output_dir)
    registry_path = args.registry_path or registry_path_for(str(output_dir))

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    registry = load_identity_registry(registry_path)

    logger.info("[ingest] started: manifest=%s entries=%d", manifest_path, len(entries))

    ingested = 0
    skipped: list[dict[str, str]] = []

    for entry in entries:
        document_id, reason = ingest_one(
            entry, inbox_dir, output_dir, registry,
            args.chunk_size, args.chunk_overlap, args.dry_run,
        )
        if reason is not None:
            skipped.append({"export_filename": entry.get("export_filename", "?"), "reason": reason})
            logger.warning("[skip] %s: %s", entry.get("export_filename", "?"), reason)
        elif document_id is not None:
            ingested += 1

    if not args.dry_run and ingested > 0:
        save_identity_registry(registry, registry_path)

    logger.info(
        "[ingest] done: ingested=%d skipped=%d registry=%s%s",
        ingested, len(skipped), registry_path, " (dry-run, 저장 안 함)" if args.dry_run else "",
    )
    if skipped:
        skipped_path = output_dir / "logos_ingest_skipped.jsonl"
        if not args.dry_run:
            with open(skipped_path, "w", encoding="utf-8") as f:
                for s in skipped:
                    f.write(json.dumps(s, ensure_ascii=False) + "\n")
            logger.info("[ingest] 건너뛴 항목 기록: %s", skipped_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
