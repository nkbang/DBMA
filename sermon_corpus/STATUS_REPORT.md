# 설교 본문-제목 대시보드 구축: 작업 기록 및 추후 계획

## 1. 완료된 작업

### 1.1 설계 단계 (2026-07-22 오전)

| 항목 | 내용 | 상태 |
|---|---|---|
| 요구사항 분석 | 설교은행 + 유튜브 데이터 기반 본문-제목 데이터셋 10만 건, 성경 권별/장별 빈도, 핵심 키워드 시각화, 본문-주제 상관관계 통계 | 완료 |
| 아키텍처 설계 | `sermon_corpus/` 패키지 구조 설계 (collector/analyzer/dashboard/schemas) | 완료 |
| 데이터 스키마 | `SermonRecord` 스키마 설계 (record_id, passage_raw, bible_book, chapter_start/end, verse_start/end, title, preacher, church, published_date, source_url, collected_at) | 완료 |
| 플로우차트 | 데이터 흐름: 수집 → 정제 → 분석 → 시각화 플로우차트 작성 | 완료 |

### 1.2 생성된 파일 목록

| 경로 | 유형 | 설명 |
|---|---|---|
| `sermon_corpus/README.md` | 문서 | 플랫폼 전체 문서 (아키텍처, 설치, 실행 방법) |
| `sermon_corpus/config/sources.yml` | 설정 | 데이터 소스 설정 (설교은행, 유튜브, 로컬) |
| `sermon_corpus/__init__.py` | 코드 | 패키지 초기화 |
| `sermon_corpus/collector/__init__.py` | 코드 | collector 패키지 초기화 |
| `sermon_corpus/collector/polite_fetcher.py` | 코드 | 정중한 웹 크롤러 (delay, retry, timeout) |
| `sermon_corpus/collector/sermonbank.py` | 코드 | 설교은행 데이터 수집기 |
| `sermon_corpus/analyzer/__init__.py` | 코드 | analyzer 패키지 초기화 |
| `sermon_corpus/analyzer/frequency.py` | 코드 | 빈도 분석 모듈 (book_frequency, chapter_frequency, testament_distribution) |
| `sermon_corpus/analyzer/keywords.py` | 코드 | 키워드 추출 모듈 (불용어 제거, 키워드 매핑, 카테고리 분류) |
| `sermon_corpus/analyzer/corpus_statistics.py` | 코드 | 코퍼스 통계 모듈 (상관행렬, 핵심 주제, 빈도 집계) |
| `sermon_corpus/dashboard/__init__.py` | 코드 | dashboard 패키지 초기화 |
| `sermon_corpus/dashboard/web_app.py` | 코드 | Streamlit 웹 대시보드 (5개 탭: 개요/빈도/키워드/상관관계/미리보기) |
| `sermon_corpus/dashboard/sermon_dashboard.html` | 코드 | 별도 HTML 대시보드 (Plotly 기반, 샘플 데이터 포함) |
| `scripts/collect_sermonbank.py` | 스크립트 | 설교은행 데이터 수집 실행 스크립트 |
| `scripts/run_sermon_dashboard.py` | 스크립트 | Streamlit 대시보드 실행 스크립트 |
| `docs/SERMON_CORPUS_PLATFORM_DESIGN.md` | 문서 | 전체 설계 문서 (아키텍처, 데이터 흐름, 스키마, API) |
| `docs/SERMON_CORPUS_PLATFORM_FLOWCHART.md` | 문서 | 플로우차트 (수집→정제→분석→시각화) |

### 1.3 주요 구현 내용

#### 데이터 수집 모듈 (`collector/`)
- **PoliteFetcher**: HTTP 요청 간 delay (3초), 재시도 (3회), timeout (30초)
- **SermonBankCollector**: 설교은행 API 연동, 유튜브 채널 목록 관리

#### 통계 분석 모듈 (`analyzer/`)
- **FrequencyAnalyzer**: 
  - `book_frequency()` - 성경 책별 설교 빈도
  - `chapter_frequency()` - 장별 설교 빈도
  - `testament_distribution()` - 구약/신약 분포
- **KeywordExtractor**:
  - `extract_keywords()` - 한국어 불용어 제거 후 키워드 추출
  - `map_to_categories()` - 주제 카테고리 매핑 (믿음, 은혜, 사랑, 기도 등 20개)
- **CorpusStatistics**:
  - `correlation_matrix()` - 본문-키워드 상관행렬
  - `key_themes_per_book()` - 책별 핵심 주제 도출

#### 대시보드 (`dashboard/`)
- **Streamlit 웹앱** (5개 탭):
  1. 전체 개요: 총 설교 수, 성경 구조 파이 차트
  2. 설교 빈도: 권별 막대차트, 장별 막대차트, 구약 vs 신약 비교
  3. 키워드 분석: 트리맵, 주제 카테고리 파이 차트
  4. 본문-주제 상관관계: 책별 핵심 주제, 상관행렬 히트맵
  5. 데이터 미리보기: 샘플 제목 목록 (Top 50)

- **HTML 대시보드** (Plotly 기반):
  - 동일한 5개 탭 구조
  - 샘플 데이터 100건 내장 (파일 업로드 지원)
  - 다크 테마 UI

## 2. 추후 계획

### Phase 1: 실제 데이터 수집 (우선순위 1)

| 단계 | 작업 | 예상 기간 | 상태 |
|---|---|---|---|
| 1.1 | 설교은행 API 연동 테스트 | 1일 | 미시작 |
| 1.2 | YouTube API 키 발급 및 연동 | 2일 | 미시작 |
| 1.3 | 10만 건 데이터 수집 및 저장 (`sermon_corpus/data/sermon_corpus.jsonl`) | 3일 | 미시작 |
| 1.4 | 데이터 정제 (중복 제거, 본문 정규화) | 2일 | 미시작 |

### Phase 2: 분석 고도화 (우선순위 2)

| 단계 | 작업 | 예상 기간 | 상태 |
|---|---|---|---|
| 2.1 | 본문-주제 상관관계 알고리즘 개선 (TF-IDF 기반) | 3일 | 미시작 |
| 2.2 | 시계열 설교 빈도 분석 추가 | 2일 | 미시작 |
| 2.3 | 교회별/설교자별 비교 분석 기능 | 2일 | 미시작 |
| 2.4 | 핵심 진리 추출 알고리즘 설계 | 5일 | 미시작 |

### Phase 3: 대시보드 고도화 (우선순위 3)

| 단계 | 작업 | 예상 기간 | 상태 |
|---|---|---|---|
| 3.1 | 실제 데이터 연동 (JSONL 파일 읽기) | 1일 | 미시작 |
| 3.2 | 인터랙티브 필터링 (기간, 성경 책, 주제) | 2일 | 미시작 |
| 3.3 | CSV/JSON 내보내기 기능 | 1일 | 미시작 |
| 3.4 | 모바일 반응형 UI 개선 | 2일 | 미시작 |

### Phase 4: 배포 및 운영 (우선순위 4)

| 단계 | 작업 | 예상 기간 | 상태 |
|---|---|---|---|
| 4.1 | 서버 배포 (Streamlit Cloud 또는 자체 서버) | 2일 | 미시작 |
| 4.2 | 자동 데이터 갱신 스케줄러 설정 | 1일 | 미시작 |
| 4.3 | 사용자 매뉴얼 작성 | 1일 | 미시작 |
| 4.4 | 성능 테스트 및 최적화 | 2일 | 미시작 |

## 3. 기술 스택

| 구분 | 기술 | 비고 |
|---|---|---|
| 언어 | Python 3.11+ | DBMA 가상환경 (`~/envs/dbma311`) |
| 데이터 수집 | requests, yt-dlp | 설교은행 API, YouTube |
| 분석 | pandas, numpy, scikit-learn | 빈도, TF-IDF, 상관관계 |
| 시각화 | plotly, streamlit | 인터랙티브 대시보드 |
| 저장 | JSONL | 10만 건 규모 |

## 4. 주요 결정 사항

1. **데이터 형식**: JSONL (줄바꿈 구분 JSON) - 대용량 데이터 처리에 적합
2. **시각화**: Plotly (인터랙티브 차트) + Streamlit (웹 앱)
3. **키워드 매핑**: 한국어-영어 매핑 테이블 (KOREAN_KEYWORD_MAP) 기반 주제 분류
4. **상관관계**: 본문(성경 책×장) × 주제 카테고리 상관행렬

## 5. 알려진 제한사항

1. 현재 대시보드는 **샘플 데이터** 100건으로 동작
2. 실제 데이터 수집을 위해서는 YouTube API 키 발급 필요
3. 키워드 추출은 단순 매칭 방식 (TF-IDF 고도화 필요)
4. 본문-주제 상관관계는 빈도 기반 단순 계산 (통계적 유의미성 검증 필요)

## 6. 다음 단계 권장사항

1. **YouTube API 키 발급** → 실제 설교 채널 데이터 수집 시작
2. **설교은행 API 연동 테스트** → 데이터 소스 다양화
3. **10만 건 샘플 데이터 생성** → 대시보드 실제 데이터 연동 테스트
4. **TF-IDF 기반 키워드 추출** → 통계적 정확도 향상