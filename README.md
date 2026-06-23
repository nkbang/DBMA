# DBMA (Document-Based Memory Assistant)

DBMA는 문서 기반 메모리 어시스턴트로, 다양한 형식의 문서를 처리하고 RAG (Retrieval-Augmented Generation) 기능을 제공하는 시스템입니다.

## 프로젝트 구조

```
.
├── dbma.py                 # 주요 애플리케이션 로직
├── dbma_rag.py            # RAG 기능 관련 코드
├── requirements.txt       # 의존성 라이브러리 목록
├── test_dbma.py           # 단위 테스트 파일
├── core/                  # 핵심 기능 모듈
│   ├── __init__.py
│   ├── chunking_optimizer.py  # 청킹 최적화 로직
│   ├── config.py          # 설정 관리
│   ├── extractors.py      # 문서 추출기
│   ├── files.py           # 파일 처리 관련 로직
│   ├── processing.py      # 프로세싱 로직
│   └── utils.py           # 유틸리티 함수
├── ui/                    # 사용자 인터페이스 구성 요소
│   ├── __init__.py
│   ├── tabs.py            # 탭 UI
│   ├── sidebar.py         # 사이드바 UI
│   └── styles.py          # 스타일 정의
├── app/                   # 애플리케이션 모듈
├── chroma_db/             # ChromaDB 벡터 데이터베이스 저장소
├── data/                  # 입력 및 출력 데이터 디렉토리
│   ├── RAW                # 원본 문서 입력 디렉토리
│   └── 제련완성본         # 처리된 문서 출력 디렉토리
├── docs/                  # 문서화 파일
├── logs/                  # 로그 파일 저장소
└── tests/                 # 테스트 코드 디렉토리
```

## 주요 기능

1. **다양한 문서 형식 지원**:
   - PDF, TXT, MD, DOCX, EPUB, HTML, RTF 등 다양한 문서 형식 처리

2. **문서 청킹 및 최적화**:
   - 문서를 적절한 크기로 분할하고 최적화된 청킹 전략 적용

3. **RAG (Retrieval-Augmented Generation) 기능**:
   - 벡터 데이터베이스를 통한 문서 검색 및 LLM을 통한 답변 생성

4. **문서 품질 평가**:
   - 문서의 노이즈 수준을 평가하여 품질 판단

## 의존성

`requirements.txt` 파일에 정의된 라이브러리들을 설치해야 합니다:

```bash
pip install -r requirements.txt
```

## 사용 방법

1. `data/RAW` 디렉토리에 처리할 문서를 추가합니다.
2. `dbma.py`를 실행하여 문서 처리를 시작합니다:
   ```bash
   python dbma.py
   ```
3. Streamlit UI에서 결과를 확인하고 RAG 채팅 기능을 사용합니다.

## 테스트

단위 테스트를 실행하려면:

```bash
python test_dbma.py
```

## 개발 정보

- **버전**: 0.6.4
- **LLM 모델**: llama3.1, gemma3:4b, etc.
- **임베딩 모델**: bge-m3, nomic-embed-text, mxbai-embed-large
- **벡터 데이터베이스**: ChromaDB

## 구성 요소 설명

### 핵심 모듈

- `core/`: 문서 처리와 관련된 핵심 로직을 포함
- `ui/`: Streamlit 기반의 사용자 인터페이스 구성 요소
- `chroma_db/`: 벡터 임베딩 저장소
- `data/`: 입력 및 출력 데이터 관리

### 주요 함수

- `process_one_file()`: 단일 문서 처리
- `build_rag_store()`: RAG 저장소 구축
- `query_rag()`: RAG 쿼리 기능
- `estimate_noise_score()`: 문서 노이즈 점수 평가

## 로그 및 추적

- 프로젝트 이벤트는 `logs/project_events.jsonl`에 기록됩니다.
- 진행 상황은 `docs/dbmar_todo_progress_board.md`와 `docs/dbmar_progress_snapshot.csv`에서 확인할 수 있습니다.

## 헬라어/히브리어 문서 처리

이 프로젝트는 헬라어와 히브리어 문서 처리를 지원합니다. 다음 기능들이 포함됩니다:

1. **OCR 지원**: 스캔된 PDF 문서에 대한 Tesseract OCR 처리
2. **언어 팩**: 히브리어 (he) 및 헬라어 (grc) 언어 팩 사용
3. **임베딩 모델**: BGE-M3 모델을 사용한 다국어 임베딩
4. **문서 분할**: 언어에 독립적인 텍스트 분할 (SentenceSplitter)

### 요구 사항

헬라어/히브리어 문서 처리를 위해 다음 추가 의존성을 설치해야 합니다:

```bash
pip install pdf2image python-tesseract
```

### 사용 방법

문서가 히브리어 또는 헬라어로 작성된 경우, 시스템은 자동으로 언어를 감지하고 적절한 언어 팩을 적용합니다. OCR 처리는 스캔된 문서에 대해 자동으로 활성화됩니다.

## Features

- **Multi-format Support**: PDF, TXT, MD, DOCX, EPUB, HTML, RTF
- **Advanced Text Extraction**:
  - PyMuPDF (1st priority) — best font mapping accuracy
  - docling converter — OCR included, high-quality structure analysis
  - pypdf fallback — pure Python
- **Text Preprocessing**: Noise filtering, Unicode cleanup, line break restoration
- **Chunking Optimization**: Intelligent chunk size selection and overlap optimization
- **RAG Pipeline**: Vector store integration with Qdrant
- **Hebrew/Greek Support**:
  - BGE-M3 embedding model for multilingual document processing
  - Language-agnostic text splitting using SentenceSplitter
  - Tesseract OCR support for scanned PDFs in Hebrew and Greek

## Project Analysis

This project has been analyzed and documented in the `analysis/` directory:
- `analysis/technology.md`: Detailed technical analysis of the project components and architecture
- `analysis/summary.md`: Comprehensive overview of the project structure, functionality, and key features

The system is built with Python and Streamlit, featuring a modular architecture with separate components for text extraction, chunking optimization, utility functions, and user interface.
