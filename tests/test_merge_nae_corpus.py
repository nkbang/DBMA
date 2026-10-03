"""tests/test_merge_nae_corpus.py — F-3 merge safety contract tests."""

import json
import hashlib
import os
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.merge_nae_corpus import (
    merge_nae_corpus,
    _transform_nae_record,
    _read_existing_dataset,
    _validate_dataset,
)


def _make_naes_record(
    id_: int,
    book: str = "Test Book",
    author: str = "Test Author",
    source_type: str = "nae_canonical",
    copyright_status: str = "public_domain",
    author_id: str = "AUTH_001",
    work_id: str = "WORK_001",
    scriptures: list | None = None,
    claim: str = "Test theological claim.",
    source_text: str = "Test source text content.",
    doctrine: str = "christology",
    confidence: float = 0.95,
    extraction_method: str = "nae_pipeline",
    review_status: str = "verified",
    page: int | None = 42,
) -> dict:
    return {
        "id": id_,
        "book": book,
        "author": author,
        "source_type": source_type,
        "copyright_status": copyright_status,
        "author_id": author_id,
        "work_id": work_id,
        "scriptures": scriptures,
        "claim": claim,
        "source_text": source_text,
        "doctrine": doctrine,
        "confidence": confidence,
        "extraction_method": extraction_method,
        "review_status": review_status,
        "page": page,
    }


def _make_unrelated_record(tsu_id: str, content: str = "unrelated") -> dict:
    return {
        "tsu_id": tsu_id,
        "document_id": f"ext_{tsu_id}",
        "chunk_id": f"ext_{tsu_id}",
        "content": content,
        "verse_mapping": {},
        "themes": [],
        "title": "External",
        "author": "External Author",
        "metadata_source": "external",
        "chapter": None,
        "page": None,
        "source_file": "ext.jsonl",
        "language": "en",
        "source_type": "external",
        "content_quality": {"noise_type": "EXTERNAL", "quality_score": 0.8},
        "structure": {},
        "theological_claim": content,
        "doctrine_category": [],
        "baptist_theme": [],
        "source_provenance": None,
        "nae_metadata": {},
    }


@pytest.fixture()
def tmp_dirs(tmp_path: Path):
    nae_corpus = tmp_path / "nae" / "corpus" / "tsu"
    output_dir = tmp_path / "output"
    tsu_dataset = output_dir / "output" / "bench" / "tsu_dataset.jsonl"
    manifest_path = output_dir / "output" / "bench" / "tsu_manifest.json"
    registry_dir = output_dir / "data" / "제련완성본" / "registry"
    registry_path = registry_dir / "documents.json"
    nae_corpus.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    (output_dir / "output" / "bench").mkdir(parents=True, exist_ok=True)
    registry_dir.mkdir(parents=True)
    registry = {"documents": {}}
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    return {
        "tmp_path": tmp_path,
        "nae_corpus": nae_corpus,
        "output_dir": output_dir,
        "data_root": output_dir,
        "tsu_dataset": tsu_dataset,
        "manifest_path": manifest_path,
        "registry_path": registry_path,
    }


def _make_approved_decisions_dir(tmp_path: Path, source_id: str, tsu_ids: list[str] | None = None) -> Path:
    """approved decisions directory를 생성 — 통합 merge_nae_corpus()의 approval gate 통과용."""
    ddir = tmp_path / "decisions"
    ddir.mkdir(parents=True, exist_ok=True)
    if tsu_ids is None:
        tsu_ids = [f"TSU-{source_id}"]
    decisions = []
    for tid in tsu_ids:
        decisions.append({
            "tsu_id": tid,
            "work_id": source_id,
            "gate_id": f"G-{source_id}",
            "reviewer_id": f"R-{source_id}",
            "answers": {"Q1": "A", "Q2": "A", "Q3": "A"},
            "final_decision": "APPROVED",
            "review_timestamp": "2026-10-01T00:00:00Z",
        })
    file_data = {"decisions": decisions}
    (ddir / f"{source_id}_decisions.json").write_text(
        json.dumps(file_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return ddir


def test_case1_single_source_once(tmp_dirs):
    """CASE 1: 동일 source 1회 처리 — 정상 record count, duplicate 0."""
    doc_dir = tmp_dirs["nae_corpus"] / "TestDoc_A"
    doc_dir.mkdir()
    rec = _make_naes_record(id_=1, book="Book A", author="Author A")
    with open(doc_dir / "tsu.json", "w", encoding="utf-8") as f:
        json.dump([rec], f, ensure_ascii=False)
    result = merge_nae_corpus(
        source_id="WORK_001",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_001", ['NAE-1']),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
    )
    assert result["total_records"] == 1
    assert result["new_records_after_dedup"] == 1
    with open(tmp_dirs["tsu_dataset"], "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) == 1
    assert lines[0]["tsu_id"] == "NAE-1"
    tsu_ids = [r["tsu_id"] for r in lines]
    assert len(tsu_ids) == len(set(tsu_ids))


def test_case2_same_source_twice(tmp_dirs):
    """CASE 2: 동일 source 2회 처리 — record count 증가 없음, duplicate 0."""
    doc_dir = tmp_dirs["nae_corpus"] / "TestDoc_B"
    doc_dir.mkdir()
    rec = _make_naes_record(id_=2, book="Book B", author="Author B")
    with open(doc_dir / "tsu.json", "w", encoding="utf-8") as f:
        json.dump([rec], f, ensure_ascii=False)
    result1 = merge_nae_corpus(
        source_id="WORK_001",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_001", ['NAE-2']),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
    )
    with open(tmp_dirs["tsu_dataset"], "r", encoding="utf-8") as f:
        lines1 = [json.loads(line) for line in f if line.strip()]
    result2 = merge_nae_corpus(
        source_id="WORK_001",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_001", ['NAE-2']),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
    )
    with open(tmp_dirs["tsu_dataset"], "r", encoding="utf-8") as f:
        lines2 = [json.loads(line) for line in f if line.strip()]
    assert result1["total_records"] == 1
    assert result2["total_records"] == 1
    assert len(lines1) == len(lines2) == 1
    tsu_ids = [r["tsu_id"] for r in lines2]
    # NEW-6 fix:实质적인 duplicate assert 추가
    assert len(tsu_ids) == len(set(tsu_ids)), "Duplicate tsu_id found!"


def test_case3_preserve_unrelated(tmp_dirs):
    """CASE 3: 기존 unrelated records가 모두 그대로 존재."""
    tmp_dirs["tsu_dataset"].parent.mkdir(parents=True, exist_ok=True)
    unrelated = [
        _make_unrelated_record("EXT_001", "unrelated content A"),
        _make_unrelated_record("EXT_002", "unrelated content B"),
    ]
    with open(tmp_dirs["tsu_dataset"], "w", encoding="utf-8") as f:
        for rec in unrelated:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    doc_dir = tmp_dirs["nae_corpus"] / "TestDoc_C"
    doc_dir.mkdir()
    rec = _make_naes_record(id_=3, book="Book C", author="Author C")
    with open(doc_dir / "tsu.json", "w", encoding="utf-8") as f:
        json.dump([rec], f, ensure_ascii=False)
    result = merge_nae_corpus(
        source_id="WORK_001",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_001", ['NAE-3']),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
    )
    assert result["existing_records"] == 2
    assert result["total_records"] == 3
    with open(tmp_dirs["tsu_dataset"], "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    ext_ids = {r["tsu_id"] for r in lines}
    assert "EXT_001" in ext_ids
    assert "EXT_002" in ext_ids
    ext_records = [r for r in lines if r["tsu_id"].startswith("EXT_")]
    for orig, merged in zip(unrelated, ext_records):
        assert merged["content"] == orig["content"]
        assert merged["metadata_source"] == orig["metadata_source"]


def test_case4_add_new_tsu(tmp_dirs):
    """CASE 4: 기존 records + 새로운 unique TSUs — expected count 정확."""
    tmp_dirs["tsu_dataset"].parent.mkdir(parents=True, exist_ok=True)
    existing = [_make_unrelated_record("EXIST_001", "existing content")]
    with open(tmp_dirs["tsu_dataset"], "w", encoding="utf-8") as f:
        for rec in existing:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    for i, name in enumerate(["TestDoc_D1", "TestDoc_D2"]):
        doc_dir = tmp_dirs["nae_corpus"] / name
        doc_dir.mkdir()
        rec = _make_naes_record(id_=4 + i, book=f"Book D{i+1}", author="Author D")
        with open(doc_dir / "tsu.json", "w", encoding="utf-8") as f:
            json.dump([rec], f, ensure_ascii=False)
    result = merge_nae_corpus(
        source_id="WORK_001",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_001", ['NAE-4', 'NAE-5']),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
    )
    assert result["existing_records"] == 1
    assert result["new_records_after_dedup"] == 2
    assert result["total_records"] == 3
    with open(tmp_dirs["tsu_dataset"], "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) == 3


def test_case5_dedup_preserves_existing(tmp_dirs):
    """CASE 5 (renamed): dedup으로 기존 tsu_id가 있으면 새 레코드 추가하지 않음."""
    tmp_dirs["tsu_dataset"].parent.mkdir(parents=True, exist_ok=True)
    original_content = json.dumps(
        {"tsu_id": "PRE_001", "content": "original data"}, ensure_ascii=False
    ) + "\n"
    with open(tmp_dirs["tsu_dataset"], "w", encoding="utf-8") as f:
        f.write(original_content)
    original_bytes = tmp_dirs["tsu_dataset"].read_bytes()

    # Pre-populate with conflicting tsu_id (simulates existing production record)
    conflict = {"tsu_id": "NAE-5", "content": "existing_conflict"}
    with open(tmp_dirs["tsu_dataset"], "w", encoding="utf-8") as f:
        json.dump(conflict, f)
        f.write("\n")
        f.write(original_content.strip() + "\n")

    doc_dir = tmp_dirs["nae_corpus"] / "TestDoc_E"
    doc_dir.mkdir()
    rec = _make_naes_record(id_=5, book="Book E", author="Author E")
    with open(doc_dir / "tsu.json", "w", encoding="utf-8") as f:
        json.dump([rec], f, ensure_ascii=False)

    # Execute — dedup should silently skip NAE-5 (already exists)
    result = merge_nae_corpus(
        source_id="WORK_001",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_001", ['NAE-5']),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
    )

    # Count should stay at 2 (no new record added due to dedup)
    assert result["total_records"] == 2
    assert result["new_records_after_dedup"] == 0

    # Original content preserved (byte-identical for PRE_001)
    with open(tmp_dirs["tsu_dataset"], "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) == 2
    pre_records = [r for r in lines if r["tsu_id"] == "PRE_001"]
    assert len(pre_records) == 1
    assert pre_records[0]["content"] == "original data"

    # No temporary artifacts left behind
    tmp_files = list(tmp_dirs["tsu_dataset"].parent.glob(f".{tmp_dirs['tsu_dataset'].name}.*.tmp"))
    assert len(tmp_files) == 0, f"Temporary artifacts left: {tmp_files}"


def test_case5b_atomic_write_failure_preserves_dataset(tmp_dirs):
    """CASE 5b: 실제 atomic write failure 시 기존 dataset bytes 보존.

    _atomic_write_text가 예외를 raise하면 temp file이 제거되고
    target path는 원래 내용이 그대로 유지된다.
    """
    from core.tsu_builder import _atomic_write_text

    tmp_dirs["tsu_dataset"].parent.mkdir(parents=True, exist_ok=True)
    original_content = '{"tsu_id": "PRE_002", "content": "original data"}\n'
    with open(tmp_dirs["tsu_dataset"], "w", encoding="utf-8") as f:
        f.write(original_content)
    original_bytes = tmp_dirs["tsu_dataset"].read_bytes()

    # Inject failure into _atomic_write_text's temp write path
    import core.tsu_builder as tsu_mod

    original_fsync = os.fsync if hasattr(os, 'fsync') else None

    class WriteFailure(Exception):
        pass

    def mock_atomic_write_fail(path, write_body):
        """Simulate a failure during atomic write — temp file is cleaned up."""
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path_obj.parent),
            prefix=f".{path_obj.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                write_body(f)
                f.flush()
                os.fsync(f.fileno())
            # Simulate failure BEFORE os.replace — raise exception
            raise WriteFailure("simulated write failure")
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    # Patch _atomic_write_text to fail on dataset write
    original_atomic = tsu_mod._atomic_write_text
    tsu_mod._atomic_write_text = mock_atomic_write_fail

    try:
        doc_dir = tmp_dirs["nae_corpus"] / "TestDoc_Eb"
        doc_dir.mkdir()
        rec = _make_naes_record(id_=51, book="Book Eb", author="Author Eb")
        with open(doc_dir / "tsu.json", "w", encoding="utf-8") as f:
            json.dump([rec], f, ensure_ascii=False)

        with pytest.raises(WriteFailure):
            merge_nae_corpus(
        source_id="WORK_001",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_001", ['NAE-51']),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
            )

        # Verify: original dataset bytes are preserved (unchanged)
        remaining_bytes = tmp_dirs["tsu_dataset"].read_bytes()
        assert remaining_bytes == original_bytes, (
            f"Dataset was corrupted by failed write!\n"
            f"  expected: {original_bytes!r}\n"
            f"  actual:   {remaining_bytes!r}"
        )

        # Verify: no temp artifacts left behind
        tmp_files = list(tmp_dirs["tsu_dataset"].parent.glob(f".{tmp_dirs['tsu_dataset'].name}.*.tmp"))
        assert len(tmp_files) == 0, f"Temporary artifacts left: {tmp_files}"
    finally:
        tsu_mod._atomic_write_text = original_atomic


def test_case6_manifest_consistency(tmp_dirs):
    """CASE 6: manifest.tsu_count == actual line count, dataset_sha256 matches."""
    doc_dir = tmp_dirs["nae_corpus"] / "TestDoc_F"
    doc_dir.mkdir()
    rec = _make_naes_record(id_=6, book="Book F", author="Author F")
    with open(doc_dir / "tsu.json", "w", encoding="utf-8") as f:
        json.dump([rec], f, ensure_ascii=False)
    merge_nae_corpus(
        source_id="WORK_001",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_001", ['NAE-6']),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
    )
    with open(tmp_dirs["manifest_path"], "r", encoding="utf-8") as f:
        manifest = json.load(f)
    with open(tmp_dirs["tsu_dataset"], "r", encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]
    assert manifest["tsu_count"] == len(lines)
    actual_sha = hashlib.sha256(tmp_dirs["tsu_dataset"].read_bytes()).hexdigest()
    assert manifest["dataset_sha256"] == actual_sha, (
        f"manifest sha={manifest['dataset_sha256']}, actual sha={actual_sha}"
    )


def test_case7_provenance_preservation(tmp_dirs):
    """CASE 7: source_type, copyright_status, author_id, work_id, scriptures 보존."""
    scriptures = [
        {"book": "Genesis", "chapter": 1, "verse_start": 1, "verse_end": 3},
        {"book": "John", "chapter": 3, "verse_start": 16, "verse_end": 16},
    ]
    doc_dir = tmp_dirs["nae_corpus"] / "TestDoc_G"
    doc_dir.mkdir()
    rec = _make_naes_record(
        id_=7, book="Book G", author="Author G", source_type="nae_canonical",
        copyright_status="public_domain", author_id="AUTH_007", work_id="WORK_007",
        scriptures=scriptures,
    )
    with open(doc_dir / "tsu.json", "w", encoding="utf-8") as f:
        json.dump([rec], f, ensure_ascii=False)
    merge_nae_corpus(
        source_id="WORK_007",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_007", ['NAE-7']),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
    )
    with open(tmp_dirs["tsu_dataset"], "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) == 1
    merged = lines[0]
    meta = merged["nae_metadata"]
    assert meta["source_type"] == "nae_canonical"
    assert meta["copyright_status"] == "public_domain"
    assert meta["author_id"] == "AUTH_007"
    assert meta["work_id"] == "WORK_007"
    assert meta["scriptures"] is not None, "scriptures was lost (None)"
    assert meta["scriptures"] == scriptures, f"scriptures mismatch: {meta['scriptures']}"
    assert merged["verse_mapping"] != {}, "verse_mapping is empty — provenance lost!"
    assert "_nae_scriptures" in merged["verse_mapping"]


def test_case8_cross_run_idempotency(tmp_dirs):
    """CASE 8: 동일 script 두 번 실행 — tsu_id duplicate=0, count stable."""
    for i, name in enumerate(["TestDoc_H1", "TestDoc_H2"]):
        doc_dir = tmp_dirs["nae_corpus"] / name
        doc_dir.mkdir()
        scriptures = [{"book": "Romans", "chapter": 1, "verse_start": 1}]
        rec = _make_naes_record(
            id_=8 + i, book=f"Book H{i+1}", author="Author H",
            source_type="nae_canonical", copyright_status="public_domain",
            author_id=f"AUTH_00{8+i}", work_id="WORK_008",
            scriptures=scriptures,
        )
        with open(doc_dir / "tsu.json", "w", encoding="utf-8") as f:
            json.dump([rec], f, ensure_ascii=False)
    tmp_dirs["tsu_dataset"].parent.mkdir(parents=True, exist_ok=True)
    unrelated = _make_unrelated_record("CROSS_001", "cross-run test data")
    with open(tmp_dirs["tsu_dataset"], "w", encoding="utf-8") as f:
        f.write(json.dumps(unrelated, ensure_ascii=False) + "\n")
    result1 = merge_nae_corpus(
        source_id="WORK_008",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_008", ['NAE-8', 'NAE-9']),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
    )
    with open(tmp_dirs["tsu_dataset"], "r", encoding="utf-8") as f:
        lines1 = [json.loads(line) for line in f if line.strip()]
    tsu_ids_run1 = [r["tsu_id"] for r in lines1]
    provenance_run1 = {
        r["tsu_id"]: {
            "source_type": r["nae_metadata"]["source_type"],
            "copyright_status": r["nae_metadata"]["copyright_status"],
            "author_id": r["nae_metadata"]["author_id"],
        }
        for r in lines1 if "nae_metadata" in r and r["nae_metadata"]
    }
    result2 = merge_nae_corpus(
        source_id="WORK_008",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_008", ['NAE-8', 'NAE-9']),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
    )
    with open(tmp_dirs["tsu_dataset"], "r", encoding="utf-8") as f:
        lines2 = [json.loads(line) for line in f if line.strip()]
    tsu_ids_run2 = [r["tsu_id"] for r in lines2]
    provenance_run2 = {
        r["tsu_id"]: {
            "source_type": r["nae_metadata"]["source_type"],
            "copyright_status": r["nae_metadata"]["copyright_status"],
            "author_id": r["nae_metadata"]["author_id"],
        }
        for r in lines2 if "nae_metadata" in r and r["nae_metadata"]
    }
    assert len(tsu_ids_run2) == len(set(tsu_ids_run2)), "Duplicate tsu_id found!"
    assert result1["total_records"] == result2["total_records"]
    assert len(lines1) == len(lines2)
    ext_records = [r for r in lines2 if r["tsu_id"].startswith("CROSS_")]
    assert len(ext_records) == 1
    assert ext_records[0]["content"] == "cross-run test data"
    assert provenance_run1 == provenance_run2


# ── NEW-6 regression tests ────────────────────────────────────────


def test_regression_empty_tsu_json(tmp_dirs):
    """NEW-3 regression: 빈 tsu.json이 들어와도 IndexError 없이 skip."""
    doc_dir = tmp_dirs["nae_corpus"] / "EmptyDoc"
    doc_dir.mkdir()
    # Empty array — should be skipped, not crash on data[0]
    with open(doc_dir / "tsu.json", "w", encoding="utf-8") as f:
        json.dump([], f)

    tmp_dirs["tsu_dataset"].parent.mkdir(parents=True, exist_ok=True)
    unrelated = _make_unrelated_record("REG_EMPTY_001", "should survive")
    with open(tmp_dirs["tsu_dataset"], "w", encoding="utf-8") as f:
        f.write(json.dumps(unrelated, ensure_ascii=False) + "\n")

    # Should not raise IndexError
    result = merge_nae_corpus(
        source_id="WORK_001",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_001"),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
    )

    # Empty corpus → skipped (no NAE records to merge)
    assert result["status"] == "skipped"
    # Only the unrelated record should remain in dataset
    with open(tmp_dirs["tsu_dataset"], "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) == 1
    assert lines[0]["tsu_id"] == "REG_EMPTY_001"


def test_regression_document_id_nae_prefix(tmp_dirs):
    """NEW-2 regression: document_id가 'nae_{identifier}' 형식이어야 함."""
    doc_dir = tmp_dirs["nae_corpus"] / "TestDoc_Prefix"
    doc_dir.mkdir()
    rec = _make_naes_record(id_=90, book="Book P", author="Author P")
    with open(doc_dir / "tsu.json", "w", encoding="utf-8") as f:
        json.dump([rec], f, ensure_ascii=False)

    merge_nae_corpus(
        source_id="WORK_001",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_001", ['NAE-90']),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
    )

    # Check dataset record document_id
    with open(tmp_dirs["tsu_dataset"], "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) == 1
    assert lines[0]["document_id"] == "nae_TestDoc_Prefix"

    # Check registry document_id
    with open(tmp_dirs["registry_path"], "r", encoding="utf-8") as f:
        registry = json.load(f)
    reg_docs = list(registry["documents"].keys())
    assert len(reg_docs) == 1
    assert reg_docs[0] == "nae_TestDoc_Prefix"


def test_regression_default_args_no_typeerror(tmp_path: Path, monkeypatch):
    """data_root 없이 merge_nae_corpus() 호출 시 CorpusMutationBlockedError 발생.

    [SPRINT34] data_root 명시적 요구로 인해, data_root 없이 호출하면
    CorpusMutationBlockedError가 발생한다. 이 테스트는 그 동작을 검증한다.

    S1-9 이식: 6f311d1f 의 production 해시 불변 6건 단언을
    tmp 모의 production sentinel 3개 파일(registry/dataset/manifest) 의
    해시 불변 단언으로 교체 이식.

    sentinel 3개가 호출에 연결되도록 함:
      - mock_production 을 data_root 로 넘기는 호출 포함
      - 대조 케이스: sentinel 파일을 직접 수정하면 단언이 실패함을 확인
    """
    import scripts.merge_nae_corpus as mod
    from scripts.corpus_approval_gate import CorpusMutationBlockedError

    # corpus directory 생성
    test_corpus = tmp_path / "NAE" / "corpus" / "tsu" / "TestDoc_A"
    test_corpus.mkdir(parents=True)
    fixture = [_make_naes_record(id_=100, book="Book D", author="Author D")]
    with open(test_corpus / "tsu.json", "w", encoding="utf-8") as f:
        json.dump(fixture, f, ensure_ascii=False)

    # --- tmp 모의 production sentinel 3개 파일 생성 ---
    mock_prod = tmp_path / "mock_production"
    mock_prod.mkdir(parents=True)
    mock_bench = mock_prod / "output" / "bench"
    mock_bench.mkdir(parents=True)
    mock_registry_dir = mock_prod / "data" / "registry"
    mock_registry_dir.mkdir(parents=True)

    sentinel_dataset = mock_bench / "tsu_dataset.jsonl"
    sentinel_manifest = mock_bench / "tsu_manifest.json"
    sentinel_registry = mock_registry_dir / "documents.json"

    # sentinel 파일에 초기 내용 작성
    sentinel_dataset.write_text("initial_dataset_content", encoding="utf-8")
    sentinel_manifest.write_text('{"tsu_count": 0}', encoding="utf-8")
    sentinel_registry.write_text('{"documents": {}}', encoding="utf-8")

    # --- 초기 해시 기록 ---
    hash_before_dataset = _file_hash(str(sentinel_dataset))
    hash_before_manifest = _file_hash(str(sentinel_manifest))
    hash_before_registry = _file_hash(str(sentinel_registry))
    sentinel_dataset_path = str(sentinel_dataset)
    sentinel_manifest_path = str(sentinel_manifest)
    sentinel_registry_path = str(sentinel_registry)

    # --- (1) mock_production 을 data_root 로 넘기는 호출 (승인 없이 → 차단) ---
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"merge-safety:\n  production_root: {mock_prod.resolve()}\n",
        encoding="utf-8",
    )

    with pytest.raises(CorpusMutationBlockedError):
        mod.merge_nae_corpus(
            source_id="WORK_001",
            data_root=mock_prod,
            nae_corpus_dir=test_corpus.parent.parent,
            decisions_dir=_make_approved_decisions_dir(tmp_path, "WORK_001", ['NAE-100']),
            config_path=config_path,
        )

    # (1) 후 해시 비교 — sentinel 파일이 변경되지 않았어야 함
    assert _file_hash(str(sentinel_dataset)) == hash_before_dataset,         "Mock production dataset was modified!"
    assert _file_hash(str(sentinel_manifest)) == hash_before_manifest,       "Mock production manifest was modified!"
    assert _file_hash(str(sentinel_registry)) == hash_before_registry,       "Mock production registry was modified!"

    # --- (2) data_root 없이 호출하면 CorpusMutationBlockedError 발생 ---
    with pytest.raises(CorpusMutationBlockedError) as exc_info:
        mod.merge_nae_corpus(
            source_id="WORK_001",
            nae_corpus_dir=test_corpus.parent.parent,
            decisions_dir=_make_approved_decisions_dir(tmp_path, "WORK_001", ['NAE-100']),
        )
    assert "data_root" in str(exc_info.value).lower()

    # (2) 후 해시 비교 — sentinel 파일이 여전히 변경되지 않았어야 함
    assert _file_hash(str(sentinel_dataset)) == hash_before_dataset,         "Mock production dataset was modified!"
    assert _file_hash(str(sentinel_manifest)) == hash_before_manifest,       "Mock production manifest was modified!"
    assert _file_hash(str(sentinel_registry)) == hash_before_registry,       "Mock production registry was modified!"

    # --- (3) 대조 케이스: sentinel 파일을 직접 수정하면 단언이 실패함을 확인 ---
    # 이 단언은 반드시 실패해야 함 — 변이가 감지됨을 검증
    sentinel_dataset.write_text("MUTATED_CONTENT", encoding="utf-8")
    with pytest.raises(AssertionError):
        assert _file_hash(str(sentinel_dataset)) == hash_before_dataset, \
            "This should fail because we mutated the file!"


def _file_hash(path: str) -> str:
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_regression_registry_document_entry(tmp_dirs):
    """Registry regression: merge 후 registry에 document entry가 생성됨."""
    doc_dir = tmp_dirs["nae_corpus"] / "TestDoc_Reg"
    doc_dir.mkdir()
    rec = _make_naes_record(id_=91, book="Book R", author="Author R")
    with open(doc_dir / "tsu.json", "w", encoding="utf-8") as f:
        json.dump([rec], f, ensure_ascii=False)

    merge_nae_corpus(
        source_id="WORK_001",
            data_root=tmp_dirs["data_root"],
        decisions_dir=_make_approved_decisions_dir(tmp_dirs["tmp_path"], "WORK_001", ['NAE-91']),
        nae_corpus_dir=tmp_dirs["nae_corpus"],
    )

    with open(tmp_dirs["registry_path"], "r", encoding="utf-8") as f:
        registry = json.load(f)

    # Should have exactly one document entry
    assert len(registry["documents"]) == 1
    doc_entry = registry["documents"]["nae_TestDoc_Reg"]
    assert doc_entry["document_id"] == "nae_TestDoc_Reg"
    assert doc_entry["source_type"] == "nae_canonical"
    assert doc_entry["corpus_membership"] == "default"
    assert doc_entry["status"] == "processed"