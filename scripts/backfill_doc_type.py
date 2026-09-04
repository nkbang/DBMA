#!/usr/bin/env python
"""registry의 doc_type=None 레코드에 guess_doc_type()으로 값을 채운다.

core/processing.py의 정상 배선(Task Order 018)이 커버하지 못하는, 이미
등록된 과거 문서 전용 — dry-run 기본, --apply로만 실제 반영.

사용법:
    python scripts/backfill_doc_type.py <registry_path> <output_dir>
    python scripts/backfill_doc_type.py <registry_path> <output_dir> --apply
"""

import argparse
import shutil
import datetime
from pathlib import Path

from core.identity_registry import load_identity_registry, save_identity_registry
from core.document_identity import guess_doc_type


def backfill(registry_path: str, output_dir: str, apply: bool) -> None:
    """registry의 doc_type=None 레코드에 guess_doc_type()으로 값을 채운다.

    Args:
        registry_path: documents.json 전체 경로
        output_dir: MD 파일이 있는 output 디렉터리
        apply: True이면 실제 저장, False이면 dry-run (목록만 출력)
    """
    registry = load_identity_registry(registry_path)
    changed = []
    skipped_no_md = []

    for doc_id, record in registry["documents"].items():
        # [never invent 원칙] 이미 값이 있으면 건드리지 않음
        if record.get("doc_type") is not None:
            continue

        source_file = record.get("source_file", "")
        # [ADR-008/기존 관례] {output_dir}/{stem}_{ext}.md 명명 규칙
        # source_file이 'file.pdf'일 때: stem='file', ext='pdf' → 'file_pdf.md'
        # source_file이 'file.pdf.pdf'일 때: stem='file.pdf', ext='pdf' → 'file.pdf_pdf.md'
        stem = Path(source_file).stem
        ext = Path(source_file).suffix.lstrip(".")
        md_path = Path(output_dir) / f"{stem}_{ext}.md"

        # fallback: {stem}.{ext} 형태도 시도 (예: 'file_pdf.md' 대신 'file.pdf.md')
        if not md_path.exists():
            alt_ext = Path(source_file).suffix.lstrip(".")
            alt_stem = Path(source_file).name.rsplit(".", 1)[0] if "." in Path(source_file).name else Path(source_file).stem
            md_path = Path(output_dir) / f"{alt_stem}.{alt_ext}.md"

        if not md_path.exists():
            skipped_no_md.append(doc_id)
            continue  # [never invent] 원문 없이 추측하지 않음

        content = md_path.read_text(encoding="utf-8")
        doc_type = guess_doc_type(content, source_file, record.get("title"))
        changed.append((doc_id, source_file, doc_type))
        if apply:
            record["doc_type"] = doc_type

    print(f"변경 대상: {len(changed)}건, md 파일 없어 건너뜀: {len(skipped_no_md)}건")
    for doc_id, source_file, doc_type in changed:
        print(f"  {doc_id[:12]}... {source_file} -> {doc_type}")

    if apply and changed:
        # 백업 먼저
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bak_path = f"{registry_path}.{timestamp}.bak"
        shutil.copy2(registry_path, bak_path)
        save_identity_registry(registry, registry_path)
        print(f"registry 저장 완료: {registry_path}")
        print(f"백업: {bak_path}")
    elif not apply:
        print("(dry-run — 실제 반영하려면 --apply)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="registry의 doc_type=None 레코드에 guess_doc_type()으로 값을 채움"
    )
    parser.add_argument("registry_path", help="documents.json 전체 경로")
    parser.add_argument("output_dir", help="MD 파일이 있는 output 디렉터리")
    parser.add_argument("--apply", action="store_true", help="실제 반영 (미사용 시 dry-run)")
    args = parser.parse_args()
    backfill(args.registry_path, args.output_dir, args.apply)