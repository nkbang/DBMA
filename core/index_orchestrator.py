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
from pathlib import Path
from typing import Any, Optional

from core.config import DEFAULT_OUTPUT_DIR, DEFAULT_TSU_DATASET_PATH, DEFAULT_TSU_MANIFEST_PATH, registry_path_for
from core.identity_registry import load_identity_registry, save_identity_registry
from core.document_context import set_pipeline_state
from core.tsu_builder import build_tsu_records, write_tsu_dataset, write_manifest


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

    source_document_count = len({
        doc_id for doc_id, doc in registry.get("documents", {}).items()
        if doc.get("chunk_count", 0) > 0
    })
    return {
        "documents": source_document_count,
        "records": len(records),
        "dataset_path": str(dataset_path),
        "manifest_path": str(manifest_path),
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
    return {
        "document_id": document_id,
        "replaced": replaced,
        "new": len(new_records),
        "records": len(all_records),
        "dataset_path": str(dataset_path),
        "manifest_path": str(manifest_path),
    }


def reconcile_pending(output_dir: str = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """[SPRINT21-B Phase2] Pull-based reconciler — Processing -> TSU 연결.

    registry에서 pipeline_state == "PROCESSED"(TSU 미반영)인 문서만 찾아
    reindex_document()로 한 건씩 색인하고, 성공 시 pipeline_state를
    PROCESSED -> TSU_READY -> INDEXED로 전진시킨다. 이미 TSU_READY/INDEXED인
    문서는 건드리지 않으므로(idempotent) 반복 호출해도 안전 — event/queue
    없이 매 호출 시점의 registry 스냅샷만 보고 필요한 것만 처리한다
    (Preflight §3 "Command/Pull 기반" 설계).

    ingest_status는 건드리지 않는다. tsu_builder.py/retrieval.py/
    embedder.py는 호출만 하며 내부 로직은 변경하지 않는다.

    Returns:
        {"pending": int, "reconciled": int, "failed": [{"document_id","error"}]}
    """
    registry_path = Path(registry_path_for(output_dir))
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

    if reconciled:
        save_identity_registry(registry, str(registry_path))

    return {"pending": len(pending), "reconciled": len(reconciled), "failed": failed}
