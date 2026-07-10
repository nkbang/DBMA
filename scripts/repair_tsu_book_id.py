#!/usr/bin/env python3
"""
PT-METADATA-001: TSU Book Identity Repair Script

Repairs corrupted verse_mapping.book_id fields in TSU dataset.
All records currently have book_id="GEN" regardless of source document.

This script:
1. Maps source_document -> correct biblical book_id
2. Updates verse_mapping.book_id
3. Rebuilds tsu_id prefix from TSU-GEN-* to TSU-{book_id}-*
4. Preserves sequence numbers

Book mapping strategy:
- Extract book name from source_document filename patterns
- Use standard 3-letter biblical abbreviations (BGU style)
- Unknown mappings -> "UNKNOWN"

Biblical Book Abbreviations:
  OT: GEN, EXO, LEV, NUM, DEU, JOS, JDG, RUT, 1SA, 2SA, 1KI, 2KI, 
      1CH, 2CH, EZR, NEH, EST, JOB, PSA, PRO, ECC, SNG, ISA, JER,
      LAM, EZK, DAN, HOS, JOL, AMO, OBA, JON, MIC, NAV, HAB, ZEP,
      HAG, ZEC, MAL
  NT: MAT, MRK, LUK, JHN, ACT, ROM, 1CO, 2CO, GAL, EPH, PHP, COL,
      1TH, 2TH, 1TI, 2TI, TIT, PHM, HEB, JAS, 1PE, 2PE, 1JN, 2JN,
      3JN, JUD, REV
"""

import json
import re
import sys
import hashlib
from pathlib import Path
from collections import defaultdict


# ============================================================
# BOOK ID MAPPING TABLE
# Map source document name patterns -> book_id
# Priority order matters: more specific patterns first
# ============================================================

BOOK_ID_MAP = [
    # --- Old Testament: Historical Books ---
    {
        "patterns": ["1 kings", "the wisdom and the folly"],
        "book_id": "1KI"
    },
    {
        "patterns": ["2 kings", "the anchor bible"],
        "book_id": "2KI"
    },
    {
        "patterns": ["2 kings", "the power and the fury"],
        "book_id": "2KI"
    },
    {
        "patterns": ["2 kings", "volume 13"],
        "book_id": "2KI"
    },
    {
        "patterns": ["2 chronicles", "volume 15"],
        "book_id": "2CH"
    },
    {
        "patterns": ["1 peter", "volume 49"],
        "book_id": "1PE"
    },
    {
        "patterns": ["1 and 2 thessalonians", "volume 45"],
        "book_id": "1TH"
    },
    # --- Korean documents (NT) - explicit patterns for source_file matching ---
    {
        "patterns": ["마태복음"],  # Matthew
        "book_id": "MAT"
    },
    {
        "patterns": ["로마서"],  # Romans
        "book_id": "ROM"
    },
    {
        "patterns": ["고린도후서"],  # 2 Corinthians
        "book_id": "2CO"
    },
    # --- Korean documents in ARIRANG encoding (old Korean character set) ---
    # These are the ARIRANG-encoded equivalents of the above Korean book names
    {
        "patterns": ["마태복음"],  # ARIRANG for 마태복음 (Matthew)
        "book_id": "MAT"
    },
    {
        "patterns": ["로마서"],  # ARIRANG for 로마서 (Romans)
        "book_id": "ROM"
    },
    {
        "patterns": ["고린도전"],  # ARIRANG for 고린도후서 (2 Corinthians)
        "book_id": "2CO"
    },
]

# Fallback pattern matching for common book name patterns (regex -> book_id)
FALLBACK_PATTERNS = [
    (r"마태복음|마태복음", "MAT"),
    (r"로마서|로마서", "ROM"),
    (r"고린도후서|고린도전", "2CO"),
    (r"1\s*kings?", "1KI"),
    (r"2\s*kings?", "2KI"),
    (r"1\s*chronicles?", "1CH"),
    (r"2\s*chronicles?", "2CH"),
    (r"1\s*peter", "1PE"),
    (r"2\s*peter", "2PE"),
    (r"1\s*thessalonians?", "1TH"),
    (r"2\s*thessalonians?", "2TH"),
    (r"1\s*corinthians?|1\s*코린트", "1CO"),
    (r"2\s*corinthians?|2\s*코린트", "2CO"),
    (r"romans?", "ROM"),
    (r"mathew?|matthew?", "MAT"),
    (r"john|요한|יוחנן", "JHN"),
]


def determine_book_id(source_document: str, source_file: str) -> str:
    """
    Determine the correct book_id from source document name.
    
    Uses pattern matching against source_document and source_file fields.
    
    Args:
        source_document: The TSU source_document field value
        source_file: The TSU source_file field value
    
    Returns:
        3-letter biblical book abbreviation or "UNKNOWN"
    """
    # Combine both fields for pattern matching
    text = f"{source_document} {source_file}"
    text_lower = text.lower()
    
    # Check explicit mapping table first
    for mapping in BOOK_ID_MAP:
        for pattern in mapping["patterns"]:
            if pattern.lower() in text_lower:
                return mapping["book_id"]
    
    # Check fallback patterns
    for regex, book_id in FALLBACK_PATTERNS:
        if re.search(regex, text_lower):
            return book_id
    
    # Cannot determine - return UNKNOWN
    return "UNKNOWN"


def rebuild_tsu_id(original_tsu_id: str, new_book_id: str) -> str:
    """
    Rebuild TSU ID with corrected book_id prefix.
    
    Preserves the sequence number from original tsu_id.
    
    BEFORE: TSU-GEN-000936
    AFTER:  TSU-1PE-000936
    
    Args:
        original_tsu_id: Original TSU ID (e.g., "TSU-GEN-000936")
        new_book_id: Corrected book_id (e.g., "1PE")
    
    Returns:
        Rebuilt TSU ID (e.g., "TSU-1PE-000936")
    """
    # Extract sequence number from original tsu_id
    match = re.match(r"TSU-[A-Z]+-(\d+)", original_tsu_id)
    if match:
        sequence = match.group(1)
        return f"TSU-{new_book_id}-{sequence}"
    
    # Fallback: preserve original suffix
    return f"TSU-{new_book_id}-UNKNOWN"


def process_dataset(input_path: str, output_mode: str = "dry_run"):
    """
    Process the TSU dataset and repair book_id fields.
    
    Args:
        input_path: Path to the TSU dataset JSONL file
        output_mode: "dry_run", "preview", or "execute"
    
    Returns:
        dict with processing statistics
    """
    # Read all records
    records = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    print(f"Read {len(records)} records from {input_path}")
    
    # Track statistics
    stats = {
        "total_records": len(records),
        "repaired": 0,
        "unknown": 0,
        "unchanged": 0,
        "mapping_details": defaultdict(int),
        "sample_changes": []
    }
    
    if output_mode == "dry_run":
        # Generate dry run preview without modifying data
        print("\n" + "=" * 80)
        print("DRY RUN PREVIEW - PT-METADATA-001")
        print("=" * 80)
        
        for i, rec in enumerate(records[:50]):  # First 50 samples
            orig_book_id = rec.get("verse_mapping", {}).get("book_id", "UNKNOWN") if isinstance(rec.get("verse_mapping"), dict) else "UNKNOWN"
            orig_tsu_id = rec.get("tsu_id", "")
            source_doc = rec.get("source_document", "")[:60]
            chapter = rec.get("verse_mapping", {}).get("chapter", "?") if isinstance(rec.get("verse_mapping"), dict) else "?"
            
            new_book_id = determine_book_id(
                rec.get("source_document", ""),
                rec.get("source_file", "")
            )
            new_tsu_id = rebuild_tsu_id(orig_tsu_id, new_book_id)
            
            is_repair = (orig_book_id != new_book_id)
            
            if is_repair:
                stats["repaired"] += 1
                stats["mapping_details"][f"GEN -> {new_book_id}"] += 1
            else:
                stats["unchanged"] += 1
            
            # Collect sample changes
            if new_book_id != "GEN":
                if len(stats["sample_changes"]) < 50:
                    stats["sample_changes"].append({
                        "record_index": i,
                        "tsu_id_before": orig_tsu_id,
                        "tsu_id_after": new_tsu_id,
                        "book_id_before": orig_book_id,
                        "book_id_after": new_book_id,
                        "source_document": source_doc,
                        "chapter": chapter
                    })
        
        # Print preview table
        print(f"\n{'INDEX':<8} {'BEFORE (tsu_id)':<22} {'AFTER (tsu_id)':<22} {'BOOK_ID':>10}")
        print("-" * 80)
        for change in stats["sample_changes"]:
            tsu_before = change["tsu_id_before"]
            tsu_after = change["tsu_id_after"]
            bid_after = change["book_id_after"]
            print(f"{change['record_index']:<8} {tsu_before:<22} {tsu_after:<22} {bid_after:>10}")
        
        # Summary
        print("\n" + "=" * 80)
        print("DRY RUN SUMMARY")
        print("=" * 80)
        print(f"Total records analyzed: {stats['total_records']}")
        print(f"Records to repair:      {stats['repaired']}")
        print(f"Records unchanged:      {stats['unchanged']}")
        print(f"\nMapping distribution:")
        for mapping, count in sorted(stats["mapping_details"].items()):
            print(f"  {mapping:<15} -> {count:>6} records")
        
        return stats
    
    elif output_mode == "execute":
        # Execute the repair and write output
        modified_records = []
        changes_count = 0
        
        for rec in records:
            orig_tsu_id = rec.get("tsu_id", "")
            orig_book_id = rec.get("verse_mapping", {}).get("book_id", "GEN") if isinstance(rec.get("verse_mapping"), dict) else "GEN"
            
            new_book_id = determine_book_id(
                rec.get("source_document", ""),
                rec.get("source_file", "")
            )
            
            # Update verse_mapping.book_id
            modified_rec = json.loads(json.dumps(rec))  # Deep copy
            if isinstance(modified_rec.get("verse_mapping"), dict):
                modified_rec["verse_mapping"]["book_id"] = new_book_id
            
            # Rebuild tsu_id
            new_tsu_id = rebuild_tsu_id(orig_tsu_id, new_book_id)
            modified_rec["tsu_id"] = new_tsu_id
            
            if orig_book_id != new_book_id:
                changes_count += 1
            
            modified_records.append(modified_rec)
        
        # Write output file (in-place replacement)
        with open(input_path, 'w', encoding='utf-8') as f:
            for rec in modified_records:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        
        stats["repaired"] = changes_count
        stats["unchanged"] = len(records) - changes_count
        
        # Post-repair verification
        print(f"\nPost-repair book distribution:")
        post_dist = defaultdict(int)
        for rec in modified_records:
            bid = rec.get("verse_mapping", {}).get("book_id", "UNKNOWN") if isinstance(rec.get("verse_mapping"), dict) else "UNKNOWN"
            post_dist[bid] += 1
        
        for book_id, count in sorted(post_dist.items()):
            print(f"  {book_id:<10} -> {count:>6} records ({count/len(records)*100:.1f}%)")
        
        return stats
    
    elif output_mode == "validate":
        # Validate the repaired dataset
        post_dist = defaultdict(int)
        source_dist = defaultdict(int)
        unknown_count = 0
        
        for rec in records:
            bid = rec.get("verse_mapping", {}).get("book_id", "UNKNOWN") if isinstance(rec.get("verse_mapping"), dict) else "UNKNOWN"
            post_dist[bid] += 1
            
            src = rec.get("source_document", "UNKNOWN")[:50]
            source_dist[src] += 1
            
            if bid == "UNKNOWN":
                unknown_count += 1
        
        print("\n" + "=" * 80)
        print("POST-REPAIR VALIDATION - PT-METADATA-001")
        print("=" * 80)
        
        # 1. Book distribution
        print(f"\n1. BOOK DISTRIBUTION (after repair):")
        total = sum(post_dist.values())
        for book_id, count in sorted(post_dist.items(), key=lambda x: -x[1]):
            print(f"   {book_id:<10} -> {count:>6} records ({count/total*100:.1f}%)")
        
        # 2. Record count check
        print(f"\n2. RECORD COUNT:")
        print(f"   Expected: 10,338")
        print(f"   Actual:   {total:,}")
        count_ok = (total == 10338)
        print(f"   Status:   {'PASS' if count_ok else 'FAIL'}")
        
        # 3. Unknown count
        print(f"\n3. UNKNOWN MAPPINGS: {unknown_count} records")
        
        # 4. Sample verification
        print(f"\n4. SAMPLE VERIFICATION:")
        for book_id in ["1PE", "2CH", "1KI"]:
            matching = [rec for rec in records if 
                       (isinstance(rec.get("verse_mapping"), dict) and 
                        rec.get("verse_mapping", {}).get("book_id") == book_id)]
            if matching:
                sample = matching[0]
                src_doc = sample.get("source_document", "")[:50]
                print(f"   {book_id}: Found {len(matching)} records")
                print(f"     Sample source: {src_doc}")
        
        return stats


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='PT-METADATA-001: TSU Book Identity Repair')
    parser.add_argument('--input', default='./output/bench/tsu_dataset.jsonl',
                       help='Path to input TSU dataset JSONL file')
    parser.add_argument('--mode', choices=['dry_run', 'execute', 'validate'], 
                       default='dry_run', help='Execution mode')
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)
    
    stats = process_dataset(args.input, args.mode)
    
    # Write mapping result to output file
    output_dir = Path('./output')
    output_dir.mkdir(exist_ok=True)
    
    if args.mode == 'dry_run':
        output_file = output_dir / 'PT_METADATA_001_MAPPING_RESULT.md'
    elif args.mode == 'execute':
        output_file = output_dir / 'PT_METADATA_001_MAPPING_RESULT.md'
    else:
        output_file = output_dir / 'PT_METADATA_001_MAPPING_RESULT.md'
    
    # Generate mapping result report
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# PT-METADATA-001 — Book Mapping Result\n\n")
        f.write(f"## Execution Mode: {args.mode}\n\n")
        f.write(f"| Field | Value |\n|-------|-------|\n")
        f.write(f"| Total Records | {stats['total_records']} |\n")
        f.write(f"| Repaired | {stats['repaired']} |\n")
        f.write(f"| Unchanged | {stats['unchanged']} |\n\n")
        
        if stats.get("mapping_details"):
            f.write("## Mapping Distribution\n\n")
            f.write("| Source -> Target | Count |\n|-----------------|-------|\n")
            for mapping, count in sorted(stats["mapping_details"].items()):
                f.write(f"| {mapping} | {count} |\n")
        
        if stats.get("sample_changes"):
            f.write("\n## Sample Changes\n\n")
            f.write("| Index | TSU ID Before | TSU ID After | Book ID Before | Book ID After |\n")
            f.write("|-------|--------------|--------------|---------------|--------------|\n")
            for change in stats["sample_changes"][:50]:
                f.write(f"| {change['record_index']} | {change['tsu_id_before']} | {change['tsu_id_after']} | {change['book_id_before']} | {change['book_id_after']} |\n")
    
    print(f"\nMapping result written to: {output_file}")


if __name__ == "__main__":
    main()