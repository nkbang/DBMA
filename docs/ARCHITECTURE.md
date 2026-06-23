# DBMA Architecture

## 목적
이 문서는 DBMA 프로젝트의 전체 구조를 한눈에 이해하기 위한 아키텍처 문서다.
특히 `dbma.py`를 시작점으로 각 모듈이 어떻게 연결되는지 정리한다.

---

## 시스템 개요

DBMA는 신학 문서 전용 RAG 시스템이다.
문서 추출, 정제, 청킹, 저장, 임베딩, 검색, 생성, 평가가 하나의 흐름으로 연결된다.
핵심 진입점은 `dbma.py`이며, Streamlit UI와 처리 파이프라인을 연결한다.

---

## 최상위 구조

```text
dbma.py
├── ui/
│   ├── tabs.py
│   ├── sidebar.py
│   └── styles.py
├── core/
│   ├── processing.py
│   ├── extractors.py
│   ├── files.py
│   ├── chunking_optimizer.py
│   └── utils.py
├── dbma_rag.py
├── tests/
├── docs/
├── loops/
└── scripts/
```

---

## 계층 구조

### 1. Presentation Layer
- `dbma.py`
- `ui/tabs.py`
- `ui/sidebar.py`
- `ui/styles.py`

이 계층은 사용자와 직접 만나는 부분이다.
탭 기반 UI, 파일 선택, 처리 상태, 결과 표시를 담당한다.

### 2. Processing Layer
- `core/processing.py`
- `core/extractors.py`
- `core/chunking_optimizer.py`

이 계층은 문서 처리의 중심이다.
문서에서 텍스트를 추출하고, 정제하고, 청킹하고, 결과를 저장한다.

### 3. Utility Layer
- `core/files.py`
- `core/utils.py`

이 계층은 파일 탐색, 이름 정리, 품질 점수 계산, 공통 보조 기능을 담당한다.

### 4. RAG Layer
- `dbma_rag.py`

이 계층은 임베딩, 벡터 검색, 질의 응답을 담당한다.
LlamaIndex 기반 구조로 운영한다 [cite:7].

### 5. Documentation and Loop Layer
- `docs/`
- `loops/`
- `scripts/`

이 계층은 프로젝트 상태, 평가 루프, 실행 스크립트를 담당한다.
DBMA의 루프 엔지니어링 방식에 맞춘 관리 영역이다.

---

## 핵심 원칙

- `dbma.py`를 기준점으로 본다.
- 기능은 작은 모듈로 나눈다.
- UI와 처리 로직을 분리한다.
- RAG와 문서 처리를 분리한다.
- 상태와 결과는 md 파일로 남긴다.
- 변경은 최소 단위로 한다.

---

## 데이터 흐름

```text
원본 문서
→ ui/tabs.py에서 선택
→ core/extractors.py에서 추출
→ core/processing.py에서 정제
→ core/chunking_optimizer.py에서 청킹 최적화
→ core/files.py에서 저장
→ dbma_rag.py에서 임베딩 및 검색
→ LLM 응답 생성
→ 결과 검증
→ docs/에 상태 기록
```

---

## 문서 처리 구조

### 입력
- PDF
- TXT
- MD
- DOCX
- EPUB
- HTML
- RTF

### 처리
- 텍스트 추출
- 언어 감지
- 노이즈 점검
- 청킹 최적화
- md 저장
- 청크 저장

### 출력
- 정제된 md 파일
- 청크 정보
- 품질 로그
- RAG용 산출물

---

## 연결 기준

### dbma.py
- 전체 흐름 시작점
- UI와 백엔드 연결
- 상태 관리 연결

### core/processing.py
- 파이프라인의 중심
- 추출과 청킹과 저장을 연결

### ui/tabs.py
- 사용자 작업 흐름 관리
- 탭별 상태 분기

### dbma_rag.py
- 검색과 응답 담당
- 벡터 기반 질의 처리

---

## 함수 단위 문서화 기준

함수는 다음 항목으로 문서화한다.
- 이름
- 역할
- 입력
- 출력
- 연결 함수
- 예외 상황

예시:
```md
### process_one_file()
- 역할: 한 문서 전체 처리
- 입력: 파일 경로
- 출력: md, chunk, 로그
- 연결: extract_text_from_file(), optimize_chunks(), save_md_with_language()
```

---

## 변경 규칙

- 구조가 바뀌면 이 문서도 함께 수정한다.
- 새 함수가 생기면 연결 위치를 추가한다.
- 복사본 파일은 구조 기준이 아니다.
- 실제 실행 흐름을 기준으로 쓴다.

---

## 점검 항목

- dbma.py가 진입점으로 동작하는가.
- UI와 처리 로직이 분리되어 있는가.
- 청킹과 저장이 안정적으로 연결되는가.
- RAG 흐름이 독립적으로 이해되는가.
- 문서화가 실제 흐름을 반영하는가.