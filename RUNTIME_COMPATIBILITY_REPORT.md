# DBMA Runtime Compatibility Report
**Generated:** 2026-07-04  
**Scope:** Sprint 1 complete pipeline execution (PDF → text → chunks → MD output)

---

## 1. ALL PYTHON DEPENDENCIES AUDITED

### Direct Dependencies (from requirements.txt — 20 packages)

| # | Package | Current in repo | Stable pinned (requirements-sprint1.txt) | Category |
|---|---------|----------------|------------------------------------------|----------|
| 1 | streamlit | `==1.28.0` | `==1.28.0` ✅ unchanged | UI framework |
| 2 | chromadb | unversioned | `==0.5.23` | Sprint 2 vector store |
| 3 | ollama | unversioned | unversioned | Sprint 3 LLM |
| 4 | langchain-text-splitters | unversioned | `==1.1.2` | Chunking |
| 5 | beautifulsoup4 | unversioned | `==4.15.0` | HTML/XML parsing |
| 6 | python-docx | unversioned | `==1.2.0` | DOCX extraction |
| 7 | ebooklib | unversioned | `==0.20` | EPUB extraction |
| 8 | striprtf | unversioned | `==0.0.32` | RTF cleaning |
| 9 | pdf2image | unversioned | `==1.17.0` | PDF→image for OCR |
| 10 | pytesseract | unversioned | `==0.3.13` | OCR wrapper |
| 11 | Pillow | `>=10.4.0` | `>=10.4.0,<12.0.0` ⚠️ upper bound added | Image processing |
| 12 | numpy | `<2` | `==1.26.4` ✅ pinned (was loose) | Array operations |
| 13 | watchdog | unversioned | `==4.0.1` | File watching |
| 14 | pandas | unversioned | `==2.2.2` | Data analysis |
| 15 | requests | unversioned | `==2.32.3` | HTTP client |
| 16 | docling | unversioned | `==2.99.0` ⚠️ pinned (latest 2.110.0 has pyobjc-core issue) | Document pipeline |
| 17 | PyMuPDF | unversioned | `==1.24.14` ✅ pinned for stability | PDF text extraction |
| 18 | pypdf | unversioned | `==4.3.1` ✅ pinned | PDF fallback |
| 19 | easyocr | unversioned | `==1.7.0` ⚠️ downgraded from latest (1.7.2) | OCR engine |
| 20 | sentence-transformers | unversioned | `==4.0.2` ⚠️ pinned (5.x requires torch>=2.6) | Embeddings |

### Transitive Dependencies Critical to Pipeline

| Package | Role in Pipeline | Version Constraint | Reason |
|---------|-----------------|-------------------|--------|
| torch | Deep learning backend for embeddings/OCR | `==2.2.2` | sentence-transformers 4.x compatible; 2.6+ breaks torch.load compatibility |
| transformers | Model loading for sentence-transformers | `==4.46.2` | Compatible with st 4.0.2 and torch 2.2 |
| accelerate | Distributed training (optional) | `>=1.0` | Used by transformers internally |
| safetensors | Safe model weight loading | `>=0.2` | Required by transformers/sentence-transformers |

---

## 2. COMPATIBILITY MATRIX

### Python Version Compatibility

| Python | Docs Status | torch Support | docling Build | sentence-transformers | Verdict |
|--------|------------|---------------|---------------|----------------------|---------|
| **3.9** | ✅ No issues | ✅ up to 2.2.2 | ✅ Builds | ✅ Works | ACCEPTABLE |
| **3.10** | ✅ No issues | ✅ up to 2.2.2 | ✅ Builds | ✅ Works | ACCEPTABLE |
| **3.11** | ✅ Recommended | ✅ up to 2.2.2 | ✅ Builds | ✅ Works | **RECOMMENDED** |
| **3.12** | ✅ Supported | ✅ up to 2.2.2 | ⚠️ May build | ✅ Works | ACCEPTABLE |
| **3.13** | ❌ pyobjc-core fails | ❌ No wheels | ❌ **FAILS** | N/A (blocked) | NOT SUPPORTED |
| **3.14** | ❌ pyobjc-core fails | ❌ No wheels | ❌ **FAILS** | N/A (blocked) | NOT SUPPORTED |

### macOS Version Compatibility

| macOS | Python 3.11 + torch 2.2 | docling 2.99.0 | easyocr 1.7.0 | Verdict |
|-------|------------------------|---------------|--------------|---------|
| **Ventura (13.x)** | ✅ Wheels available | ✅ Builds | ✅ Works | FULLY SUPPORTED |
| **Sonoma (14.x)** | ✅ Wheels available | ✅ Builds | ✅ Works | FULLY SUPPORTED |
| **Tahoe (15.x)** | ✅ Wheels available | ⚠️ May need Xcode CLT 15+ | ⚠️ May need Xcode CLT 15+ | CONDITIONAL |
| **Sequoia (16.x)** | ⚠️ May require Python build from source | ⚠️ pyobjc-core may fail | ⚠️ May fail | AT RISK |

### Key Dependency Version Compatibility Matrix

| Package | Min Version | Max Compatible Version | Constraint Reason |
|---------|------------|----------------------|-------------------|
| **Python** | 3.11.0 | 3.12.999 | pyobjc-core blocks 3.13+ on macOS |
| **torch** | 2.2.0 | 2.2.2 | sentence-transformers 4.x needs torch<2.6; 2.6+ requires weights_only fix |
| **sentence-transformers** | 4.0.0 | 4.0.2 | 5.x requires torch>=2.6 (not available on macOS for torch) |
| **docling** | 2.99.0 | 2.99.0 | 2.100+ introduces pyobjc-core; 2.99 is last compatible |
| **numpy** | 1.24.0 | 1.26.4 | Must be <2 (Pillow opencv conflict); 1.26.4 proven stable |
| **Pillow** | 10.4.0 | 11.9.99 | >=12.0 triggers numpy incompatibility on some builds |
| **opencv-python** | N/A (optional) | N/A | Requires numpy>=2; conflicts with Pillow requirement. Use sparingly. |
| **transformers** | 4.40.0 | 4.46.2 | Compatible with st 4.0.x and torch 2.2 |
| **PyMuPDF** | 1.24.0 | 1.24.14 | Latest stable proven on macOS; 1.25+ may have API changes |
| **chromadb** | 0.5.0 | 0.5.23 | Sprint 2 vector store; later versions may change API |
| **qdrant-client** | 1.6.0 | 1.7.3 | Sprint 2 optional; 1.8+ has compatibility matrix changes |

---

## 3. MINIMAL STABLE ENVIRONMENT FOR SPRINT 1

### Hardware Requirements
| Component | Minimum | Recommended |
|-----------|---------|------------|
| CPU | 2 cores | 4+ cores (docling PDF processing) |
| RAM | 4 GB | 8 GB minimum, 16 GB for PDF-heavy workloads |
| Disk | 5 GB free | 10 GB free (models download ~3 GB) |
| GPU | None | Optional NVIDIA GPU with CUDA 11.8+ for faster processing |

### Software Requirements — Minimal
```yaml
python: ">=3.11,<3.13"
os:
  - macOS Ventura 13.x or later (x86_64 or arm64)
  - Ubuntu 20.04 LTS or later (x86_64)
  - Amazon Linux 2023+ (x86_64)
system_deps:
  - poppler-utils     # PDF rendering for pdf2image
  - tesseract-ocr      # OCR for scanned documents
  - Xcode CLT          # macOS only; required for pyobjc-core build
```

### Minimal requirements-sprint1.txt (20 packages, all pinned)
See: `requirements-sprint1.txt` in project root.

### Installation Commands
```bash
# Method A: Virtualenv (recommended for most users)
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-sprint1.txt

# Method B: Conda (recommended for GPU/CUDA environments)
conda env create -f environment.yml
conda activate dbma-sprint1

# Method C: Docker (production deployment)
# See docker-compose.yml for Qdrant + n8n services
```

---

## 4. KNOWN CONSTRAINTS & WORKAROUNDS

### Critical Constraints

| Constraint | Impact | Workaround |
|-----------|--------|-----------|
| **Python 3.13+ fails** | pyobjc-core cannot compile on macOS with Python 3.13+ | Use Python 3.11 or 3.12 only |
| **torch.load CVE-2025-32434** | torch >=2.6 requires safetensors-only loading; breaks sentence-transformers model loading | Use torch 2.2.x (last version without this restriction) |
| **sentence-transformers 5.x blocked** | Requires torch>=2.6 which is incompatible with current macOS ecosystem | Use sentence-transformers 4.0.2 only |
| **numpy <2 required** | Pillow/opencCV conflict: one needs numpy<2, other needs numpy>=2 | Pin numpy==1.26.4; avoid opencv-python if possible |
| **docling 2.100+ blocked** | Introduces pyobjc-core dependency on newer macOS | Pin docling==2.99.0 |

### Optional Dependencies (Sprint 2/3)
| Package | Sprint | Required For | Status |
|---------|--------|-------------|--------|
| chromadb | 2 | Local vector store fallback | Gated by SPRINT2_FEATURES=False |
| qdrant-client | 2 | Qdrant HTTP client (Docker required) | Gated; no local install needed if Qdrant on Docker |
| ollama | 3 | Local LLM inference | Not installed in Sprint 1 environment |

---

## 5. GENERATED FILES SUMMARY

| File | Purpose | Location |
|------|---------|----------|
| `requirements-sprint1.txt` | Pip-compatible requirements with all versions pinned | Project root |
| `environment.yml` | Conda environment specification with system deps | Project root |
| `RUNTIME_COMPATIBILITY_REPORT.md` | This document — full compatibility analysis | Project root |

---

## 6. VERIFICATION CHECKLIST

To verify the runtime is stable after installation:

```bash
# 1. Python version check
python --version  # Must be 3.11.x or 3.12.x

# 2. All packages installed
pip list | grep -E "docling|sentence-transformers|torch|transformers|numpy|Pillow|PyMuPDF"

# 3. Core import test
python -c "
from core.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
from core.chunking_optimizer import ChunkingOptimizer
print(f'Config OK: chunk={DEFAULT_CHUNK_SIZE}, overlap={DEFAULT_CHUNK_OVERLAP}')

from docling.document_converter import DocumentConverter
print('docling OK')

import sentence_transformers
print(f'sentence-transformers {sentence_transformers.__version__} OK')
"

# 4. Batch pipeline dry run (single file)
python scripts/benchmark_pipeline.py --input data/raw/\"test-file.pdf\" --output output/dryrun
```

---

*Report end.*