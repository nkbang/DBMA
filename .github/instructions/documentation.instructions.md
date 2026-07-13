---
name: documentation
description: "DBMA 문서 작성 규칙: 한글, 마크다운, 명확한 구조, 코드 예시, 상태 추적."
applyTo: "docs/**/*.md,*.md"
---

# DBMA 문서 작성 규칙

## 문서 구조

### 주요 문서

| 파일 | 목적 | 대상 |
|------|------|------|
| `docs/PIPELINE.md` | 데이터 처리 흐름 설명 | 모든 개발자 |
| `docs/STATE.md` | 현재 시스템 상태 | 팀 전체 |
| `docs/TODO.md` | 작업 목록 및 진행률 | 팀 전체 |
| `docs/ARCHITECTURE.md` | 시스템 아키텍처 | 신입 개발자 |
| `docs/DBMA_MAP.md` | 함수/클래스 맵 | 코드 리뷰어 |
| `RUNTIME_COMPATIBILITY_REPORT.md` | 버전 호환성 | 배포 엔지니어 |

---

## 마크다운 작성 규칙

### 1. 제목 계층
```markdown
# 문서 제목 (파일명과 일치)

## 섹션 제목

### 소섹션 제목

#### 상세 항목 제목
```

### 2. 목록 형식
```markdown
## TODO 목록 형식

- [x] 완료된 작업
- [ ] 진행 중인 작업
- [ ] 대기 중인 작업

## 체크리스트

진행률: 40% (완료 2/5)

## 순서 있는 목록

1. 첫 번째 단계
2. 두 번째 단계
3. 세 번째 단계
```

### 3. 테이블
```markdown
| 항목 | 상태 | 담당자 | 진행률 |
|------|------|--------|--------|
| 파싱 | 진행중 | David | 80% |
| RAG | 완료 | - | 100% |
| UI | 대기 | - | 0% |
```

### 4. 코드 블록
```markdown
\`\`\`python
def process_document(file_path: str) -> dict:
    """문서 처리."""
    return {"status": "success"}
\`\`\`

\`\`\`bash
# 실행 방법
streamlit run dbma.py
\`\`\`
```

### 5. 블록 다이어그램
```markdown
\`\`\`
입력 파일
    ↓
[추출]
    ↓
[정제]
    ↓
[청킹]
    ↓
[임베딩]
    ↓
출력 인덱스
\`\`\`
```

---

## 문서별 작성 가이드

### `docs/PIPELINE.md` - 파이프라인 설명

```markdown
# DBMA 파이프라인

## 개요

신학 문서를 입력하면, 추출/정제/청킹/임베딩 단계를 거쳐 
벡터 인덱스가 생성되고, 쿼리에 대해 검색/생성/평가가 실행됨.

## 단계별 흐름

### 1. 문서 추출 (extractors.py)
- PDF, DOCX, TXT 형식 지원
- 메타데이터 추출 (제목, 작성자, 페이지 수)
- 로그: "[extract] completed: source={file_name} pages={num_pages}"

### 2. 텍스트 정제 (text_normalizer.py)
- 유니코드 정규화
- 공백 정리
- 특수 문자 처리 (히브리어/헬라어 보존)
- 로그: "[normalize] completed: size_before={X} size_after={Y}"

### 3. 청킹 (chunking_optimizer.py)
- 기본 chunk_size: 1200
- 기본 overlap: 200
- 문장 경계 존중
- 로그: "[chunk] completed: count={num_chunks} avg_size={avg_size}"

### 4. 임베딩 (embedder.py)
- 모델: bge-m3:latest
- 배치 처리: batch_size=32
- 로그: "[embed] completed: count={num_embeddings} elapsed={elapsed_time}s"

### 5. 저장 (ingest.py)
- 벡터DB: Chroma
- 메타데이터 저장
- 로그: "[ingest] completed: index_size={size}"

## 검색/생성 흐름

### 1. 쿼리 전처리
### 2. 벡터 검색
### 3. 컨텍스트 구성
### 4. LLM 호출
### 5. 응답 생성

## 평가

- 검색 정확도 (MRR, NDCG)
- 생성 품질 (ROUGE, BLEU)
- 사용자 만족도
```

### `docs/STATE.md` - 현재 상태

```markdown
# 시스템 상태

마지막 업데이트: 2026-07-11

## 제품 상태

| 컴포넌트 | 상태 | 비고 |
|----------|------|------|
| 문서 추출 | ✅ 안정 | PDF/DOCX/TXT 모두 작동 |
| 텍스트 정제 | ✅ 안정 | 히브리어/헬라어 지원 |
| 청킹 | ✅ 안정 | 최적화 완료 |
| 임베딩 | ✅ 안정 | bge-m3:latest 사용 |
| 검색 | ✅ 안정 | 정확도 87% |
| 생성 | ⚠️ 개선중 | 응답 길이 조정 중 |
| UI | ✅ 안정 | 탭 기반 인터페이스 |

## 알려진 문제

1. **생성 응답 길이**: 때로 너무 짧음 → 프롬프트 조정 필요
2. **특정 신학 용어**: 검색 정확도 낮음 → 신학 사전 추가 필요

## 성능 메트릭

- 검색 응답 시간: ~200ms
- 생성 응답 시간: ~2s
- 임베딩 처리: ~10 docs/s
- 메모리 사용: ~4GB
```

### `docs/TODO.md` - 작업 목록

```markdown
# 작업 목록 및 진행 상황

진행률: 35% (7/20 완료)

## Sprint 1: 파이프라인 안정화

- [x] 파싱 함수 개선
- [x] 정제 로직 강화
- [ ] 청킹 최적화
- [ ] 임베딩 캐싱

진행률: 50% (2/4 완료)

## Sprint 2: 검색 정확도 향상

- [ ] 신학 사전 추가
- [ ] 쿼리 확장 구현
- [ ] 재순위화 추가

진행률: 0% (0/3 완료)

## Sprint 3: 생성 품질 개선

- [ ] 프롬프트 최적화
- [ ] Few-shot 예제 추가
- [ ] 응답 길이 조정

진행률: 0% (0/3 완료)

## 버그 및 문제

- [ ] 특정 신학 용어 검색 실패
- [ ] 메모리 누수 이슈
- [ ] UI 탭 전환 시 상태 리셋

진행률: 0% (0/3 완료)
```

### `docs/ARCHITECTURE.md` - 아키텍처

```markdown
# DBMA 아키텍처

## 시스템 구성도

\`\`\`
┌─────────────────────────────────────┐
│       Streamlit UI (dbma.py)        │
├─────────────────────────────────────┤
│  Upload │ Search │ Generation │ ...│
└──────────────┬──────────────────────┘
               │
        ┌──────▼──────┐
        │   Core      │
        │  Modules    │
        ├─────────────┤
        │ Extractors  │
        │ Normalizer  │
        │ Chunking    │
        │ Embedder    │
        │ Retrieval   │
        │ Ingest      │
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │   Storage   │
        ├─────────────┤
        │  Chroma DB  │
        │  File Sys   │
        └─────────────┘
\`\`\`

## 모듈 책임

### ui/
- Streamlit 인터페이스
- 사용자 입력 처리
- 결과 표시

### core/
- extractors.py: 문서 추출
- text_normalizer.py: 텍스트 정제
- chunking_optimizer.py: 청킹
- embedder.py: 임베딩
- retrieval.py: 검색
- ingest.py: 저장소 관리
- config.py: 설정 관리

### chroma_db/
- 벡터 임베딩 저장소
- SQLite 기반

## 데이터 흐름

1. 사용자가 UI에서 문서 업로드
2. extractors.py가 텍스트 추출
3. text_normalizer.py가 정제
4. chunking_optimizer.py가 청킹
5. embedder.py가 임베딩
6. ingest.py가 Chroma에 저장
```

### `docs/DBMA_MAP.md` - 함수 맵

```markdown
# DBMA 함수/클래스 맵

## core/extractors.py

\`\`\`
ExtractorFactory
├── extract_pdf(file_path) → (text, metadata)
├── extract_docx(file_path) → (text, metadata)
└── extract_txt(file_path) → (text, metadata)
\`\`\`

## core/text_normalizer.py

\`\`\`
TextNormalizer
├── normalize_whitespace(text) → str
├── normalize_unicode(text) → str
├── normalize_special_chars(text) → str
└── normalize(text) → str
\`\`\`

## core/chunking_optimizer.py

\`\`\`
ChunkingOptimizer
├── chunk_by_sentences(text) → List[str]
├── chunk_by_tokens(text) → List[str]
└── optimize(text, metadata) → List[Dict]
\`\`\`

## core/embedder.py

\`\`\`
EmbedderService
├── load_model(model_name) → model
├── embed_texts(texts) → np.ndarray
└── embed_batch(texts, batch_size) → List[np.ndarray]
\`\`\`

## core/retrieval.py

\`\`\`
RetrieverService
├── retrieve(query) → List[Dict]
├── retrieve_with_score(query) → List[Tuple]
└── retrieve_top_k(query, k) → List[Dict]
\`\`\`

## core/ingest.py

\`\`\`
IngestService
├── add_documents(docs) → bool
├── update_document(doc_id, doc) → bool
└── delete_document(doc_id) → bool
\`\`\`
```

---

## 한글 표기법

- 고정 용어: 영문 그대로 (RAG, LLM, Chroma)
- 한글 설명: "벡터 임베딩", "텍스트 정제"
- 파이썬 기호: 백틱 사용 (`dbma.py`, `extract_pdf()`)
- 경로: 슬래시 사용 (`core/extractors.py`)

---

## 업데이트 규칙

- 매주 월요일 10시 `STATE.md` 업데이트
- 기능 완료 후 바로 `TODO.md` 업데이트
- 버그 발견 시 즉시 기록
- 마이너 수정은 매월 1일 종합 업데이트
