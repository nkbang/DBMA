# DBMA Function Map

## 목적
이 문서는 `dbma.py`를 시작점으로 DBMA 프로젝트의 연결 관계를 함수 단위로 정리한다.
개발 중 구조를 빠르게 이해하고, 수정 범위를 줄이며, 블록 다이어그램 작성에 참고하기 위한 문서다.

---

## 전체 흐름

```text
dbma.py
→ ui/tabs.py
→ core/processing.py
→ core/extractors.py
→ core/chunking_optimizer.py
→ core/files.py
→ core/utils.py
→ dbma_rag.py
```

---

## dbma.py

### 역할
- 메인 진입점
- Streamlit UI 실행
- 전체 흐름 오케스트레이션

### 주요 연결
- `ui/tabs.py`
- `core/processing.py`
- `dbma_rag.py`

### 관련 함수
- `main()`
- `run_app()`
- `load_config()`
- `render_ui()`

---

## core/processing.py

### 역할
- 문서 처리의 중심 오케스트레이터
- 추출, 정제, 청킹, 저장 흐름 관리

### 관련 함수
- `process_one_file()`
- `build_converter()`
- `build_splitter()`
- `detect_language()`
- `save_md_with_language()`
- `save_chunks()`
- `move_source_file()`

### 연결
- `core/extractors.py`
- `core/utils.py`
- `core/chunking_optimizer.py`
- `core/files.py`

---

## core/extractors.py

### 역할
- 문서에서 텍스트를 추출
- OCR이 필요한 경우 보조 처리

### 관련 함수
- `extract_text_from_file()`

### 연결
- `core/processing.py`

---

## core/chunking_optimizer.py

### 역할
- 청킹 최적화
- 텍스트 품질 점검
- 최적 청크 결과 저장

### 관련 함수
- `optimize_chunks()`
- `save_optimized_md()`

### 연결
- `core/processing.py`
- `core/utils.py`

---

## core/files.py

### 역할
- 디렉터리 스캔
- md 파일 탐색
- 청크 정보 로드

### 관련 함수
- `scan_directory()`
- `scan_md_files()`
- `load_chunks_info()`

### 연결
- `core/processing.py`
- `ui/tabs.py`

---

## core/utils.py

### 역할
- 공통 유틸리티
- 파일명 정리
- 품질 점수 계산
- 보조 포맷팅

### 관련 함수
- `make_safe_stem()`
- `calculate_noise_score()`

### 연결
- `core/processing.py`
- `core/chunking_optimizer.py`

---

## ui/tabs.py

### 역할
- 탭 기반 UI 렌더링
- 처리, 분석, 설정 흐름 분리

### 관련 함수
- `render_processing_tab()`
- `render_analysis_tab()`

### 연결
- `dbma.py`
- `core/files.py`
- `core/processing.py`

---

## dbma_rag.py

### 역할
- RAG 검색과 생성 처리
- 벡터 저장소와 질의 응답 연결

### 관련 함수
- `run_rag_query()`
- `build_retriever()`
- `generate_response()`

### 연결
- `core/processing.py`
- 벡터 저장소
- LLM 호출부

---

## 점검 순서

1. `dbma.py`를 먼저 본다.
2. `ui/tabs.py`에서 사용자 흐름을 본다.
3. `core/processing.py`에서 파이프라인을 본다.
4. `core/extractors.py`와 `core/chunking_optimizer.py`를 본다.
5. `dbma_rag.py`에서 검색과 응답을 본다.
6. `docs/TODO.md`에 현재 상태를 적는다.

---

## 작성 규칙
- 함수 이름은 실제 코드와 맞춰야 한다.
- 새 함수가 생기면 바로 추가한다.
- 연결이 바뀌면 이 문서도 같이 고친다.
- 블록 다이어그램과 함께 사용한다.