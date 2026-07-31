"""NAE Benchmark Runner 테스트.

runner.py는 실제 Qdrant에 연결하지 않는다 (Phase 5 Infrastructure First) —
retrieval_fn을 주입 가능한 함수로 설계했으므로, 여기서는 더미/스텁 함수로
run_benchmark()의 오케스트레이션·에러 격리·CLI만 검증한다.
"""

import json
from pathlib import Path

import pytest

from NAE.benchmark.runner import build_parser, main, run_benchmark


def _write_dataset(tmp_path: Path, records: list[dict]) -> Path:
    path = tmp_path / "dataset.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


def _record(benchmark_id: str, scriptures=None) -> dict:
    return {
        "benchmark_id": benchmark_id,
        "question": {"text": f"question {benchmark_id}", "language": "ko"},
        "expected": {"expected_scriptures": scriptures or [], "required_concepts": [], "expected_doctrine": ""},
        "retrieval": {"top_k": 5},
        "evaluation": {"status": "pending"},
        "metadata": {"created_version": "1.0", "source": "test"},
    }


class TestRunBenchmark:
    def test_run_benchmark_with_perfect_retrieval(self, tmp_path: Path):
        dataset = _write_dataset(tmp_path, [_record("B1", ["A"])])
        report = run_benchmark(dataset, retrieval_fn=lambda q: ["A"], top_k=5)
        assert report["passed"] == 1
        assert report["failed"] == 0

    def test_run_benchmark_empty_dataset_returns_error(self, tmp_path: Path):
        dataset = tmp_path / "empty.jsonl"
        dataset.write_text("", encoding="utf-8")
        report = run_benchmark(dataset, retrieval_fn=lambda q: [])
        assert "error" in report

    def test_run_benchmark_isolates_retrieval_failure_per_item(self, tmp_path: Path):
        """한 질문의 retrieval_fn 예외가 전체 배치를 죽이지 않아야 함."""
        dataset = _write_dataset(tmp_path, [_record("B1", ["A"]), _record("B2", ["A"])])

        def flaky_retrieval(question_text: str) -> list[str]:
            if "B1" in question_text:
                raise RuntimeError("simulated retrieval failure")
            return ["A"]

        report = run_benchmark(dataset, retrieval_fn=flaky_retrieval, top_k=5)
        assert report["retrieval_errors"] == 1
        assert report["passed"] == 1

    def test_run_benchmark_writes_output_file(self, tmp_path: Path):
        dataset = _write_dataset(tmp_path, [_record("B1", ["A"])])
        output = tmp_path / "report.json"
        run_benchmark(dataset, retrieval_fn=lambda q: ["A"], output=output)
        assert output.exists()
        saved = json.loads(output.read_text(encoding="utf-8"))
        assert saved["passed"] == 1

    def test_run_benchmark_missing_dataset_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            run_benchmark(tmp_path / "does_not_exist.jsonl", retrieval_fn=lambda q: [])


class TestCLI:
    def test_build_parser_requires_dataset(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_main_runs_with_dummy_retrieval(self, tmp_path: Path, capsys):
        dataset = _write_dataset(tmp_path, [_record("B1", ["A"])])
        exit_code = main(["--dataset", str(dataset)])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "total_questions" in out

    def test_main_returns_nonzero_on_missing_dataset(self, tmp_path: Path):
        exit_code = main(["--dataset", str(tmp_path / "missing.jsonl")])
        assert exit_code == 1
