"""scripts/ingest_nae_source.py — NAE Baptist 자료 인제스트.

docs/tasks/reports/NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md(Option B)의
구현 — scripts/ingest_logos_export.py와 동일한 패턴을 재사용한다:
DocumentContext/core/processing.py/register_document()의 고정 스키마는
전혀 수정하지 않고, register_document() 반환 후 registry dict를 직접
update()하여 NAE 전용 필드를 additive로 기록한다.

책임 범위:

    NAE source manifest.json (서지·신학 메타데이터, 사람이 직접 작성)
        ↓
    이 스크립트: 추출 → 청킹 → registry 등록 + nae_* 필드 additive 기록
        ↓
    core/tsu_builder.py::build_tsu_records() (registry를 읽어
    record["nae_metadata"] 블록 구성 — STEP4-D에서 별도 추가)

manifest.json 형식 (필수 키: source_filename, title, copyright_status,
content_genre — 하나라도 없으면 그 항목은 건너뛰고 사유를 기록한다):

    [
      {
        "source_filename": "nhc_1833.txt",
        "title": "The New Hampshire Confession of Faith (1833)",
        "author": "New Hampshire Baptist Convention",
        "resource_type": "confession",
        "language": "en",
        "copyright_status": "public_domain",
        "content_genre": ["confession"],
        "theological_position": "historical_baptist",
        "denomination_context": "..."
      }
    ]

사용례:
    python -m scripts.ingest_nae_source --manifest data/nae/metadata/pilot_manifest.json
    python -m scripts.ingest_nae_source --manifest ... --dry-run
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

from core.config import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, registry_path_for
from core.document_identity import build_document_metadata
from core.identity_registry import (
    load_identity_registry,
    register_document,
    save_identity_registry,
)
from core.processing import build_splitter, detect_language, save_chunks
from core.utils import make_safe_stem

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ingest_nae_source")

# [NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md] data/nae/ 구조는 STEP1/STEP2에서
# 이미 생성됨 — core/config.py에 신규 DEFAULT_NAE_* 상수를 추가하지 않고
# 이 스크립트 내부 기본값으로만 한정한다(STEP4-D 승인 범위: 신규 스크립트
# + core/tsu_builder.py 2개 파일).
DEFAULT_NAE_INBOX_DIR = os.path.join("data", "nae", "sources")
DEFAULT_NAE_OUTPUT_DIR = os.path.join("data", "nae", "processed")

_REQUIRED_MANIFEST_FIELDS = ("source_filename", "title", "copyright_status", "content_genre")

# NAE 자료는 텍스트/PDF 위주로 가정(STEP4_PIPELINE_DRYRUN.md) — Logos
# 스크립트가 HTML/RTF 전용이었던 것과 달리, 여기서는 순수 텍스트만 우선
# 지원한다. PDF는 이번 최소 구현 범위 밖(추가 확장 시 core/extractors.py
# 재사용 예정).
def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8")
    raise ValueError(f"이번 최소 구현에서 지원하지 않는 확장자: {suffix} ({path.name}) — txt/md만 지원")


def _validate_entry(entry: dict[str, Any]) -> Optional[str]:
    """필수 서지 필드 검증. 문제 없으면 None, 있으면 건너뛴 사유 문자열."""
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

    source_filename = entry["source_filename"]
    src_path = inbox_dir / source_filename
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

    stem = make_safe_stem(source_filename)

    metadata = build_document_metadata(
        content=text,
        source_file=source_filename,
        language=language,
        source_type=entry.get("resource_type", "nae_source"),
        chunk_count=len(chunks),
        title=entry.get("title"),
        author=entry.get("author"),
        doc_type="nae_source",
    )

    if dry_run:
        logger.info(
            "[dry-run] %s → document_id=%s chunks=%d lang=%s",
            source_filename, metadata["document_id"], len(chunks), language,
        )
        return metadata["document_id"], None

    save_chunks(str(output_dir), stem, source_filename, chunks, chunk_size, chunk_overlap)

    record, is_new = register_document(registry, metadata, str(output_dir))
    document_id = record["document_id"]

    # [NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md] Additive-only, Logos 스크립트와
    # 동일 원칙 — register_document()의 고정 스키마는 이 필드들을 모른다.
    # core/tsu_builder.py는 doc.get("nae_theological_position") 등으로 이
    # 필드가 있을 때만 nae_metadata 블록을 채우므로, register_document()를
    # 수정하는 것보다 여기서 반환된 dict를 직접 갱신하는 것이 안전하다
    # (기존 코퍼스의 레코드 스키마를 건드리지 않음).
    registry["documents"][document_id].update({
        "nae_theological_position": entry.get("theological_position"),
        "nae_denomination_context": entry.get("denomination_context"),
        "nae_content_genre": entry.get("content_genre", []),
        "nae_copyright_status": entry["copyright_status"],
    })

    logger.info(
        "[ingest] %s%s → document_id=%s chunks=%d genre=%s",
        source_filename, "" if is_new else " (기존 문서 갱신)",
        document_id, len(chunks), entry.get("content_genre"),
    )
    return document_id, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", required=True, help="NAE 소스 manifest JSON 경로")
    parser.add_argument("--inbox-dir", default=DEFAULT_NAE_INBOX_DIR, help="NAE 원본 폴더")
    parser.add_argument("--output-dir", default=DEFAULT_NAE_OUTPUT_DIR, help="청크/등록 출력 폴더")
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
            skipped.append({"source_filename": entry.get("source_filename", "?"), "reason": reason})
            logger.warning("[skip] %s: %s", entry.get("source_filename", "?"), reason)
        elif document_id is not None:
            ingested += 1

    if not args.dry_run and ingested > 0:
        save_identity_registry(registry, registry_path)

    logger.info(
        "[ingest] done: ingested=%d skipped=%d registry=%s%s",
        ingested, len(skipped), registry_path, " (dry-run, 저장 안 함)" if args.dry_run else "",
    )
    if skipped:
        skipped_path = output_dir / "nae_ingest_skipped.jsonl"
        if not args.dry_run:
            with open(skipped_path, "w", encoding="utf-8") as f:
                for s in skipped:
                    f.write(json.dumps(s, ensure_ascii=False) + "\n")
            logger.info("[ingest] 건너뛴 항목 기록: %s", skipped_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
