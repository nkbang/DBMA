import json
import re

from core.sermon_artifact import (
    SermonArtifact,
    generate_sermon_id,
    list_sermon_artifacts,
    load_sermon_artifact,
    save_sermon_artifact,
)


def _make_artifact(sermon_id: str = None, title: str = "고난 중의 소망") -> SermonArtifact:
    return SermonArtifact(
        sermon_id=sermon_id or generate_sermon_id(),
        scripture_and_theme="로마서 5:1-5, 고난 중의 소망",
        sermon_format="주제설교",
        outline={
            "title": title,
            "introduction": "서론입니다",
            "points": ["대지 1", "대지 2"],
            "conclusion": "결론입니다",
        },
        expanded={"0": "대지 1 확장", "1": "대지 2 확장"},
        evidence={"candidate_tsu_ids": ["TSU-ROM-001", "TSU-ROM-002"], "retrieval": {"k": 20, "query_id": "sermon-draft"}},
        doctrine_report={"passed": True, "warnings": [], "flagged_categories": [], "confidence": "medium"},
    )


def test_generate_sermon_id_format():
    sermon_id = generate_sermon_id()
    assert re.match(r"^SRM-\d{8}-[0-9a-f]{6}$", sermon_id)


def test_generate_sermon_id_unique():
    assert generate_sermon_id() != generate_sermon_id()


def test_save_and_load_roundtrip(tmp_path):
    output_dir = str(tmp_path / "sermon_artifacts")
    artifact = _make_artifact()

    path = save_sermon_artifact(artifact, output_dir=output_dir)
    assert path.endswith(f"{artifact.sermon_id}.json")

    loaded = load_sermon_artifact(artifact.sermon_id, output_dir=output_dir)
    assert loaded is not None
    assert loaded.sermon_id == artifact.sermon_id
    assert loaded.outline["title"] == "고난 중의 소망"
    assert loaded.expanded == artifact.expanded
    assert loaded.evidence == artifact.evidence
    assert loaded.groundedness is None  # P1은 미계산


def test_load_nonexistent_returns_none(tmp_path):
    output_dir = str(tmp_path / "sermon_artifacts")
    assert load_sermon_artifact("SRM-99999999-ffffff", output_dir=output_dir) is None


def test_list_sermon_artifacts_empty(tmp_path):
    output_dir = str(tmp_path / "sermon_artifacts")
    assert list_sermon_artifacts(output_dir=output_dir) == []


def test_list_sermon_artifacts_sorted_newest_first(tmp_path):
    output_dir = str(tmp_path / "sermon_artifacts")
    older = _make_artifact(sermon_id="SRM-20260101-aaaaaa", title="older")
    older.created_at = "2026-01-01T00:00:00+00:00"
    newer = _make_artifact(sermon_id="SRM-20260201-bbbbbb", title="newer")
    newer.created_at = "2026-02-01T00:00:00+00:00"

    save_sermon_artifact(older, output_dir=output_dir)
    save_sermon_artifact(newer, output_dir=output_dir)

    summaries = list_sermon_artifacts(output_dir=output_dir)
    assert [s["sermon_id"] for s in summaries] == ["SRM-20260201-bbbbbb", "SRM-20260101-aaaaaa"]


def test_save_writes_index_summary(tmp_path):
    output_dir = str(tmp_path / "sermon_artifacts")
    artifact = _make_artifact()
    save_sermon_artifact(artifact, output_dir=output_dir)

    index_path = tmp_path / "sermon_artifacts" / "index.jsonl"
    lines = index_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    summary = json.loads(lines[0])
    assert summary["sermon_id"] == artifact.sermon_id
    assert summary["title"] == "고난 중의 소망"
    assert summary["scripture_and_theme"] == artifact.scripture_and_theme


def test_from_dict_ignores_unknown_fields(tmp_path):
    artifact = _make_artifact()
    data = artifact.to_dict()
    data["unknown_future_field"] = "should be ignored"
    restored = SermonArtifact.from_dict(data)
    assert restored.sermon_id == artifact.sermon_id
