"""Tests for NAE/pipeline/tsu/gate_adapter.py and the Gate-wired path in
NAE/pipeline/tsu/runner.py (NAE-TSU-PIPELINE-WIRING-IMPLEMENTATION-001).

Covers: eligible-identifier selection (PASS/BLOCK/ERROR), that Builder
is called only for PASS identifiers, that BLOCK/ERROR never reach
Builder, and that real production data (0 Crosswalk records) yields
0 TSU generation end-to-end. No TSU is ever actually generated — all
`builder.build_tsu_for_identifier` calls in these tests are monkeypatched
to avoid real LLM/file-write side effects.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.crosswalk.gate_orchestrator import GateOrchestrator, ManifestEntryInput
from scripts.crosswalk.repository import InMemoryCrosswalkRepository
from scripts.crosswalk.schema import Confidence, CrosswalkRecord, MappingStatus, SourceType, TargetType

from NAE.pipeline.tsu import gate_adapter, runner


def _record(**overrides):
    defaults = dict(
        crosswalk_id="cw_001",
        source_identifier="BAP-CHURCH-DAGG-001",
        source_type=SourceType.REGISTRY_SOURCE_ID,
        target_identifier="PBC1742",
        target_type=TargetType.CORPUS_CANONICAL_ID,
        mapping_status=MappingStatus.MANUAL_CONFIRMED,
        confidence=Confidence.HIGH,
        evidence="archive.org metadata cross-checked",
        created_at="2026-08-05T00:00:00+09:00",
    )
    defaults.update(overrides)
    return CrosswalkRecord(**defaults)


class TestIterEligibleIdentifiers:
    def test_pass_entry_included_in_pass_identifiers(self):
        repo = InMemoryCrosswalkRepository()
        repo.add(_record())
        orchestrator = GateOrchestrator(repo)
        entries = [ManifestEntryInput("BAP-CHURCH-DAGG-001", tsu_eligible=True)]

        summary = gate_adapter.iter_eligible_identifiers(entries, orchestrator)
        assert summary.pass_count == 1
        assert summary.pass_identifiers == ["PBC1742"]
        assert summary.block_count == 0
        assert summary.error_count == 0

    def test_block_entry_not_in_pass_identifiers(self):
        repo = InMemoryCrosswalkRepository()  # 매핑 없음
        orchestrator = GateOrchestrator(repo)
        entries = [ManifestEntryInput("UNKNOWN-SOURCE", tsu_eligible=True)]

        summary = gate_adapter.iter_eligible_identifiers(entries, orchestrator)
        assert summary.pass_identifiers == []
        assert summary.block_count == 1
        assert summary.block_details[0][0] == "UNKNOWN-SOURCE"

    def test_error_entry_not_in_pass_identifiers(self):
        class BrokenRepository(InMemoryCrosswalkRepository):
            def validate_storage(self):
                return False, "simulated corruption"

        repo = BrokenRepository()
        orchestrator = GateOrchestrator(repo)
        entries = [ManifestEntryInput("ANY", tsu_eligible=True)]

        summary = gate_adapter.iter_eligible_identifiers(entries, orchestrator)
        assert summary.pass_identifiers == []
        assert summary.error_count == 1
        assert summary.block_count == 0

    def test_storage_error_outranks_block_for_every_entry(self):
        """저장소 자체가 손상되면, 개별 entry의 tsu_eligible 값과 무관하게
        전부 ERROR로 집계된다 — ERROR가 BLOCK보다 우선한다(tsu_gate.py
        의 storage_error 우선순위 설계와 일치)."""

        class BrokenRepository(InMemoryCrosswalkRepository):
            def validate_storage(self):
                return False, "simulated corruption"

        repo = BrokenRepository()
        orchestrator = GateOrchestrator(repo)
        entries = [
            ManifestEntryInput("SRC-A", tsu_eligible=False),  # BLOCK 사유가 있어도
            ManifestEntryInput("SRC-B", tsu_eligible=True),  # PASS 조건을 충족해도
        ]
        summary = gate_adapter.iter_eligible_identifiers(entries, orchestrator)
        assert summary.pass_count == 0
        assert summary.block_count == 0
        assert summary.error_count == 2  # 둘 다 ERROR — storage_error가 최우선

    def test_mixed_pass_block_counted_correctly(self):
        repo = InMemoryCrosswalkRepository()
        repo.add(_record(crosswalk_id="cw_001", source_identifier="OK-SOURCE"))
        orchestrator = GateOrchestrator(repo)
        entries = [
            ManifestEntryInput("OK-SOURCE", tsu_eligible=True),
            ManifestEntryInput("MISSING-SOURCE", tsu_eligible=True),
        ]
        summary = gate_adapter.iter_eligible_identifiers(entries, orchestrator)
        assert summary.pass_count == 1
        assert summary.block_count == 1
        assert summary.pass_identifiers == ["PBC1742"]


class TestLoadManifestEntriesRealData:
    def test_real_pilot_manifest_loads_10_entries(self):
        entries = gate_adapter.load_manifest_entries()
        assert len(entries) == 10
        source_ids = {e.source_identifier for e in entries}
        assert "BAP-CHURCH-DAGG-001" in source_ids
        assert "BAP-CHURCH-HISCOX" in source_ids

    def test_real_pilot_entries_are_tsu_eligible(self):
        """실제 Pilot Manifest 10건은 이미 TSU_ELIGIBLE=READY 상태(기존
        회귀 기준선과 일치) — Crosswalk mapping 부재만이 BLOCK 사유여야
        한다."""
        entries = gate_adapter.load_manifest_entries()
        assert all(e.tsu_eligible for e in entries)

    def test_real_production_repository_yields_expected_pass_block_split(self):
        """실제 Production Crosswalk Storage 대상 Gate 평가(읽기 전용 —
        Builder를 호출하지 않으므로 부작용 없음). NAE-MANUAL-CROSSWALK-
        POPULATION-IMPLEMENTATION-001에서 Dagg/Hiscox 2건이
        manual-confirmed로 등록된 이후에는 PASS>=2, 나머지(Fuller
        8권)는 여전히 매핑이 없어 BLOCK이어야 한다."""
        entries = gate_adapter.load_manifest_entries()
        orchestrator = gate_adapter.build_default_orchestrator()
        summary = gate_adapter.iter_eligible_identifiers(entries, orchestrator)
        assert summary.error_count == 0
        assert summary.pass_count >= 2
        assert {"BAP-CHURCH-DAGG-001", "BAP-CHURCH-HISCOX"} <= {
            e.source_identifier for e in entries if e.source_identifier not in dict(summary.block_details)
        }
        assert summary.pass_count + summary.block_count == len(entries)


class TestBuilderNeverCalledForBlockedOrErrored:
    def test_builder_called_only_for_pass_identifiers(self, monkeypatch):
        calls = []

        def fake_build_tsu_for_identifier(identifier, **kwargs):
            calls.append(identifier)
            return {"records": [], "report": {"identifier": identifier}}

        monkeypatch.setattr(runner.builder, "build_tsu_for_identifier", fake_build_tsu_for_identifier)

        repo = InMemoryCrosswalkRepository()
        repo.add(_record(crosswalk_id="cw_001", source_identifier="OK-SOURCE", target_identifier="TARGET-A"))
        orchestrator = GateOrchestrator(repo)

        def fake_load_manifest_entries():
            return [
                ManifestEntryInput("OK-SOURCE", tsu_eligible=True),
                ManifestEntryInput("BLOCKED-SOURCE", tsu_eligible=True),
            ]

        monkeypatch.setattr(gate_adapter, "load_manifest_entries", fake_load_manifest_entries)
        monkeypatch.setattr(gate_adapter, "build_default_orchestrator", lambda: orchestrator)

        result = runner._run_gate_wired(model="test-model", max_candidates=None)

        assert calls == ["TARGET-A"]  # BLOCKED-SOURCE는 Builder에 전달되지 않음
        assert result["tsu_generated"] == 1
        assert result["gate_pass"] == 1
        assert result["gate_block"] == 1

    def test_zero_pass_yields_zero_builder_calls(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            runner.builder, "build_tsu_for_identifier", lambda identifier, **kw: calls.append(identifier)
        )

        repo = InMemoryCrosswalkRepository()  # 매핑 없음
        orchestrator = GateOrchestrator(repo)
        monkeypatch.setattr(gate_adapter, "load_manifest_entries", lambda: [ManifestEntryInput("X", True)])
        monkeypatch.setattr(gate_adapter, "build_default_orchestrator", lambda: orchestrator)

        result = runner._run_gate_wired(model="test-model", max_candidates=None)
        assert calls == []
        assert result["tsu_generated"] == 0


class TestRunnerCliDefaultsToGateWiring:
    def test_main_no_args_uses_gate_wired_path(self, monkeypatch, capsys):
        monkeypatch.setattr(
            runner, "_run_gate_wired", lambda model, max_candidates: {"gate_pass": 0, "tsu_generated": 0}
        )
        exit_code = runner.main([])
        assert exit_code == 0
        output = capsys.readouterr().out
        assert '"tsu_generated": 0' in output

    def test_legacy_scan_flag_bypasses_gate(self, monkeypatch):
        called = {"legacy": False, "gate": False}
        monkeypatch.setattr(runner.builder, "build_tsu_for_all", lambda **kw: called.__setitem__("legacy", True) or {})
        monkeypatch.setattr(runner, "_run_gate_wired", lambda *a, **kw: called.__setitem__("gate", True) or {})

        runner.main(["--legacy-scan"])
        assert called["legacy"] is True
        assert called["gate"] is False

    def test_identifier_flag_bypasses_gate_entirely(self, monkeypatch):
        called = {"single": False, "gate": False}
        monkeypatch.setattr(
            runner.builder,
            "build_tsu_for_identifier",
            lambda identifier, **kw: called.__setitem__("single", True) or {"report": {}},
        )
        monkeypatch.setattr(runner, "_run_gate_wired", lambda *a, **kw: called.__setitem__("gate", True) or {})

        runner.main(["--identifier", "PBC1742"])
        assert called["single"] is True
        assert called["gate"] is False


class TestBuilderUntouched:
    def test_build_tsu_for_identifier_signature_unchanged(self):
        import inspect

        from NAE.pipeline.tsu import builder as builder_module

        sig = inspect.signature(builder_module.build_tsu_for_identifier)
        assert list(sig.parameters.keys())[0] == "identifier"

    def test_build_tsu_for_all_still_exists_and_callable(self):
        from NAE.pipeline.tsu import builder as builder_module

        assert callable(builder_module.build_tsu_for_all)


class TestNoTsuFilesWritten:
    """실제 Production Crosswalk Storage에 이제 manual-confirmed 레코드가
    존재하므로(NAE-MANUAL-CROSSWALK-POPULATION-IMPLEMENTATION-001), 이
    테스트는 더 이상 실제 `_run_gate_wired()`를 프로덕션 데이터로 직접
    실행하지 않는다 — 그렇게 하면 테스트를 돌릴 때마다 실제 TSU가
    재생성되는 부작용이 생긴다(비결정적, 비격리). 대신 BLOCK 판정된
    entry는 Builder를 호출하지 않는다는 동일한 속성을 tmp_path
    기반으로 격리해 검증한다(TestBuilderNeverCalledForBlockedOrErrored
    와 동일 패턴)."""

    def test_gate_wired_run_writes_no_files_when_all_blocked(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(runner.builder, "build_tsu_for_identifier", lambda identifier, **kw: calls.append(identifier))

        repo = InMemoryCrosswalkRepository()  # 매핑 없음 -> 전부 BLOCK
        orchestrator = GateOrchestrator(repo)
        monkeypatch.setattr(gate_adapter, "load_manifest_entries", lambda: [ManifestEntryInput("X", True)])
        monkeypatch.setattr(gate_adapter, "build_default_orchestrator", lambda: orchestrator)

        result = runner._run_gate_wired(model="unused-model", max_candidates=None)
        assert result["tsu_generated"] == 0
        assert calls == []

    def test_real_production_manual_confirmed_entries_would_call_builder(self):
        """실제 Production 데이터 기준(읽기 전용, Builder 호출 없음) —
        이제 최소 2건(Dagg/Hiscox)이 PASS이므로 `_run_gate_wired()`를
        실제로 돌리면 Builder가 호출될 "것"이라는 사실 자체를
        gate_adapter 레벨(부작용 없는 identifier 계산만)에서 확인한다."""
        entries = gate_adapter.load_manifest_entries()
        orchestrator = gate_adapter.build_default_orchestrator()
        summary = gate_adapter.iter_eligible_identifiers(entries, orchestrator)
        assert summary.pass_count >= 2
        assert "Dagg_Church_Order" in summary.pass_identifiers
        assert "Hiscox_Standard_Manual" in summary.pass_identifiers
