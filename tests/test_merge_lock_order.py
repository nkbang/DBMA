"""tests/test_merge_lock_order.py — S2-D: merge holds registry_lock -> tsu_dataset_lock (CUE-authored, mutation-verified).

Real flock/threads are used wherever behaviour (blocking, deadlock, release) is the point; recording wrappers around
the real lock functions are used for ORDER/STATE assertions. Nothing that implements a protection is mocked.
Helper fixtures (Env, reference hashing) come from the sibling tests/test_merge_intent.py (same commit).
"""

from __future__ import annotations

import fcntl
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import scripts.merge_nae_corpus as m  # noqa: E402
from scripts.corpus_approval_gate import CorpusMutationBlockedError  # noqa: E402
from test_merge_intent import Env, _ref_plan_hash, _ref_sha  # noqa: E402


@pytest.fixture()
def env(tmp_path):
    return Env(tmp_path)


class Recorder:
    """Wraps the REAL lock functions and the state-reading/writing steps; records what is held at each step."""

    def __init__(self, env: Env, monkeypatch):
        self.env = env
        self.events: list[str] = []
        self.held = {"R": 0, "T": 0}
        self.calls: list[tuple[str, int, int]] = []  # (step, R held, T held)
        self.lock_args: list[tuple[str, str]] = []
        self.r_entering = threading.Event()
        self._lock = threading.Lock()
        rec = self

        real_r, real_t = m.registry_lock, m.tsu_dataset_lock

        from contextlib import contextmanager

        @contextmanager
        def r_wrap(path):
            rec.r_entering.set()
            rec.lock_args.append(("R", str(path)))
            with real_r(path):
                rec.events.append("R+")
                rec.held["R"] += 1
                try:
                    yield
                finally:
                    rec.held["R"] -= 1
                    rec.events.append("R-")

        @contextmanager
        def t_wrap(path):
            rec.lock_args.append(("T", str(path)))
            with real_t(path):
                if rec.held["R"] == 0:
                    rec.events.append("T+WITHOUT_R")
                rec.events.append("T+")
                rec.held["T"] += 1
                try:
                    yield
                finally:
                    rec.held["T"] -= 1
                    rec.events.append("T-")

        monkeypatch.setattr(m, "registry_lock", r_wrap)
        monkeypatch.setattr(m, "tsu_dataset_lock", t_wrap)

        for name in (
            "compute_dataset_sha256", "_read_existing_dataset", "load_identity_registry", "_check_existing_intent",
            "_write_intent_durable", "_advance_intent_phase", "write_tsu_dataset", "save_identity_registry", "write_manifest",
        ):
            real = getattr(m, name)

            def wrapper(*a, _n=name, _r=real, **k):
                rec.calls.append((_n, rec.held["R"], rec.held["T"]))
                return _r(*a, **k)

            monkeypatch.setattr(m, name, wrapper)

    def steps(self, name: str) -> list[tuple[str, int, int]]:
        return [c for c in self.calls if c[0] == name]


def _prepare(env: Env, source_id: str, ids: list[str]) -> dict:
    """Corpus + decisions + a CORRECT approval for the CURRENT state; returns kwargs for merge_nae_corpus()."""
    croot, transformed = env.corpus(source_id, ids)
    ddir = env.decisions(source_id, ids)
    env.write_approval(source_id, _ref_plan_hash(source_id, transformed, env.targets()))
    return dict(source_id=source_id, data_root=env.prod, nae_corpus_dir=croot, decisions_dir=ddir, config_path=env.config)


def _lock_file_free(path: Path) -> bool:
    """True if a non-blocking exclusive flock on the lock file succeeds right now (i.e. nobody holds it)."""
    with open(path, "a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        fcntl.flock(f, fcntl.LOCK_UN)
        return True


def _locks_free(env: Env) -> tuple[bool, bool]:
    return (
        _lock_file_free(Path(str(env.registry) + ".lock")),
        _lock_file_free(Path(str(env.dataset.resolve()) + ".lock")),
    )


def _run_in_thread(fn):
    box: dict = {}

    def target():
        try:
            box["result"] = fn()
        except BaseException as exc:  # noqa: BLE001
            box["error"] = exc

    t = threading.Thread(target=target, daemon=True)
    t.start()
    return t, box


# ===========================================================================
# 1. order, single acquisition, ownership of the right files
# ===========================================================================

class TestOrderAndScope:
    def test_acquired_registry_then_dataset_and_released_in_reverse(self, env, monkeypatch):
        rec = Recorder(env, monkeypatch)
        kwargs = _prepare(env, "S1", ["TSU-1"])
        t, box = _run_in_thread(lambda: m.merge_nae_corpus(**kwargs))
        t.join(20)  # a self-deadlock (non-reentrant registry_lock taken twice) fails here instead of hanging the suite
        assert not t.is_alive(), "merge hung: lock acquired twice or order cycle"
        result = box["result"]
        assert result["status"] == "completed"
        ev = rec.events
        assert ev[0] == "R+" and ev[1] == "T+"            # R first, then T
        assert ev[-2:] == ["T-", "R-"]                     # reverse release
        assert ev.count("R+") == 1 and ev.count("R-") == 1  # registry_lock is NOT reentrant: exactly one acquisition
        assert "T+WITHOUT_R" not in ev                     # T is never taken without R already held
        assert ev.index("R-") == len(ev) - 1               # nothing runs after R is released
        assert rec.held == {"R": 0, "T": 0}

    def test_locks_are_taken_on_the_resolved_target_files(self, env, monkeypatch):
        rec = Recorder(env, monkeypatch)
        m.merge_nae_corpus(**_prepare(env, "S1", ["TSU-1"]))
        assert rec.lock_args[0] == ("R", str(env.registry))
        assert rec.lock_args[1] == ("T", str(env.dataset))
        assert all(a == ("T", str(env.dataset)) for a in rec.lock_args[1:])

    def test_every_state_read_and_every_write_runs_under_both_locks(self, env, monkeypatch):
        rec = Recorder(env, monkeypatch)
        m.merge_nae_corpus(**_prepare(env, "S1", ["TSU-1"]))
        expected = {
            "compute_dataset_sha256": 1,   # approval freshness check (S2-A) — D2: must be under the locks
            "_read_existing_dataset": 2, "load_identity_registry": 2, "_check_existing_intent": 1,
            "_write_intent_durable": 4, "_advance_intent_phase": 3,
            "write_tsu_dataset": 1, "save_identity_registry": 1, "write_manifest": 1,
        }
        for step, count in expected.items():
            calls = rec.steps(step)
            assert len(calls) == count, (step, calls)
            assert all(r == 1 and t >= 1 for _, r, t in calls), (step, calls)

    def test_non_production_merge_takes_the_locks_too(self, env, monkeypatch):
        other = env.root / "nonprod"
        (other / "output" / "bench").mkdir(parents=True)
        (other / "data" / "제련완성본" / "registry").mkdir(parents=True)
        (other / "output" / "bench" / "tsu_dataset.jsonl").write_text("", encoding="utf-8")
        (other / "output" / "bench" / "tsu_manifest.json").write_text("{}", encoding="utf-8")
        reg = other / "data" / "제련완성본" / "registry" / "documents.json"
        reg.write_text(json.dumps({"documents": {}}), encoding="utf-8")
        croot, _ = env.corpus("NP", ["TSU-9"])
        ddir = env.decisions("NP", ["TSU-9"])
        rec = Recorder(env, monkeypatch)
        result = m.merge_nae_corpus(source_id="NP", data_root=other, nae_corpus_dir=croot, decisions_dir=ddir, config_path=env.config)
        assert result["status"] == "completed"
        assert rec.events[:2] == ["R+", "T+"] and rec.events[-2:] == ["T-", "R-"]
        assert rec.lock_args[0] == ("R", str(reg.resolve()) if str(reg.resolve()) == rec.lock_args[0][1] else str(reg))

    def test_path_error_is_raised_before_any_lock_is_taken(self, env, monkeypatch):
        rec = Recorder(env, monkeypatch)
        with pytest.raises(CorpusMutationBlockedError, match="No data_root"):
            m.merge_nae_corpus(source_id="S1", data_root=None, nae_corpus_dir=env.root, decisions_dir=env.root, config_path=env.config)
        assert rec.events == [] and rec.lock_args == []

    def test_public_signature_and_locked_body_split(self):
        import inspect
        assert list(inspect.signature(m.merge_nae_corpus).parameters) == [
            "source_id", "data_root", "nae_corpus_dir", "decisions_dir", "config_path",
        ]
        assert inspect.signature(m._merge_nae_corpus_locked).parameters.keys() == inspect.signature(m.merge_nae_corpus).parameters.keys()


# ===========================================================================
# 2. release on every exit path (real flock state)
# ===========================================================================

class TestRelease:
    def test_released_after_success(self, env):
        m.merge_nae_corpus(**_prepare(env, "S1", ["TSU-1"]))
        assert _locks_free(env) == (True, True)

    def test_released_after_midway_exception(self, env, monkeypatch):
        rec = Recorder(env, monkeypatch)

        def boom(*a, **k):
            raise RuntimeError("manifest exploded")

        monkeypatch.setattr(m, "write_manifest", boom)
        with pytest.raises(RuntimeError, match="manifest exploded"):
            m.merge_nae_corpus(**_prepare(env, "S1", ["TSU-1"]))
        assert rec.events[-2:] == ["T-", "R-"] and rec.held == {"R": 0, "T": 0}
        assert _locks_free(env) == (True, True)

    def test_released_after_rejected_approval_and_targets_untouched(self, env, monkeypatch):
        kwargs = _prepare(env, "S1", ["TSU-1"])
        env.write_approval("S1", "sha256:" + "0" * 64)  # forged plan_hash
        before = env.target_hashes()
        rec = Recorder(env, monkeypatch)
        with pytest.raises(CorpusMutationBlockedError, match="PLAN_HASH_MISMATCH"):
            m.merge_nae_corpus(**kwargs)
        assert rec.events[-2:] == ["T-", "R-"] and rec.steps("write_tsu_dataset") == []
        assert env.target_hashes() == before and env.intent_raw() is None
        assert _locks_free(env) == (True, True)

    def test_released_after_intent_blocks_merge(self, env):
        env.intent_path.write_bytes(b"garbage{")
        with pytest.raises(CorpusMutationBlockedError, match="invalid JSON"):
            m.merge_nae_corpus(**_prepare(env, "S1", ["TSU-1"]))
        assert _locks_free(env) == (True, True)

    def test_lock_is_held_until_after_the_committed_update(self, env, monkeypatch):
        rec = Recorder(env, monkeypatch)
        seen = {}
        real_adv = m._advance_intent_phase

        def adv(path, payload, phase):
            out = real_adv(path, payload, phase)
            if phase.value == "COMMITTED":
                seen["held_after_committed"] = (rec.held["R"], rec.held["T"], _locks_free(env))
            return out

        monkeypatch.setattr(m, "_advance_intent_phase", adv)
        m.merge_nae_corpus(**_prepare(env, "S1", ["TSU-1"]))
        r, t, free = seen["held_after_committed"]
        assert r == 1 and t >= 1 and free == (False, False)  # still locked for other processes right after COMMITTED


# ===========================================================================
# 3. real blocking behaviour
# ===========================================================================

class TestBlocking:
    def _hold(self, path: Path):
        f = open(path, "a")
        fcntl.flock(f, fcntl.LOCK_EX)
        return f

    def _release(self, f):
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()

    @pytest.mark.parametrize("which", ["registry", "dataset"])
    def test_merge_waits_for_a_foreign_holder_and_does_nothing_meanwhile(self, env, monkeypatch, which):
        kwargs = _prepare(env, "S1", ["TSU-1"])
        before = env.target_hashes()
        rec = Recorder(env, monkeypatch)
        lock_path = Path(str(env.registry) + ".lock") if which == "registry" else Path(str(env.dataset.resolve()) + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        held = self._hold(lock_path)
        t, box = _run_in_thread(lambda: m.merge_nae_corpus(**kwargs))
        assert rec.r_entering.wait(5)
        time.sleep(0.4)
        assert t.is_alive(), "merge must be blocked while a foreign process holds the lock"
        assert env.target_hashes() == before and env.intent_raw() is None
        assert rec.calls == []  # no state read at all (approval freshness included) before the locks are held
        self._release(held)
        t.join(15)
        assert not t.is_alive() and box.get("result", {}).get("status") == "completed", box
        assert _locks_free(env) == (True, True)

    def test_approval_freshness_is_decided_after_the_locks_are_acquired(self, env, monkeypatch):
        """D2/TOCTOU: the dataset changes while the merge waits for the lock; the stale approval must be rejected."""
        kwargs = _prepare(env, "S1", ["TSU-1"])  # approval bound to the CURRENT (empty) dataset
        rec = Recorder(env, monkeypatch)
        lock_path = Path(str(env.registry) + ".lock")
        held = self._hold(lock_path)
        t, box = _run_in_thread(lambda: m.merge_nae_corpus(**kwargs))
        assert rec.r_entering.wait(5)
        time.sleep(0.3)
        assert t.is_alive()
        env.seed_dataset([{"tsu_id": "TSU-X", "document_id": "doc_x", "content": "changed by someone else"}])
        self._release(held)
        t.join(15)
        assert not t.is_alive()
        err = box.get("error")
        assert isinstance(err, CorpusMutationBlockedError) and "DATASET_SHA_MISMATCH" in str(err), box
        assert [json.loads(l)["tsu_id"] for l in env.dataset.read_text().splitlines()] == ["TSU-X"]
        assert env.intent_raw() is None
        assert _locks_free(env) == (True, True)

    def test_cross_process_holder_blocks_the_merge(self, env):
        kwargs = _prepare(env, "S1", ["TSU-1"])
        lock_path = str(env.registry) + ".lock"
        code = (
            "import fcntl,sys,time\n"
            f"f=open({lock_path!r},'a'); fcntl.flock(f, fcntl.LOCK_EX)\n"
            "print('locked',flush=True); time.sleep(1.5)\n"
        )
        proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
        try:
            assert proc.stdout.readline().strip() == "locked"
            t0 = time.perf_counter()
            result = m.merge_nae_corpus(**kwargs)
            waited = time.perf_counter() - t0
        finally:
            proc.wait(10)
        assert result["status"] == "completed"
        assert waited >= 1.0, f"merge did not wait for the foreign process ({waited:.2f}s)"

    def test_no_deadlock_against_daemon_style_registry_then_dataset_holders(self, env):
        """The daemon (reconcile_pending) takes R then T repeatedly; merge must interleave without deadlock."""
        stop_errors = []

        def daemon():
            try:
                for _ in range(40):
                    with m.registry_lock(str(env.registry)):
                        with m.tsu_dataset_lock(env.dataset):
                            time.sleep(0.003)
            except BaseException as exc:  # noqa: BLE001
                stop_errors.append(exc)

        d = threading.Thread(target=daemon, daemon=True)
        d.start()
        results = []

        def merges():
            for i in range(3):
                results.append(m.merge_nae_corpus(**_prepare(env, f"S{i}", [f"TSU-{i}"]))["status"])

        t, box = _run_in_thread(merges)
        t.join(60)
        d.join(60)
        assert not t.is_alive() and not d.is_alive(), "deadlock between merge and R->T holder"
        assert "error" not in box and results == ["completed"] * 3 and stop_errors == []
        assert _locks_free(env) == (True, True)

    def test_two_concurrent_merges_serialize_and_both_commit_or_one_is_blocked_cleanly(self, env):
        a, b = _prepare(env, "SA", ["TSU-A"]), None
        # second merge prepared with its own approval bound to the same (empty) dataset
        b = _prepare(env, "SB", ["TSU-B"])
        ta, ba = _run_in_thread(lambda: m.merge_nae_corpus(**a))
        tb, bb = _run_in_thread(lambda: m.merge_nae_corpus(**b))
        ta.join(30); tb.join(30)
        assert not ta.is_alive() and not tb.is_alive()
        outcomes = [x.get("result", {}).get("status") if "result" in x else type(x["error"]).__name__ for x in (ba, bb)]
        # exactly one wins; the loser is rejected by the (now stale) approval freshness check — never a corrupt/partial merge
        assert sorted(outcomes) == ["CorpusMutationBlockedError", "completed"], outcomes
        ids = [json.loads(l)["tsu_id"] for l in env.dataset.read_text().splitlines()]
        assert len(ids) == 1 and ids[0] in ("TSU-A", "TSU-B")
        m._validate_intent_payload(env.intent_raw())
        assert env.intent_state()[0] == "COMMITTED"


# ===========================================================================
# 4. D3 — save_identity_registry() returning False
# ===========================================================================

class TestRegistrySaveFailure:
    def test_false_return_blocks_and_stops_before_manifest_and_phase_advance(self, env, monkeypatch):
        calls = {"save": 0, "manifest": 0}
        real_manifest = m.write_manifest

        def failing_save(registry, path):
            calls["save"] += 1
            return False

        def counting_manifest(*a, **k):
            calls["manifest"] += 1
            return real_manifest(*a, **k)

        monkeypatch.setattr(m, "save_identity_registry", failing_save)
        monkeypatch.setattr(m, "write_manifest", counting_manifest)
        before_registry = env.registry.read_bytes()
        before_manifest = env.manifest.read_bytes()
        with pytest.raises(CorpusMutationBlockedError, match="registry write failed"):
            m.merge_nae_corpus(**_prepare(env, "S1", ["TSU-1"]))
        assert calls == {"save": 1, "manifest": 0}
        phase, data = env.intent_state()
        assert phase == "DATASET_WRITTEN" and data["intent_content_sha256"] == m._intent_checksum(data)
        assert env.registry.read_bytes() == before_registry and env.manifest.read_bytes() == before_manifest
        assert _locks_free(env) == (True, True)
        monkeypatch.undo()
        with pytest.raises(CorpusMutationBlockedError, match="incomplete intent exists"):
            m.merge_nae_corpus(**_prepare(env, "S2", ["TSU-2"]))

    def test_false_return_also_blocks_non_production_merges(self, env, monkeypatch):
        other = env.root / "nonprod2"
        (other / "output" / "bench").mkdir(parents=True)
        (other / "data" / "제련완성본" / "registry").mkdir(parents=True)
        (other / "output" / "bench" / "tsu_dataset.jsonl").write_text("", encoding="utf-8")
        (other / "output" / "bench" / "tsu_manifest.json").write_text("{}", encoding="utf-8")
        (other / "data" / "제련완성본" / "registry" / "documents.json").write_text(json.dumps({"documents": {}}), encoding="utf-8")
        croot, _ = env.corpus("NP", ["TSU-9"])
        ddir = env.decisions("NP", ["TSU-9"])
        monkeypatch.setattr(m, "save_identity_registry", lambda registry, path: False)
        with pytest.raises(CorpusMutationBlockedError, match="registry write failed"):
            m.merge_nae_corpus(source_id="NP", data_root=other, nae_corpus_dir=croot, decisions_dir=ddir, config_path=env.config)

    def test_true_return_proceeds(self, env):
        assert m.merge_nae_corpus(**_prepare(env, "S1", ["TSU-1"]))["status"] == "completed"
        assert env.intent_state()[0] == "COMMITTED"
