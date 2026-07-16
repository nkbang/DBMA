---
title: DBMA Legacy Entry Point Analysis
category: architecture
sprint: SPRINT16-B-2
based_on:
  - docs/architecture/DBMA-Module-Responsibility-v2.md (SPRINT16-B-1)
  - repository inspection (rg 검색, git log, import 그래프)
status: current
created: 2026-07-16
scope_modified: docs/architecture/ only (읽기 전용 분석, 코드/설정 미수정)
---

# DBMA Legacy Entry Point Analysis

## 1. dbma.py Current Role

`dbma.py`는 **여전히 저장소 내에서 실행 가능한 완전한 Streamlit 애플리케이션**이며,
문서 처리 + 자체 RAG 스택(임베딩·검색·생성)까지 전부 포함한 단일 파일이다.
(SPRINT16-B-1에서 확인한 `query_rag`, `build_rag_store`, `upsert_to_qdrant`,
`embed_text_ollama` 등이 여기 있다.)

그러나 공식 릴리스 문서는 이를 명시적으로 폐기 대상으로 선언하고 있다.

> `docs/releases/v1.1.0/CHANGELOG.md:48`
> | Entry point | `dbma.py` (deprecated) | `ui/app.py` (current) |

**모순되는 신호**: 이 "deprecated" 선언(v1.1.0 릴리스, `ui/app.py` 최종 커밋 `1574d67` —
2026-07-11)이 있은 *이후*에도 `dbma.py`는 2026-07-15까지 활발한 버그 수정을 받았다
(아래 3절 참조). 즉 문서상 지위와 실제 유지보수 활동이 어긋난다.

---

## 2. Execution Path

### 실행 명령 기준 문서 간 불일치

| 문서 | 실행 명령 | 최종 수정 맥락 |
|---|---|---|
| `README.md:67` | `streamlit run dbma.py` | 구버전 안내 (미갱신 추정) |
| `.github/instructions/streamlit.instructions.md:241` | `streamlit run dbma.py` | Copilot 지침, 미갱신 |
| `.github/instructions/documentation.instructions.md:75` | `streamlit run dbma.py` | 동일 |
| `docs/UI_GUIDE.md:363` | `streamlit run ui/app.py` | 현재 세대 |
| `docs/releases/v1.1.0/USER_GUIDE.md:12,23` | `streamlit run ui/app.py` | 공식 v1.1.0 사용자 가이드 |
| `docs/releases/v1.1.0/OPERATIONS.md:148,204` | `streamlit run ui/app.py` | 공식 v1.1.0 운영 가이드 |

**해석**: v1.1.0 공식 산출물(`USER_GUIDE.md`, `OPERATIONS.md`, `CHANGELOG.md`)은 일관되게
`ui/app.py`를 현재 진입점으로 지정한다. 반면 저장소 루트의 `README.md`와 `.github/`
지침 파일들은 여전히 `streamlit run dbma.py`를 안내하고 있어 **신규 사용자/AI 어시스턴트가
구 진입점으로 유입될 위험**이 존재한다.

### CLI / 패키지 진입점
- `pyproject.toml`에 `dbma`/`entry` 관련 스크립트 정의 없음 (grep 결과 0건) — 즉
  패키지 설치형 CLI 진입점으로 등록되어 있지 않다. 실행은 순수하게
  `streamlit run <file>` 수동 호출에 의존한다.
- Makefile, Procfile 등 배포/구동 스크립트 없음.

---

## 3. Dependency Analysis

### 코드 레벨에서 dbma.py를 import하는 유일한 지점
```python
# scripts/backup_chroma.py:32
from dbma import CHROMA_DIR
```
`try/except ImportError`로 감싸여 있고 실패 시 기본 경로(`Path("chroma_db")`)로
폴백한다 — **하드 의존이 아니라 있으면 쓰고 없으면 무시하는 느슨한 결합**이다.
이 외에 `core/`, `ui/`, `tests/`, `scripts/` 어디에서도 `import dbma` 형태의 참조가
없다 (rg 결과 0건). `tests/test_dbma.py`는 `README.md`에 언급만 되어 있고
저장소에 실제 파일은 존재하지 않는다(구 문서 잔재로 추정).

### query_rag / build_rag_store 사용처
```
dbma.py:580   def build_rag_store(...)
dbma.py:651   def query_rag(...)
dbma.py:883   out = build_rag_store(...)   # dbma.py 자기 자신의 UI 콜백 내부
dbma.py:906   res = query_rag(...)         # 동일
```
두 함수 모두 **`dbma.py` 내부에서만 정의되고 호출된다.** 외부(core/, ui/, scripts/,
tests/) 어디에서도 참조되지 않는다 — 완전히 self-contained.

### RetrievalEngine 사용처
```
ui/pages/research.py:19   from core.retrieval import QueryProcessor, RetrievalEngine, RankedCandidate
core/runtime_state.py:260 from core.retrieval import RetrievalEngine   (지연 임포트, 가용성 체크용)
tests/test_book_alias_resolution.py:208  engine = RetrievalEngine(...)
```
`RetrievalEngine`은 현재 세대 UI(`ui/pages/research.py`)와 회귀 테스트에서
실제로 사용되는 유일한 검색 엔진이다. `dbma.py`의 `query_rag`는 `RetrievalEngine`을
전혀 참조하지 않는다 — 완전히 분리된 두 세계다.

### Chroma 관련 참조
```
scripts/backup_chroma.py   — ChromaDB 백업 전용 스크립트, dbma.py의 CHROMA_DIR을 참조 시도
core/config.py:80          — "Ollama 모델 (dbma.py UI용)" 주석과 함께 CHROMA_* 설정 정의
core/runtime_state.py      — chroma_db persist 디렉터리 존재 여부로 인덱싱 상태 판정
```
Chroma 관련 코드는 `dbma.py` 생태계(및 그 백업 스크립트)에만 실질적으로 연결되어 있고,
`core/retrieval.py`/`core/search.py`/`core/ingest.py`/`core/qdrant_init.py` 계열은
전부 Qdrant만 사용한다.

---

## 4. Comparison with Core Architecture

```text
[Legacy] dbma.py 자체 스택
  dbma.py
   ├─ embedding   : embed_text_ollama() — Ollama 직접 호출
   ├─ chunking    : rag_chunk_text() — 자체 청커 (core/chunking_optimizer.py 미사용)
   ├─ storage     : Chroma(get_vector_client/get_collection) + Qdrant(upsert_to_qdrant) 혼재
   ├─ retrieval   : query_qdrant() — 자체 질의 함수, RetrievalEngine 미사용
   └─ generation  : query_rag() 내부에서 Ollama 생성 모델 직접 호출

[Current] ui/ → core/retrieval.py 스택
  ui/pages/research.py
   └─ core/retrieval.py
        ├─ QueryParser / EnhancedQueryParser  : 질의 파싱
        ├─ RetrievalEngine                     : Qdrant 질의 + BM25/TF-IDF + 신학 스코어링
        ├─ ContextAssembler / CitationBuilder  : 응답 조립
        └─ ResponseFormatter / QueryProcessor  : 최종 응답 형식화
```

두 스택은 **임베딩 모델, 청킹 로직, 벡터 저장소, 검색 알고리즘, 생성 방식 전부가 다르다.**
공유되는 것은 오직 `core/processing.py`가 만든 md 산출물(파일 시스템 경로)뿐이며,
그마저도 `dbma.py`는 `read_indexable_docs()`로 별도 로딩한다. 사실상 두 개의
독립된 애플리케이션이 하나의 저장소에 공존하는 구조다.

---

## 5. Legacy Components

| Component | Classification | 근거 |
|---|---|---|
| `dbma.py` (전체) | **legacy — archive candidate** | v1.1.0 CHANGELOG가 명시적으로 "deprecated" 선언, 그러나 최근(2026-07-15)까지 수정됨 → "죽지 않은 legacy" |
| `query_rag()` | **migrate** | `RetrievalEngine`/`QueryProcessor` 계약으로 흡수, 응답 생성 로직은 별도 Generation 계층으로 분리 필요 |
| `build_rag_store()` | **migrate 또는 remove** | `core/ingest.py`+`core/embedder.py` 경로로 흡수 가능한 기능(청킹→임베딩→색인); 자체 노이즈필터(`_rag_noise`)는 `core/utils.calculate_noise_score`와 통합 검토 |
| `embed_text_ollama()` | **migrate 또는 remove** | 임베딩 모델을 Ollama로 고정하는 레거시 경로. `core/embedder.py`가 이미 임베딩 책임을 갖고 있으므로 중복. Ollama 지원이 여전히 필요한 요구사항인지 먼저 확인 |
| `upsert_to_qdrant()`, `query_qdrant()` (dbma.py 내부) | **remove (중복)** | `core/ingest.py::insert()`, `core/search.py::search()`와 기능 중복 |
| `get_vector_client()`, `get_collection()`, `_qdrant_available()` (dbma.py) | **remove (중복)** | `core/runtime_state.py`가 이미 인덱싱/가용성 상태 판정을 담당 |
| Chroma references (`CHROMA_COLLECTION`, `CHROMA_PERSIST_DIR`, `scripts/backup_chroma.py`) | **legacy** | 활성 벡터 백엔드는 Qdrant로 확정(core/ 전체가 Qdrant만 사용). Chroma는 `dbma.py` 생태계 전용 잔재 |
| `core/search.py` (경량 검색) | **migrate 또는 absorb** | SPRINT16-B-1에서 이미 지적 — `RetrievalEngine` 계약으로 흡수 대상 (이번 조사로 재확인, dbma.py와는 무관) |
| `README.md`, `.github/instructions/*` 의 `streamlit run dbma.py` 안내 | **문서 legacy** | 코드가 아니라 문서 오류. v1.1.0 공식 가이드와 불일치 |

---

## 6. Migration Recommendation

1. **먼저 "왜 아직 수정되고 있는가"를 확인한다.** `dbma.py`가 "deprecated" 선언 이후에도
   2026-07-15까지 수정된 이유(예: 특정 사용자가 여전히 `dbma.py`를 직접 구동 중,
   또는 마이그레이션이 완료되지 않아 임시로 병행 유지 중)를 담당자에게 확인하기 전에는
   archive 처리를 실행해서는 안 된다. 이 문서는 판단 근거만 제공하며 삭제/보관 결정은
   내리지 않는다.
2. **문서 정합성부터 정정**: `README.md`와 `.github/instructions/*`의 `streamlit run dbma.py`
   안내를 `streamlit run ui/app.py`로 맞추는 작업은 코드 변경 없이 가능한 저위험 선행 작업이다
   (단, 이번 스프린트의 "docs/architecture/만 수정" 범위 밖이므로 별도 티켓으로 분리 필요).
3. **`query_rag`/`build_rag_store` 마이그레이션 순서**: (a) Retrieval 부분은
   `core/retrieval.py::RetrievalEngine`으로, (b) Generation(LLM 호출) 부분은
   현재 `RetrievalEngine`에 없는 신규 책임이므로 별도 Generation 계층 설계가 필요,
   (c) Ingestion(`build_rag_store`)은 `core/ingest.py`+`core/embedder.py`로 흡수.
4. **Chroma 참조 제거는 벡터 백엔드 단일화(Qdrant) 확정 이후에** 진행한다 —
   `scripts/backup_chroma.py`가 여전히 유효한 백업 대상을 갖고 있는지(실제 운영 중인
   Chroma 인스턴스가 있는지) 먼저 확인해야 한다.
5. **`dbma.py` 자체는 즉시 삭제하지 말고 "archive candidate"로 표시만 한다.**
   deprecated 선언과 실제 유지보수 활동 사이의 모순이 해소되기 전까지는 active
   사용자가 있을 가능성을 배제할 수 없다.

---

## 7. Impact on SPRINT16-C DocumentContext

- **DocumentContext의 정본 파이프라인 정의에서 `dbma.py`의 자체 청킹(`rag_chunk_text`)과
  노이즈 필터(`_rag_noise`)는 제외**하고 `core/chunking_optimizer.py` + `core/utils.py`
  경로만을 기준으로 설계해야 한다. `dbma.py` 경로는 병행 존재가 확인됐지만
  "target" 아키텍처에는 포함하지 않는다.
- **ExecutionContext가 흡수해야 할 상태 판정 함수 목록이 이번 조사로 확정됐다**:
  `dbma.py`의 `get_vector_client()`, `get_collection()`, `_qdrant_available()`
  세 함수가 `core/runtime_state.py`의 책임과 충돌 없이 대체 가능한지 SPRINT16-C에서
  명시적으로 설계에 반영해야 한다.
- **Retrieval Engine Authority는 이미 SPRINT16-B-1에서 `core/retrieval.py::RetrievalEngine`으로
  확정됐다.** 이번 조사는 그 결정에 반하는 새로운 증거를 발견하지 못했으며, 오히려
  `dbma.py`의 `query_rag`가 외부에서 전혀 참조되지 않는 self-contained 코드임을
  확인함으로써 **마이그레이션 시 외부 호출자를 걱정할 필요가 없다는 안전 신호**를 추가했다.
- **미해결 리스크**: `dbma.py`가 여전히 active하게 수정되고 있다는 사실은
  DocumentContext 설계 착수 시점에 "이 레거시 경로를 병행 지원해야 하는가"라는
  질문에 대한 명확한 답 없이 진행하면 재작업 위험이 있다는 뜻이다.
  **SPRINT16-C 착수 전 사람의 판단(정본 확정)이 선행 조건이다.**

---

*본 문서는 SPRINT16-B-2 범위(`docs/architecture/`)에서 읽기 전용 분석으로만 작성되었으며,
`core/`, `ui/`, `scripts/`, `tests/`, `config.yaml`, `dbma.py`는 수정하지 않았다.*
