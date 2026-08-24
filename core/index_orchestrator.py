"""core/index_orchestrator.py — UI-callable wrapper around the TSU batch pipeline.

SPRINT20-I: dbma.py::build_rag_store()의 UI 재색인 워크플로우
("문서 선택 → 즉시 재색인")를 공식 검색 경로(core/retrieval.py::RetrievalEngine,
TSU + TF-IDF 기반)로 대체하기 위한 오케스트레이터.

core/tsu_builder.py의 배치 로직(build_tsu_records/write_tsu_dataset/
write_manifest)을 그대로 재사용한다 — 새 파싱/스코어링 로직을 만들지 않고,
이미 검증된 배치 파이프라인을 함수 호출로 감싸기만 한다. Embedding은 쿼리
시점 core/embedder.py::EmbeddingCache가 지연 계산하므로 이 오케스트레이터는
embedding을 생성하지 않는다(TSU 레코드 생성 + 데이터셋/매니페스트 기록까지만).
"""

import json
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.config import (
    DEFAULT_BIBLE_INDEX_PATH,
    DEFAULT_CANDIDATE_INDEX_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RAW_DIR,
    DEFAULT_TSU_DATASET_PATH,
    DEFAULT_TSU_MANIFEST_PATH,
    SUPPORTED_EXTENSIONS,
    registry_path_for,
)
from core.identity_registry import (
    load_identity_registry,
    save_identity_registry,
    registry_lock,
    exclude_document,
    unexclude_document,
    find_by_source_file,
)
from core.document_context import set_pipeline_state
from core.tsu_builder import build_tsu_records, write_tsu_dataset, write_manifest
from core.utils import make_safe_stem
from core.candidate_generator import build_index, open_or_build_index
from core.bible_index import BibleIndex
from core.bible_index import build_index as build_bible_index

BACKUP_ROOT = Path("backups")


def rebuild_tsu_index(output_dir: str = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Identity registry 전체를 읽어 TSU 데이터셋/매니페스트를 재생성한다.

    scripts/build_tsu_dataset.py::main()과 동일한 동작을 함수 호출로
    제공한다(CLI 인자 파싱 없이 UI/스크립트에서 직접 호출 가능하도록).

    Returns:
        {"documents": int, "records": int, "dataset_path": str, "manifest_path": str}
    """
    out_dir = Path(output_dir)
    registry_path = Path(registry_path_for(output_dir))
    dataset_path = Path(DEFAULT_TSU_DATASET_PATH)
    manifest_path = Path(DEFAULT_TSU_MANIFEST_PATH)
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"

    registry = load_identity_registry(str(registry_path))
    records = build_tsu_records(registry, out_dir)
    write_tsu_dataset(records, dataset_path)
    write_manifest(
        records, registry, manifest_path,
        registry_path=registry_path,
        dataset_path=dataset_path,
        config_path=config_path,
    )

    # [DBMA-SEARCH-INFRA-001 Phase2-4] Rebuild the Tantivy candidate index
    # from the dataset file we just wrote, so it never drifts out of sync
    # with the TSU dataset it mirrors.
    candidate_index_dir = Path(DEFAULT_CANDIDATE_INDEX_DIR)
    indexed_count = build_index(dataset_path, candidate_index_dir)

    # [DBMA-SEARCH-INFRA-001 Phase2-3] Same for the Bible reference posting
    # index — independent storage, rebuilt from the same dataset file.
    bible_index_path = Path(DEFAULT_BIBLE_INDEX_PATH)
    bible_postings = build_bible_index(dataset_path, bible_index_path)

    source_document_count = len({
        doc_id for doc_id, doc in registry.get("documents", {}).items()
        if doc.get("chunk_count", 0) > 0
    })
    return {
        "documents": source_document_count,
        "records": len(records),
        "dataset_path": str(dataset_path),
        "manifest_path": str(manifest_path),
        "candidate_index_dir": str(candidate_index_dir),
        "candidate_index_documents": indexed_count,
        "bible_index_path": str(bible_index_path),
        "bible_index_postings": bible_postings,
    }


def reindex_document(document_id: str, output_dir: str = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """지정한 document_id의 TSU 레코드만 재생성하고 나머지는 그대로 둔 채
    전체 TSU 데이터셋/매니페스트를 다시 저장한다.

    build_tsu_records(TSU Builder)와 기존 registry를 재사용한다. registry
    구조는 변경하지 않는다. 대상 문서가 registry에 없으면 KeyError.

    Returns:
        {"document_id": str, "replaced": int, "new": int, "records": int,
         "dataset_path": str, "manifest_path": str}
    """
    out_dir = Path(output_dir)
    registry_path = Path(registry_path_for(output_dir))
    dataset_path = Path(DEFAULT_TSU_DATASET_PATH)
    manifest_path = Path(DEFAULT_TSU_MANIFEST_PATH)
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"

    registry = load_identity_registry(str(registry_path))
    if document_id not in registry.get("documents", {}):
        raise KeyError(f"document_id not in registry: {document_id}")

    # 대상 문서 하나만 담은 subset으로 TSU 재생성 (Builder 재사용)
    subset = {"documents": {document_id: registry["documents"][document_id]}}
    new_records = build_tsu_records(subset, out_dir)

    # 기존 데이터셋에서 대상 문서 레코드만 제거, 나머지는 원형 유지
    existing: list[dict[str, Any]] = []
    if dataset_path.exists():
        with open(dataset_path, "r", encoding="utf-8") as f:
            existing = [json.loads(line) for line in f if line.strip()]
    kept = [r for r in existing if r.get("document_id") != document_id]
    replaced = len(existing) - len(kept)

    all_records = kept + new_records
    write_tsu_dataset(all_records, dataset_path)
    write_manifest(
        all_records, registry, manifest_path,
        registry_path=registry_path,
        dataset_path=dataset_path,
        config_path=config_path,
    )

    # [DBMA-SEARCH-INFRA-001 Phase2-4] Mirror the same delete-by-document_id +
    # re-add the candidate index just did to the TSU dataset above — this is
    # the actual "no full re-index on document add" requirement (HQ Phase 2
    # 완료기준): only this one document's rows are touched in the index.
    candidate_index_dir = Path(DEFAULT_CANDIDATE_INDEX_DIR)
    generator = open_or_build_index(dataset_path, candidate_index_dir)
    generator.replace_document(document_id, new_records)

    # [DBMA-SEARCH-INFRA-001 Phase2-3] Same replace semantics for the Bible
    # index — a bootstrap build from the just-written dataset if it doesn't
    # exist yet, otherwise an in-place delete-by-document_id + re-add.
    bible_index_path = Path(DEFAULT_BIBLE_INDEX_PATH)
    if not bible_index_path.exists():
        build_bible_index(dataset_path, bible_index_path)
    else:
        bible_index = BibleIndex(bible_index_path)
        bible_index.replace_document(document_id, new_records)
        bible_index.close()

    return {
        "document_id": document_id,
        "replaced": replaced,
        "new": len(new_records),
        "records": len(all_records),
        "dataset_path": str(dataset_path),
        "manifest_path": str(manifest_path),
        "candidate_index_dir": str(candidate_index_dir),
        "bible_index_path": str(bible_index_path),
    }


def reconcile_pending(output_dir: str = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """[SPRINT21-B Phase2, extended SPRINT21-G-2 Option C] Pull-based
    reconciler — Processing -> TSU 연결 + superseded 문서 정리.

    1. registry에서 pipeline_state == "PROCESSED"(TSU 미반영)인 문서만 찾아
       reindex_document()로 한 건씩 색인하고, 성공 시 pipeline_state를
       PROCESSED -> TSU_READY -> INDEXED로 전진시킨다. 이미 TSU_READY/INDEXED인
       문서는 건드리지 않으므로(idempotent) 반복 호출해도 안전 — event/queue
       없이 매 호출 시점의 registry 스냅샷만 보고 필요한 것만 처리한다
       (Preflight §3 "Command/Pull 기반" 설계).
    2. superseded_by가 설정된 문서(SPRINT21-G-2 Option C — 같은 source_file을
       내용만 바꿔 재처리한 결과 남은 옛 버전)의 TSU 레코드를 데이터셋에서
       제거한다. reindex_document()를 재사용하지 않는다 — 옛 문서의 {stem}.md는
       이미 새 버전 내용으로 덮어써져 있어(같은 source_file), 그걸로 다시 빌드하면
       옛 document_id에 새 내용이 잘못 매핑된다. 대신 document_id로 필터링만
       한다(재빌드 없음, 순수 삭제). 이미 제거된 문서는 0건이라 idempotent.

    ingest_status는 건드리지 않는다. tsu_builder.py/retrieval.py/
    embedder.py는 호출만 하며 내부 로직은 변경하지 않는다.

    Returns:
        {"pending": int, "reconciled": int, "failed": [...], "purged": int}
    """
    registry_path = Path(registry_path_for(output_dir))

    # [RACE-FIX 2026-08-23] This function's load->mutate->save runs on a
    # background timer (core/background_index_builder.py) while
    # core/processing.py::process_one_file() does its own independent
    # load->mutate->save on the same registry file during foreground batch
    # processing. Without coordination, whichever side saves last silently
    # discards the other's in-memory-only additions (confirmed: 49
    # freshly-registered documents vanished this way in one batch run —
    # no exception, no log line, since neither individual save call
    # fails). registry_lock() (see core/identity_registry.py) makes the
    # two critical sections mutually exclusive.
    with registry_lock(str(registry_path)):
        registry = load_identity_registry(str(registry_path))

        pending = [
            doc_id for doc_id, doc in registry.get("documents", {}).items()
            if doc.get("pipeline_state") == "PROCESSED"
        ]

        reconciled: list[str] = []
        failed: list[dict[str, str]] = []
        for doc_id in pending:
            try:
                reindex_document(doc_id, output_dir=output_dir)
            except Exception as e:
                failed.append({"document_id": doc_id, "error": str(e)})
                continue
            # TSU record build + dataset/manifest write both completed inside
            # reindex_document() above — TSU_READY and INDEXED happen together
            # in this implementation (no partial/observable midpoint), so only
            # the final state is persisted.
            set_pipeline_state(registry["documents"][doc_id], "INDEXED")
            reconciled.append(doc_id)

        # [SPRINT21-G-2 Option C] Purge superseded documents' TSU records so
        # edited-then-reprocessed content stops being searchable under its old
        # document_id, without disturbing anything else in the dataset.
        superseded_ids = {
            doc_id for doc_id, doc in registry.get("documents", {}).items()
            if doc.get("superseded_by") is not None
        }
        purged = 0
        if superseded_ids:
            dataset_path = Path(DEFAULT_TSU_DATASET_PATH)
            if dataset_path.exists():
                with open(dataset_path, "r", encoding="utf-8") as f:
                    existing = [json.loads(line) for line in f if line.strip()]
                kept = [r for r in existing if r.get("document_id") not in superseded_ids]
                purged = len(existing) - len(kept)
                if purged > 0:
                    write_tsu_dataset(kept, dataset_path)
                    manifest_path = Path(DEFAULT_TSU_MANIFEST_PATH)
                    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
                    write_manifest(
                        kept, registry, manifest_path,
                        registry_path=registry_path,
                        dataset_path=dataset_path,
                        config_path=config_path,
                    )
                    # [DBMA-SEARCH-INFRA-001 Phase2-4] Mirror the purge to the
                    # candidate index — otherwise superseded content stays
                    # searchable there even though the TSU dataset dropped it.
                    candidate_index_dir = Path(DEFAULT_CANDIDATE_INDEX_DIR)
                    if (candidate_index_dir / "meta.json").exists():
                        generator = open_or_build_index(dataset_path, candidate_index_dir)
                        for doc_id in superseded_ids:
                            generator.delete_document(doc_id)
                    # [DBMA-SEARCH-INFRA-001 Phase2-3] Same purge, mirrored to
                    # the Bible index.
                    bible_index_path = Path(DEFAULT_BIBLE_INDEX_PATH)
                    if bible_index_path.exists():
                        bible_index = BibleIndex(bible_index_path)
                        for doc_id in superseded_ids:
                            bible_index.delete_document(doc_id)
                        bible_index.close()

        if reconciled:
            save_identity_registry(registry, str(registry_path))

    return {"pending": len(pending), "reconciled": len(reconciled), "failed": failed, "purged": purged}


def exclude_document_from_index(
    document_id: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    execute: bool = False,
) -> dict[str, Any]:
    """제외(exclude) 처리된 문서의 파생 산출물을 정리한다.

    RAW 원본은 건드리지 않는다. 두 가지만 수행:
    1. TSU 데이터셋에서 해당 document_id 레코드 제거(reindex_document()의
       필터 패턴 재사용, 재빌드 없이 순수 삭제) — RetrievalEngine이 TSU
       데이터셋을 직접 로드하므로 이것만으로 검색 대상에서 제외된다.
    2. {stem}_chunks.txt / {stem}.md를 scripts/cleanup_legacy_outputs.py와
       동일한 패턴(backups/excluded_documents/{YYYYMMDD}/로 이동)으로 정리.

    execute=False(기본)면 dry-run — 무엇이 지워지고 이동될지만 계산해
    반환하고 파일/데이터셋은 건드리지 않는다.

    registry의 ingest_status 변경은 하지 않는다 — 그건
    core/identity_registry.py::exclude_document()의 책임이다.

    Returns:
        {"document_id", "purged_tsu_records", "moved_files", "backup_dir", "executed"}
    """
    registry_path = Path(registry_path_for(output_dir))
    registry = load_identity_registry(str(registry_path))
    record = registry.get("documents", {}).get(document_id)
    if record is None:
        raise KeyError(f"document_id not in registry: {document_id}")

    dataset_path = Path(DEFAULT_TSU_DATASET_PATH)
    purged = 0
    if dataset_path.exists():
        with open(dataset_path, "r", encoding="utf-8") as f:
            existing = [json.loads(line) for line in f if line.strip()]
        kept = [r for r in existing if r.get("document_id") != document_id]
        purged = len(existing) - len(kept)
        if purged > 0 and execute:
            write_tsu_dataset(kept, dataset_path)
            manifest_path = Path(DEFAULT_TSU_MANIFEST_PATH)
            config_path = Path(__file__).resolve().parent.parent / "config.yaml"
            write_manifest(
                kept, registry, manifest_path,
                registry_path=registry_path,
                dataset_path=dataset_path,
                config_path=config_path,
            )
            # [DBMA-SEARCH-INFRA-001 Phase2-4] Same purge, mirrored to the
            # candidate index so an excluded document stops being searchable
            # there too.
            candidate_index_dir = Path(DEFAULT_CANDIDATE_INDEX_DIR)
            if (candidate_index_dir / "meta.json").exists():
                generator = open_or_build_index(dataset_path, candidate_index_dir)
                generator.delete_document(document_id)
            # [DBMA-SEARCH-INFRA-001 Phase2-3] Same purge, mirrored to the
            # Bible index.
            bible_index_path = Path(DEFAULT_BIBLE_INDEX_PATH)
            if bible_index_path.exists():
                bible_index = BibleIndex(bible_index_path)
                bible_index.delete_document(document_id)
                bible_index.close()

    stem = make_safe_stem(record.get("source_file", ""))
    out_dir = Path(output_dir)
    candidates = [out_dir / f"{stem}_chunks.txt", out_dir / f"{stem}.md"]
    existing_files = [f for f in candidates if f.exists()]

    timestamp = datetime.now().strftime("%Y%m%d")
    backup_dir = BACKUP_ROOT / f"excluded_documents_{timestamp}"
    moved: list[str] = []
    if execute:
        for f in existing_files:
            backup_dir.mkdir(parents=True, exist_ok=True)
            dest = backup_dir / f.name
            shutil.move(str(f), str(dest))
            moved.append(str(dest))

    return {
        "document_id": document_id,
        "purged_tsu_records": purged,
        "moved_files": moved if execute else [str(f) for f in existing_files],
        "backup_dir": str(backup_dir),
        "executed": execute,
    }


def delete_raw_source(
    source_filename: str,
    raw_dir: str = DEFAULT_RAW_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    reason: str = "",
    execute: bool = False,
) -> dict[str, Any]:
    """[2026-08-24] 사용자가 더 이상 필요 없는 RAW 원본을 휴지통으로
    옮긴다 — "원본 절대 삭제 안 함"(Sprint 2 정책, core/processing.py
    참고)을 os.remove()가 아닌 이동으로 지키면서도, 사용자가 요청한
    "진짜 제거"(목록/검색에서 완전히 빠짐)를 만족시킨다.

    이미 처리된 문서라면 먼저 exclude_document()(registry 상태) +
    exclude_document_from_index()(TSU/청크 정리)를 그대로 재사용해
    검색 대상에서 뺀 뒤, RAW 파일 자체를 backups/deleted_raw_{날짜}/로
    이동한다. 아직 처리 전인 raw 파일은 정리할 색인이 없으므로 파일
    이동만 한다.

    RAW 안의 파일명을 찾을 때 rglob()으로 하위 폴더까지 재귀 탐색하고
    NFC로 정규화해 대조한다 — 2026-08-24 processing.py 하위 폴더 스캔
    수정, 2026-08-23 find_by_source_file() 정규화 수정과 동일 기준.

    execute=False(기본)면 dry-run — 무엇이 지워지고 이동될지만 계산해
    반환하고 registry/파일은 건드리지 않는다.

    Returns:
        {"found": bool, "document_id": str|None, "purged_tsu_records": int,
         "moved_index_files": [...], "raw_path": str|None,
         "trash_path": str|None, "executed": bool}
    """
    target_nfc = unicodedata.normalize("NFC", source_filename)
    raw_root = Path(raw_dir)
    raw_path: Optional[Path] = None
    if raw_root.exists():
        for f in raw_root.rglob("*"):
            if (
                f.is_file()
                and not f.name.startswith(".")
                and f.suffix.lower() in SUPPORTED_EXTENSIONS
                and unicodedata.normalize("NFC", f.name) == target_nfc
            ):
                raw_path = f
                break

    if raw_path is None:
        return {
            "found": False, "document_id": None, "purged_tsu_records": 0,
            "moved_index_files": [], "raw_path": None, "trash_path": None,
            "executed": execute,
        }

    registry_path = registry_path_for(output_dir)
    purged_tsu_records = 0
    moved_index_files: list[str] = []
    document_id: Optional[str] = None

    with registry_lock(registry_path):
        registry = load_identity_registry(registry_path)
        record = find_by_source_file(registry, source_filename)
        if record is not None:
            document_id = record["document_id"]
            if execute:
                cleanup = exclude_document_from_index(document_id, output_dir=output_dir, execute=True)
                purged_tsu_records = cleanup["purged_tsu_records"]
                moved_index_files = cleanup["moved_files"]
                exclude_document(registry, document_id, reason=reason or "RAW 원본 삭제(휴지통 이동)")
                save_identity_registry(registry, registry_path)
            else:
                # dry-run: 실제로 삭제될 TSU 레코드 수만 미리 계산 —
                # exclude_document_from_index(execute=False)는 파일은
                # 건드리지 않고 개수만 센다.
                cleanup = exclude_document_from_index(document_id, output_dir=output_dir, execute=False)
                purged_tsu_records = cleanup["purged_tsu_records"]
                moved_index_files = cleanup["moved_files"]

    trash_path: Optional[Path] = None
    if execute:
        timestamp = datetime.now().strftime("%Y%m%d")
        trash_dir = BACKUP_ROOT / f"deleted_raw_{timestamp}"
        trash_dir.mkdir(parents=True, exist_ok=True)
        dest = trash_dir / raw_path.name
        counter = 2
        while dest.exists():
            dest = trash_dir / f"{raw_path.stem}_{counter}{raw_path.suffix}"
            counter += 1
        shutil.move(str(raw_path), str(dest))
        trash_path = dest

    return {
        "found": True,
        "document_id": document_id,
        "purged_tsu_records": purged_tsu_records,
        "moved_index_files": moved_index_files,
        "raw_path": str(raw_path),
        "trash_path": str(trash_path) if trash_path else None,
        "executed": execute,
    }


def list_trashed_raw_files() -> list[dict[str, Any]]:
    """[2026-08-24] delete_raw_source()가 backups/deleted_raw_{날짜}/로
    옮긴 파일 목록. "휴지통이라면 복구도 가능해야 한다"는 사용자 요청 —
    복구 UI가 무엇을 되돌릴 수 있는지 보여주는 목록.

    Returns: 최근 삭제 순으로 정렬된
        [{"trash_path", "name", "deleted_at"(YYYY-MM-DD)}, ...]
    """
    if not BACKUP_ROOT.exists():
        return []

    items: list[dict[str, Any]] = []
    for sub in BACKUP_ROOT.glob("deleted_raw_*"):
        if not sub.is_dir():
            continue
        date_str = sub.name.removeprefix("deleted_raw_")
        deleted_at = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}" if len(date_str) == 8 else date_str
        for f in sub.iterdir():
            if f.is_file():
                items.append({"trash_path": str(f), "name": f.name, "deleted_at": deleted_at})

    items.sort(key=lambda x: x["deleted_at"], reverse=True)
    return items


def restore_raw_source(
    trash_path: str,
    raw_dir: str = DEFAULT_RAW_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """[2026-08-24] delete_raw_source()가 휴지통으로 옮긴 파일을 RAW로
    되돌린다. 삭제 당시 registry 레코드가 EXCLUDED로 바뀐 문서였다면
    unexclude_document()로 상태를 되돌리되(기존 "제외 해제" UI와 동일
    패턴), 검색 색인(TSU)은 삭제 시 이미 정리됐으므로 재처리(재색인)해야
    다시 검색된다는 점은 그대로 안내해야 한다 — 이 함수는 파일/registry
    상태만 되돌리고 색인은 재생성하지 않는다.

    Returns: {"restored": bool, "raw_path": str|None, "document_id": str|None,
              "reason": str|None}
    """
    src = Path(trash_path)
    if not src.is_file():
        return {"restored": False, "raw_path": None, "document_id": None, "reason": "휴지통에서 파일을 찾을 수 없습니다."}

    raw_root = Path(raw_dir)
    raw_root.mkdir(parents=True, exist_ok=True)
    dest = raw_root / src.name
    counter = 2
    while dest.exists():
        dest = raw_root / f"{src.stem} ({counter}){src.suffix}"
        counter += 1
    shutil.move(str(src), str(dest))

    registry_path = registry_path_for(output_dir)
    document_id: Optional[str] = None
    with registry_lock(registry_path):
        registry = load_identity_registry(registry_path)
        record = find_by_source_file(registry, dest.name)
        if record is not None and record.get("ingest_status") == "EXCLUDED":
            document_id = record["document_id"]
            unexclude_document(registry, document_id)
            save_identity_registry(registry, registry_path)

    return {"restored": True, "raw_path": str(dest), "document_id": document_id, "reason": None}
