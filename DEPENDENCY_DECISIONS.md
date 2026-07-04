# DBMA Dependency Decisions
**Generated:** 2026-07-04  
**Scope:** Sprint 1 data pipeline runtime environment  
**Reference:** `requirements-sprint1.txt`, `RUNTIME_COMPATIBILITY_REPORT.md`

---

## Pinned Package Justifications

### Core Framework

| Package | Pinned Version | Why This Version | Incompatibilities |
|---------|---------------|-----------------|------------------|
| **streamlit** | `==1.28.0` | Original requirements.txt specified this exact version. It is stable and provides the UI components used by `dbma.py`. No need to upgrade — no known bugs in this version for our use case. | Later versions (1.29+) may have changed API for widgets. Downgrading from newer streamlit will not work without code changes. |
| **chromadb** | `==0.5.23` | Last stable version before major API shifts in 0.6+. Provides reliable vector store functionality for Sprint 2. Later versions (1.x) have changed embedding and collection APIs. | Version 1.x+ has breaking API changes. Do not upgrade beyond 0.5.x without code review. |
| **ollama** | unversioned | No pinning — latest version accepted. Ollama is a daemon/service; the Python package is a thin client wrapper. It does not affect Sprint 1 data pipeline. | None known. The Ollama binary itself should be kept up-to-date for security fixes. |

### Document Processing (Sprint 1 Core)

| Package | Pinned Version | Why This Version | Incompatibilities |
|---------|---------------|-----------------|------------------|
| **docling** | `==2.99.0` | **CRITICAL PIN.** Latest compatible version before pyobjc-core dependency was introduced in 2.100+. pyobjc-core fails to compile on macOS with Python 3.13+ (Xcode CLT compatibility issue). Version 2.99.0 works on macOS Ventura+ with Python 3.11/3.12. | - `==2.100.0+`: Requires pyobjc-core, fails to build on macOS + Python 3.13+
- `==1.x`: Incompatible embedding model API changes

**This is the most critical pin in the entire dependency tree.** Do not upgrade without verifying pyobjc-core builds on your system. |
| **PyMuPDF** | `==1.24.14` | Proven stable version with reliable PDF text extraction, table detection, and annotation support used by `core/extractors.py`. Version 1.25+ introduced API changes that affect extractors. | - `>=1.25.0`: New API may break `core/extractors.py` PDF fallback path
- `<1.24.0`: Missing table extraction features needed by pipeline |
| **pypdf** | `==4.3.1` | Stable PDF text extraction fallback used in `core/extractors.py`. Version 4.3.x is the last before significant API changes in 5.x (e.g., changed reader/writer interfaces). | - `>=5.0.0`: Breaking reader API changes
- `<4.0.0`: Missing hydration features used by extractors |
| **Pillow** | `>=10.4.0,<12.0.0` | Pillow handles image processing for OCR pipeline (`pdf2image` renders PDF pages as images). Version >=12.0.0 introduces numpy compatibility issues when running alongside certain opencv-python versions (both may be installed in the same environment). Lower bound 10.4.0 ensures WebP support for modern PDFs. | - `>=12.0.0`: Numpy incompatibility with opencv-python
- `<10.4.0`: Missing WebP codec support; some PDFs fail to render

**Upper bound is intentional.** Do not remove without testing opencv-python coexistence. |
| **pdf2image** | `==1.17.0` | Latest version of the pdf2image library. This is a thin wrapper around `pdftoppm` (poppler-utils) and does not have API changes across versions. Pinned for reproducibility. | None known. Compatible with all poppler-utils versions. |
| **python-docx** | `==1.2.0` | Latest stable version. DOCX extraction in `core/extractors.py` uses the standard document parsing API which has been stable since 1.0.0. Pinned to avoid unexpected changes from downstream packages. | None known. Backwards compatible with 1.x series. |

### OCR & Text Extraction

| Package | Pinned Version | Why This Version | Incompatibilities |
|---------|---------------|-----------------|------------------|
| **pytesseract** | `==0.3.13` | Latest version of the Tesseract OCR wrapper. Works with any Tesseract 4.x or 5.x engine installed on the system. The Python package itself does not drive model loading — the underlying Tesseract binary does. Pinned for reproducibility. | None known. Compatible with all tesseract-ocr 4.0+ installations. |
| **easyocr** | `==1.7.0` | **CRITICAL PIN.** Version 1.7.0 is compatible with torch 2.2.x and sentence-transformers 4.x. Later versions (1.7.1+) have been observed to introduce conflicts with newer C++ dependencies. Earlier versions (1.6.x) use older model formats that may not download correctly. | - `>=1.8.0`: Unknown future incompatibilities
- `<1.5.0`: Different model architecture; incompatible with current pipeline config

Requires torch 2.2.x. **Cannot** be used with torch 2.6+ (torch.load security restriction). |
| **beautifulsoup4** | `==4.15.0` | Latest stable version. Used for HTML/XML cleaning in `core/extractors.py`. Lacks breaking API changes across versions. Compatible with all Python 3.x versions. Pinned for reproducibility. | None known. Backwards compatible across all versions. |
| **striprtf** | `==0.0.32` | Latest version of this minimal library for RTF document cleaning. No known incompatibilities. Very stable project with infrequent releases. Pinned for reproducibility. | None known. Single-function library, highly stable. |

### Embedding & Deep Learning

| Package | Pinned Version | Why This Version | Incompatibilities |
|---------|---------------|-----------------|------------------|
| **torch** | `==2.2.2` | **CRITICAL PIN.** Last version before CVE-2025-32434 torch.load security restriction was enforced. Torch >=2.6 requires safetensors-only model loading, which breaks sentence-transformers 4.x and easyocr model loading on macOS (no CUDA wheels available for newer torch). Version 2.2.2 is the stable baseline. | - `>=2.6.0`: Requires safetensors-only; breaks st/easyocr
- `<2.1.0`: Lacks macOS arm64 wheel support in some builds

**This pin constrains sentence-transformers to 4.x.** Do not upgrade without migrating all models to safetensors format. |
| **transformers** | `==4.46.2` | Compatible with torch 2.2.x and sentence-transformers 4.0.x. Transformers 5.x+ introduced breaking changes in model loading pipelines that are incompatible with st 4.x's internal architecture. | - `>=5.0.0`: Breaking model loading API
- `<4.40.0`: May lack BAAI/bge-m3 model support (used by pipeline)

**Must stay <5.0.** |
| **sentence-transformers** | `==4.0.2` | **CRITICAL PIN.** Last version compatible with torch 2.2.x. Version 5.x requires torch>=2.6 which is incompatible due to CVE-2025-32434 (see torch pin). Version 4.0.2 works correctly with BAAI/bge-m3 model used by `core/embedder.py`. | - `>=5.0.0`: Requires torch>=2.6 — circular conflict
- `<3.0.0`: Different API; uses Embedding class, not SentenceTransformer

**This pin is the most constrained package in the tree.** Do not upgrade without resolving torch constraint first. |
| **accelerate** | `==1.14.0` | Compatible with torch 2.2.x and transformers 4.46.x. Provides distributed training infrastructure used by sentence-transformers internally. Later versions may introduce new configuration schemas but remain backwards compatible. | None known at this version. Compatible with all st 4.x features. |
| **safetensors** | `==0.7.0` | Required by transformers and sentence-transformers for safe model weight loading. Version 0.7.x is stable and works with torch 2.2.x tensor serialization. | None known. Must be >=0.2.0 (minimum required by transformers). |

### Chunking & Text Processing

| Package | Pinned Version | Why This Version | Incompatibilities |
|---------|---------------|-----------------|------------------|
| **langchain-text-splitters** | `==1.1.2` | Provides `SentenceTransformersTokenTextSplitter` used by `core/processing.py`. Version 1.x API is stable. Later versions may introduce LangChain integration changes but remain compatible. Pinned for reproducibility. | None known. Compatible with all langchain-core 1.x series. |
| **numpy** | `==1.26.4` | **CRITICAL PIN.** Must be <2 due to Pillow conflict: Pillow (via pdf2image → PIL.Image) requires numpy<2 on some platforms, while opencv-python requires numpy>=2. This is a fundamental incompatibility — both libraries may be present in the same environment. Version 1.26.4 is the latest 1.x release and fully compatible with all ML packages in our stack. | - `>=2.0.0`: Pillow/opencCV conflict; some docling wheels fail
- `<1.24.0`: Missing array optimizations needed by torch

**This pin constrains all numeric operations.** Do not upgrade without removing opencv-python or testing both together. |

### Data & Utilities

| Package | Pinned Version | Why This Version | Incompatibilities |
|---------|---------------|-----------------|------------------|
| **pandas** | `==2.2.2` | Latest stable 2.2.x release. Used by benchmark dashboards and data analysis utilities. Compatible with numpy 1.26.x. Version 3.x introduced breaking API changes. | - `>=3.0.0`: Breaking DataFrame API
- `<2.0.0`: Missing dtype backend features

Must stay <3.0 due to numpy dependency. |
| **watchdog** | `==4.0.1` | File system monitoring library used for live document ingestion. Version 4.x uses inotify on Linux and FSEvents on macOS. Earlier versions (3.x) use deprecated API. | None known within 4.x series. |
| **requests** | `==2.32.3` | Universal HTTP client. Extremely stable library with no breaking changes across recent versions. Used by qdrant-client, docling, and other dependencies internally. Pinned for reproducibility. | None known. Fully backwards compatible. |
| **qdrant-client** | `==1.7.3` | HTTP client for Qdrant vector database (Sprint 2). Version 1.7.x API is stable. Later versions may add new features but maintain HTTP API compatibility with all Qdrant server versions >=1.7.0. | None known within 1.x series. Compatible with Qdrant 1.7+. |

---

## Summary of Critical Pins

These three packages have **blocker-level** constraints — changing any of them cascades to multiple other dependencies:

| Package | Current Pin | If Changed To | Cascade Effect |
|---------|------------|---------------|----------------|
| **torch** | `==2.2.2` | >=2.6.0 | sentence-transformers must upgrade → may require pyobjc-core → fails on macOS Python 3.13+ |
| **sentence-transformers** | `==4.0.2` | >=5.0.0 | Requires torch>=2.6 → conflicts with CVE-2025-32434 workaround |
| **docling** | `==2.99.0` | >=2.100.0 | Introduces pyobjc-core → fails on macOS Python 3.13+ |

**These pins must be reviewed together.** They form a dependency cluster that cannot be partially changed without full ecosystem validation.

---

*End of DEPENDENCY_DECISIONS.md*