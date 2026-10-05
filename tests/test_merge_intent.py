"""tests/test_merge_intent.py — S2-C write-ahead intent (CUE-authored, mutation-verified).

Principles (why this file looks the way it does):
  * Every expectation comes from a hard-coded golden constant or from a reference implementation that is
    local to this file and never calls the code under test (``_ref_*``).
  * Production merges are driven through the real ``merge_nae_corpus()``; only FAILURE INJECTION is patched
    (directory fsync, atomic writer) and the three data writers are wrapped by pass-through spies.
    Nothing that implements a protection (compute_plan_hash, intent functions, validators) is mocked.
  * Every "blocked" assertion also checks the REASON (``match=``), the number of production writes, and the
    state of the intent file, so a merge that is blocked for an unrelated reason cannot pass.
  * tests/ is mutation-checked with scratchpad/s2c_mutations.py (all mutants must be caught).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.merge_nae_corpus as m  # noqa: E402
from scripts.merge_nae_corpus import (  # noqa: E402
    ApprovalReasonCode,
    ApprovalState,
    CorpusMutationBlockedError,
    IntentPhase,
    evaluate_approval_v2,
)

INTENT_NAME = "tsu_merge_intent.json"

# ---------------------------------------------------------------------------
# Golden constants (computed once with a stand-alone script that does not import this repo)
# ---------------------------------------------------------------------------

GOLDEN_EXISTING_RECORDS = [
    {"tsu_id": "TSU-B", "document_id": "doc_b", "content": "나의 눈이"},
    {"tsu_id": "TSU-A", "document_id": "doc_a", "content": "abc"},
]
GOLDEN_DATASET_PRE = [
    ["TSU-A", "doc_a", "530a2c00ec6355854af59d5df9f3693736f5d78d8b2a7c37180c5e39ba21d846"],
    ["TSU-B", "doc_b", "8cc102b923e8df243c0938048ea6f95424ef98b091a5a42cbd278a456a9c7b43"],
]
GOLDEN_REGISTRY_DOCS = {
    "doc_b": {"document_id": "doc_b", "title": "B", "excluded_at": "2026-01-01", "pipeline_flags": {"x": True}},
    "doc_a": {"document_id": "doc_a", "title": "A", "exclude_reason": "r"},
}
GOLDEN_REGISTRY_PRE = [
    ["doc_a", "6217cb31f8bd526b52f6ab81c1339ed7e605c6457b370461bbe3d2b27d25721f"],
    ["doc_b", "36bf0cd29dfe0035645ed850d910569c5fb9b2996fccb0ba2d6adc412a2c6e35"],
]

_FLAGS = {"chunked": False, "cleaned": False, "copied": False, "extracted": False, "ingested": False, "output_generated": False, "verified": False}


def _normalized_entry(document_id: str, title: str, **extra) -> dict:
    """An entry already in the shape load_identity_registry() returns (the merge fingerprints the LOADED view)."""
    entry = {
        "document_id": document_id, "ingest_status": "PROCESSED", "last_content_hash": None, "last_failure_reason": None,
        "last_processed_at": None, "max_retries": 3, "pipeline_flags": dict(_FLAGS), "pipeline_state": "PROCESSED",
        "retry_count": 0, "superseded_by": None, "supersedes": None, "title": title,
    }
    entry.update(extra)
    return entry


MERGE_REGISTRY_DOCS = {
    "doc_b": _normalized_entry("doc_b", "B", excluded_at="2026-01-01"),
    "doc_a": _normalized_entry("doc_a", "A", exclude_reason="r"),
}
MERGE_REGISTRY_PRE = [
    ["doc_a", "60abc710adfb18fc36823bc04f2f881d5ba42de52e6abe3f7912f26c1b0667d7"],
    ["doc_b", "d4b84accbdb8a81f90b83fa50d09d78f09be8a329c08156fd7273be6a718c5c3"],
]

GOLDEN_FIXED_CHECKSUM_INTENT_WRITTEN = "a995f1a88418fd7724b8f3328352555b58a85f764d0b3732583a31f74ca7c505"
GOLDEN_FIXED_CHECKSUM_COMMITTED = "59cd0730499826f1b8ba2f74656e1853f570954f0d28c34300f49ec409881d81"


# ---------------------------------------------------------------------------
# Reference implementations (independent of the code under test)
# ---------------------------------------------------------------------------

def _ref_canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _ref_sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ref_plan_hash(source_id: str, records: list[dict], targets: list) -> str:
    rows = sorted(
        ({"tsu_id": r["tsu_id"], "content_sha256": _ref_sha(_ref_canonical(r))} for r in records),
        key=lambda row: row["tsu_id"],
    )
    payload = {"v": 1, "source_id": source_id, "records": rows, "targets": [str(Path(t).resolve()) for t in targets]}
    return "sha256:" + _ref_sha(_ref_canonical(payload))


def _ref_checksum(payload: dict) -> str:
    return _ref_sha(_ref_canonical({k: v for k, v in payload.items() if k != "intent_content_sha256"}))


def _sealed(payload: dict) -> dict:
    out = dict(payload)
    out["intent_content_sha256"] = _ref_checksum(out)
    return out


def _fixed_payload(**overrides) -> dict:
    """A hand-built valid intent (checksum computed by the reference function)."""
    payload = {
        "intent_version": 1,
        "intent_id": "123e4567-e89b-42d3-a456-426614174000",
        "phase": "INTENT_WRITTEN",
        "created_at": "2026-10-05T00:00:00+00:00",
        "source_id": "SRC_001",
        "approval": {
            "path": "/ap/production_targets/SRC_001.json",
            "artifact_sha256": "a" * 64,
            "plan_hash": "sha256:" + "b" * 64,
            "approved_at": "2026-10-04T00:00:00+00:00",
        },
        "plan_hash": "sha256:" + "b" * 64,
        "targets": [
            "/p/output/bench/tsu_dataset.jsonl",
            "/p/output/bench/tsu_manifest.json",
            "/p/data/제련완성본/registry/documents.json",
        ],
        "dataset_pre_image": [list(r) for r in GOLDEN_DATASET_PRE],
        "registry_pre_image": [list(r) for r in GOLDEN_REGISTRY_PRE],
        "mutation_plan": {
            "planned_tsu_ids": ["TSU-A", "TSU-C"],
            "new_tsu_ids": ["TSU-C"],
            "new_document_ids": ["nae_SRC_001"],
            "new_record_count": 1,
        },
    }
    payload.update(overrides)
    return _sealed(payload)


def _bytes(payload: dict) -> bytes:
    return _ref_canonical(payload)


# ---------------------------------------------------------------------------
# Mock production environment
# ---------------------------------------------------------------------------

class Env:
    """tmp mock production + tmp config (production_root, approval_dir) + approvals/corpora/decisions."""

    def __init__(self, tmp_path: Path):
        self.root = tmp_path
        self.prod = tmp_path / "prod"
        (self.prod / "output" / "bench").mkdir(parents=True)
        (self.prod / "data" / "제련완성본" / "registry").mkdir(parents=True)
        self.approval_dir = tmp_path / "approvals"
        (self.approval_dir / "production_targets").mkdir(parents=True)
        self.config = tmp_path / "config.yaml"
        self.config.write_text(
            f"merge-safety:\n  production_root: {self.prod.resolve()}\n  approval_dir: {self.approval_dir.resolve()}\n",
            encoding="utf-8",
        )
        target = m.resolve_target_paths(self.prod, self.config)
        self.dataset, self.manifest, self.registry = target.dataset_path, target.manifest_path, target.registry_path
        self.dataset.write_text("", encoding="utf-8")
        self.manifest.write_text("{}", encoding="utf-8")
        self.registry.write_text(json.dumps({"documents": {}}), encoding="utf-8")
        self.intent_path = self.manifest.parent / INTENT_NAME
        self._n = 0
        assert target.is_production is True  # fixture relation: this tmp data_root IS the declared production root
        assert self.intent_path.parent == self.dataset.parent

    # -- state helpers -------------------------------------------------------
    def seed_dataset(self, records: list[dict]) -> None:
        self.dataset.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
        )

    def seed_registry(self, docs: dict) -> None:
        self.registry.write_text(json.dumps({"documents": docs}, ensure_ascii=False), encoding="utf-8")

    def intent_raw(self):
        return self.intent_path.read_bytes() if self.intent_path.exists() else None

    def intent_state(self):
        """(phase, parsed dict) or (None, None) if no intent / not parseable."""
        raw = self.intent_raw()
        if raw is None:
            return None, None
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return "<unparseable>", None
        return data.get("phase"), data

    def target_hashes(self) -> tuple:
        return tuple(_ref_sha(p.read_bytes()) for p in (self.dataset, self.manifest, self.registry))

    def tmp_leftovers(self) -> list[str]:
        return sorted(p.name for p in self.dataset.parent.glob(".*.tmp"))

    # -- inputs ----------------------------------------------------------------
    def corpus(self, source_id: str, ids: list[str]):
        self._n += 1
        croot = self.root / f"corpus{self._n}"
        cdir = croot / source_id
        cdir.mkdir(parents=True)
        raw = [
            {"id": i + 1, "tsu_id": tid, "work_id": source_id, "claim": f"Claim {tid}", "source_text": f"Text {tid}"}
            for i, tid in enumerate(ids)
        ]
        (cdir / "tsu.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        transformed = [m._transform_nae_record(r, f"nae_{source_id}") for r in raw]
        return croot, transformed

    def decisions(self, source_id: str, ids: list[str]) -> Path:
        ddir = self.root / f"decisions{self._n}"
        ddir.mkdir(parents=True)
        body = {
            "decisions": [
                {
                    "tsu_id": tid, "work_id": source_id, "gate_id": f"G-{source_id}", "reviewer_id": f"R-{source_id}",
                    "answers": {"Q1": "A", "Q2": "A", "Q3": "A"}, "final_decision": "APPROVED",
                }
                for tid in ids
            ]
        }
        (ddir / f"{source_id}_decisions.json").write_text(json.dumps(body), encoding="utf-8")
        return ddir

    def targets(self) -> list[Path]:
        return [self.dataset, self.manifest, self.registry]

    def write_approval(self, source_id: str, plan_hash: str, **overrides) -> tuple[Path, bytes]:
        approval = {
            "schema_version": 2,
            "source_id": source_id,
            "target_paths_realpath": [str(t) for t in self.targets()],
            "plan_hash": plan_hash,
            "reviewer_id": "검토자-김",
            "gate_id": "G-1",
            "dataset_sha256_before": _ref_sha(self.dataset.read_bytes()),
            "final_decision": "APPROVED",
            "approved_at": "2020-01-01T00:00:00+00:00",
        }
        approval.update(overrides)
        raw = json.dumps(approval, ensure_ascii=False, indent=1).encode("utf-8")
        path = self.approval_dir / "production_targets" / f"{source_id}.json"
        path.write_bytes(raw)
        return path, raw

    def merge(self, source_id: str, ids: list[str], *, plan_hash: str | None = None, **approval_overrides):
        """Prepare corpus/decisions/approval for the CURRENT state and call the real merge_nae_corpus()."""
        croot, transformed = self.corpus(source_id, ids)
        ddir = self.decisions(source_id, ids)
        good_hash = _ref_plan_hash(source_id, transformed, self.targets())
        self.last_approval_path, self.last_approval_raw = self.write_approval(
            source_id, plan_hash or good_hash, **approval_overrides
        )
        self.last_transformed = transformed
        return m.merge_nae_corpus(
            source_id=source_id, data_root=self.prod, nae_corpus_dir=croot, decisions_dir=ddir, config_path=self.config
        )


class Writes:
    """Pass-through spies on the three production writers; records the intent state at each call."""

    def __init__(self, env: Env, monkeypatch):
        self.log: list[tuple[str, str | None]] = []
        self.payloads: list[dict | None] = []
        for name in ("write_tsu_dataset", "save_identity_registry", "write_manifest"):
            real = getattr(m, name)

            def wrapper(*args, _name=name, _real=real, **kwargs):
                phase, data = env.intent_state()
                self.log.append((_name, phase))
                self.payloads.append(data)
                return _real(*args, **kwargs)

            monkeypatch.setattr(m, name, wrapper)

    @property
    def counts(self) -> tuple[int, int, int]:
        names = [n for n, _ in self.log]
        return (names.count("write_tsu_dataset"), names.count("save_identity_registry"), names.count("write_manifest"))


def _fail_kth_strict_fsync(monkeypatch, k: int) -> None:
    real = m._fsync_directory_strict
    state = {"n": 0}

    def injected(directory):
        state["n"] += 1
        if state["n"] == k:
            raise OSError(5, "injected directory fsync failure")
        return real(directory)

    monkeypatch.setattr(m, "_fsync_directory_strict", injected)


@pytest.fixture()
def env(tmp_path):
    return Env(tmp_path)


# ===========================================================================
# 1. write-ahead timing, field exactness, phase progression (S2C-1, 2, 8)
# ===========================================================================

class TestWriteAheadAndFields:
    def test_golden_fixture_intent_fields_and_phase_progression(self, env, monkeypatch):
        """S2C-1/2/8: exact intent at the first write (golden pre-images), phase at each writer, final COMMITTED."""
        env.seed_dataset(GOLDEN_EXISTING_RECORDS)
        env.seed_registry(MERGE_REGISTRY_DOCS)
        spies = Writes(env, monkeypatch)
        result = env.merge("SRC_001", ["TSU-A", "TSU-C"])
        assert result["status"] == "completed"

        # the three writers ran once each, in the contract order, with the intent phase advanced before each one
        assert [n for n, _ in spies.log] == ["write_tsu_dataset", "save_identity_registry", "write_manifest"]
        assert [p for _, p in spies.log] == ["INTENT_WRITTEN", "DATASET_WRITTEN", "REGISTRY_WRITTEN"]
        final_phase, final = env.intent_state()
        assert final_phase == "COMMITTED"

        first = spies.payloads[0]  # intent as it existed when the FIRST production write started
        assert first is not None
        approval_bytes = env.last_approval_raw
        plan_hash = _ref_plan_hash("SRC_001", env.last_transformed, env.targets())
        expected = {
            "intent_version": 1,
            "intent_id": first["intent_id"],
            "phase": "INTENT_WRITTEN",
            "created_at": first["created_at"],
            "source_id": "SRC_001",
            "approval": {
                "path": str(env.last_approval_path.resolve()),
                "artifact_sha256": _ref_sha(approval_bytes),
                "plan_hash": plan_hash,
                "approved_at": "2020-01-01T00:00:00+00:00",
            },
            "plan_hash": plan_hash,
            "targets": [str(t.resolve()) for t in env.targets()],
            "dataset_pre_image": GOLDEN_DATASET_PRE,
            "registry_pre_image": MERGE_REGISTRY_PRE,
            "mutation_plan": {
                "planned_tsu_ids": ["TSU-A", "TSU-C"],
                "new_tsu_ids": ["TSU-C"],
                "new_document_ids": ["nae_SRC_001"],
                "new_record_count": 1,
            },
        }
        expected["intent_content_sha256"] = _ref_checksum(expected)
        assert first == expected
        assert re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", first["intent_id"])
        assert first["created_at"].endswith("+00:00")

        # every later snapshot differs from the first ONLY in phase and checksum (created_at/intent_id/pre-images untouched)
        for snapshot, phase in ((spies.payloads[1], "DATASET_WRITTEN"), (spies.payloads[2], "REGISTRY_WRITTEN"), (final, "COMMITTED")):
            assert snapshot["phase"] == phase
            assert snapshot["intent_content_sha256"] == _ref_checksum(snapshot)
            assert {k: v for k, v in snapshot.items() if k not in ("phase", "intent_content_sha256")} == {
                k: v for k, v in first.items() if k not in ("phase", "intent_content_sha256")
            }
            assert snapshot["intent_content_sha256"] != first["intent_content_sha256"]
        # the merge itself really happened (dataset gained exactly the new TSU, registry gained the new document)
        assert [json.loads(l)["tsu_id"] for l in env.dataset.read_text().splitlines()] == ["TSU-B", "TSU-A", "TSU-C"]
        assert "nae_SRC_001" in json.loads(env.registry.read_text())["documents"]

    def test_new_document_ids_exclude_documents_already_registered(self, env, monkeypatch):
        """S2C-2: a document that is already in the registry is not listed in new_document_ids."""
        env.seed_registry({"nae_SRC_001": {"document_id": "nae_SRC_001", "title": "old"}})
        spies = Writes(env, monkeypatch)
        env.merge("SRC_001", ["TSU-1"])
        plan = spies.payloads[0]["mutation_plan"]
        assert plan["new_document_ids"] == []
        assert plan["new_tsu_ids"] == ["TSU-1"] and plan["planned_tsu_ids"] == ["TSU-1"] and plan["new_record_count"] == 1

    def test_first_write_happens_after_intent_exists_even_for_empty_dataset(self, env, monkeypatch):
        """S2C-1: the intent file exists, is valid, and is INTENT_WRITTEN when the first production write starts."""
        spies = Writes(env, monkeypatch)
        env.merge("S1", ["TSU-1", "TSU-2"])
        assert spies.log[0] == ("write_tsu_dataset", "INTENT_WRITTEN")
        assert spies.payloads[0]["dataset_pre_image"] == []
        assert spies.payloads[0]["plan_hash"] == _ref_plan_hash("S1", env.last_transformed, env.targets())
        m._validate_intent_payload(_bytes(spies.payloads[0]))  # complete payload passes the full validator

    def test_intent_failure_to_exist_before_write_is_visible(self, env, monkeypatch):
        """S2C-1 negative control: the spy really sees 'no intent' when none exists (the spy is not blind)."""
        phases = []
        real = m.write_tsu_dataset
        monkeypatch.setattr(m, "write_tsu_dataset", lambda *a, **k: (phases.append(env.intent_state()[0]), real(*a, **k))[1])
        # non-production merge: no intent file at all at write time
        other = env.root / "nonprod"
        (other / "output" / "bench").mkdir(parents=True)
        (other / "data" / "제련완성본" / "registry").mkdir(parents=True)
        (other / "output" / "bench" / "tsu_dataset.jsonl").write_text("", encoding="utf-8")
        (other / "output" / "bench" / "tsu_manifest.json").write_text("{}", encoding="utf-8")
        (other / "data" / "제련완성본" / "registry" / "documents.json").write_text(json.dumps({"documents": {}}), encoding="utf-8")
        croot, _ = env.corpus("NP", ["TSU-9"])
        ddir = env.decisions("NP", ["TSU-9"])
        result = m.merge_nae_corpus(source_id="NP", data_root=other, nae_corpus_dir=croot, decisions_dir=ddir, config_path=env.config)
        assert result["status"] == "completed"
        assert phases == [None]  # env.intent_path belongs to the production tree; none was written there
        assert not (other / "output" / "bench" / INTENT_NAME).exists()  # non-production: no intent at all


# ===========================================================================
# 2. S2-B binding is still enforced and no intent is created for a rejected plan (M35 etc.)
# ===========================================================================

class TestPlanHashStillBinds:
    def test_forged_plan_hash_blocks_before_any_write_and_before_any_intent(self, env, monkeypatch):
        spies = Writes(env, monkeypatch)
        before = env.target_hashes()
        with pytest.raises(CorpusMutationBlockedError, match="PLAN_HASH_MISMATCH"):
            env.merge("S1", ["TSU-1"], plan_hash="sha256:" + "0" * 64)
        assert spies.counts == (0, 0, 0)
        assert env.target_hashes() == before
        assert env.intent_raw() is None

    def test_plan_hash_one_character_off_blocks(self, env, monkeypatch):
        croot, transformed = env.corpus("S1", ["TSU-1"])
        good = _ref_plan_hash("S1", transformed, env.targets())
        bad = good[:-1] + ("0" if good[-1] != "0" else "1")
        spies = Writes(env, monkeypatch)
        env.write_approval("S1", bad)
        with pytest.raises(CorpusMutationBlockedError, match="PLAN_HASH_MISMATCH"):
            m.merge_nae_corpus(source_id="S1", data_root=env.prod, nae_corpus_dir=croot, decisions_dir=env.decisions("S1", ["TSU-1"]), config_path=env.config)
        assert spies.counts == (0, 0, 0) and env.intent_raw() is None


# ===========================================================================
# 3. existing intent handling (S2C-5, S2C-22) through the real merge
# ===========================================================================

def _committed_intent_for(env: Env, **overrides) -> dict:
    """A valid COMMITTED intent for THIS environment's targets (built by hand, not by the implementation)."""
    base = _fixed_payload(
        phase="COMMITTED",
        targets=[str(t.resolve()) for t in env.targets()],
        dataset_pre_image=[], registry_pre_image=[],
        mutation_plan={"planned_tsu_ids": [], "new_tsu_ids": [], "new_document_ids": [], "new_record_count": 0},
    )
    base.update(overrides)
    return _sealed(base)


class TestExistingIntent:
    @pytest.mark.parametrize("phase", ["INTENT_WRITTEN", "DATASET_WRITTEN", "REGISTRY_WRITTEN"])
    def test_incomplete_intent_blocks_new_merge(self, env, monkeypatch, phase):
        payload = _committed_intent_for(env, phase=phase)
        env.intent_path.write_bytes(_bytes(payload))
        raw, before = env.intent_raw(), env.target_hashes()
        spies = Writes(env, monkeypatch)
        with pytest.raises(CorpusMutationBlockedError, match="incomplete intent exists"):
            env.merge("S2", ["TSU-2"])
        assert spies.counts == (0, 0, 0) and env.target_hashes() == before and env.intent_raw() == raw

    @pytest.mark.parametrize(
        "name,raw,reason",
        [
            ("garbage", b"garbage{", "invalid JSON"),
            ("not-utf8", b"\xff\xfe{}", "not valid UTF-8"),
            ("empty-object", b"{}", "key set mismatch"),
            ("top-level-list", b"[]", "top level must be a JSON object"),
        ],
    )
    def test_unreadable_or_wrong_shape_intent_blocks(self, env, monkeypatch, name, raw, reason):
        env.intent_path.write_bytes(raw)
        before = env.target_hashes()
        spies = Writes(env, monkeypatch)
        with pytest.raises(CorpusMutationBlockedError, match=reason):
            env.merge("S2", ["TSU-2"])
        assert spies.counts == (0, 0, 0) and env.target_hashes() == before and env.intent_raw() == raw

    def _tamper_cases(self, env):
        good = _committed_intent_for(env)
        cases = {}
        t = dict(good); t["source_id"] = "tampered"                       # valid shape, stale checksum
        cases["checksum-mismatch"] = (_bytes(t), "intent_content_sha256 mismatch")
        cases["unknown-key"] = (_bytes(_sealed({**good, "extra": 1})), "key set mismatch")
        cases["bool-version"] = (_bytes(_sealed({**good, "intent_version": True})), "intent_version")
        cases["float-version"] = (_bytes(_sealed({**good, "intent_version": 1.0})), "intent_version")
        cases["bad-phase"] = (_bytes(_sealed({**good, "phase": "DONE"})), "phase is not a known IntentPhase")
        raw = _bytes(good).decode("utf-8")
        cases["duplicate-key"] = (raw[:-1].encode() + b',"phase":"COMMITTED"}', "duplicate JSON key")
        cases["nan-constant"] = (raw.replace('"new_record_count":0', '"new_record_count":NaN').encode(), "unsupported JSON constant")
        return cases

    @pytest.mark.parametrize(
        "case",
        ["checksum-mismatch", "unknown-key", "bool-version", "float-version", "bad-phase", "duplicate-key", "nan-constant"],
    )
    def test_committed_looking_but_invalid_intent_blocks(self, env, monkeypatch, case):
        raw, reason = self._tamper_cases(env)[case]
        env.intent_path.write_bytes(raw)
        before = env.target_hashes()
        spies = Writes(env, monkeypatch)
        with pytest.raises(CorpusMutationBlockedError, match=reason):
            env.merge("S2", ["TSU-2"])
        assert spies.counts == (0, 0, 0) and env.target_hashes() == before and env.intent_raw() == raw

    def test_valid_committed_intent_for_same_targets_is_replaced_by_a_new_write_ahead_intent(self, env, monkeypatch):
        """S2C-5/22: replacement must produce a NEW intent (new id, new approval, pre-image of the current state)."""
        env.seed_dataset(GOLDEN_EXISTING_RECORDS)
        old = _committed_intent_for(env)
        env.intent_path.write_bytes(_bytes(old))
        spies = Writes(env, monkeypatch)
        result = env.merge("S2", ["TSU-A", "TSU-9"])
        assert result["status"] == "completed"
        first = spies.payloads[0]
        assert first["intent_id"] != old["intent_id"] and first["source_id"] == "S2" and first["phase"] == "INTENT_WRITTEN"
        assert [r[0] for r in first["dataset_pre_image"]] == ["TSU-A", "TSU-B"]
        assert first["mutation_plan"]["new_tsu_ids"] == ["TSU-9"] and first["mutation_plan"]["planned_tsu_ids"] == ["TSU-9", "TSU-A"]
        assert env.intent_state()[0] == "COMMITTED" and env.intent_state()[1]["intent_id"] == first["intent_id"]

    def test_committed_intent_for_other_targets_is_not_replaced(self, env, monkeypatch):
        other = _committed_intent_for(
            env, targets=["/other/output/bench/tsu_dataset.jsonl", "/other/output/bench/tsu_manifest.json", "/other/data/r/documents.json"]
        )
        env.intent_path.write_bytes(_bytes(other))
        raw, before = env.intent_raw(), env.target_hashes()
        spies = Writes(env, monkeypatch)
        with pytest.raises(CorpusMutationBlockedError, match="different targets"):
            env.merge("S2", ["TSU-2"])
        assert spies.counts == (0, 0, 0) and env.target_hashes() == before and env.intent_raw() == raw

    @pytest.mark.parametrize("which", [0, 1, 2])
    def test_each_target_position_is_compared(self, env, monkeypatch, which):
        targets = [str(t.resolve()) for t in env.targets()]
        targets[which] = "/somewhere/else/" + Path(targets[which]).name
        env.intent_path.write_bytes(_bytes(_committed_intent_for(env, targets=targets)))
        spies = Writes(env, monkeypatch)
        with pytest.raises(CorpusMutationBlockedError, match="different targets"):
            env.merge("S2", ["TSU-2"])
        assert spies.counts == (0, 0, 0)

    def test_intent_that_is_a_directory_blocks(self, env, monkeypatch):
        env.intent_path.mkdir()
        spies = Writes(env, monkeypatch)
        with pytest.raises(CorpusMutationBlockedError, match="existing intent cannot be read"):
            env.merge("S2", ["TSU-2"])
        assert spies.counts == (0, 0, 0)


# ===========================================================================
# 4. durability and phase-failure contract (S2C-6, 7a, 7b, 9)
# ===========================================================================

class TestDurabilityAndPhaseFailures:
    @pytest.mark.parametrize(
        "k,writes,label",
        [(1, (0, 0, 0), "initial intent"), (2, (1, 0, 0), "DATASET_WRITTEN update"), (3, (1, 1, 0), "REGISTRY_WRITTEN update")],
    )
    def test_strict_directory_fsync_failure_stops_every_later_write(self, env, monkeypatch, k, writes, label):
        _fail_kth_strict_fsync(monkeypatch, k)
        spies = Writes(env, monkeypatch)
        with pytest.raises(CorpusMutationBlockedError, match="intent durable write failed"):
            env.merge("S1", ["TSU-1"])
        assert spies.counts == writes, label
        phase, data = env.intent_state()
        # the (complete) intent file was never deleted or rolled back: it exists and fully validates
        expected_phase = ["INTENT_WRITTEN", "DATASET_WRITTEN", "REGISTRY_WRITTEN"][k - 1]
        assert phase == expected_phase
        m._validate_intent_payload(env.intent_raw())
        assert env.tmp_leftovers() == []

    def test_committed_update_failing_after_replace_never_reports_success(self, env, monkeypatch):
        _fail_kth_strict_fsync(monkeypatch, 4)
        spies = Writes(env, monkeypatch)
        with pytest.raises(CorpusMutationBlockedError, match="intent durable write failed"):
            env.merge("S1", ["TSU-1"])
        assert spies.counts == (1, 1, 1)  # all data was written; the merge still must not report success
        phase, _ = env.intent_state()
        assert phase in ("REGISTRY_WRITTEN", "COMMITTED")  # indeterminate by contract (A-option)
        m._validate_intent_payload(env.intent_raw())  # the file is complete and valid either way
        assert env.tmp_leftovers() == []

    def test_committed_update_failing_before_replace_keeps_previous_intent_and_blocks_next_merge(self, env, monkeypatch):
        real = m._atomic_write_text
        calls = {"n": 0}

        def failing(path, body):
            if Path(path).name == INTENT_NAME:
                calls["n"] += 1
                if calls["n"] == 4:  # initial, DATASET, REGISTRY, COMMITTED
                    raise OSError(28, "injected failure before replace")
            return real(path, body)

        monkeypatch.setattr(m, "_atomic_write_text", failing)
        # the intent bytes just before the failing (4th) write are the REGISTRY_WRITTEN snapshot
        snapshot = {}
        real_manifest = m.write_manifest

        def manifest_spy(*a, **k):
            result = real_manifest(*a, **k)
            snapshot["raw"] = env.intent_raw()
            return result

        monkeypatch.setattr(m, "write_manifest", manifest_spy)
        with pytest.raises(CorpusMutationBlockedError, match="intent durable write failed"):
            env.merge("S1", ["TSU-1"])
        assert env.intent_state()[0] == "REGISTRY_WRITTEN" and env.intent_raw() == snapshot["raw"]
        assert env.tmp_leftovers() == []
        monkeypatch.setattr(m, "_atomic_write_text", real)
        with pytest.raises(CorpusMutationBlockedError, match="incomplete intent exists"):
            env.merge("S2", ["TSU-2"])

    def test_real_directory_fsync_error_is_not_swallowed_at_merge_level(self, env, monkeypatch):
        """Core's atomic writer ignores directory fsync errors; the intent wrapper must not."""
        real_fsync = os.fsync

        def dir_fsync_fails(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise OSError(5, "EIO on directory fsync")
            return real_fsync(fd)

        monkeypatch.setattr(m.os, "fsync", dir_fsync_fails)
        spies = Writes(env, monkeypatch)
        with pytest.raises(CorpusMutationBlockedError, match="intent durable write failed"):
            env.merge("S1", ["TSU-1"])
        assert spies.counts == (0, 0, 0)

    def test_fsync_directory_strict_propagates_oserror(self, tmp_path, monkeypatch):
        def boom(fd):
            raise OSError(5, "EIO")

        monkeypatch.setattr(m.os, "fsync", boom)
        with pytest.raises(OSError):
            m._fsync_directory_strict(tmp_path)
        monkeypatch.undo()
        m._fsync_directory_strict(tmp_path)  # works on a healthy directory

    def test_registry_write_exception_leaves_dataset_written_intent_and_blocks_next_merge(self, env, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("registry write exploded")

        monkeypatch.setattr(m, "save_identity_registry", boom)
        with pytest.raises(RuntimeError, match="registry write exploded"):
            env.merge("S1", ["TSU-1"])
        phase, data = env.intent_state()
        assert phase == "DATASET_WRITTEN"
        assert data["intent_content_sha256"] == _ref_checksum(data)
        assert data["dataset_pre_image"] == [] and data["mutation_plan"]["new_tsu_ids"] == ["TSU-1"]  # initial content preserved
        monkeypatch.undo()
        with pytest.raises(CorpusMutationBlockedError, match="incomplete intent exists"):
            env.merge("S2", ["TSU-2"])

    def test_durable_write_failure_wraps_any_exception_and_keeps_existing_file(self, tmp_path, monkeypatch):
        path = tmp_path / INTENT_NAME
        good = _fixed_payload()
        m._write_intent_durable(path, good)
        before = path.read_bytes()

        def exploding(p, body):
            raise ValueError("disk on fire")

        monkeypatch.setattr(m, "_atomic_write_text", exploding)
        with pytest.raises(CorpusMutationBlockedError, match="intent durable write failed: disk on fire"):
            m._write_intent_durable(path, _fixed_payload(phase="DATASET_WRITTEN"))
        assert path.read_bytes() == before  # never deleted or truncated by the wrapper


# ===========================================================================
# 5. candidate validation first; pre-image fail-closed (S2C-10, S2C-11)
# ===========================================================================

class TestValidationAndPreImages:
    def test_duplicate_tsu_id_in_existing_dataset_fails_before_any_intent_or_write(self, env, monkeypatch):
        rec = {"tsu_id": "TSU-A", "document_id": "doc_a", "content": "x"}
        env.seed_dataset([rec, rec])
        before = env.target_hashes()
        spies = Writes(env, monkeypatch)
        with pytest.raises(ValueError, match="Duplicate tsu_id"):
            env.merge("S2", ["TSU-2"])
        assert env.intent_raw() is None and spies.counts == (0, 0, 0) and env.target_hashes() == before

    @pytest.mark.parametrize(
        "record,reason",
        [
            ({"document_id": "d", "content": "x"}, ""),   # rejected earlier by the core dataset validator
            ({"tsu_id": "", "document_id": "d"}, None),
            ({"tsu_id": "TSU-A", "content": "x"}, "no valid str document_id"),
            ({"tsu_id": "TSU-A", "document_id": 7}, "no valid str document_id"),
        ],
    )
    def test_existing_record_without_valid_ids_blocks_without_intent(self, env, monkeypatch, record, reason):
        env.seed_dataset([record])
        before = env.target_hashes()
        spies = Writes(env, monkeypatch)
        with pytest.raises((CorpusMutationBlockedError, ValueError, KeyError), match=reason):
            env.merge("S2", ["TSU-2"])
        assert env.intent_raw() is None and spies.counts == (0, 0, 0) and env.target_hashes() == before

    def test_dataset_pre_image_golden_and_completeness(self):
        assert m._build_dataset_pre_image(GOLDEN_EXISTING_RECORDS) == GOLDEN_DATASET_PRE
        many = [{"tsu_id": f"T{i:03d}", "document_id": "d"} for i in range(50)]
        rows = m._build_dataset_pre_image(many)
        assert len(rows) == 50 and [r[0] for r in rows] == sorted(r[0] for r in rows)  # every record, sorted

    @pytest.mark.parametrize(
        "records,reason",
        [
            ([{"tsu_id": "A", "document_id": "d"}, {"tsu_id": "A", "document_id": "d"}], "duplicate tsu_id"),
            ([{"tsu_id": None, "document_id": "d"}], "no valid str tsu_id"),
            ([{"tsu_id": 5, "document_id": "d"}], "no valid str tsu_id"),
            ([{"tsu_id": "A"}], "no valid str document_id"),
            ([{"tsu_id": "A", "document_id": ""}], "no valid str document_id"),
            (["not-a-dict"], "is not an object"),
            ([{"tsu_id": "A", "document_id": "d", "bad": float("nan")}], "canonically serialisable"),
        ],
    )
    def test_dataset_pre_image_builder_is_fail_closed(self, records, reason):
        with pytest.raises(CorpusMutationBlockedError, match=reason):
            m._build_dataset_pre_image(records)

    def test_registry_pre_image_golden_excludes_only_the_allowlist(self):
        assert m._build_registry_pre_image({"documents": GOLDEN_REGISTRY_DOCS}) == GOLDEN_REGISTRY_PRE
        base = {"documents": {"d": {"document_id": "d", "title": "t", "pipeline_state": "INDEXED"}}}
        fp = m._build_registry_pre_image(base)
        for field in ("excluded_at", "exclude_reason"):  # allowlist: not part of the fingerprint
            with_field = {"documents": {"d": {**base["documents"]["d"], field: "x"}}}
            assert m._build_registry_pre_image(with_field) == fp
        changed = {"documents": {"d": {**base["documents"]["d"], "pipeline_state": "FAILED"}}}
        assert m._build_registry_pre_image(changed) != fp  # every other field is compared

    @pytest.mark.parametrize(
        "registry,reason",
        [
            ({}, "no 'documents' object"),
            ({"documents": []}, "no 'documents' object"),
            ({"documents": {"d": "not-a-dict"}}, "is not an object"),
            ({"documents": {"d": {"document_id": "other"}}}, "differs from its key"),
            ({"documents": {"d": {"nested": {1: "int key"}}}}, "non-str key"),
            ({"documents": {"d": {"list": [{2: "x"}]}}}, "non-str key"),
            ({"documents": {"d": {"v": float("inf")}}}, "canonically serialisable"),
            ({"documents": {"": {"title": "t"}}}, "non-empty str"),
        ],
    )
    def test_registry_pre_image_builder_is_fail_closed(self, registry, reason):
        with pytest.raises(CorpusMutationBlockedError, match=reason):
            m._build_registry_pre_image(registry)

    def test_registry_pre_image_is_sorted_by_document_id(self):
        docs = {k: {"title": k} for k in ("z", "a", "m")}
        assert [r[0] for r in m._build_registry_pre_image({"documents": docs})] == ["a", "m", "z"]

    def test_mutation_plan_builder(self):
        new_records = [{"tsu_id": "T9"}, {"tsu_id": "T1"}]
        plan = m._build_mutation_plan(
            {"T1", "T9", "T5"}, new_records, [["doc_x", "0" * 64]],
            {Path("p1"): {"document_id": "doc_x"}, Path("p2"): {"document_id": "doc_y"}},
        )
        assert plan == {
            "planned_tsu_ids": ["T1", "T5", "T9"], "new_tsu_ids": ["T1", "T9"], "new_document_ids": ["doc_y"], "new_record_count": 2,
        }
        with pytest.raises(CorpusMutationBlockedError, match="duplicate tsu_id"):
            m._build_mutation_plan({"T1"}, [{"tsu_id": "T1"}, {"tsu_id": "T1"}], [], {})

    def test_build_intent_payload_resolves_targets_and_checks_before_sealing(self, tmp_path):
        approval = m.ApprovalEvaluation(
            state=ApprovalState.VALID, reason_code=None, source_id="S1", approved_at="2020-01-01T00:00:00+00:00",
            dataset_sha256_before="0" * 64, plan_hash="sha256:" + "a" * 64, artifact_sha256="b" * 64, artifact_path=str(tmp_path / "a.json"),
        )
        unresolved = [tmp_path / "x" / ".." / "d.jsonl", tmp_path / "m.json", tmp_path / "sub" / ".." / "r.json"]
        plan = {"planned_tsu_ids": [], "new_tsu_ids": [], "new_document_ids": [], "new_record_count": 0}
        payload = m._build_intent_payload("S1", approval, unresolved, [], [], plan)
        assert payload["targets"] == [str(p.resolve()) for p in unresolved]  # resolved, no '..' segments
        assert payload["source_id"] == "S1" and payload["approval"]["approved_at"] == "2020-01-01T00:00:00+00:00"
        assert payload["intent_content_sha256"] == _ref_checksum(payload)
        rejected = m.ApprovalEvaluation(state=ApprovalState.REJECTED, reason_code=ApprovalReasonCode.MALFORMED, source_id="S1")
        with pytest.raises(CorpusMutationBlockedError, match="VALID approval"):
            m._build_intent_payload("S1", rejected, unresolved, [], [], plan)


# ===========================================================================
# 6. validator (S2C-3, 4, 21), checksum, phase transitions
# ===========================================================================

class TestValidator:
    def test_golden_checksums_and_valid_payload(self):
        assert _fixed_payload()["intent_content_sha256"] == GOLDEN_FIXED_CHECKSUM_INTENT_WRITTEN
        assert _fixed_payload(phase="COMMITTED")["intent_content_sha256"] == GOLDEN_FIXED_CHECKSUM_COMMITTED
        assert m._intent_checksum(_fixed_payload()) == GOLDEN_FIXED_CHECKSUM_INTENT_WRITTEN
        assert m._intent_checksum(_fixed_payload(phase="COMMITTED")) == GOLDEN_FIXED_CHECKSUM_COMMITTED  # phase IS hashed
        assert m._validate_intent_payload(_bytes(_fixed_payload())) == _fixed_payload()

    @pytest.mark.parametrize(
        "mutate,reason",
        [
            (lambda p: p.pop("phase"), "key set mismatch"),
            (lambda p: p.update(extra=1), "key set mismatch"),
            (lambda p: p.update(intent_version=2), "intent_version"),
            (lambda p: p.update(intent_version=True), "intent_version"),
            (lambda p: p.update(intent_version=1.0), "intent_version"),
            (lambda p: p.update(intent_id="not-a-uuid"), "intent_id"),
            (lambda p: p.update(intent_id="123E4567-E89B-42D3-A456-426614174000"), "intent_id"),
            (lambda p: p.update(intent_id="123e4567-e89b-12d3-a456-426614174000"), "intent_id"),
            (lambda p: p.update(phase="DONE"), "phase is not a known IntentPhase"),
            (lambda p: p.update(created_at="yesterday"), "created_at is not ISO-8601"),
            (lambda p: p.update(created_at="2026-10-05T00:00:00+09:00"), "created_at must be UTC"),
            (lambda p: p.update(created_at="2026-10-05T00:00:00"), "created_at must be UTC"),
            (lambda p: p.update(created_at=5), "created_at must be str"),
            (lambda p: p.update(source_id="../x"), "source_id violates"),
            (lambda p: p.update(source_id=""), "source_id violates"),
            (lambda p: p.update(plan_hash="sha256:" + "B" * 64, approval={**p["approval"], "plan_hash": "sha256:" + "B" * 64}), "plan_hash must be sha256"),
            (lambda p: p.update(plan_hash="sha256:" + "c" * 64), "plan_hash differs from approval.plan_hash"),
            (lambda p: p["approval"].pop("path"), "approval must be an object"),
            (lambda p: p["approval"].update(path="relative/x.json"), "approval.path"),
            (lambda p: p["approval"].update(artifact_sha256="A" * 64), "artifact_sha256"),
            (lambda p: p["approval"].update(approved_at=1), "approval.approved_at"),
            (lambda p: p.update(targets=["/a", "/b"]), "targets must be 3 absolute"),
            (lambda p: p.update(targets=["/a", "/b", "rel"]), "targets must be 3 absolute"),
            (lambda p: p.update(dataset_pre_image="x"), "dataset_pre_image must be a list"),
            (lambda p: p.update(dataset_pre_image=[["A", "d"]]), "dataset_pre_image rows"),
            (lambda p: p.update(dataset_pre_image=[["A", "d", "g" * 64]]), "content_sha256"),
            (lambda p: p.update(dataset_pre_image=[["", "d", "a" * 64]]), "non-empty str"),
            (lambda p: p.update(dataset_pre_image=[["B", "d", "a" * 64], ["A", "d", "a" * 64]]), "strictly ascending"),
            (lambda p: p.update(dataset_pre_image=[["A", "d", "a" * 64], ["A", "d", "a" * 64]]), "strictly ascending"),
            (lambda p: p.update(registry_pre_image=[["b", "a" * 64], ["a", "a" * 64]]), "strictly ascending"),
            (lambda p: p.update(registry_pre_image=[["a", "xyz"]]), "invalid document_id/entry_sha256"),
            (lambda p: p.update(mutation_plan={**p["mutation_plan"], "extra": 1}), "mutation_plan must have exactly"),
            (lambda p: p["mutation_plan"].update(planned_tsu_ids=["TSU-C", "TSU-A"]), "strictly ascending"),
            (lambda p: p["mutation_plan"].update(new_tsu_ids=["TSU-C", "TSU-C"]), "strictly ascending"),
            (lambda p: p["mutation_plan"].update(new_record_count=2), "new_record_count"),
            (lambda p: p["mutation_plan"].update(new_record_count=True), "new_record_count"),
            (lambda p: p["mutation_plan"].update(new_record_count=1.0), "new_record_count"),
            # invariant 1: new_tsu_ids subset of planned_tsu_ids
            (lambda p: p["mutation_plan"].update(planned_tsu_ids=["TSU-A"]), "subset of planned_tsu_ids"),
            # invariant 2: new ids must not already exist in the dataset pre-image
            (lambda p: p["mutation_plan"].update(new_tsu_ids=["TSU-A", "TSU-C"], new_record_count=2), "must not already exist in dataset_pre_image"),
            # invariant 3: planned ids that are not new must exist in the pre-image
            (lambda p: p["mutation_plan"].update(planned_tsu_ids=["TSU-A", "TSU-C", "TSU-Z"]), "planned ids that are not new must exist"),
            # new_document_ids must not already be in the registry pre-image
            (lambda p: p["mutation_plan"].update(new_document_ids=["doc_a"]), "new_document_ids must not already exist"),
        ],
    )
    def test_checksum_valid_but_schema_invalid_is_rejected(self, mutate, reason):
        """S2C-3/4/21: the checksum is recomputed AFTER the mutation, so only the schema can reject it."""
        payload = json.loads(json.dumps(_fixed_payload()))
        mutate(payload)
        with pytest.raises(CorpusMutationBlockedError, match=reason):
            m._validate_intent_payload(_bytes(_sealed(payload)))

    @pytest.mark.parametrize("field", ["intent_id", "created_at", "source_id", "targets", "dataset_pre_image", "registry_pre_image", "mutation_plan", "approval", "phase"])
    def test_any_changed_field_without_resealing_breaks_the_checksum(self, field):
        payload = json.loads(json.dumps(_fixed_payload()))
        replacements = {
            "intent_id": "223e4567-e89b-42d3-a456-426614174000", "created_at": "2026-10-06T00:00:00+00:00", "source_id": "SRC_002",
            "plan_hash": "sha256:" + "d" * 64, "targets": ["/p/x", "/p/y", "/p/z"],
            "dataset_pre_image": [["TSU-A", "doc_a", "0" * 64]], "registry_pre_image": [],
            "mutation_plan": {"planned_tsu_ids": [], "new_tsu_ids": [], "new_document_ids": [], "new_record_count": 0},
            "approval": {**payload["approval"], "approved_at": "2026-10-05T00:00:00+00:00"}, "phase": "COMMITTED",
        }
        payload[field] = replacements[field]
        with pytest.raises(CorpusMutationBlockedError, match="intent_content_sha256 mismatch"):
            m._validate_intent_payload(_bytes(payload))

    def test_checksum_must_be_lowercase_hex64(self):
        payload = _fixed_payload()
        payload["intent_content_sha256"] = "A" * 64
        with pytest.raises(CorpusMutationBlockedError, match="lowercase hex64"):
            m._validate_intent_payload(_bytes(payload))

    @pytest.mark.parametrize(
        "raw,reason",
        [
            (lambda: _bytes(_fixed_payload()).replace(b'"phase":"INTENT_WRITTEN"', b'"phase":"INTENT_WRITTEN","phase":"COMMITTED"'), "duplicate JSON key"),
            (lambda: _bytes(_fixed_payload()).replace(b'"new_record_count":1', b'"new_record_count":NaN'), "unsupported JSON constant"),
            (lambda: _bytes(_fixed_payload()).replace(b'"new_record_count":1', b'"new_record_count":Infinity'), "unsupported JSON constant"),
            (lambda: _bytes(_fixed_payload()).replace(b'"new_record_count":1', b'"new_record_count":-Infinity'), "unsupported JSON constant"),
            (lambda: b"\xff\xfe\x00", "not valid UTF-8"),
            (lambda: b"{not json", "invalid JSON"),
            (lambda: b"[]", "top level must be a JSON object"),
            (lambda: b"null", "top level must be a JSON object"),
        ],
    )
    def test_parser_level_rejections(self, raw, reason):
        with pytest.raises(CorpusMutationBlockedError, match=reason):
            m._validate_intent_payload(raw())

    def test_non_bytes_input_is_rejected(self):
        with pytest.raises(CorpusMutationBlockedError, match="intent bytes required"):
            m._validate_intent_payload("{}")  # type: ignore[arg-type]

    def test_advance_phase_only_follows_the_legal_order_and_changes_only_phase_and_checksum(self, tmp_path):
        path = tmp_path / INTENT_NAME
        payload = _fixed_payload()
        for current, nxt in (("INTENT_WRITTEN", "DATASET_WRITTEN"), ("DATASET_WRITTEN", "REGISTRY_WRITTEN"), ("REGISTRY_WRITTEN", "COMMITTED")):
            assert payload["phase"] == current
            advanced = m._advance_intent_phase(path, payload, IntentPhase(nxt))
            assert advanced["phase"] == nxt and advanced["intent_content_sha256"] == _ref_checksum(advanced)
            assert {k: v for k, v in advanced.items() if k not in ("phase", "intent_content_sha256")} == {
                k: v for k, v in payload.items() if k not in ("phase", "intent_content_sha256")
            }
            assert json.loads(path.read_bytes()) == advanced  # the durable file equals the returned in-memory payload
            payload = advanced
        assert payload["phase"] == "COMMITTED"

    @pytest.mark.parametrize(
        "current,target",
        [
            ("INTENT_WRITTEN", "COMMITTED"), ("INTENT_WRITTEN", "REGISTRY_WRITTEN"), ("INTENT_WRITTEN", "INTENT_WRITTEN"),
            ("DATASET_WRITTEN", "INTENT_WRITTEN"), ("DATASET_WRITTEN", "COMMITTED"), ("REGISTRY_WRITTEN", "DATASET_WRITTEN"),
            ("COMMITTED", "INTENT_WRITTEN"), ("COMMITTED", "COMMITTED"),
        ],
    )
    def test_illegal_phase_transitions_raise_and_write_nothing(self, tmp_path, current, target):
        path = tmp_path / INTENT_NAME
        with pytest.raises(CorpusMutationBlockedError, match="illegal phase transition"):
            m._advance_intent_phase(path, _fixed_payload(phase=current), IntentPhase(target))
        assert not path.exists()

    def test_advance_does_not_reread_the_file(self, tmp_path):
        """The in-memory payload is authoritative: a tampered file on disk does not influence the update."""
        path = tmp_path / INTENT_NAME
        path.write_bytes(b"garbage that is not an intent")
        advanced = m._advance_intent_phase(path, _fixed_payload(), IntentPhase.DATASET_WRITTEN)
        assert advanced["phase"] == "DATASET_WRITTEN" and json.loads(path.read_bytes()) == advanced

    def test_intent_file_path_is_next_to_manifest_and_dataset(self, tmp_path):
        d = tmp_path / "bench"
        d.mkdir()
        assert m._intent_file_path(d / "tsu_manifest.json", d / "tsu_dataset.jsonl") == d / INTENT_NAME
        with pytest.raises(CorpusMutationBlockedError, match="share one directory"):
            m._intent_file_path(d / "tsu_manifest.json", tmp_path / "other" / "tsu_dataset.jsonl")

    def test_intent_file_path_identity_ignores_case_and_nfd_when_the_filesystem_does(self, tmp_path):
        d = tmp_path / "제련Bench"
        d.mkdir()
        import unicodedata
        variant = Path(unicodedata.normalize("NFD", str(d)).replace("Bench", "BENCH"))
        if not (variant.exists() and os.path.samefile(variant, d)):
            pytest.skip("filesystem distinguishes case/NFD variants")
        assert m._intent_file_path(d / "tsu_manifest.json", variant / "tsu_dataset.jsonl") == d / INTENT_NAME

    def test_same_target_identity(self, tmp_path):
        a = tmp_path / "f.json"
        a.write_text("x")
        assert m._same_target(str(a), a) is True
        assert m._same_target(str(a), tmp_path / "g.json") is False
        assert m._same_target(str(tmp_path / "nofile1"), tmp_path / "nofile1") is True  # missing paths: normalised comparison
        assert m._same_target(str(tmp_path / "nofile1"), tmp_path / "nofile2") is False

    def test_no_recovery_resume_or_rollback_logic_exists(self):
        """S2C-17: the intent is only read to decide whether to BLOCK; there is no recovery code path."""
        src = Path(m.__file__).read_text(encoding="utf-8")
        assert not re.search(r"def\s+\w*(recover|resume|rollback|roll_forward|restore)\w*\(", src, re.IGNORECASE)
        readers = [
            name for name, obj in vars(m).items()
            if callable(obj) and getattr(obj, "__module__", "") == m.__name__ and name.startswith("_") and "intent" in name.lower()
            and "INTENT_FILENAME" in getattr(getattr(obj, "__code__", None), "co_names", ())
        ]
        assert readers == ["_intent_file_path"], f"unexpected functions touching the intent file name: {readers}"


# ===========================================================================
# 7. approval bytes binding (S2C-12)
# ===========================================================================

class TestApprovalBytes:
    def _valid_approval(self, tmp_path, env=None) -> tuple[Path, bytes, str]:
        env = env or Env(tmp_path)
        path, raw = env.write_approval("SRC_001", "sha256:" + "a" * 64, reviewer_id="검토자-이순신")
        return path, raw, _ref_sha(env.dataset.read_bytes())

    def test_valid_approval_carries_artifact_identity_of_the_exact_bytes(self, tmp_path):
        path, raw, ds_sha = self._valid_approval(tmp_path)
        assert any(b > 127 for b in raw)  # fixture contains non-ASCII bytes
        res = evaluate_approval_v2(path, dataset_sha256_current=ds_sha, config_path=None) if False else None
        env = Env(tmp_path / "e2")
        path, raw = env.write_approval("SRC_001", "sha256:" + "a" * 64, reviewer_id="검토자-이순신")
        res = evaluate_approval_v2(path, config_path=env.config, expected_target_paths=[str(t) for t in env.targets()], dataset_sha256_current=_ref_sha(env.dataset.read_bytes()))
        assert res.state == ApprovalState.VALID
        assert res.artifact_sha256 == _ref_sha(raw) and res.artifact_path == str(path.resolve())
        assert res.plan_hash == "sha256:" + "a" * 64

    def test_rejected_results_carry_no_artifact_identity(self, tmp_path):
        env = Env(tmp_path)
        path, _ = env.write_approval("SRC_001", "sha256:" + "a" * 64, final_decision="REJECTED")
        res = evaluate_approval_v2(path, config_path=env.config, expected_target_paths=[str(t) for t in env.targets()], dataset_sha256_current=_ref_sha(env.dataset.read_bytes()))
        assert res.state == ApprovalState.REJECTED and res.artifact_sha256 is None and res.artifact_path is None and res.plan_hash is None

    def test_non_utf8_approval_is_rejected_as_malformed_not_raised(self, tmp_path):
        env = Env(tmp_path)
        bad = env.approval_dir / "production_targets" / "BAD.json"
        bad.write_bytes(b"\xff\xfe{}")
        res = evaluate_approval_v2(bad, config_path=env.config, expected_target_paths=[], dataset_sha256_current="0" * 64)
        assert res.state == ApprovalState.REJECTED and res.reason_code == ApprovalReasonCode.MALFORMED
        assert res.artifact_sha256 is None and res.artifact_path is None

    def test_approval_path_that_cannot_be_read_maps_to_malformed(self, tmp_path):
        env = Env(tmp_path)
        directory = env.approval_dir / "production_targets" / "DIR.json"
        directory.mkdir()
        res = evaluate_approval_v2(directory, config_path=env.config, expected_target_paths=[], dataset_sha256_current="0" * 64)
        assert res.state == ApprovalState.REJECTED and res.reason_code == ApprovalReasonCode.MALFORMED  # existing mapping preserved

    def test_the_approval_file_is_read_exactly_once_during_a_merge(self, env, monkeypatch):
        reads = []
        real_read_bytes, real_read_text = Path.read_bytes, Path.read_text

        def counting_bytes(self_, *a, **k):
            reads.append(("bytes", self_.name))
            return real_read_bytes(self_, *a, **k)

        def counting_text(self_, *a, **k):
            reads.append(("text", self_.name))
            return real_read_text(self_, *a, **k)

        monkeypatch.setattr(Path, "read_bytes", counting_bytes)
        monkeypatch.setattr(Path, "read_text", counting_text)
        env.merge("S1", ["TSU-1"])
        approval_reads = [r for r in reads if r[1] == "S1.json"]
        assert approval_reads == [("bytes", "S1.json")]  # one read, as bytes, never re-read as text

    def test_merge_records_artifact_sha_of_the_bytes_that_were_validated(self, env, monkeypatch):
        spies = Writes(env, monkeypatch)
        env.merge("S1", ["TSU-1"])
        assert spies.payloads[0]["approval"]["artifact_sha256"] == _ref_sha(env.last_approval_raw)
        assert spies.payloads[0]["approval"]["path"] == str(env.last_approval_path.resolve())


# ===========================================================================
# 8. non-production, normal merge, scale measurement
# ===========================================================================

class TestNormalAndScale:
    def test_normal_merge_ends_committed_with_valid_intent(self, env):
        result = env.merge("S1", ["TSU-1", "TSU-2"])
        assert result["status"] == "completed" and result["total_records"] == 2
        phase, data = env.intent_state()
        assert phase == "COMMITTED"
        assert m._validate_intent_payload(env.intent_raw()) == data
        assert env.tmp_leftovers() == []

    def test_second_sequential_merge_replaces_the_committed_intent(self, env):
        env.merge("S1", ["TSU-1"])
        first_id = env.intent_state()[1]["intent_id"]
        env.merge("S2", ["TSU-2"])
        phase, data = env.intent_state()
        assert phase == "COMMITTED" and data["intent_id"] != first_id and data["source_id"] == "S2"
        assert [r[0] for r in data["dataset_pre_image"]] == ["TSU-1"]  # the pre-image is the state right before THIS merge

    def test_scale_measurement_is_reported(self, tmp_path, record_property, capsys):
        """S2C-15: measurement only (no thresholds)."""
        n = 119_595
        records = [{"tsu_id": f"TSU-{i:07d}", "document_id": f"doc_{i % 92:03d}", "content": "x" * 200} for i in range(n)]
        t0 = time.perf_counter()
        pre = m._build_dataset_pre_image(records)
        t1 = time.perf_counter()
        registry = {"documents": {f"doc_{i:03d}": {"document_id": f"doc_{i:03d}", "title": "t"} for i in range(92)}}
        rpre = m._build_registry_pre_image(registry)
        approval = m.ApprovalEvaluation(
            state=ApprovalState.VALID, reason_code=None, source_id="S", approved_at="2020-01-01T00:00:00+00:00",
            dataset_sha256_before="0" * 64, plan_hash="sha256:" + "a" * 64, artifact_sha256="b" * 64, artifact_path=str(tmp_path / "a.json"),
        )
        plan = {"planned_tsu_ids": ["TSU-9999999"], "new_tsu_ids": ["TSU-9999999"], "new_document_ids": [], "new_record_count": 1}
        payload = m._build_intent_payload("S", approval, [tmp_path / "d", tmp_path / "m", tmp_path / "r"], pre, rpre, plan)
        t2 = time.perf_counter()
        path = tmp_path / INTENT_NAME
        m._write_intent_durable(path, payload)
        t3 = time.perf_counter()
        m._advance_intent_phase(path, payload, IntentPhase.DATASET_WRITTEN)
        t4 = time.perf_counter()
        size = path.stat().st_size
        assert len(pre) == n and size > 0
        record_property("records", n)
        record_property("intent_size_bytes", size)
        record_property("pre_image_seconds", round(t1 - t0, 3))
        record_property("payload_build_and_self_validate_seconds", round(t2 - t1, 3))
        record_property("first_durable_write_seconds", round(t3 - t2, 3))
        record_property("one_phase_update_seconds", round(t4 - t3, 3))
        with capsys.disabled():
            print(
                f"\n[S2C-15] records={n} intent_size={size/1e6:.1f}MB pre_image={t1-t0:.2f}s "
                f"build+validate={t2-t1:.2f}s first_write={t3-t2:.2f}s phase_update={t4-t3:.2f}s"
            )
