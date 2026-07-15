#!/usr/bin/env python3
"""
DBMA v1.1.x — TSU Book Metadata Repair Script
===============================================

Purpose:
  Repair verse_mapping.book_id and tsu_id for all 10,338 TSU records
  by parsing source_file paths and document titles.

Rules:
  - NEVER overwrites original file
  - ALWAYS creates new output file
  - DRY-RUN mode REQUIRED (default) — set MODE="EXECUTE" to actually apply changes
  - Before/after sample (50 records) always displayed

Usage:
  python scripts/repair_tsu_book_metadata.py [--mode dry-run|execute]
"""

import json
import os
import sys
import hashlib
import shutil
import unicodedata
import re
from collections import Counter
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

INPUT_PATH = "output/bench/tsu_dataset.jsonl"
BACKUP_PATH = "output/bench/tsu_dataset_backup_pre_P0.jsonl"
OUTPUT_PATH = "output/bench/tsu_dataset_repaired_book_metadata.jsonl"
DRY_RUN_OUTPUT = "output/bench/tsu_dataset_repaired_book_metadata_dryrun.jsonl"

# Korean → English book mapping
# NOTE: values MUST be full English book names (keys of BOOK_NAME_TO_SBL_ID),
# not book_id codes — extract_book_name_from_source() does a second lookup
# via BOOK_NAME_TO_SBL_ID.get(en_book, "UNKNOWN"), so a code here silently
# resolves to "UNKNOWN" even when the Korean name is matched correctly.
KOREAN_TO_ENGLISH = {
    "마태복음": "Matthew",
    "마가복음": "Mark",
    "누가복음": "Luke",
    "요한복음": "John",
    "사도행전": "Acts",
    "로마서": "Romans",
    "고린도전서": "1 Corinthians",
    "고린도후서": "2 Corinthians",
    "갈라디아서": "Galatians",
    "에베소서": "Ephesians",
    "빌립보서": "Philippians",
    "골로새서": "Colossians",
    "데살로니가전서": "1 Thessalonians",
    "데살로니가후서": "2 Thessalonians",
    "디모데전서": "1 Timothy",
    "디모데후서": "2 Timothy",
    "디도서": "Titus",
    "빌레몬서": "Philemon",
    "히브리서": "Hebrews",
    "야고보서": "James",
    "베드로전서": "1 Peter",
    "베드로후서": "2 Peter",
    "요한일서": "1 John",
    "요한이서": "2 John",
    "요한삼서": "3 John",
    "유다서": "Jude",
}

# English book name → SBL ID mapping (66 books)
BOOK_NAME_TO_SBL_ID = {
    # Old Testament — Law
    "Genesis": "GEN",
    "Exodus": "EXO",
    "Leviticus": "LEV",
    "Numbers": "NUM",
    "Deuteronomy": "DEU",
    
    # Old Testament — Historical
    "Joshua": "JOS",
    "Judges": "JDG",
    "Ruth": "RUT",
    "1 Samuel": "1SA",
    "2 Samuel": "2SA",
    "1 Kings": "1KI",
    "2 Kings": "2KI",
    "1 Chronicles": "1CH",
    "2 Chronicles": "2CH",
    "1 & 2 Chronicles": "2CH",
    "Ezra": "EZR",
    "Nehemiah": "NEH",
    "Esther": "EST",
    
    # Old Testament — Wisdom/Poetry
    "Job": "JOB",
    "Psalms": "PSA",
    "Proverbs": "PRO",
    "Ecclesiastes": "ECC",
    "Song of Solomon": "SOL",
    "Song of Songs": "SOL",
    
    # Old Testament — Prophets
    "Isaiah": "ISA",
    "Jeremiah": "JER",
    "Lamentations": "LAM",
    "Ezekiel": "EZE",
    "Daniel": "DAN",
    "Hosea": "HOS",
    "Joel": "JOEL",
    "Amos": "AMOS",
    "Obadiah": "OBA",
    "Jonah": "JON",
    "Micah": "MIC",
    "Nahum": "NAM",
    "Habakkuk": "HAB",
    "Zephaniah": "ZEP",
    "Haggai": "HAG",
    "Zechariah": "ZEC",
    "Malachi": "MAL",
    
    # New Testament
    "Matthew": "MAT",
    "Mark": "MRK",
    "Luke": "LUK",
    "John": "JHN",
    "Acts": "ACT",
    "Romans": "ROM",
    "1 Corinthians": "1CO",
    "2 Corinthians": "2CO",
    "Galatians": "GAL",
    "Ephesians": "EPH",
    "Philippians": "PHP",
    "Colossians": "COL",
    "1 Thessalonians": "1TH",
    "2 Thessalonians": "2TH",
    "1 and 2 Thessalonians": "1TH",
    "1 Timothy": "1TI",
    "2 Timothy": "2TI",
    "Titus": "TIT",
    "Philemon": "PHM",
    "Hebrews": "HEB",
    "James": "JAS",
    "1 Peter": "1PE",
    "2 Peter": "2PE",
    "1 John": "1JN",
    "2 John": "2JN",
    "3 John": "3JN",
    "Jude": "JUD",
    "Revelation": "REV",
}


# ============================================================================
# PARSING FUNCTIONS
# ============================================================================

def extract_book_name_from_source(source_file: str) -> tuple:
    """
    Extract book name from source_file path.
    
    Returns:
        (book_name, confidence) — confidence = 'HIGH', 'MEDIUM', or 'LOW'
    """
    basename = os.path.basename(source_file)
    
    # Korean document detection — handle both composed and jamo forms
    # NFKC normalize the basename to convert jamo to composed form
    norm_basename = unicodedata.normalize('NFKC', basename)
    
    # Try direct match first on normalized basename
    for kr_book, en_book in KOREAN_TO_ENGLISH.items():
        if kr_book in norm_basename or kr_book in basename:
            sbl_id = BOOK_NAME_TO_SBL_ID.get(en_book, "UNKNOWN")
            return (en_book, sbl_id, "HIGH")
    
    # Additional Korean detection: look for Hangul range characters after "N. " prefix
    ko_match = re.search(r'^\d+\.\s+[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF]+', norm_basename)
    if ko_match:
        # Extract Korean text and normalize it to find the book name
        kr_text = ko_match.group(0).split('.', 1)[1].strip()
        # Direct mapping for known documents (check before NFKC-normalized forms)
        # Original jamo/composed forms from filename
        orig_kr = ko_match.group(0).split('.', 1)[1].strip() if ko_match else kr_text
        
        if '고린도전서' in orig_kr or '고린도전서' in orig_kr or re.search(r'[ᄀ-῿]+도전서', orig_kr):
            return ("1 Corinthians", "1CO", "HIGH")
        if '고린도후서' in kr_text or '고린도후서' in orig_kr or re.search(r'[ᄀ-῿]+후서', orig_kr):
            return ("2 Corinthians", "2CO", "HIGH")
        if '로마서' in kr_text or re.search(r'[ᄅ-῿]+서', orig_kr):
            # Verify it's Romans specifically by checking for '로' pattern
            if '로마서' in orig_kr or (re.search(r'[ᄅ-῿]+서', orig_kr) and not any(x in orig_kr for x in ['전서', '후서'])):
                return ("Romans", "ROM", "HIGH")
        if '마태복음' in kr_text or '매태복음' in kr_text or re.search(r'[ᄆ-῿]+다하복음', orig_kr):
            return ("Matthew", "MAT", "HIGH")
        return (None, "UNKNOWN", "LOW")  # unknown Korean book
    
    # English document detection (priority order — specific patterns first)
    
    # Combined volumes
    if "1 and 2 Thessalonians" in basename:
        return ("1 and 2 Thessalonians", "1TH", "HIGH")
    if "1 & 2 Chronicles" in basename or "1_ 2 Chronicles" in basename or "1, 2 Chronicles" in basename:
        return ("1 & 2 Chronicles", "2CH", "HIGH")
    
    # Multi-book combinations
    if "1 Kings" in basename and "2 Kings" in basename:
        return ("1 & 2 Kings", "1KI", "MEDIUM")
    
    # Specific documents (priority order)
    if "Power and the Fury" in basename and "2 Kings" in basename:
        return ("2 Kings", "2KI", "HIGH")
    if "Anchor Bible Commentary" in basename and "2 Kings" in basename:
        return ("2 Kings", "2KI", "HIGH")
    if "Volume 13" in basename and "2 Kings" in basename:
        return ("2 Kings", "2KI", "HIGH")
    if "2 Kings" in basename:
        return ("2 Kings", "2KI", "HIGH")
    
    if "Wisdom and the Folly" in basename or ("1 Kings" in basename and "Volume" not in basename):
        return ("1 Kings", "1KI", "HIGH")
    if "1 Kings" in basename:
        return ("1 Kings", "1KI", "HIGH")
    
    if "1 Peter" in basename:
        return ("1 Peter", "1PE", "HIGH")
    
    if "Romans" in basename and ("로마서" not in basename):
        return ("Romans", "ROM", "HIGH")
    
    if "고린도후서" in basename:
        return ("2 Corinthians", "2CO", "HIGH")
    
    # Fallback — try to extract first book name from content header
    # (will be handled in repair_record)
    
    return (None, "UNKNOWN", "LOW")


def parse_book_id_from_content(content: str) -> tuple:
    """
    Fallback: extract book name from content header.
    
    Returns:
        (book_name, sbl_id, confidence)
    """
    # Look for source line in YAML front matter
    for line in content.split('\n')[:5]:
        if line.startswith('source:'):
            source_title = line.replace('source:', '').strip()
            # Remove author/editor info after parentheses
            if '(' in source_title:
                source_title = source_title[:source_title.index('(')].strip()
            
            # Check English book names
            for eng_book, sbl_id in BOOK_NAME_TO_SBL_ID.items():
                if eng_book.lower() in source_title.lower():
                    return (eng_book, sbl_id, "HIGH")
            
            # Check Korean book names
            for kr_book, en_book in KOREAN_TO_ENGLISH.items():
                if kr_book in source_title:
                    sbl_id = BOOK_NAME_TO_SBL_ID.get(en_book, "UNKNOWN")
                    return (en_book, sbl_id, "HIGH")
    
    # Look for book name pattern like "1 KINGS" or "2 Kings" in chunk header
    for line in content.split('\n')[:10]:
        if '## Chunk' in line:
            # Try to extract from markdown title
            title_part = line.split('## Chunk')[0].strip()
            if 'KINGS' in title_part.upper():
                if '1 KINGS' in title_part.upper():
                    return ("1 Kings", "1KI", "MEDIUM")
                return ("2 Kings", "2KI", "MEDIUM")
    
    return (None, "UNKNOWN", "LOW")


def repair_record(tsu: dict) -> dict:
    """
    Repair a single TSU record's book_id and tsu_id.
    
    Returns:
        (repaired_tsu, new_book_id, confidence, source_used)
    """
    source_file = tsu.get('source_file', '')
    content = tsu.get('content', '')
    
    # Primary: Parse from source_file
    book_name, sbl_id, conf = extract_book_name_from_source(source_file)
    source_used = "source_file"
    
    # Fallback: Parse from content header if primary failed
    if sbl_id == "UNKNOWN":
        book_name, sbl_id, conf = parse_book_id_from_content(content)
        source_used = "content_header"
    
    # Create new tsu_id (preserve original number)
    original_tsu_id = tsu.get('tsu_id', 'TSU-GEN-000001')
    num_part = original_tsu_id.split('-')[-1] if '-' in original_tsu_id else original_tsu_id
    
    new_book_id = sbl_id
    new_tsu_id = f"TSU-{new_book_id}-{num_part}"
    
    # Create repaired copy of record
    repaired = dict(tsu)
    repaired['tsu_id'] = new_tsu_id
    
    if 'verse_mapping' in repaired and isinstance(repaired['verse_mapping'], dict):
        repaired = dict(repaired)  # shallow copy outer dict
        repaired['verse_mapping'] = dict(tsu['verse_mapping'])
        repaired['verse_mapping']['book_id'] = new_book_id
    elif 'verse_mapping' not in repaired:
        repaired['verse_mapping'] = {'book_id': new_book_id}
    
    return (repaired, new_book_id, conf, source_used)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    mode = "dry-run"
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith('--mode='):
                mode = arg.split('=')[1]
            elif arg in ('execute', 'exec'):
                mode = 'execute'
    
    print("=" * 70)
    print("DBMA TSU Book Metadata Repair Script")
    print("=" * 70)
    print(f"Mode: {mode}")
    print(f"Input: {INPUT_PATH}")
    print()
    
    # Validate input
    if not os.path.exists(INPUT_PATH):
        print(f"ERROR: Input file not found: {INPUT_PATH}")
        sys.exit(1)
    
    # Verify backup exists
    if not os.path.exists(BACKUP_PATH):
        print(f"WARNING: Backup not found at {BACKUP_PATH}")
        confirm = input("Continue without backup verification? (y/N): ")
        if confirm.lower() != 'y':
            sys.exit(0)
    
    # Read TSU dataset
    records = []
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('$'):
                continue
            try:
                tsu = json.loads(line)
                records.append(tsu)
            except json.JSONDecodeError:
                pass
    
    total_records = len(records)
    print(f"Total TSU records: {total_records:,}")
    print()
    
    # ---- DRY-RUN / EXECUTE ----
    repair_stats = Counter()
    unknown_records = []
    samples_before = []
    samples_after = []
    
    if mode == "dry-run":
        output_path = DRY_RUN_OUTPUT
        print("DRY-RUN MODE — no files will be modified")
        print("=" * 70)
        
        for i, tsu in enumerate(records):
            original_book_id = tsu.get('verse_mapping', {}).get('book_id', 'GEN')
            original_tsu_id = tsu.get('tsu_id', 'TSU-GEN-000001')
            
            # Sample first 50 for before/after
            if i < 50:
                samples_before.append((original_book_id, original_tsu_id))
            
            repaired, new_book_id, conf, src_used = repair_record(tsu)
            repair_stats[new_book_id] += 1
            
            # Track unknowns
            if new_book_id == "UNKNOWN":
                unknown_records.append({
                    'index': i,
                    'original_tsu_id': original_tsu_id,
                    'source_file': tsu.get('source_file', ''),
                    'confidence': conf,
                })
            
            # Sample first 50 for after
            if i < 50:
                samples_after.append((new_book_id, repaired['tsu_id']))
    
    elif mode == "execute":
        output_path = OUTPUT_PATH
        print("EXECUTE MODE — writing repaired records to:", output_path)
        print("=" * 70)
        
        for i, tsu in enumerate(records):
            original_book_id = tsu.get('verse_mapping', {}).get('book_id', 'GEN')
            original_tsu_id = tsu.get('tsu_id', 'TSU-GEN-000001')
            
            repaired, new_book_id, conf, src_used = repair_record(tsu)
            repair_stats[new_book_id] += 1
            
            if new_book_id == "UNKNOWN":
                unknown_records.append({
                    'index': i,
                    'original_tsu_id': original_tsu_id,
                    'source_file': tsu.get('source_file', ''),
                    'confidence': conf,
                })
        
        # Write repaired file
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, tsu in enumerate(records):
                repaired, new_book_id, conf, src_used = repair_record(tsu)
                if i > 0:
                    f.write('\n')
                json.dump(repaired, f, ensure_ascii=False, indent=2)
        
        print(f"\nRepaired file written to: {output_path}")
    else:
        print(f"ERROR: Unknown mode: {mode}")
        sys.exit(1)
    
    # ---- DISPLAY RESULTS ----
    print("\n" + "=" * 70)
    print("REPAIR STATISTICS")
    print("=" * 70)
    
    for book_id, count in sorted(repair_stats.items(), key=lambda x: -x[1]):
        bar = '#' * (count // 100)
        print(f"  {book_id:>4}: {count:>6,} records  {bar}")
    
    total_repaired = sum(repair_stats.values())
    print(f"\nTotal repaired: {total_repaired:,}/{total_records:,}")
    
    if unknown_records:
        print(f"\nUNKNOWN RECORDS ({len(unknown_records)}):")
        for ur in unknown_records[:20]:
            print(f"  [{ur['index']}] {ur['original_tsu_id']} — src={ur.get('source_file', '')[:60]}...")
    else:
        print("\nUNKNOWN RECORDS: NONE (100% success)")
    
    if samples_before and samples_after:
        print("\n" + "=" * 70)
        print("BEFORE/AFTER SAMPLES (first 50 records)")
        print("=" * 70)
        print(f"\n{'Index':<6} {'Book ID Before':>14} {'TSU ID Before':>22} {'Book ID After':>14} {'TSU ID After':>22}")
        print("-" * 80)
        for i in range(min(50, len(samples_before))):
            ob, ot = samples_before[i]
            nb, nt = samples_after[i]
            print(f"  {i:<4} {ob:>14} {ot:>22} {nb:>14} {nt:>22}")
    
    if mode == "dry-run":
        print("\n" + "=" * 70)
        print("DRY-RUN COMPLETE — No files modified")
        print("=" * 70)
        print(f"\nTo execute: python scripts/repair_tsu_book_metadata.py --mode=execute")
    else:
        # Verify repaired file integrity
        sha256 = hashlib.sha256()
        with open(output_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        
        print("\n" + "=" * 70)
        print("EXECUTION COMPLETE")
        print("=" * 70)
        print(f"Output file: {output_path}")
        print(f"SHA256: {sha256.hexdigest()}")


if __name__ == '__main__':
    main()