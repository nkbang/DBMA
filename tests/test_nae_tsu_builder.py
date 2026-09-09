import json
from pathlib import Path
from unittest.mock import patch

from NAE.pipeline.tsu import builder, claim, config


def _setup_item(tmp_path: Path, identifier: str) -> tuple[Path, Path, Path]:
    canonical_root = tmp_path / "canonical"
    raw_root = tmp_path / "raw"
    tsu_root = tmp_path / "tsu"

    canonical_dir = canonical_root / identifier
    canonical_dir.mkdir(parents=True)
    canonical_json = {
        "identifier": identifier,
        "paragraphs": [
            {
                "index": 0,
                "type": "prose",
                "text": "Believer's baptism follows a profession of faith. This is a second sentence here.",
                "page_start": 1,
                "page_end": 1,
                "sentences": [
                    {"sentence_index": 0, "text": "Believer's baptism follows a profession of faith."},
                    {"sentence_index": 1, "text": "This is a second sentence here."},
                ],
                "scripture_references": [],
            },
        ],
        "footnotes": [],
        "scripture_references": [],
    }
    with open(canonical_dir / "canonical.json", "w", encoding="utf-8") as fh:
        json.dump(canonical_json, fh)

    raw_dir = raw_root / "books" / identifier
    raw_dir.mkdir(parents=True)
    with open(raw_dir / "metadata.json", "w", encoding="utf-8") as fh:
        json.dump({"title": "Body of Divinity", "creator": "John Gill"}, fh)

    return canonical_root, raw_root, tsu_root


def test_build_tsu_for_identifier_writes_records_and_report(tmp_path: Path):
    canonical_root, raw_root, tsu_root = _setup_item(tmp_path, "gill_body_of_divinity")

    claim_result = claim.ClaimResult(
        is_claim=True, claim="A restated claim.", doctrine="Baptism",
        scriptures=[], citations=[], confidence=0.9, model="test-model",
    )
    with patch("NAE.pipeline.tsu.builder.claim_mod.extract_claim", return_value=claim_result):
        result = builder.build_tsu_for_identifier(
            "gill_body_of_divinity", canonical_root=canonical_root, raw_root=raw_root, tsu_root=tsu_root,
        )

    assert len(result["records"]) == 2
    assert result["records"][0]["id"] == "TSU-0000001"
    assert result["records"][1]["id"] == "TSU-0000002"
    assert result["records"][0]["book"] == "Body of Divinity"
    assert result["records"][0]["doctrine"] == "Baptism"
    assert result["records"][0]["review_status"] == "generated"
    assert result["records"][0]["tsu_schema_version"] == config.TSU_SCHEMA_VERSION
    assert result["records"][0]["source_identifier"] == "gill_body_of_divinity"

    out_dir = tsu_root / "gill_body_of_divinity"
    assert (out_dir / "tsu.json").exists()
    assert (out_dir / "tsu_report.json").exists()

    report = json.loads((out_dir / "tsu_report.json").read_text(encoding="utf-8"))
    assert report["claims_extracted"] == 2
    assert report["candidates_evaluated"] == 2
    assert report["llm_errors"] == 0


def test_build_tsu_id_counter_persists_across_calls(tmp_path: Path):
    canonical_root, raw_root, tsu_root = _setup_item(tmp_path, "gill_body_of_divinity")

    claim_result = claim.ClaimResult(is_claim=True, claim="X", confidence=0.5, model="test-model")
    with patch("NAE.pipeline.tsu.builder.claim_mod.extract_claim", return_value=claim_result):
        builder.build_tsu_for_identifier(
            "gill_body_of_divinity", canonical_root=canonical_root, raw_root=raw_root, tsu_root=tsu_root,
        )
        result2 = builder.build_tsu_for_identifier(
            "gill_body_of_divinity", canonical_root=canonical_root, raw_root=raw_root, tsu_root=tsu_root,
        )

    assert result2["records"][0]["id"] == "TSU-0000003"


def test_build_tsu_skips_non_claim_sentences(tmp_path: Path):
    canonical_root, raw_root, tsu_root = _setup_item(tmp_path, "gill_body_of_divinity")

    with patch("NAE.pipeline.tsu.builder.claim_mod.extract_claim",
               return_value=claim.ClaimResult(is_claim=False)):
        result = builder.build_tsu_for_identifier(
            "gill_body_of_divinity", canonical_root=canonical_root, raw_root=raw_root, tsu_root=tsu_root,
        )
    assert result["records"] == []
    report = json.loads((tsu_root / "gill_body_of_divinity" / "tsu_report.json").read_text(encoding="utf-8"))
    assert report["claims_extracted"] == 0


def test_build_tsu_counts_llm_errors_without_crashing(tmp_path: Path):
    canonical_root, raw_root, tsu_root = _setup_item(tmp_path, "gill_body_of_divinity")

    with patch("NAE.pipeline.tsu.builder.claim_mod.extract_claim",
               return_value=claim.ClaimResult(is_claim=False, error="boom")):
        result = builder.build_tsu_for_identifier(
            "gill_body_of_divinity", canonical_root=canonical_root, raw_root=raw_root, tsu_root=tsu_root,
        )
    report = json.loads((tsu_root / "gill_body_of_divinity" / "tsu_report.json").read_text(encoding="utf-8"))
    assert report["llm_errors"] == 2
    assert result["records"] == []


def _setup_many(tmp_path: Path, identifier: str, n_sentences: int):
    """Canonical item with many prose sentences in one paragraph."""
    canonical_root = tmp_path / "canonical"
    raw_root = tmp_path / "raw"
    tsu_root = tmp_path / "tsu"
    cdir = canonical_root / identifier
    cdir.mkdir(parents=True)
    sents = [{"sentence_index": i, "text": f"Sentence number {i} makes a claim about doctrine."}
             for i in range(n_sentences)]
    cj = {
        "identifier": identifier,
        "paragraphs": [{
            "index": 0, "type": "prose",
            "text": " ".join(s["text"] for s in sents),
            "page_start": 1, "page_end": 1,
            "sentences": sents, "scripture_references": [],
        }],
        "footnotes": [], "scripture_references": [],
    }
    (cdir / "canonical.json").write_text(json.dumps(cj), encoding="utf-8")
    rdir = raw_root / "books" / identifier
    rdir.mkdir(parents=True)
    (rdir / "metadata.json").write_text(json.dumps({"title": "T", "creator": "C"}), encoding="utf-8")
    return canonical_root, raw_root, tsu_root


def test_max_workers_output_is_deterministic(tmp_path: Path):
    """max_workers=1 and max_workers=4 must produce byte-identical tsu records
    (same ids in candidate order), even with interleaved/jittered LLM calls."""
    import random
    import time as _t

    def fake_extract(sentence, **kw):
        _t.sleep(random.uniform(0, 0.01))  # force real interleaving under threads
        num = int(sentence.split()[2])
        return claim.ClaimResult(
            is_claim=(num % 3 != 0),  # some non-claims + some errors-free claims
            claim=f"claim for {num}", doctrine="Baptism" if num % 2 else "Ecclesiology",
            scriptures=[], citations=[], confidence=0.8, model="test-model",
        )

    def run(workers):
        cr, rr, tr = _setup_many(tmp_path / f"w{workers}", "gill_x", 23)
        with patch("NAE.pipeline.tsu.builder.claim_mod.extract_claim", side_effect=fake_extract):
            res = builder.build_tsu_for_identifier(
                "gill_x", canonical_root=cr, raw_root=rr, tsu_root=tr,
                checkpoint_every=5, max_workers=workers,
            )
        return res["records"]

    seq = run(1)
    par = run(4)
    assert seq == par
    assert [r["id"] for r in seq] == [r["id"] for r in par]
    # ids are contiguous and in order
    assert [r["id"] for r in seq] == [f"TSU-{i:07d}" for i in range(1, len(seq) + 1)]
    # claim text follows candidate order (no shuffling)
    assert seq[0]["claim"] == "claim for 1"
