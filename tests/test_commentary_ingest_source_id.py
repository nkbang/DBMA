"""nae_commentary_ingest의 source_id 해석 — 빈 source_id 적재 회귀 방지.

2026-10-14: nae_ref_commentary_v1의 8,539건(Gill/Broadus/Carroll)이 매핑 누락 +
조용한 빈 문자열 기본값 때문에 source_id 없이 적재된 것을 확인했다.
"""
from pathlib import Path

import pytest
import yaml

import scripts.nae_commentary_ingest as cli

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "NAE/pipeline/registration/state/source_manifest.yaml"


@pytest.mark.parametrize("identifier,expected", [
    ("Spurgeon_TreasuryOfDavid_Vol1", "BAP-COMM-SPURGEON-TDA-VOL01"),
    ("Gill_ExpositionNT_Vol1", "BAP-COMM-GILL-ENT-VOL01"),
    ("Broadus_CommentaryMatthew", "BAP-COMM-BROADUS-MATT-VOL01"),
    ("Carroll_InterpretationEB_Vol2", "BAP-COMM-CARROLL-IEB-VOL02"),
])
def test_known_identifiers_resolve(identifier, expected):
    assert cli.resolve_source_id(identifier) == expected


def test_unknown_identifier_raises_instead_of_empty():
    with pytest.raises(ValueError, match="Unknown identifier"):
        cli.resolve_source_id("Some_Unmapped_Commentary")


def test_override_allows_unmapped_identifier():
    assert cli.resolve_source_id("Some_Unmapped_Commentary", "BAP-COMM-X-Y-VOL01") == "BAP-COMM-X-Y-VOL01"


def test_blank_override_does_not_bypass_check():
    with pytest.raises(ValueError):
        cli.resolve_source_id("Some_Unmapped_Commentary", "   ")


def test_mapped_source_ids_exist_in_manifest():
    manifest_ids = {s["source_id"] for s in yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["sources"]}
    for source_id in cli._COMMENTARY_SOURCE_IDS.values():
        assert source_id in manifest_ids
