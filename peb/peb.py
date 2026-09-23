"""PEB v0.1 command-line entry point."""
from __future__ import annotations
import argparse
import asyncio
from pathlib import Path
from typing import Any
import yaml
from peb.llm import OllamaPlanner
from peb.runner import SessionRecorder, run_browser

def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pastor End-User Bot v0.1")
    parser.add_argument("--scenario", required=True, type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8501")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--ollama-model", default="qwen3.6:35b-DBMAcode")
    parser.add_argument("--runs-dir", type=Path, default=Path("peb/runs"))
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser

async def async_main(args: argparse.Namespace) -> int:
    scenario = load_yaml(args.scenario)
    run_file = args.runs_dir / f"{scenario['id']}.jsonl"
    recorder = SessionRecorder(run_file)
    planner = OllamaPlanner(args.ollama_model, args.ollama_url)
    if args.dry_run:
        print(f"PEB scenario loaded: {scenario['id']}")
        print(f"Goal: {scenario['goal']['statement'].strip()}")
        print(f"Workflow steps: {len(scenario['workflow'])}")
        print("Mode: planner/browser execution not started")
        return 0
    result = await run_browser(
        scenario=scenario,
        planner=planner,
        base_url=args.base_url,
        recorder=recorder,
        headless=not args.headed,
    )
    print(f"PEB result: {result['status']} ({result['steps']} steps)")
    print(f"Session log: {run_file}")
    return 0 if result["status"] == "COMPLETED" else 2

def main() -> int:
    return asyncio.run(async_main(build_parser().parse_args()))

if __name__ == "__main__":
    raise SystemExit(main())
