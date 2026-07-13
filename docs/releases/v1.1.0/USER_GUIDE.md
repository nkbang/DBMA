# DBMA v1.1.0 — User Guide

---

## Quick Start

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Start DBMA
streamlit run ui/app.py

# 3. Open UI
# Navigate to http://localhost:8501 in your browser
```

---

## User Workflow

```
Start DBMA                    → streamlit run ui/app.py
↓
Select a page                  → Dashboard, Library, Processing, Research, Monitor
↓
Search for information         → Research page text input
↓
Review results                 → Click result for full context and metadata
↓
Export / copy results          → Use UI controls to export findings
```

---

## Page Descriptions

### Dashboard
- System overview with corpus statistics
- Processing metrics and health indicators
- Quick access to all major functions

### Library
- Document inventory listing
- Search raw documents by metadata
- View document counts, processing status

### Processing
- Document ingestion controls
- Corpus management tools
- Batch processing for new documents

### Research (Main Interface)
- Primary query input interface
- Hybrid retrieval (BM25 + Vector) results
- Ranking with theological scoring
- Full text snippets and source metadata

### Monitor
- System health monitoring
- Performance metrics visualization
- Error log viewing

---

## Searching DBMA

### Basic Query
1. Navigate to the **Research** page
2. Enter your query in the text input box
3. Click **Search** or press Enter
4. Review ranked results below

### Query Examples

| Query Type | Example |
|-----------|---------|
| Book reference | "예레미야 서론" |
| Theological concept | "구약 하나님의 주권" |
| Theme search | "종말론 신학적 해석" |
| Korean keyword | "선지와 메시아" |

### Search Behavior

- **BM25** handles exact keyword matching
- **Vector retrieval** captures semantic similarity
- **Hybrid ranking** combines both signals
- **Theological scoring** boosts relevant domain terms

---

## Document Processing

### Ingesting New Documents

1. Place PDF files in `data/RAW/`
2. Navigate to **Processing** page
3. Click **Process RAW Documents**
4. Monitor progress in the output panel
5. Processed documents appear in `data/제련완성본/`

### Processing Pipeline

```
data/RAW/*.pdf
    ↓
Extraction (PDF → text)
    ↓
Chunking (512-token chunks)
    ↓
Metadata extraction
    ↓
Embedding (vector generation)
    ↓
data/제련완성본/ + ChromaDB index
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Module not found" | Activate venv: `source .venv/bin/activate` |
| Empty search results | Ensure corpus exists in data/제련완성본/ |
| UI won't load | Check port 8501 is free |
| Slow processing | Increase CPU cores or reduce chunk_overlap |

---

## Keyboard Shortcuts (Streamlit)

| Shortcut | Action |
|----------|--------|
| `Shift + Enter` | Run cell/submit query |
| `Esc` | Command palette |
| `/` | Search UI |

---

*DBMA v1.1.0 is designed for research workflows. All searches are non-destructive and read-only.*