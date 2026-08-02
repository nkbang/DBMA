#!/usr/bin/env python3
"""One-time classification pass for NAE/corpus/raw/archive_org/history/early_baptist_collection.
Fetches archive.org metadata (creator/title/year) for each downloaded item and buckets it into
verified / duplicate / fragment / non_baptist / unverified based on simple heuristics, then
moves each item's directory into the matching subfolder.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time

BASE = "/Users/David/DBMA/NAE/corpus/raw/archive_org/history/early_baptist_collection"
LOG = "/Users/David/DBMA/scripts/_classify_early_baptist.log"
META_CACHE = "/Users/David/DBMA/scripts/_classify_early_baptist_meta.jsonl"

KNOWN_NON_BAPTIST_AUTHORS = [
    "john milton", "richard baxter", "daniel featley", "john bastwick",
    "symon patrick", "gabriel towerson", "thomas edwards", "john taylor",
    "john vicars", "josiah ricraft", "john white", "vincent gookin",
    "giles workman", "edmond bicknoll", "thomas roger", "r. alison",
    "john saltmarsh", "frederick spanhemius", "guy de bres", "john cotton",
    "arnold meschovius", "george philips",
]

def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def load_cache():
    cache = {}
    if os.path.exists(META_CACHE):
        with open(META_CACHE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                cache[d["id"]] = d
    return cache

def save_meta(cache_f, rec):
    cache_f.write(json.dumps(rec) + "\n")
    cache_f.flush()

def fetch_meta(item_id):
    r = sh(f'curl -s --max-time 12 "https://archive.org/metadata/{item_id}"')
    try:
        d = json.loads(r.stdout)
    except Exception:
        return {"id": item_id, "creator": None, "title": None, "year": None, "error": True}
    md = d.get("metadata", {})
    creator = md.get("creator")
    if isinstance(creator, list):
        creator = "; ".join(creator)
    return {
        "id": item_id,
        "creator": creator,
        "title": md.get("title"),
        "year": md.get("year") or md.get("date"),
        "error": False,
    }

def classify(item_id, meta, ocr_size, pdf_size):
    creator = (meta.get("creator") or "").lower()
    title = (meta.get("title") or "").lower()

    if ocr_size < 800 and pdf_size < 2_000_000:
        return "fragment"

    for name in KNOWN_NON_BAPTIST_AUTHORS:
        if name in creator:
            return "non_baptist"

    if meta.get("error"):
        return "unverified"

    if not meta.get("creator") and not meta.get("title"):
        return "unverified"

    return "verified"

def main():
    dirs = sorted(d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d)))
    cache = load_cache()

    log_f = open(LOG, "a")
    cache_f = open(META_CACHE, "a")

    title_seen = {}  # (title, creator, year) -> first item_id, for duplicate detection

    counts = {"verified": 0, "duplicate": 0, "fragment": 0, "non_baptist": 0, "unverified": 0}

    for i, item_id in enumerate(dirs, 1):
        src = os.path.join(BASE, item_id)
        if not os.path.isdir(src):
            continue

        ocr_path = os.path.join(src, "ocr.txt")
        pdf_path = os.path.join(src, "original.pdf")
        ocr_size = os.path.getsize(ocr_path) if os.path.exists(ocr_path) else 0
        pdf_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0

        if item_id in cache:
            meta = cache[item_id]
        else:
            meta = fetch_meta(item_id)
            save_meta(cache_f, meta)
            time.sleep(0.15)

        bucket = classify(item_id, meta, ocr_size, pdf_size)

        if bucket == "verified":
            key = (
                (meta.get("title") or "").strip().lower(),
                (meta.get("creator") or "").strip().lower(),
                str(meta.get("year") or ""),
            )
            if key[0] and key in title_seen:
                bucket = "duplicate"
            elif key[0]:
                title_seen[key] = item_id

        dest_dir = os.path.join(BASE, bucket)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, item_id)
        if not os.path.exists(dest):
            shutil.move(src, dest)

        counts[bucket] += 1
        log_f.write(f"[{i}/{len(dirs)}] {item_id} -> {bucket} (ocr={ocr_size} pdf={pdf_size} creator={meta.get('creator')})\n")
        log_f.flush()

    log_f.write(f"=== CLASSIFICATION COMPLETE: {counts} ===\n")
    log_f.close()
    cache_f.close()
    print(counts)

if __name__ == "__main__":
    main()
