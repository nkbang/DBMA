"""tests/test_merge_e0.py — S2-E E-0 (CUE-authored; author-side verification, mutation-checked).

E-0a: the five extracted helpers keep the behaviour of the inline code they replaced.
E-0b: a durability barrier (`_ensure_durable`) runs after a successful registry save and before the REGISTRY_WRITTEN phase
      advance and the manifest write.

Rules this file follows:
  * The REAL `merge_nae_corpus` is always executed. Production protections (approval, plan_hash, production identity,
    locks, intent) are never mocked.
  * Allowed test doubles: a frozen clock / constant git hash, observation spies that call the original function, and
    injected I/O failures (real os.fsync failures).
  * `TestRealMergeGolden` only needs behaviour that already exists at the base revision e4d721ad, so its constants are
    reproducible from the base tree (see the golden generator in the evidence package).
  * No skips. Fixed roots are replaced by the token <ROOT> in observed text (the only normalisation).
"""

from __future__ import annotations

import contextlib
import copy
import datetime as _dtmod
import hashlib
import io
import json
import os
import re
import stat
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import core.tsu_builder as tb  # noqa: E402
import scripts.merge_nae_corpus as m  # noqa: E402
from scripts.corpus_approval_gate import CorpusMutationBlockedError  # noqa: E402
from test_merge_intent import Env  # noqa: E402  (sibling fixture: mock production + approval artifacts)

ROOT_TOKEN = "<ROOT>"


# ---------------------------------------------------------------------------
# Frozen clock (the only global double besides spies/failure injection)
# ---------------------------------------------------------------------------

class _FrozenDatetime(_dtmod.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 5, 12, 0, 0, tzinfo=tz)


def _freeze(monkeypatch):
    monkeypatch.setattr(m, "datetime", _FrozenDatetime)
    ns = types.SimpleNamespace(**{k: getattr(_dtmod, k) for k in dir(_dtmod) if not k.startswith("_")})
    ns.datetime = _FrozenDatetime
    monkeypatch.setattr(tb, "datetime", ns)
    monkeypatch.setattr(tb, "_git_commit_hash", lambda *a, **k: "FIXED_GIT_HASH")


@pytest.fixture()
def frozen(monkeypatch):
    _freeze(monkeypatch)


@pytest.fixture()
def env(tmp_path):
    return Env(tmp_path)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Scenario observation (shared with the evidence-package golden generator)
# ---------------------------------------------------------------------------

class Layout:
    def __init__(self, root: Path, dataset: Path, manifest: Path, registry: Path, intent: Path | None):
        self.root, self.dataset, self.manifest, self.registry, self.intent = root, dataset, manifest, registry, intent


def _make_other_layout(env: Env, name: str = "nonprod") -> Layout:
    other = env.root / name
    (other / "output" / "bench").mkdir(parents=True)
    (other / "data" / "제련완성본" / "registry").mkdir(parents=True)
    ds = other / "output" / "bench" / "tsu_dataset.jsonl"
    mf = other / "output" / "bench" / "tsu_manifest.json"
    rg = other / "data" / "제련완성본" / "registry" / "documents.json"
    ds.write_text("", encoding="utf-8")
    mf.write_text("{}", encoding="utf-8")
    rg.write_text(json.dumps({"documents": {}}), encoding="utf-8")
    return Layout(other, ds, mf, rg, None)


def _prod_layout(env: Env) -> Layout:
    return Layout(env.prod, env.dataset, env.manifest, env.registry, env.intent_path)


_SEED_RECORD = {"tsu_id": "TSU-1", "document_id": "doc_pre", "content": "pre-existing"}


def _run_scenario(env: Env, name: str):
    """Returns (layout, callable) — the callable executes the real merge."""
    if name == "ok_empty":
        return _prod_layout(env), lambda: env.merge("S1", ["TSU-1", "TSU-2"])
    if name == "ok_overlap":
        env.seed_dataset([_SEED_RECORD])
        return _prod_layout(env), lambda: env.merge("S1", ["TSU-1", "TSU-2"])
    if name == "ok_registry_has_doc":
        env.seed_registry({"nae_S1": {"document_id": "nae_S1", "title": "old"}})
        return _prod_layout(env), lambda: env.merge("S1", ["TSU-1"])
    if name == "block_dup_existing":
        env.seed_dataset([_SEED_RECORD, _SEED_RECORD])
        return _prod_layout(env), lambda: env.merge("S1", ["TSU-2"])
    lay = _make_other_layout(env)
    if name == "nonprod_ok":
        croot, _ = env.corpus("NP", ["TSU-7", "TSU-8"])
        ddir = env.decisions("NP", ["TSU-7", "TSU-8"])
        return lay, lambda: m.merge_nae_corpus(source_id="NP", data_root=lay.root, nae_corpus_dir=croot, decisions_dir=ddir, config_path=env.config)
    if name == "nonprod_skipped_other_work":
        croot, _ = env.corpus("OTHER", ["TSU-7"])
        ddir = env.decisions("OTHER", ["TSU-7"])
        return lay, lambda: m.merge_nae_corpus(source_id="NP", data_root=lay.root, nae_corpus_dir=croot, decisions_dir=ddir, config_path=env.config)
    if name == "nonprod_missing_corpus_dir":
        _, _ = env.corpus("NP", ["TSU-7"])
        ddir = env.decisions("NP", ["TSU-7"])
        return lay, lambda: m.merge_nae_corpus(source_id="NP", data_root=lay.root, nae_corpus_dir=env.root / "no_such_corpus", decisions_dir=ddir, config_path=env.config)
    if name == "nonprod_dup_in_corpus":
        croot, _ = env.corpus("NP", ["TSU-7", "TSU-7"])
        ddir = env.decisions("NP", ["TSU-7"])
        return lay, lambda: m.merge_nae_corpus(source_id="NP", data_root=lay.root, nae_corpus_dir=croot, decisions_dir=ddir, config_path=env.config)
    raise KeyError(name)


SCENARIOS = [
    "ok_empty", "ok_overlap", "ok_registry_has_doc", "block_dup_existing",
    "nonprod_ok", "nonprod_skipped_other_work", "nonprod_missing_corpus_dir", "nonprod_dup_in_corpus",
]


def observe(root: Path, name: str, *, raw_stdout: bool = False) -> dict:
    """Run one scenario in a fresh Env under `root` (must not exist) with the real merge; return normalised observations."""
    env = Env(root)
    layout, run = _run_scenario(env, name)
    buf = io.StringIO()
    result = exc = None
    with contextlib.redirect_stdout(buf):
        try:
            result = run()
        except BaseException as e:  # noqa: BLE001
            exc = [type(e).__name__, str(e)]
    roots = {str(root), str(root.resolve())}

    def norm(text: str) -> str:
        for r in sorted(roots, key=len, reverse=True):
            text = text.replace(r, ROOT_TOKEN)
        return text

    def file_sha(p: Path):
        return _sha(p.read_bytes()) if p.exists() else None

    manifest = None
    if layout.manifest.exists():
        manifest = json.loads(layout.manifest.read_text(encoding="utf-8"))
        if "registry_path" in manifest:
            assert manifest["registry_path"] in (str(layout.registry), str(layout.registry.resolve()))
            manifest.pop("registry_path")
    phase = None
    if layout.intent is not None and layout.intent.exists():
        phase = json.loads(layout.intent.read_text(encoding="utf-8"))["phase"]
    obs = {
        "result": json.loads(norm(json.dumps(result, ensure_ascii=False, default=str, sort_keys=True))) if result is not None else None,
        "exc": [exc[0], norm(exc[1])] if exc else None,
        "stdout_sha256": _sha(norm(buf.getvalue()).encode("utf-8")),
        "dataset_sha256": file_sha(layout.dataset),
        "registry_sha256": file_sha(layout.registry),
        "manifest": manifest,
        "intent_phase": phase,
    }
    if raw_stdout:
        obs["stdout_sha256_raw"] = _sha(buf.getvalue().encode("utf-8"))
    return obs


# GOLDEN is produced from the BASE revision e4d721ad by the evidence-package generator (real merge, frozen clock).
# BEGIN GOLDEN
GOLDEN: dict = {'block_dup_existing': {'dataset_sha256': '7fd1223d41497feac5685eed7265f49e9d5dec7e3e898e105b17c9711c01e363',
                        'exc': ['ValueError', "Duplicate tsu_id found: {'TSU-1'}"],
                        'intent_phase': None,
                        'manifest': {},
                        'registry_sha256': 'a50bf35a2630cc8f6b8515cc783771cfbd0f28035ac8c9effde9427073716ec7',
                        'result': None,
                        'stdout_sha256': 'd78645646ced32f3d99369c5e84d8ed0b52a249e4c7bc99f61fe3dd2f824101e'},
 'nonprod_dup_in_corpus': {'dataset_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                           'exc': ['ValueError', "Duplicate tsu_id found: {'TSU-7'}"],
                           'intent_phase': None,
                           'manifest': {},
                           'registry_sha256': 'a50bf35a2630cc8f6b8515cc783771cfbd0f28035ac8c9effde9427073716ec7',
                           'result': None,
                           'stdout_sha256': 'b4cf8a13dce789729c9fc789fe2e02eba212113792fb60518fdf5a740e079693'},
 'nonprod_missing_corpus_dir': {'dataset_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                                'exc': None,
                                'intent_phase': None,
                                'manifest': {},
                                'registry_sha256': 'a50bf35a2630cc8f6b8515cc783771cfbd0f28035ac8c9effde9427073716ec7',
                                'result': {'duplicate_count': 0,
                                           'merged_count': 0,
                                           'reason': "No TSU records found for source='NP' in <ROOT>/no_such_corpus",
                                           'status': 'skipped'},
                                'stdout_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
 'nonprod_ok': {'dataset_sha256': 'd85fafd0c0e94642df7f60e26331d5d14283de208b5fc202622c4cd700c60024',
                'exc': None,
                'intent_phase': None,
                'manifest': {'build_commit': 'FIXED_GIT_HASH',
                             'builder_script': 'scripts/build_tsu_dataset.py',
                             'config_file': 'config.yaml',
                             'config_sha256': None,
                             'dataset_records': 2,
                             'dataset_sha256': 'd85fafd0c0e94642df7f60e26331d5d14283de208b5fc202622c4cd700c60024',
                             'generated_at': '2026-10-05T12:00:00',
                             'registry_sha256': 'a46b07609b7045f4e39d5c789b126b6cf68b24010c825236ddbab678c534e0d9',
                             'source_document_count': 1,
                             'tsu_count': 2},
                'registry_sha256': 'a46b07609b7045f4e39d5c789b126b6cf68b24010c825236ddbab678c534e0d9',
                'result': {'approved_count': 2,
                           'duplicate_count': 0,
                           'existing_records': 0,
                           'manifest_source': 'NP',
                           'nae_records': 2,
                           'new_documents': 1,
                           'new_records_after_dedup': 2,
                           'source_id': 'NP',
                           'status': 'completed',
                           'total_records': 2},
                'stdout_sha256': 'eb123cd364ae9543f40e5582d7b4aa7b27b4269b77e7f34ccd34019f8f7ea497'},
 'nonprod_skipped_other_work': {'dataset_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                                'exc': None,
                                'intent_phase': None,
                                'manifest': {},
                                'registry_sha256': 'a50bf35a2630cc8f6b8515cc783771cfbd0f28035ac8c9effde9427073716ec7',
                                'result': {'duplicate_count': 0,
                                           'merged_count': 0,
                                           'reason': "No TSU records found for source='NP' in <ROOT>/corpus1",
                                           'status': 'skipped'},
                                'stdout_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
 'ok_empty': {'dataset_sha256': '48ad66b50c6bf91237cef83fe204b522516e1fadd0ac4b101b48efc20a7460b7',
              'exc': None,
              'intent_phase': 'COMMITTED',
              'manifest': {'build_commit': 'FIXED_GIT_HASH',
                           'builder_script': 'scripts/build_tsu_dataset.py',
                           'config_file': 'config.yaml',
                           'config_sha256': None,
                           'dataset_records': 2,
                           'dataset_sha256': '48ad66b50c6bf91237cef83fe204b522516e1fadd0ac4b101b48efc20a7460b7',
                           'generated_at': '2026-10-05T12:00:00',
                           'registry_sha256': 'fbe4cffab722942040e1139d051211de3ef971d75d67866e448c94a2c33e3d95',
                           'source_document_count': 1,
                           'tsu_count': 2},
              'registry_sha256': 'fbe4cffab722942040e1139d051211de3ef971d75d67866e448c94a2c33e3d95',
              'result': {'approved_count': 2,
                         'duplicate_count': 0,
                         'existing_records': 0,
                         'manifest_source': 'S1',
                         'nae_records': 2,
                         'new_documents': 1,
                         'new_records_after_dedup': 2,
                         'source_id': 'S1',
                         'status': 'completed',
                         'total_records': 2},
              'stdout_sha256': 'aaaae00cecf3c5b464940be85967804f8d2abcb209bb409a7304b89ae919a692'},
 'ok_overlap': {'dataset_sha256': 'c310958f80055680dad879fd7031f3a90556483b768322e9eb8a3098dfcd91db',
                'exc': None,
                'intent_phase': 'COMMITTED',
                'manifest': {'build_commit': 'FIXED_GIT_HASH',
                             'builder_script': 'scripts/build_tsu_dataset.py',
                             'config_file': 'config.yaml',
                             'config_sha256': None,
                             'dataset_records': 2,
                             'dataset_sha256': 'c310958f80055680dad879fd7031f3a90556483b768322e9eb8a3098dfcd91db',
                             'generated_at': '2026-10-05T12:00:00',
                             'registry_sha256': 'fbe4cffab722942040e1139d051211de3ef971d75d67866e448c94a2c33e3d95',
                             'source_document_count': 1,
                             'tsu_count': 2},
                'registry_sha256': 'fbe4cffab722942040e1139d051211de3ef971d75d67866e448c94a2c33e3d95',
                'result': {'approved_count': 2,
                           'duplicate_count': 1,
                           'existing_records': 1,
                           'manifest_source': 'S1',
                           'nae_records': 2,
                           'new_documents': 1,
                           'new_records_after_dedup': 1,
                           'source_id': 'S1',
                           'status': 'completed',
                           'total_records': 2},
                'stdout_sha256': '0ba5a8d254b6d5b77e84e06273b1ad7b83776fb2de063c7261e8473c07927047'},
 'ok_registry_has_doc': {'dataset_sha256': '25cfa2bb03857b395e4e320ef9c98f831ecc2f410d8c1a786933019234a9a137',
                         'exc': None,
                         'intent_phase': 'COMMITTED',
                         'manifest': {'build_commit': 'FIXED_GIT_HASH',
                                      'builder_script': 'scripts/build_tsu_dataset.py',
                                      'config_file': 'config.yaml',
                                      'config_sha256': None,
                                      'dataset_records': 1,
                                      'dataset_sha256': '25cfa2bb03857b395e4e320ef9c98f831ecc2f410d8c1a786933019234a9a137',
                                      'generated_at': '2026-10-05T12:00:00',
                                      'registry_sha256': '75feba8e24e6238dfecd025d9ea2b30ffb0a8a3dec8e35617d89716d0922a2ac',
                                      'source_document_count': 0,
                                      'tsu_count': 1},
                         'registry_sha256': '75feba8e24e6238dfecd025d9ea2b30ffb0a8a3dec8e35617d89716d0922a2ac',
                         'result': {'approved_count': 1,
                                    'duplicate_count': 0,
                                    'existing_records': 0,
                                    'manifest_source': 'S1',
                                    'nae_records': 1,
                                    'new_documents': 1,
                                    'new_records_after_dedup': 1,
                                    'source_id': 'S1',
                                    'status': 'completed',
                                    'total_records': 1},
                         'stdout_sha256': '287f9429325f66355d6ab34dbb3beec0726c4dc7deeaaf6d45df0fc79ee0ec69'}}
# END GOLDEN


class TestRealMergeGolden:
    """Behaviour that must be identical before and after E-0. These tests also pass on the base tree."""

    @pytest.mark.parametrize("name", SCENARIOS)
    def test_scenario_matches_base_golden(self, tmp_path, frozen, name):
        obs = observe(tmp_path / "fx", name)
        assert obs == GOLDEN[name]

    def test_golden_covers_every_scenario_and_both_outcomes(self):
        assert sorted(GOLDEN) == sorted(SCENARIOS)
        statuses = {k: (v["exc"][0] if v["exc"] else v["result"]["status"]) for k, v in GOLDEN.items()}
        assert statuses["ok_empty"] == "completed" and statuses["ok_overlap"] == "completed"
        assert statuses["ok_registry_has_doc"] == "completed" and statuses["nonprod_ok"] == "completed"
        assert statuses["nonprod_skipped_other_work"] == "skipped" and statuses["nonprod_missing_corpus_dir"] == "skipped"
        assert statuses["block_dup_existing"] == "ValueError" and statuses["nonprod_dup_in_corpus"] == "ValueError"

    def test_blocked_scenarios_leave_every_target_untouched(self, tmp_path, frozen):
        for name in ("block_dup_existing", "nonprod_dup_in_corpus", "nonprod_skipped_other_work"):
            env = Env(tmp_path / name)
            layout, run = _run_scenario(env, name)
            before = [layout.dataset.read_bytes(), layout.manifest.read_bytes(), layout.registry.read_bytes()]
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    run()
                except ValueError:
                    pass
            after = [layout.dataset.read_bytes(), layout.manifest.read_bytes(), layout.registry.read_bytes()]
            assert after == before, name
            assert layout.intent is None or not layout.intent.exists(), name


# ---------------------------------------------------------------------------
# E-0a: extracted helpers vs independent reference implementations of the old inline logic
# ---------------------------------------------------------------------------

def _raw(tsu_id, work_id, book="Book", author="Auth"):
    return {"id": 1, "tsu_id": tsu_id, "work_id": work_id, "claim": f"claim {tsu_id}", "source_text": f"text {tsu_id}", "book": book, "author": author}


def _write_corpus(root: Path) -> Path:
    root.mkdir()
    layout = {
        "doc_a": [_raw("A-1", "S1", "Book A", "Auth A"), _raw("A-2", "S1", "Book A", "Auth A"), _raw("A-X", "OTHER")],
        "doc_b": [_raw("B-1", "S1", "Book B", "Auth B")],
        "doc_c": [_raw("C-1", "OTHER")],
        "doc_e": [],
    }
    for name, recs in layout.items():
        d = root / name
        d.mkdir()
        (d / "tsu.json").write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
    (root / "doc_d_no_tsu").mkdir()
    (root / "notes.txt").write_text("not a directory entry", encoding="utf-8")
    return root


def _ref_collect(corpus_dir: Path, source_id: str):
    if not corpus_dir.exists():
        raise FileNotFoundError(f"NAE corpus directory not found: {corpus_dir}")
    records, info = [], {}
    for item in sorted(corpus_dir.glob("*")):
        if not item.is_dir():
            continue
        f = item / "tsu.json"
        if not f.exists():
            continue
        data = [r for r in json.loads(f.read_text(encoding="utf-8")) if r.get("work_id") == source_id]
        if not data:
            continue
        doc = f"nae_{item.name}"
        info[item] = {"document_id": doc, "title": data[0].get("book", ""), "author": data[0].get("author", ""), "record_count": len(data)}
        for r in data:
            records.append(m._transform_nae_record(r, doc))
    return records, info


def _snapshot_tree(root: Path):
    return sorted((str(p.relative_to(root)), p.stat().st_mtime_ns, p.stat().st_size if p.is_file() else -1) for p in root.rglob("*"))


class TestCollect:
    def test_matches_reference_and_expected_values(self, tmp_path):
        corpus = _write_corpus(tmp_path / "corpus")
        records, info = m._collect_nae_candidates(corpus, "S1")
        ref_records, ref_info = _ref_collect(corpus, "S1")
        assert records == ref_records and info == ref_info
        assert [r["tsu_id"] for r in records] == ["A-1", "A-2", "B-1"]  # sorted dirs, work_id filtered, other works dropped
        assert list(info) == [corpus / "doc_a", corpus / "doc_b"]
        assert info[corpus / "doc_a"] == {"document_id": "nae_doc_a", "title": "Book A", "author": "Auth A", "record_count": 2}
        assert info[corpus / "doc_b"]["record_count"] == 1

    @pytest.mark.parametrize("source_id", ["S1", "OTHER", "NOBODY"])
    def test_other_sources_match_reference(self, tmp_path, source_id):
        corpus = _write_corpus(tmp_path / "corpus")
        assert m._collect_nae_candidates(corpus, source_id) == _ref_collect(corpus, source_id)

    def test_no_match_returns_empty(self, tmp_path):
        corpus = _write_corpus(tmp_path / "corpus")
        assert m._collect_nae_candidates(corpus, "NOBODY") == ([], {})

    def test_missing_directory_raises_with_the_original_message(self, tmp_path):
        missing = tmp_path / "nope"
        with pytest.raises(FileNotFoundError) as e:
            m._collect_nae_candidates(missing, "S1")
        assert str(e.value) == f"NAE corpus directory not found: {missing}"

    def test_read_only_no_disk_writes(self, tmp_path):
        corpus = _write_corpus(tmp_path / "corpus")
        before = _snapshot_tree(corpus)
        m._collect_nae_candidates(corpus, "S1")
        assert _snapshot_tree(corpus) == before

    def test_directory_order_is_sorted(self, tmp_path):
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        for name in ("zz", "aa", "mm"):
            (corpus / name).mkdir()
            (corpus / name / "tsu.json").write_text(json.dumps([_raw(f"{name}-1", "S1")]), encoding="utf-8")
        records, info = m._collect_nae_candidates(corpus, "S1")
        assert [r["tsu_id"] for r in records] == ["aa-1", "mm-1", "zz-1"]
        assert [p.name for p in info] == ["aa", "mm", "zz"]


class TestDedupCompose:
    def test_dedup_matches_reference_preserves_order_and_inputs(self):
        existing = [{"tsu_id": "E1"}, {"tsu_id": "E2"}]
        nae = [{"tsu_id": "N2"}, {"tsu_id": "E1"}, {"tsu_id": "N1"}, {"tsu_id": "N2"}, {"tsu_id": "E2"}]
        e_copy, n_copy = copy.deepcopy(existing), copy.deepcopy(nae)
        out = m._dedup_new_records(nae, existing)
        ids = {r["tsu_id"] for r in existing}
        assert out == [r for r in nae if r["tsu_id"] not in ids]
        assert [r["tsu_id"] for r in out] == ["N2", "N1", "N2"]  # order kept; duplicates inside the candidates are NOT collapsed here
        assert existing == e_copy and nae == n_copy and out is not nae

    def test_dedup_with_nothing_existing_returns_all_as_new_list(self):
        nae = [{"tsu_id": "N1"}]
        out = m._dedup_new_records(nae, [])
        assert out == nae and out is not nae

    def test_dedup_keyerror_semantics_are_preserved(self):
        with pytest.raises(KeyError):
            m._dedup_new_records([{"tsu_id": "N"}], [{"no_id": 1}])
        with pytest.raises(KeyError):
            m._dedup_new_records([{"no_id": 1}], [{"tsu_id": "E"}])

    def test_compose_order_new_list_inputs_unchanged(self):
        existing, new = [{"tsu_id": "E"}], [{"tsu_id": "N"}]
        e_copy, n_copy = copy.deepcopy(existing), copy.deepcopy(new)
        out = m._compose_candidate_dataset(existing, new)
        assert out == existing + new and [r["tsu_id"] for r in out] == ["E", "N"]
        assert out is not existing and out is not new
        assert existing == e_copy and new == n_copy
        out.append({"tsu_id": "X"})
        assert existing == e_copy  # the result does not alias an input


class TestRegistryEntry:
    INFO = {"document_id": "nae_doc_a", "title": "Book A", "author": "Auth A", "record_count": 2}

    def test_new_registry_entry_exact_literal(self, tmp_path):
        info = copy.deepcopy(self.INFO)
        entry = m._new_registry_entry(tmp_path / "doc_a", info, "2026-10-05T12:00:00", "2026-10-05T12:00:01")
        assert entry == {
            "document_id": "nae_doc_a", "source_file": "doc_a.jsonl", "title": "Book A", "author": "Auth A",
            "status": "processed", "chunk_count": 2, "language": "en", "source_type": "nae_canonical", "doc_type": "신학",
            "ingest_status": "PROCESSED", "pipeline_state": "INDEXED",
            "created_at": "2026-10-05T12:00:00", "last_processed_at": "2026-10-05T12:00:01",
            "last_content_hash": "nae_doc_a", "corpus_membership": "default",
            "pipeline_flags": {k: True for k in ("ingested", "copied", "extracted", "cleaned", "chunked", "output_generated", "verified")},
        }
        assert info == self.INFO

    def test_entries_do_not_share_the_flags_dict(self, tmp_path):
        a = m._new_registry_entry(tmp_path / "a", self.INFO, "t", "t")
        b = m._new_registry_entry(tmp_path / "b", self.INFO, "t", "t")
        a["pipeline_flags"]["verified"] = False
        assert b["pipeline_flags"]["verified"] is True

    def test_apply_adds_missing_only_preserves_existing_and_returns_ids_in_order(self, tmp_path, monkeypatch):
        calls = []

        class Counting(_FrozenDatetime):
            @classmethod
            def now(cls, tz=None):
                calls.append(1)
                return super().now(tz)

        monkeypatch.setattr(m, "datetime", Counting)
        existing_entry = {"document_id": "nae_doc_b", "title": "keep me", "pipeline_state": "FAILED"}
        registry = {"documents": {"nae_doc_b": existing_entry}, "schema_version": "2.0"}
        existing_copy = copy.deepcopy(existing_entry)
        info = {
            tmp_path / "doc_z": {"document_id": "nae_doc_z", "title": "Z", "author": "a", "record_count": 1},
            tmp_path / "doc_b": {"document_id": "nae_doc_b", "title": "NEW B", "author": "b", "record_count": 9},
            tmp_path / "doc_a": {"document_id": "nae_doc_a", "title": "A", "author": "a", "record_count": 3},
        }
        before_dir = _snapshot_tree(tmp_path)
        added = m._apply_new_documents(registry, info)
        assert added == ["nae_doc_z", "nae_doc_a"]  # insertion order of nae_docs_info, existing skipped
        assert registry["documents"]["nae_doc_b"] is existing_entry and existing_entry == existing_copy  # byte-for-byte untouched
        assert registry["schema_version"] == "2.0" and list(registry["documents"]) == ["nae_doc_b", "nae_doc_z", "nae_doc_a"]
        assert registry["documents"]["nae_doc_a"] == m._new_registry_entry(tmp_path / "doc_a", info[tmp_path / "doc_a"], "2026-10-05T12:00:00", "2026-10-05T12:00:00")
        assert len(calls) == 4  # two now() calls per ADDED document (created_at, last_processed_at), none for the skipped one
        assert _snapshot_tree(tmp_path) == before_dir  # no disk writes

    def test_apply_with_nothing_new_returns_empty_and_changes_nothing(self, tmp_path):
        registry = {"documents": {"nae_doc_a": {"document_id": "nae_doc_a"}}}
        before = copy.deepcopy(registry)
        assert m._apply_new_documents(registry, {tmp_path / "doc_a": {"document_id": "nae_doc_a", "title": "", "author": "", "record_count": 1}}) == []
        assert registry == before

    def test_apply_requires_a_documents_key(self, tmp_path):
        with pytest.raises(KeyError):
            m._apply_new_documents({}, {tmp_path / "doc_a": {"document_id": "nae_doc_a", "title": "", "author": "", "record_count": 1}})


# ---------------------------------------------------------------------------
# E-0b: durability barrier — units
# ---------------------------------------------------------------------------

class _FdTracker:
    """Wraps os.open/os.close/os.fsync (calling the originals) to record fd lifecycle and fsync targets."""

    def __init__(self, monkeypatch, fail_on=None):
        self.opened, self.closed, self.fsyncs = [], [], []
        self.fail_on = fail_on  # "file" | "dir" | None
        self._open, self._close, self._fsync = os.open, os.close, os.fsync
        monkeypatch.setattr(os, "open", self._o)
        monkeypatch.setattr(os, "close", self._c)
        monkeypatch.setattr(os, "fsync", self._f)

    def _o(self, *a, **k):
        fd = self._open(*a, **k)
        self.opened.append(fd)
        return fd

    def _c(self, fd):
        self.closed.append(fd)
        return self._close(fd)

    def _f(self, fd):
        kind = "dir" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file"
        self.fsyncs.append(kind)
        if kind == self.fail_on:
            self.error = OSError(5, f"injected {kind} fsync failure")
            raise self.error
        return self._fsync(fd)

    @property
    def leaked(self):
        return [fd for fd in self.opened if fd not in self.closed]


class TestEnsureDurableUnit:
    def _file(self, tmp_path):
        p = tmp_path / "registry.json"
        p.write_text("{}", encoding="utf-8")
        return p

    def test_success_fsyncs_file_then_parent_directory_and_closes_everything(self, tmp_path, monkeypatch):
        t = _FdTracker(monkeypatch)
        m._ensure_durable(self._file(tmp_path))
        assert t.fsyncs == ["file", "dir"] and t.leaked == []

    def test_file_fsync_failure_converts_error_keeps_cause_skips_directory_and_closes_fd(self, tmp_path, monkeypatch):
        t = _FdTracker(monkeypatch, fail_on="file")
        p = self._file(tmp_path)
        with pytest.raises(CorpusMutationBlockedError) as e:
            m._ensure_durable(p)
        assert str(e.value).startswith("Corpus mutation BLOCKED: durability barrier failed for ")
        assert str(p) in str(e.value) and "injected file fsync failure" in str(e.value)
        assert e.value.__cause__ is t.error and isinstance(e.value.__cause__, OSError)
        assert t.fsyncs == ["file"] and t.leaked == []

    def test_directory_fsync_failure_converts_error_keeps_cause_and_closes_fds(self, tmp_path, monkeypatch):
        t = _FdTracker(monkeypatch, fail_on="dir")
        with pytest.raises(CorpusMutationBlockedError, match="durability barrier failed") as e:
            m._ensure_durable(self._file(tmp_path))
        assert e.value.__cause__ is t.error and "injected dir fsync failure" in str(e.value)
        assert t.fsyncs == ["file", "dir"] and t.leaked == []

    def test_missing_file_is_converted_and_nothing_is_fsynced(self, tmp_path, monkeypatch):
        t = _FdTracker(monkeypatch)
        with pytest.raises(CorpusMutationBlockedError, match="durability barrier failed") as e:
            m._ensure_durable(tmp_path / "absent.json")
        assert isinstance(e.value.__cause__, FileNotFoundError) and t.fsyncs == [] and t.leaked == []

    def test_barrier_fsyncs_the_parent_directory_of_the_given_file(self, tmp_path, monkeypatch):
        sub = tmp_path / "sub"
        sub.mkdir()
        p = sub / "f.json"
        p.write_text("{}", encoding="utf-8")
        seen = []
        real_impl = m._fsync_directory_impl
        monkeypatch.setattr(m, "_fsync_directory_impl", lambda d: (seen.append(Path(d)), real_impl(d))[1])
        m._ensure_durable(p)
        assert seen == [sub]

    def test_barrier_does_not_go_through_the_strict_intent_wrapper(self, tmp_path, monkeypatch):
        strict_calls = []
        monkeypatch.setattr(m, "_fsync_directory_strict", lambda d: strict_calls.append(d))
        m._ensure_durable(self._file(tmp_path))
        assert strict_calls == []  # the intent-only injection point is not consumed by the barrier


class TestFsyncDirectoryUnits:
    def test_strict_delegates_exactly_once_to_the_shared_implementation(self, tmp_path, monkeypatch):
        seen = []
        monkeypatch.setattr(m, "_fsync_directory_impl", lambda d: seen.append(d))
        m._fsync_directory_strict(tmp_path)
        assert seen == [tmp_path]

    def test_strict_propagates_the_implementation_error_unchanged(self, tmp_path, monkeypatch):
        boom = OSError(5, "EIO")

        def raising(d):
            raise boom

        monkeypatch.setattr(m, "_fsync_directory_impl", raising)
        with pytest.raises(OSError) as e:
            m._fsync_directory_strict(tmp_path)
        assert e.value is boom

    def test_impl_fsyncs_a_directory_closes_the_fd_and_propagates_errors(self, tmp_path, monkeypatch):
        t = _FdTracker(monkeypatch)
        m._fsync_directory_impl(tmp_path)
        assert t.fsyncs == ["dir"] and t.leaked == []
        t2 = _FdTracker(monkeypatch, fail_on="dir")
        with pytest.raises(OSError, match="injected dir fsync failure"):
            m._fsync_directory_impl(tmp_path)
        assert t2.leaked == []


# ---------------------------------------------------------------------------
# E-0b: real-merge ordering, failure behaviour, intent injection contract
# ---------------------------------------------------------------------------

def _install_event_log(monkeypatch, env_probe=None):
    events = []

    def spy(name, extra=None):
        real = getattr(m, name)

        def wrapper(*a, **k):
            events.append((name, extra(a, k) if extra else None, env_probe() if env_probe else None))
            return real(*a, **k)

        monkeypatch.setattr(m, name, wrapper)

    spy("save_identity_registry")
    spy("_ensure_durable", lambda a, k: str(a[0]))
    spy("_advance_intent_phase", lambda a, k: a[2].value)
    spy("write_manifest")
    return events


class TestMergeLevelOrder:
    def test_production_order_and_state_at_each_step(self, env, frozen, monkeypatch):
        def probe():
            phase = env.intent_state()[0]
            reg = json.loads(env.registry.read_text(encoding="utf-8"))["documents"]
            return {"phase": phase, "registry_has_new_doc": "nae_S1" in reg, "manifest": env.manifest.read_bytes()}

        events = _install_event_log(monkeypatch, probe)
        manifest_before = env.manifest.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            env.merge("S1", ["TSU-1"])
        names = [(n, x) for n, x, _ in events]
        assert names == [
            ("_advance_intent_phase", "DATASET_WRITTEN"),
            ("save_identity_registry", None),
            ("_ensure_durable", str(env.registry)),
            ("_advance_intent_phase", "REGISTRY_WRITTEN"),
            ("write_manifest", None),
            ("_advance_intent_phase", "COMMITTED"),
        ]
        by = {(n, x): p for n, x, p in events}
        assert by[("save_identity_registry", None)]["registry_has_new_doc"] is False  # not saved yet at save time
        barrier = by[("_ensure_durable", str(env.registry))]
        assert barrier["registry_has_new_doc"] is True and barrier["phase"] == "DATASET_WRITTEN"  # saved, phase not advanced yet
        assert barrier["manifest"] == manifest_before
        manifest_step = by[("write_manifest", None)]
        assert manifest_step["phase"] == "REGISTRY_WRITTEN" and manifest_step["manifest"] == manifest_before

    def test_non_production_merge_runs_the_barrier_after_save_and_before_manifest(self, env, frozen, monkeypatch):
        layout, run = _run_scenario(env, "nonprod_ok")
        events = _install_event_log(monkeypatch)
        with contextlib.redirect_stdout(io.StringIO()):
            run()
        assert [(n, x) for n, x, _ in events] == [
            ("save_identity_registry", None), ("_ensure_durable", str(layout.registry)), ("write_manifest", None),
        ]
        assert layout.intent is None and not (layout.manifest.parent / "tsu_merge_intent.json").exists()  # no intent / phase outside production

    def test_save_returning_false_blocks_before_the_barrier(self, env, frozen, monkeypatch):
        events = _install_event_log(monkeypatch)
        monkeypatch.setattr(m, "save_identity_registry", lambda registry, path: False)
        manifest_before = env.manifest.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            with pytest.raises(CorpusMutationBlockedError, match="registry write failed"):
                env.merge("S1", ["TSU-1"])
        assert [n for n, _, _ in events] == ["_advance_intent_phase"]  # only DATASET_WRITTEN; no barrier, no REGISTRY_WRITTEN, no manifest
        assert env.intent_state()[0] == "DATASET_WRITTEN" and env.manifest.read_bytes() == manifest_before


def _arm_after_save(monkeypatch, fail_kind):
    """Real os.fsync failure injection: armed once save_identity_registry has returned; fails regular files or directories."""
    state = {"armed": False, "error": None}
    real_save, real_fsync = m.save_identity_registry, os.fsync

    def save(*a, **k):
        r = real_save(*a, **k)
        state["armed"] = True
        return r

    def fsync(fd):
        if state["armed"]:
            kind = "dir" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file"
            if kind == fail_kind:
                state["error"] = OSError(5, f"injected {kind} EIO")
                raise state["error"]
        return real_fsync(fd)

    monkeypatch.setattr(m, "save_identity_registry", save)
    monkeypatch.setattr(os, "fsync", fsync)
    return state


def _fd_count() -> int:
    return len(os.listdir("/dev/fd" if os.path.isdir("/dev/fd") else "/proc/self/fd"))


class TestMergeLevelFailures:
    @pytest.mark.parametrize("kind", ["file", "dir"])
    def test_production_barrier_failure_blocks_phase_and_manifest_and_the_next_merge(self, env, frozen, monkeypatch, kind):
        state = _arm_after_save(monkeypatch, kind)
        manifest_calls = []
        real_manifest = m.write_manifest
        monkeypatch.setattr(m, "write_manifest", lambda *a, **k: (manifest_calls.append(1), real_manifest(*a, **k))[1])
        manifest_before = env.manifest.read_bytes()
        fd_before = _fd_count()
        with contextlib.redirect_stdout(io.StringIO()):
            with pytest.raises(CorpusMutationBlockedError, match="durability barrier failed") as e:
                env.merge("S1", ["TSU-1"])
        assert e.value.__cause__ is state["error"] and f"injected {kind} EIO" in str(e.value)
        assert manifest_calls == [] and env.manifest.read_bytes() == manifest_before
        phase, data = env.intent_state()
        assert phase == "DATASET_WRITTEN" and data["intent_content_sha256"] == m._intent_checksum(data)
        m._validate_intent_payload(env.intent_raw())
        assert "nae_S1" in json.loads(env.registry.read_text(encoding="utf-8"))["documents"]  # replaced registry is NOT rolled back
        assert [r["tsu_id"] for r in map(json.loads, env.dataset.read_text(encoding="utf-8").splitlines())] == ["TSU-1"]
        assert env.tmp_leftovers() == [] and not Path(str(env.registry) + ".tmp").exists()
        assert _fd_count() == fd_before
        monkeypatch.undo()
        _freeze(monkeypatch)
        with contextlib.redirect_stdout(io.StringIO()):
            with pytest.raises(CorpusMutationBlockedError, match="incomplete intent exists"):
                env.merge("S2", ["TSU-2"])

    @pytest.mark.parametrize("kind", ["file", "dir"])
    def test_non_production_barrier_failure_blocks_manifest_and_leaves_no_intent(self, env, frozen, monkeypatch, kind):
        layout, run = _run_scenario(env, "nonprod_ok")
        state = _arm_after_save(monkeypatch, kind)
        manifest_before = layout.manifest.read_bytes()
        fd_before = _fd_count()
        with contextlib.redirect_stdout(io.StringIO()):
            with pytest.raises(CorpusMutationBlockedError, match="durability barrier failed") as e:
                run()
        assert e.value.__cause__ is state["error"]
        assert layout.manifest.read_bytes() == manifest_before
        assert not (layout.manifest.parent / "tsu_merge_intent.json").exists()
        assert "nae_NP" in json.loads(layout.registry.read_text(encoding="utf-8"))["documents"]
        assert _fd_count() == fd_before


class TestIntentFsyncContract:
    def test_strict_wrapper_is_called_four_times_for_the_intent_and_the_barrier_uses_the_shared_impl_directly(self, env, frozen, monkeypatch):
        log = []
        real_strict, real_impl = m._fsync_directory_strict, m._fsync_directory_impl
        monkeypatch.setattr(m, "_fsync_directory_strict", lambda d: (log.append(("strict", Path(d))), real_strict(d))[1])
        monkeypatch.setattr(m, "_fsync_directory_impl", lambda d: (log.append(("impl", Path(d))), real_impl(d))[1])
        with contextlib.redirect_stdout(io.StringIO()):
            env.merge("S1", ["TSU-1"])
        kinds = [k for k, _ in log]
        assert kinds.count("strict") == 4  # intent records: initial, DATASET_WRITTEN, REGISTRY_WRITTEN, COMMITTED (wrapper calls only)
        assert kinds.count("impl") == 5    # the 4 wrapper calls + exactly one direct call by the barrier
        direct = [i for i, k in enumerate(kinds) if k == "impl" and (i == 0 or kinds[i - 1] != "strict")]
        assert len(direct) == 1
        assert log[direct[0]][1] == env.registry.parent  # the barrier fsyncs the registry's directory
        # the barrier sits between the 2nd and 3rd intent record
        assert kinds[:direct[0]].count("strict") == 2

    def test_the_fourth_wrapper_call_is_the_committed_update(self, env, frozen, monkeypatch):
        real = m._fsync_directory_strict
        state = {"n": 0}

        def injected(d):
            state["n"] += 1
            if state["n"] == 3:  # REGISTRY_WRITTEN record (the barrier no longer shifts this index)
                raise OSError(5, "injected on 3rd intent fsync")
            return real(d)

        monkeypatch.setattr(m, "_fsync_directory_strict", injected)
        with contextlib.redirect_stdout(io.StringIO()):
            with pytest.raises(CorpusMutationBlockedError, match="intent durable write failed"):
                env.merge("S1", ["TSU-1"])
        assert env.intent_state()[0] == "REGISTRY_WRITTEN"  # reached only because the barrier already passed
