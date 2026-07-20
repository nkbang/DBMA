# Project Analysis

## Overview
This is a document processing and analysis application built with Python and Streamlit. The system processes various document formats (PDF, DOCX, EPUB, RTF, HTML, etc.) through a web interface, performing text extraction, language detection, noise filtering, and chunking optimization for RAG (Retrieval-Augmented Generation) applications.

## Main Files and Their Purposes

### `dbma.py` - Archived (moved to `archive/legacy/dbma.py` on 2026-07-17; official entry point is now `dbma_ui.py`)
- **Purpose**: Streamlit-based web application that served as the user interface
- **Key Functions**:
  - Main application logic with tab-based UI (Parse, Analyze, Project, RAG)
  - Configuration management and session state handling
  - Integration of all processing components
  - RAG chat functionality with vector database support

### `core/processing.py` - Core Processing Logic
- **Purpose**: Main document processing and chunking implementation
- **Key Functions**:
  - `build_converter()` - Creates document converter instance
  - `build_splitter()` - Creates text splitter for chunking
  - `detect_language()` - Detects Hebrew/Greek language characters
  - `save_md_with_language()` - Saves markdown with metadata
  - `save_chunks()` - Saves chunks in legacy format for RAG pipeline
  - `move_source_file()` - Moves source files to output directory
  - `process_one_file()` - Main processing function that orchestrates the entire flow

### `core/extractors.py` - Document Extraction Functions
- **Purpose**: Extract text from various document formats
- **Key Functions**:
  - `extract_text_from_file()` - Main extraction function with OCR support

### `ui/tabs.py` - UI Tab Rendering
- **Purpose**: Render different tabs in the Streamlit application
- **Key Functions**:
  - `render_processing_tab()` - File selection and processing tab
  - `render_analysis_tab()` - Analysis and visualization tab

### `core/utils.py` - Utility Functions
- **Purpose**: Supporting utilities for text processing and analysis
- **Key Functions**:
  - `make_safe_stem()` - Creates safe filenames
  - `calculate_noise_score()` - Calculates text quality score
  - Various formatting and helper functions

### `core/chunking_optimizer.py` - Chunking Optimization
- **Purpose**: Advanced chunking optimization with quality assessment
- **Key Functions**:
  - `optimize_chunks()` - Main optimization function
  - `save_optimized_md()` - Saves optimized markdown files

### `core/files.py` - File System Operations
- **Purpose**: File scanning and management utilities
- **Key Functions**:
  - `scan_directory()` - Scans directory for supported files
  - `scan_md_files()` - Scans for markdown files
  - `load_chunks_info()` - Loads chunk information

## Imported Libraries

### Standard Library
- `os`, `json`, `shutil`, `datetime`, `pathlib` - Core system operations

### Third-party Libraries
- `streamlit` - Web application framework
- `docling.document_converter` - Document processing
- `langchain_text_splitters` - Text splitting utilities
- `sentence_transformers` - Sentence embeddings
- `qdrant_client` - Vector database client
- `fastembed` - Fast embedding models
- `easyocr`, `pytesseract` - OCR libraries
- `python-docx`, `ebooklib`, `beautifulsoup4`, `striprtf`, `pdf2image` - Document format support

## Data Flow Between Modules

1. **UI Interaction**:
   - User selects files in `ui/tabs.py`
   - Process button triggers `process_one_file()` in `core/processing.py`

2. **Document Processing**:
   - `process_one_file()` calls `extract_text_from_file()` from `core/extractors.py`
   - Text is analyzed for language detection
   - Noise score calculation via `calculate_noise_score()` from `core/utils.py`
   - Chunking optimization via `optimize_chunks()` from `core/chunking_optimizer.py`

3. **Output Generation**:
   - Results saved as markdown files with metadata
   - Legacy chunk files saved for RAG pipeline compatibility
   - Optimized markdown files generated
   - Source files moved to output directory

4. **RAG Integration**:
   - Vector database support through `qdrant_client`
   - Embedding generation using `sentence_transformers` and `fastembed`

## Key Features

### Document Processing
- Multi-format document support (PDF, DOCX, EPUB, RTF, HTML)
- OCR integration for scanned documents
- Language detection for Hebrew/Greek characters

### Text Quality Assessment
- Noise score calculation with multiple metrics
- Automated filtering of low-quality text
- Text cleaning and preprocessing

### Chunking Optimization
- Custom chunking algorithm with quality assessment
- Fallback to standard splitter when optimization fails
- Chunk quality monitoring and warnings

### RAG Support
- Vector database integration (Qdrant)
- Embedding generation for retrieval
- Chat interface with LLM support

## Architecture Pattern

The application follows a modular architecture pattern:
1. **Presentation Layer**: Streamlit UI in `ui/app.py` and `ui/tabs.py`
2. **Business Logic Layer**: Core processing in `core/processing.py`, `core/extractors.py`, `core/chunking_optimizer.py`
3. **Utility Layer**: Helper functions in `core/utils.py`, `core/files.py`
4. **Data Access Layer**: File system operations and vector database interaction

## Dependencies

The application requires several key dependencies:
- Streamlit for web interface
- Docling for document conversion
- Langchain text splitters for chunking
- Sentence transformers for embeddings
- Qdrant client for vector storage
- OCR libraries (EasyOCR, Tesseract) for text extraction