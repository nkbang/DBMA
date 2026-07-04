# DBMA Sprint 1 — Environment Verification Guide
**Generated:** 2026-07-04  
**Objective:** Step-by-step commands to verify the runtime environment is correctly installed and functional

---

## Level 1: Python Version Verification

### Command
```bash
python --version
```

### Expected Output
```
Python 3.11.x
```
or
```
Python 3.12.x
```

### Acceptable Ranges
| Version | Status | Action if Not Met |
|---------|--------|------------------|
| 3.11.x | ✅ PASS | N/A — continue |
| 3.12.x | ✅ PASS | N/A — continue |
| 3.13+ | ❌ FAIL | Install Python 3.11 or 3.12 |
| < 3.9 | ❌ FAIL | Install Python 3.11 or 3.12 |

---

## Level 2: Core Package Verification

### Command
```bash
pip list 2>/dev/null | grep -iE "docling|torch|sentence-transformers|transformers|numpy|Pillow|PyMuPDF|streamlit|chromadb|qdrant-client|easyocr"
```

### Expected Output
```
docling                    2.99.0
docling-core               2.86.0
docling-ibm-models         3.13.3
docling-parse              7.5.0
docling-slim               2.109.0
streamlit                  1.28.0
chromadb                   0.5.23
easyocr                    1.7.0
numpy                      1.26.4
Pillow                     11.x.x
PyMuPDF                    1.24.14
qdrant-client              1.7.3
sentence-transformers      4.0.2
torch                      2.2.2
transformers               4.46.2
```

### Critical Version Checks

| Package | Required Version | Command to Verify | Acceptable Range |
|---------|-----------------|-------------------|-----------------|
| torch | `==2.2.2` | `pip show torch \| grep Version` | 2.2.x only |
| sentence-transformers | `==4.0.2` | `pip show sentence-transformers \| grep Version` | 4.0.x only |
| docling | `==2.99.0` | `pip show docling \| grep Version` | 2.99.0 only |
| numpy | `==1.26.4` | `pip show numpy \| grep Version` | 1.26.x only |
| PyMuPDF | `==1.24.14` | `pip show PyMuPDF \| grep Version` | 1.24.x only |
| streamlit | `==1.28.0` | `pip show streamlit \| grep Version` | 1.28.x only |

---

## Level 3: Import Verification (Core Pipeline)

### Command
```bash
python -c "
# Core config check
from core.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
print(f'[OK] core.config: chunk={DEFAULT_CHUNK_SIZE}, overlap={DEFAULT_CHUNK_OVERLAP}')

# Chunking optimizer check
from core.chunking_optimizer import ChunkingOptimizer
print('[OK] core.chunking_optimizer imported')

# Processing pipeline check
from core.processing import build_converter, build_splitter
print('[OK] core.processing imports OK')

# Docling check
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.backend.pypdfium2_backend import PyPdfium2DocumentBackend
print('[OK] docling components imported')

# Sentence transformers check
import sentence_transformers
print(f'[OK] sentence-transformers {sentence_transformers.__version__}')

# PyTorch check
import torch
print(f'[OK] torch version {torch.__version__}, CUDA available: {torch.cuda.is_available()}')

# NumPy check
import numpy as np
print(f'[OK] numpy {np.__version__}')

print()
print('=== ALL CORE IMPORTS SUCCESSFUL ===')
"
```

### Expected Output
```
[OK] core.config: chunk=1200, overlap=120
[OK] core.chunking_optimizer imported
[OK] core.processing imports OK
[OK] docling components imported
[OK] sentence-transformers 4.0.2
[OK] torch version 2.2.2 (cuda: True or cpu), CUDA available: False/True
[OK] numpy 1.26.4

=== ALL CORE IMPORTS SUCCESSFUL ===
```

### Failure Recovery

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'docling'` | docling not installed | `pip install docling==2.99.0` |
| `ImportError: Could not import sentence_transformers` | st not installed or version mismatch | `pip install sentence-transformers==4.0.2` |
| `ValueError: Due to a serious vulnerability issue in torch.load...` | torch >= 2.6 installed | `pip uninstall torch && pip install torch==2.2.2` |
| `_ARRAY_API not found` | numpy version mismatch | `pip install numpy==1.26.4` |
| `ModuleNotFoundError: No module named 'core'` | Not in project root directory | `cd /path/to/DBMA && python -c "..."` |

---

## Level 4: External Tool Verification

### Tesseract OCR

#### Command
```bash
tesseract --version
```

#### Expected Output (macOS)
```
tesseract 5.x.x with leptonica
```

#### Expected Output (Ubuntu)
```
tesseract 4.x.x or 5.x.x
```

#### If Not Found
```bash
# macOS
brew install tesseract

# Ubuntu
sudo apt-get install -y tesseract-ocr
```

### Poppler Utilities (pdftoppm)

#### Command
```bash
pdftoppm -v 2>&1 || pdfinfo -v 2>&1
```

#### Expected Output
```
poppler x.x.x
```

#### If Not Found
```bash
# macOS
brew install poppler

# Ubuntu
sudo apt-get install -y poppler-utils
```

---

## Level 5: Complete Pipeline Smoke Test

### Single-File Ingestion Test

This test runs the full pipeline on a single file to verify all components work together.

#### Command (with test file)
```bash
cd /path/to/DBMA

# Use a small file for quick testing
python scripts/benchmark_pipeline.py \
  --input "data/raw/<your-smallest-file.pdf or .txt>" \
  --output output/smoke-test \
  --chunk-size 1200 \
  --chunk-overlap 120 2>&1 | head -30
```

#### Expected Output (success)
```
[SPRINT1] Processing: <filename>
[EXTRACTORS] PyMuPDF loaded
[CHUNKING] Using config defaults (chunk=1200, overlap=120)
[CHUNKING] Saved canonical MD output: output/smoke-test/<stem>.md
[CHUNKING] Skipped deprecated outputs (_chunks.txt, _chunks_meta.json)
[SPRINT1] Success rate: 100.0% (1/1)
```

#### Expected Output (failure examples)

| Error Message | Cause | Fix |
|--------------|-------|-----|
| `Processing skipped (already done)` | Batch state blocks reprocessing | `rm output/smoke-test/.batch_state.json` and retry |
| `docling: not found` | docling not installed | See Level 3 |
| `tesseract: not found` | Tesseract binary missing | See Level 4 |
| `pdftoppm: not found` | Poppler missing | See Level 4 |
| `No input files found.` | File path incorrect or doesn't exist | Verify file exists with `ls data/raw/` |

---

## Level 6: Sprint 2 Services (Optional)

### Qdrant Check

#### Command
```bash
curl -s http://localhost:6333/ 2>/dev/null || echo "Qdrant NOT running"
```

#### Expected Output
```json
{"status":"ok"}
```

#### If Not Running
```bash
docker compose up -d qdrant
sleep 5
curl -s http://localhost:6333/
```

---

## Verification Checklist (Quick Reference)

| # | Check | Command | Pass Condition |
|---|-------|---------|---------------|
| 1 | Python version | `python --version` | 3.11.x or 3.12.x |
| 2 | Critical packages | `pip list \| grep -E "docling|torch"` | Versions match table above |
| 3 | Core imports | Import test (Level 3) | All `[OK]` messages shown |
| 4 | Tesseract | `tesseract --version` | Version 4.x or 5.x |
| 5 | Poppler | `pdftoppm -v` | poppler x.x.x |
| 6 | Pipeline smoke test | benchmark_pipeline.py (Level 5) | `Success rate: 100%` |
| 7 | Qdrant (optional) | `curl localhost:6333/` | `{"status":"ok"}` |

---

## Troubleshooting Reference

### All Imports Fail Immediately

```bash
# Likely cause: virtual environment not activated
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Verify active Python is from venv
which python  # Should point to .venv/bin/python
python --version  # Should match expected version
```

### docling Import Works But Processing Fails at PDF

```bash
# Check poppler and tesseract are found
python -c "
from pdf2image import convert_from_path
import tempfile, os
with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
    pass
print('poppler check: pdftoppm should be in PATH')
"

pdftoppm -v 2>&1 || echo "poppler missing"
tesseract --version 2>&1 || echo "tesseract missing"
```

### torch Import Works But Model Loading Fails

```bash
# Check torch version is exactly 2.2.2
python -c "import torch; assert torch.__version__ == '2.2.2', f'Got {torch.__version__}'"

# If wrong version, reinstall:
pip uninstall -y torch torchvision torchaudio
pip install torch==2.2.2
```

---

*End of VERIFY_ENVIRONMENT.md*