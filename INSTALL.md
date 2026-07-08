# DBMA Sprint 1 — Installation Guide
**Generated:** 2026-07-04  
**Objective:** Fresh installation of the complete runtime environment for Sprint 1

---

## Prerequisites

| Item | Minimum | Recommended |
|------|---------|-------------|
| Python | 3.11.x or 3.12.x | 3.11.9 |
| Disk Space | 5 GB | 10 GB |
| RAM | 4 GB | 8 GB+ |
| Internet | Required (model download ~3 GB) | Required |

### Python Version Check

```bash
python3 --version
# Must output: Python 3.11.x or Python 3.12.x
# If output is 3.13+ or lower than 3.9, DO NOT proceed — install Python 3.11 or 3.12 first
```

### Installing Python 3.11/3.12 (if not present)

```bash
# macOS (Homebrew)
brew install python@3.11

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

# Windows
# Download from https://www.python.org/downloads/ — select 3.11.x or 3.12.x
# IMPORTANT: Check "Add Python to PATH" during installation
```

---

## macOS Installation

### Step 1: Install System Dependencies

```bash
# Install poppler (PDF rendering for pdf2image)
brew install poppler

# Install tesseract (OCR engine)
brew install tesseract

# Verify Xcode Command Line Tools are installed
xcode-select --install

# Verify Python version
python3.11 --version  # Should be 3.11.x
```

### Step 2: Create Virtual Environment

```bash
cd /path/to/DBMA

python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
# Verify core imports resolve correctly
python -c "import streamlit; import chromadb; import docling; print('OK')"

# Or manually:
python -c "from core.config import DEFAULT_CHUNK_SIZE; print(f'OK: chunk={DEFAULT_CHUNK_SIZE}')"
```

---

## Ubuntu/Debian Installation

### Step 1: Install System Dependencies

```bash
# Install poppler (PDF rendering for pdf2image)
sudo apt-get update
sudo apt-get install -y poppler-utils

# Install tesseract (OCR engine) — version 4.x or 5.x
sudo apt-get install -y tesseract-ocr

# Additional dependencies for easyocr and PyTorch
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0

# If compiling from source is needed (e.g., pyobjc-core alternative on Linux)
sudo apt-get install -y build-essential gcc g++
```

### Step 2: Create Virtual Environment

```bash
cd /path/to/DBMA

python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
python -c "import streamlit; import chromadb; import docling; print('OK')"
```

---

## Windows Installation

### Step 1: Install System Dependencies

**poppler for pdf2image:**
1. Download from: https://github.com/oschwartz10612/poppler-windows/releases/
2. Extract to `C:\poppler\`
3. Add `C:\poppler\Library\bin` to PATH

**tesseract OCR engine:**
1. Download installer from: https://github.com/tesseract-ocr/tesseract/wiki
2. Run the `.exe` installer (select "Base" and "langdata" packages)
3. Default install path: `C:\Program Files\Tesseract-OCR\`

### Step 2: Create Virtual Environment

```cmd
cd C:\path\to\DBMA

python3.11 -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
```

### Step 3: Install Python Dependencies

```cmd
pip install -r requirements.txt
```

### Step 4: Configure Tesseract Path (if not auto-detected)

Create or edit `.env` in project root:
```
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### Step 5: Verify Installation

```cmd
python -c "from core.config import DEFAULT_CHUNK_SIZE; print(f'OK: chunk={DEFAULT_CHUNK_SIZE}')"
```

---

## Conda Environment (Optional Alternative)

For users who prefer conda over venv, or need GPU support:

### Step 1: Install Conda (if not installed)

```bash
# Download from https://docs.conda.io/en/latest/miniconda.html
# Then:
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

### Step 2: Create Environment from YAML

```bash
cd /path/to/DBMA

conda env create -f environment.yml
conda activate dbma-sprint1
```

### Step 3: Verify Installation

```bash
python -c "from core.config import DEFAULT_CHUNK_SIZE; print(f'OK: chunk={DEFAULT_CHUNK_SIZE}')"
```

---

## GPU Support (Optional)

For CUDA-enabled NVIDIA GPUs:

### Prerequisites
- NVIDIA GPU with compute capability >=5.0
- NVIDIA drivers >=520.x
- CUDA Toolkit >=11.8

### Installation

```bash
# After creating the virtual environment:
pip uninstall -y torch torchvision

# Install PyTorch with CUDA 11.8 support
pip install torch==2.2.2 torchvision==0.17.2 \
  --index-url https://download.pytorch.org/whl/cu118
```

For ROCm (AMD GPUs):
```bash
pip uninstall -y torch torchvision
pip install torch==2.2.2 torchvision==0.17.2 \
  --index-url https://download.pytorch.org/whl/rocm6.0
```

---

## Docker Services (Qdrant + n8n)

These are **optional** Sprint 2/3 services. They run in Docker containers.

```bash
# Start only Qdrant (Sprint 2 vector store)
docker compose up -d qdrant

# Start all services
docker compose up -d
```

Verify:
```bash
docker ps | grep qdrant
# Should show running dbma_qdrant container

# Test API
curl http://localhost:6333/  # Should return {"status":"ok"}```

---

## Troubleshooting

### Issue: `pyobjc-core` fails to build on macOS with Python 3.13+
**Resolution:** Downgrade to Python 3.11 or 3.12. This is a hard constraint from Apple's Python packaging pipeline.

### Issue: `torch` download fails (network/proxy)
```bash
# Use mirror
export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
pip install torch==2.2.2

# Or manually download wheel:
# https://download.pytorch.org/whl/torch/
```

### Issue: `poppler` / `pdftoppm` not found (pdf2image error)
**macOS:** `brew install poppler`
**Ubuntu:** `sudo apt-get install -y poppler-utils`
**Windows:** Download from poppler-windows releases and add to PATH

### Issue: Tesseract binary not found (OCR errors)
```bash
# macOS
brew install tesseract

# Ubuntu
sudo apt-get install -y tesseract-ocr

# Verify
tesseract --version
```

### Issue: `docling` import error after install
**Resolution:** Ensure torch 2.2.2 is installed: `pip show torch | grep Version`  
Expected: `Version: 2.2.2`

---

*End of INSTALL.md*