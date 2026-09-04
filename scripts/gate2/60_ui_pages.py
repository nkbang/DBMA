#!/usr/bin/env python3
"""60_ui_pages.py — EXPECTED_PAGES import verification (exactly 9 pages).

Verifies that exactly these 9 page modules can be imported:
  ui.pages.dashboard, ui.pages.library, ui.pages.processing,
  ui.pages.research, ui.pages.monitor, ui.pages.chat,
  ui.pages.sermon_draft, ui.pages.sermon_review, ui.pages.help

DO NOT include: ui.pages.onboarding, ui.tabs, ui.sidebar

Task Order: C1-TASK-ORDER-GATE2-ORCHESTRATOR-SCAFFOLDING.md §3 Phase A
"""

import importlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVIDENCE_DIR = Path(__file__).resolve().parent / ".." / ".." / "evidence" / "gate2"

# Add project root to sys.path for module imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# EXPECTED_PAGES: exactly 9 pages — no more, no less
EXPECTED_PAGES = [
    "ui.pages.dashboard",
    "ui.pages.library",
    "ui.pages.processing",
    "ui.pages.research",
    "ui.pages.monitor",
    "ui.pages.chat",
    "ui.pages.sermon_draft",
    "ui.pages.sermon_review",
    "ui.pages.help",
]

# Explicitly excluded modules (must NOT be in EXPECTED_PAGES)
EXCLUDED_MODULES = [
    "ui.pages.onboarding",
    "ui.tabs",
    "ui.sidebar",
]


def main() -> dict:
    results: dict = {}
    all_pass = True

    # 1. Verify exactly 9 pages
    if len(EXPECTED_PAGES) != 9:
        results["page_count"] = {
            "status": "FAIL",
            "expected": 9,
            "actual": len(EXPECTED_PAGES),
        }
        all_pass = False
    else:
        results["page_count"] = {"status": "PASS", "count": 9}

    # 2. Verify no excluded modules in EXPECTED_PAGES
    for exc in EXCLUDED_MODULES:
        if exc in EXPECTED_PAGES:
            results[f"excluded_{exc}"] = {
                "status": "FAIL",
                "reason": f"{exc} must not be in EXPECTED_PAGES",
            }
            all_pass = False
        else:
            results[f"excluded_{exc}"] = {"status": "PASS"}

    # 3. Try importing each page module
    import_errors: list[str] = []
    for mod_name in EXPECTED_PAGES:
        try:
            mod = importlib.import_module(mod_name)
            results[mod_name] = {
                "status": "PASS",
                "file": str(getattr(mod, "__file__", "unknown")),
            }
        except Exception as exc:
            results[mod_name] = {
                "status": "FAIL",
                "reason": str(exc),
            }
            import_errors.append(f"{mod_name}: {exc}")
            all_pass = False

    # 4. Verify page files exist on disk
    pages_dir = PROJECT_ROOT / "ui" / "pages"
    if pages_dir.exists():
        disk_files = set()
        for p in pages_dir.glob("*.py"):
            if p.name not in ("__init__.py", "_base.py"):
                disk_files.add(p.stem)
        expected_stems = {m.split(".")[-1] for m in EXPECTED_PAGES}
        missing_on_disk = expected_stems - disk_files
        if missing_on_disk:
            results["disk_files"] = {
                "status": "FAIL",
                "missing": list(missing_on_disk),
            }
            all_pass = False
        else:
            results["disk_files"] = {"status": "PASS", "found": len(disk_files)}
    else:
        results["disk_files"] = {"status": "FAIL", "reason": f"{pages_dir} not found"}
        all_pass = False

    summary = {
        "script": "60_ui_pages.py",
        "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "all_pass": all_pass,
        "expected_pages_count": 9,
        "expected_pages": EXPECTED_PAGES,
        "excluded_modules": EXCLUDED_MODULES,
        "checks": results,
    }

    evidence_dir = EVIDENCE_DIR.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "60_ui_pages.json"
    evidence_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Result: {'PASS' if all_pass else 'FAIL'}")
    print(f"Expected pages (9): {EXPECTED_PAGES}")
    print(f"Import errors: {import_errors if import_errors else 'none'}")
    print(f"Evidence written to: {evidence_file}")
    return summary


if __name__ == "__main__":
    sys.exit(0 if main()["all_pass"] else 1)
