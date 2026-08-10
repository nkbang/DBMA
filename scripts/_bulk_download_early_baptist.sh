#!/bin/bash
# Bulk downloader for archive.org "per_early-baptist_" collection (730 items)
# Downloads ocr.txt + original.pdf into NAE/corpus/raw/archive_org/history/early_baptist_collection/{id}/
set -uo pipefail

BASE_DIR="/Users/David/DBMA/NAE/corpus/raw/archive_org/history/early_baptist_collection"
LOG="/Users/David/DBMA/scripts/_bulk_download_early_baptist.log"
IDS_FILE="/tmp/all_early_baptist_ids.txt"
DONE_FILE="/Users/David/DBMA/scripts/_bulk_download_early_baptist.done"

touch "$DONE_FILE"
mkdir -p "$BASE_DIR"

total=$(wc -l < "$IDS_FILE")
count=0

while IFS= read -r id; do
  count=$((count+1))
  [ -z "$id" ] && continue
  if grep -qxF "$id" "$DONE_FILE"; then
    continue
  fi

  meta=$(curl -s --max-time 15 "https://archive.org/metadata/${id}")
  restricted=$(echo "$meta" | ~/envs/dbma311/bin/python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    print(d.get('metadata',{}).get('access-restricted-item','false'))
except Exception:
    print('error')
" 2>/dev/null)

  if [ "$restricted" = "true" ] || [ "$restricted" = "error" ]; then
    echo "[$count/$total] SKIP $id (restricted=$restricted)" >> "$LOG"
    echo "$id" >> "$DONE_FILE"
    continue
  fi

  dir="${BASE_DIR}/${id}"
  mkdir -p "$dir"
  curl -sL --max-time 30 "https://archive.org/download/${id}/${id}_djvu.txt" -o "${dir}/ocr.txt" 2>/dev/null
  curl -sL --max-time 45 "https://archive.org/download/${id}/${id}.pdf" -o "${dir}/original.pdf" 2>/dev/null

  ocrsize=$(wc -c < "${dir}/ocr.txt" 2>/dev/null || echo 0)
  pdfsize=$(wc -c < "${dir}/original.pdf" 2>/dev/null || echo 0)

  if [ "$ocrsize" -lt 50 ] && [ "$pdfsize" -lt 500 ]; then
    echo "[$count/$total] EMPTY $id (ocr=$ocrsize pdf=$pdfsize)" >> "$LOG"
    rm -rf "$dir"
  else
    echo "[$count/$total] OK $id (ocr=$ocrsize pdf=$pdfsize)" >> "$LOG"
  fi
  echo "$id" >> "$DONE_FILE"
done < "$IDS_FILE"

echo "=== BULK DOWNLOAD COMPLETE ===" >> "$LOG"
