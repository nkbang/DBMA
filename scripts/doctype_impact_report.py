#!/usr/bin/env python
"""scripts/doctype_impact_report.py — 사이드카 메타데이터 적용 시 doc_type 변경 영향 목록.

C1 Review 1차 조건 C3(`docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_001.md`)
"재처리 전 doc_type 변경 영향 문서 목록 산출 + HQ 승인"을 위한 산출 도구.

배경:
  core/document_identity.py::guess_doc_type(content, source_file, title)가
  title을 입력으로 받는다. 사이드카가 title을 채우면(현재 None) 분류 결과가
  바뀔 수 있다 — 재처리 전에 어떤 문서가 바뀌는지 먼저 알아야 한다.

동작 (읽기 전용):
  registry의 각 문서에 대해 guess_doc_type()을 두 조건으로 돌려 비교한다.
    (1) 현재 title (대개 None)
    (2) 사이드카 후보 title
  registry / 코퍼스 / TSU / 색인 / 코드 어느 것도 변경하지 않는다.

후보 title 탐색 순서:
  a. `<RAW파일경로>.meta.json` 의 "title"  — 사이드카가 이미 있으면 그것을 쓴다
  b. --docinfo-map 으로 준 {source_file: PDF경로} 매핑의 PDF docinfo
  둘 다 없으면 그 문서는 "후보 없음"으로 보고되고 변경 대상에서 제외된다.

Usage:
    python scripts/doctype_impact_report.py
    python scripts/doctype_impact_report.py --docinfo-map map.json --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RAW_DIR,
    registry_path_for,
)
from core.document_identity import guess_doc_type  # noqa: E402
from core.extractors import _extract_pdf_title_author  # noqa: E402
from core.identity_registry import load_identity_registry  # noqa: E402


def _processed_text(output_dir: Path, source_file: str) -> str:
    """처리 단계가 저장한 정규화 본문(.md)을 읽는다.

    guess_doc_type()은 본문 앞 2000자만 보므로 전체를 읽을 필요는 없지만,
    파일이 작아 그대로 읽는다. 없으면 빈 문자열 — 분류는 파일명/title만으로 수행된다.
    """
    stem = f"{Path(source_file).stem}_{Path(source_file).suffix.lstrip('.')}"
    md = output_dir / f"{stem}.md"
    if not md.exists():
        return ""
    return md.read_text(encoding="utf-8", errors="replace")


def _candidate_title(source_file: str, docinfo_map: dict[str, str]) -> tuple[str | None, str]:
    """사이드카 후보 title과 그 출처를 돌려준다. (title, 출처설명)"""
    sidecar = Path(DEFAULT_RAW_DIR) / f"{source_file}.meta.json"
    if sidecar.exists():
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            title = (data.get("title") or "").strip() or None
            if title:
                return title, f"sidecar:{sidecar.name}"
        except Exception as e:  # 손상된 사이드카가 분석 전체를 막지 않게 한다
            print(f"[warn] 사이드카 파싱 실패 {sidecar}: {e}", file=sys.stderr)

    pdf = docinfo_map.get(source_file)
    if pdf and Path(pdf).exists():
        title, _author = _extract_pdf_title_author(pdf)
        if title:
            return title, f"pdf_docinfo:{Path(pdf).parent.name}"

    return None, "후보 없음"


def _classify_with_keywords(
    keywords: dict, content: str, source_file: str, title: str | None
) -> str:
    """제안 키워드 표로 분류한다. 모듈 전역 표를 임시 교체 후 반드시 복원한다.

    guess_doc_type()을 그대로 재사용해야 매칭 규칙(haystack 구성, 정의 순서
    우선, 무매칭 시 "기타")이 프로덕션과 어긋나지 않는다 — 규칙을 복제하면
    분석과 실제가 갈라진다.
    """
    import core.document_identity as di

    original = di._DOC_TYPE_KEYWORDS
    try:
        di._DOC_TYPE_KEYWORDS = keywords
        return di.guess_doc_type(content, source_file, title)
    finally:
        di._DOC_TYPE_KEYWORDS = original


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--docinfo-map",
        help='{"source_file": "원본PDF경로"} 형태의 JSON — 사이드카가 아직 없을 때 후보 출처',
    )
    ap.add_argument(
        "--keywords-json",
        help="제안 _DOC_TYPE_KEYWORDS 를 담은 JSON — 키워드 표 변경의 재분류 영향을 함께 계산한다",
    )
    ap.add_argument("--json", help="결과를 이 경로에 JSON으로 저장")
    args = ap.parse_args()

    docinfo_map: dict[str, str] = {}
    if args.docinfo_map:
        docinfo_map = json.loads(Path(args.docinfo_map).read_text(encoding="utf-8"))

    proposed_keywords: dict | None = None
    if args.keywords_json:
        proposed_keywords = json.loads(Path(args.keywords_json).read_text(encoding="utf-8"))

    output_dir = Path(DEFAULT_OUTPUT_DIR)
    registry = load_identity_registry(registry_path_for(DEFAULT_OUTPUT_DIR))
    documents = registry.get("documents", {})

    rows: list[dict] = []
    for doc in documents.values():
        source_file = doc.get("source_file", "")
        content = _processed_text(output_dir, source_file)
        current = doc.get("doc_type")

        # registry에 저장된 값과 지금 재계산한 값이 다르면 그 자체가 신호다
        # (분류기 변경 또는 registry 오염) — 변경 영향과 구분해 보고한다.
        recomputed = guess_doc_type(content, source_file, doc.get("title"))
        cand_title, origin = _candidate_title(source_file, docinfo_map)
        after = guess_doc_type(content, source_file, cand_title)

        # 키워드 표 변경 영향 — 제안 표를 적용해 같은 입력을 다시 분류한다.
        # 원본 표는 복원하므로 프로세스 내 다른 호출에 영향을 주지 않는다.
        after_kw = None
        if proposed_keywords is not None:
            after_kw = _classify_with_keywords(
                proposed_keywords, content, source_file, cand_title
            )

        rows.append(
            {
                "source_file": source_file,
                "current_doc_type": current,
                "recomputed_now": recomputed,
                "candidate_title": cand_title,
                "candidate_origin": origin,
                "doc_type_after": after,
                "doc_type_after_keywords": after_kw,
                "will_change": after != current,
                "will_change_keywords": (after_kw is not None and after_kw != current),
                "registry_drift": recomputed != current,
            }
        )

    changed = [r for r in rows if r["will_change"]]
    changed_kw = [r for r in rows if r.get("will_change_keywords")]
    drifted = [r for r in rows if r["registry_drift"]]

    print("=" * 78)
    print("doc_type 변경 영향 목록 — 사이드카 메타데이터 적용 시 (읽기 전용 분석)")
    print("=" * 78)
    print(f"등록 문서 {len(rows)}건 · 변경 예상 {len(changed)}건 · registry 불일치 {len(drifted)}건\n")

    for r in rows:
        mark = "CHANGE" if r["will_change"] else " 유지 "
        print(f"[{mark}] {r['source_file']}")
        print(f"         doc_type  {r['current_doc_type']} → {r['doc_type_after']}")
        print(f"         후보 title ({r['candidate_origin']}): {str(r['candidate_title'])[:80]}")
        if r.get("doc_type_after_keywords") is not None:
            kwmark = "CHANGE" if r["will_change_keywords"] else "유지"
            print(f"         제안 키워드표 적용: {r['current_doc_type']} → {r['doc_type_after_keywords']}  [{kwmark}]")
        if r["registry_drift"]:
            print(
                f"         ※ registry 값과 재계산 불일치: "
                f"{r['current_doc_type']} vs {r['recomputed_now']}"
            )
        print()

    if proposed_keywords is not None:
        print(f"[키워드 표 변경] 재분류 예상 {len(changed_kw)}건 / {len(rows)}건")
        for r in changed_kw:
            print(f"    {r['source_file']}: {r['current_doc_type']} → {r['doc_type_after_keywords']}")
        print()

    if not changed:
        print("→ title 변경 영향: 없음. 재처리해도 doc_type은 현행대로 유지된다.")
    else:
        print(f"→ {len(changed)}건이 바뀐다. HQ 승인 전 재처리하지 말 것.")

    if args.json:
        Path(args.json).write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nJSON 저장: {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
