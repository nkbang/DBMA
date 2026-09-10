import json
from pathlib import Path
from unittest.mock import patch

import pytest

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


# --- checkpoint resume (NAE-TSU-BUILDER-RESUME-001) ---------------------------

_RESUME_SENTENCES = [
    "Believer's baptism follows a public profession of personal faith in Christ.",
    "The Lord's Supper is a memorial ordinance observed by the gathered church.",
    "Regenerate church membership is the historic Baptist distinctive here stated.",
    "Congregational polity vests final authority under Christ in the whole body.",
    "The local church has authority to receive and to dismiss its own members.",
    "Elders lead by teaching and example rather than by coercive hierarchy today.",
    "Deacons serve the practical needs of the congregation and its ministry work.",
    "Scripture alone is the final rule for faith and for the ordering of practice.",
]


def _setup_multi(tmp_path: Path, identifier: str, *, n: int, paragraph_index: int = 0):
    """Single prose paragraph with `n` claim-length sentences -> `n` candidates."""
    canonical_root = tmp_path / "canonical"
    raw_root = tmp_path / "raw"
    tsu_root = tmp_path / "tsu"
    canonical_dir = canonical_root / identifier
    canonical_dir.mkdir(parents=True)

    sentences = [
        {"sentence_index": i, "text": _RESUME_SENTENCES[i]} for i in range(n)
    ]
    canonical_json = {
        "identifier": identifier,
        "paragraphs": [
            {
                "index": paragraph_index,
                "type": "prose",
                "text": " ".join(s["text"] for s in sentences),
                "page_start": 3,
                "page_end": 3,
                "sentences": sentences,
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
        json.dump({"title": "Church Order", "creator": "J. L. Dagg"}, fh)

    return canonical_root, raw_root, tsu_root


def _claim_for(cand_text, **_kw):
    # Deterministic, input-independent claim so a from-scratch run and a resumed
    # run must produce byte-identical tsu.json.
    return claim.ClaimResult(
        is_claim=True, claim="Restated: " + cand_text[:20], doctrine="Ecclesiology",
        scriptures=[], citations=[], confidence=0.8, model="test-model",
    )


def test_build_tsu_resume_byte_identical(tmp_path: Path):
    ident = "dagg_church_order"

    # (a) from-scratch, full run
    cr_a, rr_a, tr_a = _setup_multi(tmp_path / "a", ident, n=6)
    with patch("NAE.pipeline.tsu.builder.claim_mod.extract_claim", side_effect=_claim_for):
        builder.build_tsu_for_identifier(
            ident, canonical_root=cr_a, raw_root=rr_a, tsu_root=tr_a, checkpoint_every=2,
        )
    full_bytes = (tr_a / ident / "tsu.json").read_bytes()

    # (b) interrupt after candidate 3 (checkpoint at 2 lands on disk)
    cr_b, rr_b, tr_b = _setup_multi(tmp_path / "b", ident, n=6)
    calls = {"n": 0}

    def crashing(cand_text, **kw):
        calls["n"] += 1
        if calls["n"] >= 4:
            raise RuntimeError("simulated ollama wedge")
        return _claim_for(cand_text, **kw)

    with patch("NAE.pipeline.tsu.builder.claim_mod.extract_claim", side_effect=crashing):
        with pytest.raises(RuntimeError):
            builder.build_tsu_for_identifier(
                ident, canonical_root=cr_b, raw_root=rr_b, tsu_root=tr_b, checkpoint_every=2,
            )
    partial_report = json.loads((tr_b / ident / "tsu_report.json").read_text(encoding="utf-8"))
    assert partial_report["partial"] is True
    assert partial_report["candidates_evaluated"] == 2

    # (c) resume -> must reproduce the full run exactly
    with patch("NAE.pipeline.tsu.builder.claim_mod.extract_claim", side_effect=_claim_for):
        result = builder.build_tsu_for_identifier(
            ident, canonical_root=cr_b, raw_root=rr_b, tsu_root=tr_b, checkpoint_every=2,
            resume=True,
        )

    assert (tr_b / ident / "tsu.json").read_bytes() == full_bytes
    assert result.get("skipped") is not True

    report_a = json.loads((tr_a / ident / "tsu_report.json").read_text(encoding="utf-8"))
    report_b = json.loads((tr_b / ident / "tsu_report.json").read_text(encoding="utf-8"))
    stable = ("identifier", "builder_version", "model", "candidates_evaluated",
              "candidates_total", "claims_extracted", "llm_errors",
              "doctrine_breakdown", "partial")
    assert {k: report_a[k] for k in stable} == {k: report_b[k] for k in stable}
    assert report_b["builder_version"] == "3.0.0"


def test_build_tsu_resume_noop_when_complete(tmp_path: Path):
    ident = "dagg_church_order"
    cr, rr, tr = _setup_multi(tmp_path, ident, n=5)

    with patch("NAE.pipeline.tsu.builder.claim_mod.extract_claim", side_effect=_claim_for) as m1:
        builder.build_tsu_for_identifier(ident, canonical_root=cr, raw_root=rr, tsu_root=tr)
    assert m1.call_count == 5
    done_bytes = (tr / ident / "tsu.json").read_bytes()

    with patch("NAE.pipeline.tsu.builder.claim_mod.extract_claim", side_effect=_claim_for) as m2:
        result = builder.build_tsu_for_identifier(
            ident, canonical_root=cr, raw_root=rr, tsu_root=tr, resume=True,
        )
    assert m2.call_count == 0
    assert result["skipped"] is True
    assert len(result["records"]) == 5
    assert (tr / ident / "tsu.json").read_bytes() == done_bytes


def test_build_tsu_resume_without_prior_report_starts_fresh(tmp_path: Path):
    ident = "dagg_church_order"
    cr, rr, tr = _setup_multi(tmp_path, ident, n=4)

    with patch("NAE.pipeline.tsu.builder.claim_mod.extract_claim", side_effect=_claim_for):
        result = builder.build_tsu_for_identifier(
            ident, canonical_root=cr, raw_root=rr, tsu_root=tr, resume=True,
        )
    assert [r["id"] for r in result["records"]] == [
        "TSU-0000001", "TSU-0000002", "TSU-0000003", "TSU-0000004",
    ]
    assert result["report"]["partial"] is False


def test_build_tsu_resume_aborts_on_canonical_drift(tmp_path: Path):
    ident = "dagg_church_order"
    cr, rr, tr = _setup_multi(tmp_path, ident, n=6, paragraph_index=0)
    calls = {"n": 0}

    def crashing(cand_text, **kw):
        calls["n"] += 1
        if calls["n"] >= 4:
            raise RuntimeError("simulated wedge")
        return _claim_for(cand_text, **kw)

    with patch("NAE.pipeline.tsu.builder.claim_mod.extract_claim", side_effect=crashing):
        with pytest.raises(RuntimeError):
            builder.build_tsu_for_identifier(
                ident, canonical_root=cr, raw_root=rr, tsu_root=tr, checkpoint_every=2,
            )
    partial_bytes = (tr / ident / "tsu.json").read_bytes()

    # canonical.json regenerated with a different paragraph index -> loaded
    # records no longer map to any current candidate.
    cj_path = cr / ident / "canonical.json"
    cj = json.loads(cj_path.read_text(encoding="utf-8"))
    cj["paragraphs"][0]["index"] = 99
    cj_path.write_text(json.dumps(cj), encoding="utf-8")

    with patch("NAE.pipeline.tsu.builder.claim_mod.extract_claim", side_effect=_claim_for):
        with pytest.raises(RuntimeError, match="canonical.json changed"):
            builder.build_tsu_for_identifier(
                ident, canonical_root=cr, raw_root=rr, tsu_root=tr, checkpoint_every=2,
                resume=True,
            )
    # aborted before any write
    assert (tr / ident / "tsu.json").read_bytes() == partial_bytes
