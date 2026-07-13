# DBMA v1.1.0 — Installation Guide

---

## Overview

This guide walks you through installing DBMA (David Bang Ministry Archive) from scratch. After installation, you will be able to launch the interactive research UI and query the Korean theological corpus.

---

## Requirements

### Hardware

| Item | Minimum | Recommended |
|------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8 GB+ |
| Disk | 5 GB free | 10 GB+ |

### Software

- **Python**: 3.9+ (3.10 recommended)
- **OS**: macOS, Linux, Windows (WSL2 for Windows)
- **Git**: For cloning the repository
- **Stremili**t: Runs the interactive UI (`streamlit`)

---

## Installation Steps

### Step 1: Clone the Repository

```bash
git clone http://100.94.139.122:3000/David/DBMA.git
cd DBMA
```

Or from GitHub:

```bash
git clone https://github.com/nkbang/DBMA.git
cd DBMA
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate   # macOS/Linux
# or
.venv\Scripts\activate      # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
# Check Python version
python --version

# Check key packages
python -c "import streamlit; print('Streamlit:', streamlit.__version__)"
python -c "import chromadb; print('ChromaDB:', chromadb.__version__)"
python -c "import yaml; print('PyYAML: OK')"

# Verify core module loads
python -c "from core.config import DEFAULT_CHUNK_SIZE; print('Core config loaded:', DEFAULT_CHUNK_SIZE)"
```

All checks should pass without errors.

---

## Storage Structure

DBMA v1.1.0 uses the following storage layout:

```
DBMA/
├── data/
│   ├── RAW/                    # Input documents (place PDFs here)
│   └── 제련완성본/              # Processed output
├── chroma_db/                  # Vector database (auto-created on first run)
├── core/identity_registry.json # Document identity registry (auto-created)
├── logs/                       # Runtime logs
└── output/                     # Audit reports and benchmark outputs
```

### ChromaDB Auto-Initialization

DBMA uses ChromaDB for vector storage. On first run:
1. ChromaDB database is **automatically created** at `chroma_db/`
2. No manual database initialization is required
3. The database is initialized with the existing corpus from `data/제련완성본/`

---

## Configuration

The main configuration file is `config.yaml`. Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `chunk_size` | 512 | Document chunk token size |
| `chunk_overlap` | 50 | Overlap between chunks |
| `vector_db_path` | chroma_db/ | ChromaDB storage location |
| `raw_docs_dir` | data/RAW/ | Input document directory |
| `processed_docs_dir` | data/제련완성본/ | Processed corpus location |

---

## Troubleshooting

### "Module not found" errors

Activate your virtual environment:

```bash
source .venv/bin/activate
```

### ChromaDB initialization fails

Delete and recreate the database:

```bash
rm -rf chroma_db/
# Then restart DBMA — it will auto-recreate
```

### Corpus not loading

Ensure `data/제련완성본/` contains PDF documents. The directory should have files like:

```
data/제련완성본/
├── book1.pdf
├── book2.pdf
└── ...
```

---

## Next Steps

After installation, proceed to:

- [USER_GUIDE.md](USER_GUIDE.md) — How to use DBMA
- [OPERATIONS.md](OPERATIONS.md) — Backup and restore procedures