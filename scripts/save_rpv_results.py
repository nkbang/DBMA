#!/usr/bin/env python3
"""Save raw RPV results to individual JSON files."""
import json, re, sys

raw_dir = "/tmp"
bench_dir = "output/bench"
ids = ["01a", "01b", "02", "03a", "03b", "04", "07", "08a", "08b"]

for rid in ids:
    raw_file = f"{raw_dir}/rpv_{rid}_raw.txt"
    out_file = f"{bench_dir}/rpv_real_{rid}.json"
    try:
        with open(raw_file, 'r') as f:
            content = f.read()
        match = re.search(r'=== JSON RESULTS ===\s*\n(\[.*\])\s*$', content, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"{rid}: saved ({len(data)} query results)")
        else:
            print(f"{rid}: NO JSON FOUND (lines: {content.count(chr(10))})")
    except FileNotFoundError:
        print(f"{rid}: RAW FILE NOT FOUND")
