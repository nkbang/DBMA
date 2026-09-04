"""One-time backfill for 48 of the 49 documents lost to the registry race
condition fixed in core/identity_registry.py::registry_lock() (2026-08-23).

These files already have {stem}.md output and are marked "processed" in
.batch_state.json — mark_processed() ran fine, only the identity_registry
write was clobbered by the background reconciler thread. Rather than
hand-construct registry records with guessed metadata (chunk_count,
language, noise_score, etc. — normally computed during real processing),
this re-runs them through the exact same, now-race-fixed process_batch()
pipeline with force_reingest=True (batch_state/file-list gates bypassed;
classify_ingest_decision() naturally returns PROCESS since no registry
record exists yet). Slightly wasteful (re-extracts/re-chunks unchanged
content) but reuses the tested pipeline instead of writing a second,
less-trustworthy registration path.

The 49th orphaned batch_state entry, "로마서 8장 연구 - 성령의 자유 (내
자료).md", is excluded — the actual RAW file is named "로마서 8장 연구 -
성령의 자유.md" (no "(내 자료)" suffix), a separate filename-mismatch
issue unrelated to the registry race. Needs manual attention.

Usage:
    python3 scripts/backfill_49_orphaned_registrations.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_TSU_DATASET_PATH
from core.processing import build_converter, build_splitter, process_batch
from core.index_orchestrator import reconcile_pending

ORPHANED_FILENAMES = [
    "5. 요한복음1clearscan_cropped.pdf",
    "6. 요한복음2clearscan_cropped.pdf",
    "9. 로마서1clearscan_cropped.pdf",
    "10. 로마서2clearscan_cropped.pdf",
    "11. 고린도전서.pdf",
    "13. 갈라디아서,데살로니가전후서clearscan_cropped.pdf",
    "14. 옥중서신(에베소서, 빌립보서, 골로새서, 빌레몬서).pdf",
    "15. 목회서신(디모데전,후서 디도서).pdf",
    "16. 히브리서.pdf",
    "17. 공동서신(야고보서, 베드로전,후서, 요한일이삼서, 유다서).pdf",
    "18. 요한계시록.pdf",
    "2. 마태복음2clearscan_cropped.pdf",
    "2025년 설교 모음.rtf",
    "2025년 설교 모음.txt",
    "2026-02-11 참 자유한 성도의 본분-1.rtf",
    "3. 마가복음.pdf",
    "5 SOLAS시리즈01 [토머스슈라이너] 오직 믿음 2.pdf.pdf",
    "5 SOLAS시리즈01 [토머스슈라이너] 오직 믿음.pdf.pdf",
    "5 SOLAS시리즈02 [데이비드반드루넨] 오직 하나님의 영광 2.pdf.pdf",
    "5 SOLAS시리즈02 [데이비드반드루넨] 오직 하나님의 영광.pdf.pdf",
    "5 SOLAS시리즈03 [매튜바렛] 오직 하나님의 말씀 2.pdf.pdf",
    "5 SOLAS시리즈03 [매튜바렛] 오직 하나님의 말씀.pdf.pdf",
    "5 SOLAS시리즈04 [스티븐웰럼] 오직 그리스도 2.pdf.pdf",
    "5 SOLAS시리즈04 [스티븐웰럼] 오직 그리스도.pdf.pdf",
    "5 SOLAS시리즈05 [칼트루먼] 오직 은혜 2.pdf.pdf",
    "5 SOLAS시리즈05 [칼트루먼] 오직 은혜.pdf.pdf",
    "5. 요한복음1.pdf",
    "6. 요한복음2.pdf",
    "7. 사도행전1 복사본.pdf",
    "7. 사도행전1.pdf",
    "8. 사도행전2 복사본.pdf",
    "8. 사도행전2.pdf",
    "9. 로마서1.pdf",
    "개혁교의학개요.pdf",
    "개혁교회의 성령론과 오순절교회의 성령론.pdf",
    "개혁파 조직신학(1)-신학 서론과 계시론 - Joel R. Beeke and Paul M. Smalley.pdf",
    "개혁파 조직신학(2)-신론 -  Joel R. Beeke and Paul M. Smalley.pdf",
    "개혁파 조직신학(3)-인간론 -  Joel R. Beeke and Paul M. Smalley.pdf",
    "개혁파 조직신학(4) 기독론 -  Joel R. Beeke and Paul M. Smalley.pdf",
    "결핍은 충만을 확인시킨다.rtf",
    "사랑하는 성도 여러분, 오늘 우리는 족보를 통해 하나님의 구원 계획을 함께 살펴.rtf",
    "어떠한 사람이 되어야 마땅하냐? 베드로후서 3:11-13.rtf",
    "이방인_선교의_관점에서_본_사도행전의_주요_주제들.pdf",
    "주간 묵상가이드.rtf",
    "토착화의 관점에서 바라본 존 네비우스 선교방법의 재평가.pdf",
    "하나님 나라 중심의 선교신학 연구.PDF",
    "하나님의  형상 이해에 기초한 성화 연구.pdf",
    "함께 가는 길.rtf",
]


def main() -> None:
    raw_dir = Path(DEFAULT_RAW_DIR)
    file_list = []
    missing_on_disk = []
    for name in ORPHANED_FILENAMES:
        f = raw_dir / name
        if not f.is_file():
            missing_on_disk.append(name)
            continue
        file_list.append({
            "path": str(f),
            "name": name,
            "ext": f.suffix.lower().lstrip("."),
            "use_ocr": False,
        })

    print(f"대상: {len(ORPHANED_FILENAMES)}개, RAW에 실제 존재: {len(file_list)}개")
    if missing_on_disk:
        print(f"RAW에서 못 찾음 (건너뜀): {missing_on_disk}")

    converter = build_converter(use_ocr=False)
    splitter = build_splitter(chunk_size=1000, chunk_overlap=200)

    def report(stage, message, progress=None):
        print(f"  [{stage}] {message}")

    results = process_batch(
        file_list=file_list,
        converter=converter,
        splitter=splitter,
        output_dir=DEFAULT_OUTPUT_DIR,
        chunk_size=1000,
        chunk_overlap=200,
        report=report,
        force_reingest=True,
    )

    success = sum(1 for r in results if r.get("success"))
    failed = [r for r in results if not r.get("success")]
    print(f"\n재처리 결과: {success}/{len(file_list)} 성공, {len(failed)} 실패")
    for r in failed:
        for log in r.get("logs", []):
            print("  FAIL:", log.get("msg"))

    print("\nreconcile_pending() 실행 (PROCESSED -> INDEXED)...")
    reconcile_result = reconcile_pending(DEFAULT_OUTPUT_DIR)
    print(f"  reconciled={reconcile_result['reconciled']} failed={len(reconcile_result['failed'])} purged={reconcile_result['purged']}")
    for f in reconcile_result["failed"]:
        print("  RECONCILE_FAIL:", f)

    # Verify against TSU dataset
    tsu_sources = set()
    tsu_path = Path(DEFAULT_TSU_DATASET_PATH)
    with open(tsu_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            sf = rec.get("source_file")
            if sf:
                tsu_sources.add(sf)

    still_missing = [n for n in ORPHANED_FILENAMES if n not in tsu_sources]
    print(f"\n검증: {len(ORPHANED_FILENAMES) - len(still_missing)}/{len(ORPHANED_FILENAMES)}개가 이제 TSU에 존재")
    if still_missing:
        print("여전히 누락:", still_missing)


if __name__ == "__main__":
    main()
