#!/usr/bin/env python3
"""
sync_architecture_visualization.py

Parse docs/STATE.md checkpoint and sprint information, then update
architecture visualization files (DBMA_ARCHITECTURE_MAP.md and
docs/ARCHITECTURE_DIAGRAM.md) with current status.

Usage:
    python scripts/sync_architecture_visualization.py [--dry-run]

Output:
    - Updates "Current Sprint" and "Last synced" in DBMA_ARCHITECTURE_MAP.md
    - Updates "ADR Summary" and date in docs/ARCHITECTURE_DIAGRAM.md
    - Prints summary of changes
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Workspace root
ROOT = Path(__file__).resolve().parents[1]
STATE_MD = ROOT / "docs" / "STATE.md"
ARCH_MAP = ROOT / "DBMA_ARCHITECTURE_MAP.md"
ARCH_DIAGRAM = ROOT / "docs" / "ARCHITECTURE_DIAGRAM.md"

# --- Parsing ---

def parse_state_md(path: Path) -> dict:
    """Parse STATE.md and extract sprint status, checkpoints, and ADRs."""
    text = path.read_text(encoding="utf-8")
    
    result = {
        "current_sprint": "",
        "release_version": "",
        "release_status": "",
        "checkpoints_done": [],
        "checkpoints_pending": [],
        "adrs": [],
        "last_sprint_section": "",
    }
    
    # Extract version status block
    version_match = re.search(
        r"```\s*\nRelease State:\s*(.+?)\s*\nDevelopment:\s*(.+?)\s*\nNext:\s*(.+?)\s*\n```",
        text
    )
    if version_match:
        result["release_status"] = version_match.group(1).strip()
        result["development"] = version_match.group(2).strip()
        result["next"] = version_match.group(3).strip()
    
    # Extract version line
    ver_match = re.search(r"Version:\s*(.+?)\s*\+", text)
    if ver_match:
        result["release_version"] = ver_match.group(1).strip()
    
    # Extract latest sprint from SPRINT28~33-D section
    sprint_section = re.search(
        r"## SPRINT28~33-D 진행 내역.*?(?=---)",
        text,
        re.DOTALL
    )
    if sprint_section:
        content = sprint_section.group()
        # Find the highest sprint number
        sprints = re.findall(r"SPRINT(\d+)[-A-Z]?", content)
        if sprints:
            max_sprint = max(int(s) for s in sprints)
            result["current_sprint"] = f"SPRINT{max_sprint}"
            result["last_sprint_section"] = content[:200] + "..."
    
    # Extract checkpoints
    checkpoint_section = re.search(
        r"## 체크포인트\s*\n((?:- \[.\].*\n*)+)",
        text,
        re.DOTALL
    )
    if checkpoint_section:
        cp_text = checkpoint_section.group(1)
        result["checkpoints_done"] = [
            line.strip().lstrip("- [x] ").split("\n")[0].strip()
            for line in cp_text.split("\n")
            if line.strip().startswith("- [x]")
        ]
        result["checkpoints_pending"] = [
            line.strip().lstrip("- [ ] ").split("\n")[0].strip()
            for line in cp_text.split("\n")
            if line.strip().startswith("- [ ]")
        ]
    
    # Extract ADRs — handle multi-line entries by joining continuation lines
    adr_section = re.search(
        r"## 아키텍처 결정 \(ADR\)\s*\n((?:- .+\n*)+)",
        text,
        re.DOTALL
    )
    if adr_section:
        adr_text = adr_section.group(1)
        # Join lines that start with `- ` as separate ADR entries
        # Lines that don't start with `- ` are continuations of the previous entry
        lines = adr_text.split("\n")
        merged_lines = []
        current = ""
        for line in lines:
            if line.strip().startswith("- "):
                if current:
                    merged_lines.append(current)
                current = line.strip()
            else:
                if current:
                    current += " " + line.strip()
        if current:
            merged_lines.append(current)
        
        for line in merged_lines:
            # Match: - `docs/architecture/ADR-001-Retrieval-Engine-Authority.md` (accepted):
            # Also handles: ADR-007-Semantic-Boundary-Detector.md` + Amendment A (accepted):
            adr_match = re.search(
                r"ADR-(\d+)-([A-Za-z0-9][A-Za-z0-9\-]+(?:\+[A-Za-z0-9\-]+)?)\.md`\s*(?:\+\s*[A-Za-z\s]*?)?\(([^)]+)\)",
                line
            )
            if adr_match:
                result["adrs"].append({
                    "number": int(adr_match.group(1)),
                    "name": adr_match.group(2).strip(),
                    "status": adr_match.group(3).strip() if adr_match.group(3) else "unknown",
                })
    
    return result


# --- Update functions ---

def update_arch_map(state: dict, dry_run: bool = False) -> str | None:
    """Update DBMA_ARCHITECTURE_MAP.md with current sprint status."""
    text = ARCH_MAP.read_text(encoding="utf-8")
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Update Sprint Status Reference section
    new_section = f"""## Sprint Status Reference

Current Phase: Production Engineering / Release Stabilization  
Latest Sprint: {state['current_sprint'] or 'N/A'}  
Release: {state['release_version'] or 'v1.3.0'}  
Status: {state['release_status'] or 'STABLE'}  
Last synced: {today}  
For detailed state: see [`docs/STATE.md`](docs/STATE.md)
"""
    
    # Find and replace the Sprint Status Reference section
    pattern = r"## Sprint Status Reference\s*\n.*?(?=\n## |\Z)"
    if re.search(pattern, text, re.DOTALL):
        new_text = re.sub(
            pattern, 
            new_section.rstrip() + "\n", 
            text, 
            flags=re.DOTALL
        )
    else:
        new_text = text + "\n\n" + new_section
    
    if not dry_run:
        ARCH_MAP.write_text(new_text, encoding="utf-8")
    
    return new_text if dry_run else None


def update_arch_diagram(state: dict, dry_run: bool = False) -> str | None:
    """Update docs/ARCHITECTURE_DIAGRAM.md with current ADR summary and date."""
    text = ARCH_DIAGRAM.read_text(encoding="utf-8")
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Build ADR table from parsed data
    adr_rows = ""
    for adr in sorted(state.get("adrs", []), key=lambda x: x["number"]):
        adr_rows += f"| ADR-{adr['number']:03d} | {adr['name']} | {adr['status']}\n"
    
    if not adr_rows.strip():
        adr_rows = "| (no ADRs parsed) | — | — |\n"
    
    new_adr_table = f"""## Key Architecture Decisions (ADR Summary)

| ADR | Topic | Status |
|-----|-------|--------|
{adr_rows}"""
    
    # Replace ADR table section — match from header up to (not including) the
    # NEXT "## " heading of any kind, or end of file. Anchoring only on
    # "## Current Sprint" (the original pattern) silently swallows any other
    # sections a human has added in between (confirmed: deleted 7 diagram
    # sections, 2026-07-27) — stop at the first following heading instead.
    pattern = r"(## Key Architecture Decisions \(ADR Summary\))\s*\n.*?(?=\n## |\Z)"
    if re.search(pattern, text, re.DOTALL):
        new_text = re.sub(
            pattern,
            new_adr_table.rstrip() + "\n",
            text,
            flags=re.DOTALL
        )
    else:
        # Append if not found
        new_text = text + "\n\n" + new_adr_table
    
    # Update date
    new_text = re.sub(
        r"\*Generated: \d{4}-\d{2}-\d{2}\*",
        f"*Generated: {today}*",
        new_text
    )
    
    if not dry_run:
        ARCH_DIAGRAM.write_text(new_text, encoding="utf-8")
    
    return new_text if dry_run else None


# --- Main ---

def main():
    dry_run = "--dry-run" in sys.argv
    
    if not STATE_MD.exists():
        print(f"ERROR: {STATE_MD} not found.", file=sys.stderr)
        sys.exit(1)
    
    state = parse_state_md(STATE_MD)
    
    print(f"=== Architecture Visualization Sync ===")
    print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}")
    print(f"Current Sprint: {state['current_sprint'] or 'N/A'}")
    print(f"Release: {state['release_version'] or 'v1.3.0'}")
    print(f"Status: {state['release_status'] or 'STABLE'}")
    print(f"ADR count: {len(state.get('adrs', []))}")
    print(f"Checkpoints done: {len(state.get('checkpoints_done', []))}")
    print(f"Checkpoints pending: {len(state.get('checkpoints_pending', []))}")
    print()
    
    if dry_run:
        print("[DRY RUN] No files will be modified.")
        update_arch_map(state, dry_run=True)
        update_arch_diagram(state, dry_run=True)
    else:
        update_arch_map(state)
        update_arch_diagram(state)
        print("Files updated:")
        print(f"  - {ARCH_MAP}")
        print(f"  - {ARCH_DIAGRAM}")
    
    print()
    print("Sync complete.")


if __name__ == "__main__":
    main()