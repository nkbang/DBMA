#!/usr/bin/env python
"""registry의 doc_type을 guess_doc_type()으로 채우거나(기본) 재분류한다(--reclassify).

core/processing.py의 정상 배선(Task Order 018)이 커버하지 못하는, 이미
등록된 과거 문서 전용 — dry-run 기본, --apply로만 실제 반영.

두 가지 모드:
  기본            doc_type이 None인 레코드만 채운다. 기존 값은 절대 건드리지 않는다.
  --reclassify    값이 이미 있어도 다시 분류해 달라진 것만 갱신한다.

--reclassify가 필요한 이유 (2026-09-15):
  doc_type은 처리 시점에 계산돼 registry에 저장되고,
  identity_registry.register_document()는 이미 등록된 document_id를 만나면
  기존 레코드를 그대로 반환한다(:131) — 재처리해도 갱신되지 않는다.
  기본 모드는 None만 채우므로 "기타"로 확정된 레코드도 건드리지 않는다.
  따라서 분류 규칙(_DOC_TYPE_KEYWORDS)이 개선돼도 기존 문서를 따라가게 할
  경로가 없었다. 실제 사례: 설교 유형에 영어 키워드를 추가했으나
  (docs/DBMA_DOCTYPE_SERMON_KEYWORDS_REPORT_001.md) 이미 "기타"로 등록된
  스펄전 설교집 3건이 그대로 남았다.

  --reclassify는 기존 값을 덮어쓰므로 기본값이 아니다. 사람이 손으로 지정한
  doc_type이 있을 수 있고(ui/pages/sermon_review.py가 이 필드로 후보를 거른다)
  registry에는 그 값이 기계 판정인지 수동 지정인지 구분할 정보가 없다.
  반드시 dry-run으로 변경 목록을 먼저 확인할 것.

사용법:
    python scripts/backfill_doc_type.py <registry_path> <output_dir>
    python scripts/backfill_doc_type.py <registry_path> <output_dir> --apply
    python scripts/backfill_doc_type.py <registry_path> <output_dir> --reclassify
    python scripts/backfill_doc_type.py <registry_path> <output_dir> --reclassify --apply
"""

import argparse
import shutil
import datetime
from pathlib import Path

from core.identity_registry import load_identity_registry, save_identity_registry
from core.document_identity import guess_doc_type


def backfill(
    registry_path: str, output_dir: str, apply: bool, reclassify: bool = False
) -> None:
    """registry의 doc_type을 채우거나(기본) 재분류한다(reclassify=True).

    Args:
        registry_path: documents.json 전체 경로
        output_dir: MD 파일이 있는 output 디렉터리
        apply: True이면 실제 저장, False이면 dry-run (목록만 출력)
        reclassify: True이면 기존 값이 있어도 재분류해 달라진 것만 갱신한다
    """
    registry = load_identity_registry(registry_path)
    changed = []
    skipped_no_md = []

    for doc_id, record in registry["documents"].items():
        # [never invent 원칙] 이미 값이 있으면 건드리지 않음.
        # --reclassify는 이 보호를 명시적으로 해제한다(기본 아님).
        if record.get("doc_type") is not None and not reclassify:
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
        before = record.get("doc_type")
        # 재분류 모드에서 결과가 같으면 변경이 아니다 — 목록을 실제 변경만으로 유지한다.
        if reclassify and before == doc_type:
            continue
        changed.append((doc_id, source_file, before, doc_type))
        if apply:
            record["doc_type"] = doc_type

    mode = "재분류(--reclassify)" if reclassify else "None 채우기"
    print(f"모드: {mode}")
    print(f"변경 대상: {len(changed)}건, md 파일 없어 건너뜀: {len(skipped_no_md)}건")
    for doc_id, source_file, before, doc_type in changed:
        print(f"  {doc_id[:12]}... {source_file} : {before} -> {doc_type}")

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
    parser.add_argument(
        "--reclassify",
        action="store_true",
        help="기존 doc_type 값이 있어도 재분류해 달라진 것만 갱신 (기본은 None만 채움)",
    )
    args = parser.parse_args()
    backfill(args.registry_path, args.output_dir, args.apply, args.reclassify)