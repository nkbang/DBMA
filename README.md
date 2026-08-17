# 내서재 (NAE)

문서 기반 메모리 어시스턴트. 다양한 형식의 문서를 처리하고 RAG(Retrieval-Augmented Generation) 기반 검색·채팅 기능을 제공합니다.

DBMA는 내부 engineering identifier입니다(repository, 소스 코드, 설정 키 등에서 계속 사용).

**현재 버전**: `1.3.0` (`config.yaml::app.version` 기준)

---

## UI 페이지 (9개)

Streamlit UI에서 다음 9개 페이지를 제공합니다:

| # | 페이지 | 설명 |
|---|--------|------|
| 1 | **Dashboard** | 사용자용 통계 대시보드 (처리된 문서 수, 진행 상황 등) |
| 2 | **Library** | 처리된 문서 라이브러리 조회 |
| 3 | **Processing** | 문서 업로드 및 처리 진행 관리 |
| 4 | **Research** | 문서 기반 연구 검색 |
| 5 | **Chat** | RAG 기반 채팅 (질문 → 문서 인용 답변) |
| 6 | **설교문 작성** | 설교문 자동 생성 |
| 7 | **설교 리뷰** | 설교문 검토 및 피드백 |
| 8 | **Monitor** | 시스템 모니터링 (로그, 처리 상태, 성능 지표) |
| 9 | **도움말** | 사용 가이드 및 FAQ |

---

## 주요 기능

- **다양한 문서 형식 지원**: PDF, TXT, MD, DOCX, EPUB, HTML, RTF
- **문서 청킹 및 최적화**: 문서를 적절한 크기로 분할하고 최적화된 청킹 전략 적용
- **RAG 검색**: TSU dataset + in-memory 유사도 검색 (production authority)
  - ChromaDB / Qdrant는 legacy corpus history로만 보존되며, 현재 검색 경로에서 쿼리되지 않음
- **Citation / Provenance 표시**: 검색 결과에 author, source_title, evidence_confidence 포함
- **설교문 생성 및 리뷰**: LLM 기반 설교문 작성·검토 파이프라인
- **다국어 지원**: 헬라어, 히브리어, 영어, 한국어, 라틴어
- **OCR 지원**: 스캔된 PDF 문서의 텍스트 추출
- **설정 중앙화**: `config.yaml`에서 모든 설정 관리

---

## 의존성

```bash
pip install -r requirements.txt
```

---

## 설치 및 실행

자세한 설치 절차는 [INSTALL.md](INSTALL.md)를 참조하세요.

간략히:

1. Python 3.11+ 준비
2. Ollama 설치 + 임베딩 모델 (`bge-m3:latest`) pull
3. `pip install -r requirements.txt`
4. `streamlit run dbma_ui.py`

---

## 테스트

```bash
python -m pytest tests/ -v
```

주요 테스트 파일:
- `tests/test_processing_pipeline.py` — 문서 처리 파이프라인 smoke 테스트
- `tests/test_chunking_optimizer.py` — 청킹 최적화 회귀 테스트
- `tests/test_text_normalizer.py` — 텍스트 정규화 테스트
- `tests/test_utils_noise.py` — 노이즈 점수 평가 테스트

---

## 설정

모든 설정은 `config.yaml`에서 관리됩니다:

| 섹션 | 내용 |
|------|------|
| `app` | 앱 이름, 버전 |
| `directories` | RAW/출력/로그/벤치마크 경로 |
| `chunking` | 청크 크기, 오버랩, 최소/최대 크기 |
| `ollama` | 임베딩·생성 모델 옵션 |
| `rag` | 검색 파라미터 (top_k, temperature 등) |
| `ui` | UI 기본값 |

---

## 로그 및 추적

- 프로젝트 이벤트: `logs/project_events.jsonl`
- 진행 상황: `docs/dbmar_todo_progress_board.md`, `docs/dbmar_progress_snapshot.csv`

---

## NAE Public Theology Module (opt-in)

`config.yaml::modules.nae_pd`를 `enabled: true`로 활성화하면 NAE Public Theology corpus 처리 모듈을 사용할 수 있습니다. 기본값은 `false`이며, 활성화 시 별도 corpus 경로와 manifest가 필요합니다.

---

## 개발자 참고

- 아키텍처 상세: `docs/architecture/`
- Metadata Model / ID Governance: `docs/governance/`
- ADR: `docs/adr/`
