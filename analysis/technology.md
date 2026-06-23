# Technology Stack

## Core Technologies

### Python Libraries
- **streamlit**: Web application framework for building data apps
- **docling**: Document processing library for extracting text from various document formats
- **langchain-text-splitters**: Text splitting utilities for handling document chunking
- **sentence-transformers**: Library for generating sentence embeddings
- **qdrant-client[fastembed]**: Vector database client with fast embedding support
- **fastembed**: Efficient embedding models for vector search
- **easyocr**: Optical character recognition library
- **python-docx**: Word document processing
- **ebooklib**: E-book processing library
- **beautifulsoup4**: HTML/XML parsing library
- **striprtf**: RTF document processing
- **pdf2image**: PDF to image conversion
- **pytesseract**: Tesseract OCR wrapper

### Document Processing
- **OCR Support**: Integrated with EasyOCR for text extraction from images/scanned documents
- **Multi-format Support**: Handles various document types including PDF, DOCX, EPUB, RTF, HTML, etc.
- **Language Detection**: Automatic detection of Hebrew and Greek language characters

## Architecture Components

### Core Modules
1. **core/processing.py** - Main processing logic with chunking optimization
2. **core/extractors.py** - Document extraction functions for different file types
3. **core/utils.py** - Utility functions for text processing and noise calculation
4. **core/chunking_optimizer.py** - Advanced chunking optimization logic
5. **core/files.py** - File system operations and scanning utilities

### UI Components
1. **ui/tabs.py** - Streamlit tab rendering logic
2. **ui/sidebar.py** - Sidebar configuration and settings
3. **ui/styles.py** - UI styling and formatting
4. **ui/init.py** - UI initialization

### Data Flow
1. File selection in UI
2. Document conversion using docling
3. Text extraction with OCR support
4. Language detection and metadata addition
5. Noise score calculation for text quality assessment
6. Chunking optimization using custom optimizer or fallback to standard splitter
7. Output generation in both standard format and optimized markdown
8. File movement and storage

## Key Features
- **Multi-language Support**: Hebrew/Greek language detection and processing
- **Chunking Optimization**: Custom chunking algorithm with quality assessment
- **Noise Detection**: Automated text quality scoring and filtering
- **RAG Integration**: Vector database support for Retrieval-Augmented Generation
- **OCR Integration**: Support for scanned documents through Tesseract/EasyOCR
- **Web Interface**: Streamlit-based user interface for document processing