import sys; sys.path.insert(0, "/Users/David/DBMA")
"""SPRINT34-SMITH-PHASEB: E2E verification script for Smith Bible Dictionary integration."""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("smith_e2e_verify")

@dataclass
class TestCaseResult:
    name: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)

@dataclass
class E2EReport:
    test_cases: list[TestCaseResult] = field(default_factory=list)
    def add(self, name: str, status: str, details: dict | None = None):
        self.test_cases.append(TestCaseResult(name=name, status=status, details=details or {}))
    @property
    def all_passed(self) -> bool:
        return all(tc.status == "PASS" for tc in self.test_cases)
    def summary(self) -> str:
        lines = ["\n" + "=" * 70, "  SPRINT34-SMITH-PHASEB E2E VERIFICATION REPORT", "=" * 70]
        for tc in self.test_cases:
            icon = "OK" if tc.status == "PASS" else "FAIL"
            lines.append(f"  [{icon}] {tc.name}")
            if tc.details:
                for k, v in tc.details.items():
                    lines.append(f"      {k}: {v}")
        lines.append("=" * 70)
        lines.append(f"  Overall: {'ALL PASS' if self.all_passed else 'SOME FAILED'}")
        lines.append("=" * 70 + "\n")
        return "\n".join(lines)

report = E2EReport()

def phase1_activation():
    from NAE.smith_activation import should_activate_smith, rewrite_query_for_smith
    test_cases = [
        ("Who was Aaron in the Bible?", True),
        ("What does covenant mean in the Bible?", True),
        ("Who were the Pharisees?", True),
        ("Where is Bethlehem?", True),
        ("What happened at the Red Sea?", True),
        ("오늘 날씨가 어때?", False),
        ("파이썬 배우기", False),
    ]
    all_pass = True
    details = {}
    for query, expected in test_cases:
        result = should_activate_smith(query)
        status = "PASS" if result == expected else "FAIL"
        if status == "FAIL":
            all_pass = False
        details[query[:40]] = f"{result} (exp {expected}) [{status}]"
    report.add("Phase 1: Smith Activation Heuristic", "PASS" if all_pass else "FAIL", details)

def phase2_smith_retrieval():
    from NAE.reference_retrieval_adapter import search_reference
    test_queries = ["Aaron", "covenant", "Bethlehem", "Pharisees", "Red Sea"]
    all_pass = True
    details = {}
    for query in test_queries:
        start = time.time()
        results = search_reference(query, top_k=3)
        elapsed = time.time() - start
        count = len(results)
        valid_schema = all(
            isinstance(r, dict) and "text" in r and "source_id" in r
            for r in results
        ) if results else True
        status = "PASS" if (count > 0 and valid_schema) else "FAIL"
        if status == "FAIL":
            all_pass = False
        details[query] = f"{count} results, schema={valid_schema}, time={elapsed:.2f}s [{status}]"
    report.add("Phase 2: Smith Retrieval (direct)", "PASS" if all_pass else "FAIL", details)

def phase3_e2e_pipeline():
    from ui.pages.chat import generate_answer, _get_processor, _inject_smith_context
    test_queries = [
        "Who was Aaron in the Bible?",
        "What does covenant mean in the Bible?",
        "Where is Bethlehem?",
    ]
    all_pass = True
    details = {}
    for query in test_queries:
        start = time.time()
        answer, sources = generate_answer(query)
        elapsed = time.time() - start
        tsu_count = len(sources) if sources else 0
        has_answer = bool(answer and len(answer.strip()) > 10)
        processor = _get_processor()
        response = processor.process(query, query_id="e2e-test", k=5)
        smith_results = _inject_smith_context(response, query)
        smith_injected = len(smith_results) > 0
        context_block_len = len(response.llm_context_block or "")
        status = "PASS" if (has_answer and tsu_count > 0) else "FAIL"
        if status == "FAIL":
            all_pass = False
        details[query[:40]] = {
            "answer_length": len(answer),
            "tsu_results": tsu_count,
            "smith_injected": smith_injected,
            "smith_entries": len(smith_results),
            "context_block_len": context_block_len,
            "gen_time_s": f"{elapsed:.2f}",
            "status": status,
        }
    report.add("Phase 3: E2E Pipeline (generate_answer)", "PASS" if all_pass else "FAIL", details)

def phase4_context_injection():
    from ui.pages.chat import _get_processor, _inject_smith_context
    from core.generation import GenerationService
    test_queries = [
        "Who was Aaron in the Bible?",
        "What does covenant mean in the Bible?",
    ]
    all_pass = True
    details = {}
    for query in test_queries:
        processor = _get_processor()
        response = processor.process(query, query_id="ctx-test", k=5)
        smith_results = _inject_smith_context(response, query)
        generator = GenerationService()
        prompt, context_used = generator._build_prompt(response)
        has_smith_in_prompt = "Smith Bible Dictionary" in prompt if smith_results else True
        has_smith_in_context = "Smith Bible Dictionary" in (response.llm_context_block or "")
        status = "PASS" if (has_smith_in_prompt and context_used) else "FAIL"
        if status == "FAIL":
            all_pass = False
        details[query[:40]] = {
            "smith_results": len(smith_results),
            "context_used": context_used,
            "smith_in_prompt": has_smith_in_prompt,
            "smith_in_context_block": has_smith_in_context,
            "status": status,
        }
    report.add("Phase 4: Context Injection Verification", "PASS" if all_pass else "FAIL", details)

def phase5_provenance():
    from ui.pages.chat import _get_processor, _inject_smith_context
    test_queries = [
        "Who was Aaron in the Bible?",
        "What does covenant mean in the Bible?",
    ]
    all_pass = True
    details = {}
    for query in test_queries:
        processor = _get_processor()
        response = processor.process(query, query_id="prov-test", k=5)
        smith_results = _inject_smith_context(response, query)
        tsu_citations = len(response.citations or [])
        smith_provenance = len(smith_results)
        status = "PASS" if (tsu_citations > 0) else "FAIL"
        if status == "FAIL":
            all_pass = False
        details[query[:40]] = {
            "tsu_citations": tsu_citations,
            "smith_provenance_entries": smith_provenance,
            "status": status,
        }
    report.add("Phase 5: Provenance Check", "PASS" if all_pass else "FAIL", details)

def phase6_fault_isolation():
    from ui.pages.chat import _get_processor, _inject_smith_context
    from NAE import reference_retrieval_adapter
    original_search = reference_retrieval_adapter.search_reference
    def failing_search(query, top_k=3):
        raise ConnectionError("Simulated Smith connection failure")
    reference_retrieval_adapter.search_reference = failing_search
    try:
        processor = _get_processor()
        response = processor.process("Who was Aaron in the Bible?", query_id="fault-test", k=5)
        smith_results = _inject_smith_context(response, "Who was Aaron in the Bible?")
        tsu_count = len(response.top_k_results or [])
        tsu_citations = len(response.citations or [])
        smith_injected = len(smith_results)
        status = "PASS" if (tsu_count > 0 and tsu_citations > 0 and smith_injected == 0) else "FAIL"
        report.add("Phase 6: Fault Isolation", status, {
            "tsu_results": tsu_count,
            "tsu_citations": tsu_citations,
            "smith_entries_on_failure": smith_injected,
            "status": status,
        })
    except Exception as e:
        report.add("Phase 6: Fault Isolation", "FAIL", {"error": str(e)})
    finally:
        reference_retrieval_adapter.search_reference = original_search

def phase7_regression():
    from ui.pages.chat import _get_processor
    processor = _get_processor()
    test_queries = ["은혜", "하나님의 주권", "예수 그리스도"]
    all_pass = True
    details = {}
    for query in test_queries:
        response = processor.process(query, query_id="reg-test", k=5)
        tsu_count = len(response.top_k_results or [])
        tsu_citations = len(response.citations or [])
        status = "PASS" if (tsu_count > 0 and tsu_citations > 0) else "FAIL"
        if status == "FAIL":
            all_pass = False
        details[query] = {"tsu_results": tsu_count, "tsu_citations": tsu_citations, "status": status}
    report.add("Phase 7: Regression (TSU flow)", "PASS" if all_pass else "FAIL", details)

def main():
    print("\n" + "=" * 70)
    print("  SPRINT34-SMITH-PHASEB E2E VERIFICATION")
    print("=" * 70)
    phases = [
        ("Phase 1: Smith Activation Heuristic", phase1_activation),
        ("Phase 2: Smith Retrieval (direct)", phase2_smith_retrieval),
        ("Phase 3: E2E Pipeline (generate_answer)", phase3_e2e_pipeline),
        ("Phase 4: Context Injection Verification", phase4_context_injection),
        ("Phase 5: Provenance Check", phase5_provenance),
        ("Phase 6: Fault Isolation", phase6_fault_isolation),
        ("Phase 7: Regression (TSU flow)", phase7_regression),
    ]
    for name, func in phases:
        print(f"\n{'-' * 70}")
        print(f"  Running {name}...")
        try:
            func()
            print(f"  OK {name} completed")
        except Exception as e:
            logger.error("%s FAILED with exception: %s", name, e, exc_info=True)
            report.add(name, "FAIL", {"error": str(e)})
    print(report.summary())
    report_path = "/Users/David/DBMA/output/smith_e2e_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {tc.name: {"status": tc.status, **tc.details} for tc in report.test_cases},
            f, ensure_ascii=False, indent=2,
        )
    print(f"  Detailed report written to: {report_path}")
    return 0 if report.all_passed else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
