# Download Command Templates

**Directive:** HQ-C1-DIRECTIVE-NAE-DOWNLOAD-SPEC-007 §9  
**Mode:** Read-only specification (commands NOT to be executed)  
**Date:** 2026-08-01  

---

## 1. Placeholder Definitions

| Placeholder | Meaning |
|---|---|
| `<REPOSITORY_BASE_URL>` | Repository base URL (e.g., `https://archive.org/download`, `https://name.umdl.umich.edu`) |
| `<STABLE_IDENTIFIER>` | Item-level stable identifier |
| `<SELECTED_DERIVATIVE_FILENAME>` | Target derivative filename |
| `<OUTPUT_QUARANTINE_PATH>` | Local quarantine directory path (e.g., `NAE/corpus/quarantine/<source_id>/`) |
| `<IA_ITEM_ID>` | Internet Archive item ID |
| `<GB_BOOK_ID>` | Google Books book ID |
| `<CCEL_PATH>` | CCEL content path |

---

## 2. PBC1765 Command Templates

### 2.1 Metadata Request

```bash
# Internet Archive item metadata (JSON)
curl -s -I "<REPOSITORY_BASE_URL>/<STABLE_IDENTIFIER>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

### 2.2 Derivative Inventory

```bash
# List all derivatives available for the item
curl -s "https://archive.org/metadata/<STABLE_IDENTIFIER>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)" \
  | jq '.data.files[].name'
```

### 2.3 Selected Artifact Download

```bash
# Download preferred derivative (Scan PDF with OCR)
curl -L -o "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>" \
  "https://archive.org/download/<STABLE_IDENTIFIER>/<SELECTED_DERIVATIVE_FILENAME>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

### 2.4 HTTP Header Capture

```bash
# Capture full HTTP headers for transport validation
curl -s -D - -o /dev/null \
  "https://archive.org/download/<STABLE_IDENTIFIER>/<SELECTED_DERIVATIVE_FILENAME>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

### 2.5 SHA256 Checksum

```bash
# Compute SHA256 of downloaded file
sha256sum "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>"
```

### 2.6 MIME Type Inspection

```bash
# Inspect MIME type of downloaded file
file --mime-type "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>"
```

### 2.7 File Size Inspection

```bash
# Inspect file size in bytes
stat -f%z "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>"  # macOS
# OR
wc -c "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>"      # Linux
```

### 2.8 Title Marker Inspection (PDF)

```bash
# Extract first page text from PDF for title marker verification
pdftotext -f 1 -l 1 "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>" - \
  | grep -i "Plain and Short Account\|Orthodox Baptist Confession"
```

### 2.9 Error Template Inspection (PDF)

```bash
# Check for Internet Archive error patterns in PDF content
pdftotext "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>" - \
  | grep -i "Internet Archive.*error\|corrupted file\|file not found"
```

---

## 3. TH1612 Command Templates

### 3.1 Internet Archive Derivative

#### Metadata Request

```bash
curl -s "https://archive.org/metadata/<IA_ITEM_ID>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)" \
  | jq '.data.metadata'
```

#### Derivative Inventory

```bash
curl -s "https://archive.org/metadata/<IA_ITEM_ID>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)" \
  | jq '.data.files[] | select(.name | endswith(".pdf")) | .name'
```

#### Download

```bash
curl -L -o "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>" \
  "https://archive.org/download/<IA_ITEM_ID>/<SELECTED_DERIVATIVE_FILENAME>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### Header Capture

```bash
curl -s -D - -o /dev/null \
  "https://archive.org/download/<IA_ITEM_ID>/<SELECTED_DERIVATIVE_FILENAME>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### SHA256

```bash
sha256sum "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>"
```

#### MIME Type

```bash
file --mime-type "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>"
```

#### File Size

```bash
stat -f%z "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>"
```

#### Title Marker Inspection

```bash
pdftotext -f 1 -l 1 "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>" - \
  | grep -i "Short Declaration\|Mystery of Iniquity"
```

#### Author Marker Inspection

```bash
pdftotext "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>" - \
  | grep -i "Helwys\|T\.H\."
```

### 3.2 University of Michigan EEBO2

#### Metadata/Access Request

```bash
curl -s -I "https://name.umdl.umich.edu/A02915.0001.001" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### Derivative Access (TCP XML)

```bash
curl -s "https://name.umdl.umich.edu/cgi/t/text/text-idx?c=eebo;idno=A02915.0001.001" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)" \
  -o "<OUTPUT_QUARANTINE_PATH>/A02915.0001.001.xml"
```

#### Header Capture

```bash
curl -s -D - -o /dev/null \
  "https://name.umdl.umich.edu/cgi/t/text/text-idx?c=eebo;idno=A02915.0001.001" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### MIME Type

```bash
file --mime-type "<OUTPUT_QUARANTINE_PATH>/A02915.0001.001.xml"
```

#### Title Marker Inspection (XML)

```bash
grep -i "Short Declaration" "<OUTPUT_QUARANTINE_PATH>/A02915.0001.001.xml"
```

#### Author Marker Inspection (XML)

```bash
grep -i "Helwys\|Thomas" "<OUTPUT_QUARANTINE_PATH>/A02915.0001.001.xml"
```

### 3.3 CCEL HTML Fallback

#### Access Request

```bash
curl -s -I "https://www.ccel.org/ccel/helwys/declaration.html" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### Download

```bash
curl -s -o "<OUTPUT_QUARANTINE_PATH>/helwys_declaration.html" \
  "https://www.ccel.org/ccel/helwys/declaration.html" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### Header Capture

```bash
curl -s -D - -o /dev/null \
  "https://www.ccel.org/ccel/helwys/declaration.html" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### MIME Type

```bash
file --mime-type "<OUTPUT_QUARANTINE_PATH>/helwys_declaration.html"
```

#### Title Marker Inspection

```bash
grep -i "Short Declaration\|Mystery of Iniquity" "<OUTPUT_QUARANTINE_PATH>/helwys_declaration.html"
```

---

## 4. AF1785 Command Templates

### 4.1 Internet Archive Derivative

#### Metadata Request

```bash
curl -s "https://archive.org/metadata/<IA_ITEM_ID>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)" \
  | jq '.data.metadata'
```

#### Derivative Inventory

```bash
curl -s "https://archive.org/metadata/<IA_ITEM_ID>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)" \
  | jq '.data.files[] | select(.name | endswith(".pdf")) | .name'
```

#### Download

```bash
curl -L -o "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>" \
  "https://archive.org/download/<IA_ITEM_ID>/<SELECTED_DERIVATIVE_FILENAME>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### Header Capture

```bash
curl -s -D - -o /dev/null \
  "https://archive.org/download/<IA_ITEM_ID>/<SELECTED_DERIVATIVE_FILENAME>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### SHA256

```bash
sha256sum "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>"
```

#### MIME Type

```bash
file --mime-type "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>"
```

#### File Size

```bash
stat -f%z "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>"
```

#### Title Marker Inspection (correct work)

```bash
pdftotext -f 1 -l 1 "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>" - \
  | grep -i "Gospel Worthy\|Acceptation"
```

#### Wrong Work Check

```bash
pdftotext "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>" - \
  | grep -i "Gospel Defended"
```

#### Author Marker Inspection

```bash
pdftotext "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>" - \
  | grep -i "Fuller\|Andrew Fuller"
```

### 4.2 Google Books Derivative

#### Access Request

```bash
curl -s -I "https://books.google.com/books?id=<GB_BOOK_ID>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### Download (if Full View available)

```bash
curl -L -o "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>" \
  "https://books.google.com/books?id=<GB_BOOK_ID>&printsec=frontcover" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### Header Capture

```bash
curl -s -D - -o /dev/null \
  "https://books.google.com/books?id=<GB_BOOK_ID>&printsec=frontcover" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### MIME Type

```bash
file --mime-type "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>"
```

#### Title Marker Inspection

```bash
pdftotext -f 1 -l 1 "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>" - \
  | grep -i "Gospel Worthy\|Acceptation"
```

### 4.3 CCEL HTML Fallback

#### Access Request

```bash
curl -s -I "https://www.ccel.org/ccel/fuller/<CCEL_PATH>.html" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### Download

```bash
curl -s -o "<OUTPUT_QUARANTINE_PATH>/fuller_gospel_worthy.html" \
  "https://www.ccel.org/ccel/fuller/<CCEL_PATH>.html" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### Header Capture

```bash
curl -s -D - -o /dev/null \
  "https://www.ccel.org/ccel/fuller/<CCEL_PATH>.html" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)"
```

#### MIME Type

```bash
file --mime-type "<OUTPUT_QUARANTINE_PATH>/fuller_gospel_worthy.html"
```

#### Title Marker Inspection

```bash
grep -i "Gospel Worthy\|Acceptation" "<OUTPUT_QUARANTINE_PATH>/fuller_gospel_worthy.html"
```

---

## 5. Universal Post-Download Validation Commands

### 5.1 Error Page Detection (all sources)

```bash
# Check for Internet Archive error patterns
grep -i "Internet Archive.*error\|error page\|file corrupted\|not found" \
  "<OUTPUT_QUARANTINE_PATH>/<SELECTED_DERIVATIVE_FILENAME>" && echo "ERROR PAGE DETECTED"
```

### 5.2 Redirect Chain Inspection

```bash
# Show full redirect chain
curl -s -L -I \
  "https://archive.org/download/<STABLE_IDENTIFIER>/<SELECTED_DERIVATIVE_FILENAME>" \
  -H "User-Agent: NAE-Corpus-Collector/1.0 (research@nae.org)" \
  | grep -i "HTTP/.* [0-9][0-9][0-9]\|Location:"
```

### 5.3 Quarantine Decision Log Entry Template

```json
{
  "timestamp": "<ISO8601_TIMESTAMP>",
  "source_id": "<SOURCE_ID>",
  "action": "ACCEPT" | "REJECT",
  "quarantine_class": "QUARANTINE/VERIFIED/<source_id>" | "QUARANTINE/REJECT/<reason>",
  "rule_violated": null | "<RULE_ID>",
  "actual_content_type": "<MIME_TYPE>",
  "file_size_bytes": <FILE_SIZE>,
  "sha256": "<SHA256_HASH>",
  "notes": "<ADDITIONAL_NOTES>"
}